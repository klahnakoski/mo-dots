#!/usr/bin/env python
"""Fill dist/ with everything a release uploads: sdist, pure wheel, binary wheels.

Ported from mo-black's packaging/deploy.py, minus mypyc, versioning and upload:
mo-deploy owns the version (stamped into packaging/setuptools.json) and the
twine step; its translator (the synced copy packaging/gen_setup.py) renders
setup.py.
Run standalone to rehearse a release; mo-deploy runs it in pypi() because this
file exists.

- sdist: setup.py with the C extension optional=True, so a source install
  compiles when it can and falls back to pure python when it cannot
- pure wheel (py3-none-any): no extension; what pip takes on platforms with no
  binary wheel (macos - CI wheels need a Mac), same behavior as before
- binary wheels: cibuildwheel, windows natively, linux via docker; every wheel
  runs the smoke (C accelerator asserted active) then the full suite, except
  aarch64 under qemu which keeps the smoke only. One cibuildwheel call per
  identifier, --jobs at a time, each in its own mo-files TempDirectory copy of
  the tree
- macos wheels: --github dispatches .github/workflows/wheels.yml (which builds
  on real Macs), waits, and downloads just the macos artifacts into dist/; the
  ref must be pushed and carry the same version as packaging/setup.py. It goes
  out only after every local wheel has passed, so a broken matrix spends no
  github run; the macs then build their own matrix in parallel

    python packaging/build_wheels.py                    # everything local
    python packaging/build_wheels.py --github           # plus macos, via gh
    python packaging/build_wheels.py --only cp313-win_amd64
    python packaging/build_wheels.py --skip-linux       # no docker
    python packaging/build_wheels.py --jobs 2           # narrower matrix
"""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import tarfile
import threading
import time
from contextlib import ExitStack
from pathlib import Path

# NEEDS mo-files IN THE BUILD PYTHON (mo-deploy USES python["latest"]): WINDOWS
# HOLDS A DIRECTORY FOR A WHILE AFTER THE LAST HANDLE CLOSES, AND TempDirectory
# DELETES IN A THREAD THAT KEEPS RETRYING INSTEAD OF FAILING THE BUILD
from mo_files import File, TempDirectory

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SETUP = ROOT / "setup.py"

# SAME ASSERTION AS .github/workflows/wheels.yml: THE C ACCELERATOR IS ACTIVE.
# Data(a=42) EXERCISES object.__setattr__-VIA-_set, WHICH TRIPPED CPython's
# hackcheck ON 3.8-3.12; w['.']=[1] EXERCISES THE __class__ REASSIGNMENT
SMOKE = (
    'python -c "import mo_dots; '
    "assert type(mo_dots.to_data).__name__ == 'builtin_function_or_method'; "
    "d = mo_dots.to_data({'a': {'b': 1}}); "
    "assert d.a.b == 1; assert d.x.y == None; "
    "w = mo_dots.Data(a=42); assert w.a == 42; "
    "w['.'] = [1]; assert list(w) == [1]\""
)

CIBUILDWHEEL_PLATFORM = {"win32": "windows", "darwin": "macos", "linux": "linux"}

CIBW_ENV = {
    # NO musllinux: ONE IMAGE PER ARCH; ALPINE INSTALLS FALL BACK TO THE SDIST
    "CIBW_SKIP": "pp* *musllinux*",
    "CIBW_TEST_COMMAND": SMOKE,
    "CIBW_BUILD_VERBOSITY": "1",
    # KEEP OUTPUT LINE-Y: mo-deploy KILLS A COMMAND SILENT FOR TOO LONG
    "PIP_PROGRESS_BAR": "off",
}


def suite_env():
    """FULL SUITE AGAINST THE INSTALLED WHEEL; THE SMOKE STAYS AS LINE ONE.

    EVERY WHEEL RUNS THE FULL SUITE, EXERCISING THE C CODE ON EACH os AND
    python. ONLY aarch64 UNDER qemu KEEPS THE SMOKE - THE SUITE EMULATED
    ADDS HOURS.
    """
    return {
        **CIBW_ENV,
        "CIBW_TEST_SOURCES": "tests",
        # tests/install_locked.py, NOT CIBW_TEST_REQUIRES OR -r requirements.txt:
        # THE MANAGED PACKAGES PIN EACH OTHER WITH ==, SO ANY RESOLVE OF THE
        # FLOORS IS ResolutionImpossible THE MOMENT TWO GENERATIONS MIX. THE
        # LOCK IS WHAT run_tests PROVED, AND THE HELPER PICKS THE ONE FOR THE
        # WHEEL'S OWN python - ALSO NOTHING FOR cmd TO EAT.
        # THE LOCK PINS mo-dots==<LAST RELEASE>: REINSTALL THE WHEEL LAST
        # (SAME REASON mo-deploy run_tests INSTALLS SELF AGAIN)
        "CIBW_TEST_COMMAND": (
            "python tests/install_locked.py && "
            'python -m pip install --quiet --force-reinstall --no-deps "{wheel}" && '
            + SMOKE
            + " && python -m unittest discover -s tests -t ."
        ),
    }


def run(*args, add_env=None):
    print("+ " + " ".join(str(a) for a in args), flush=True)
    done = subprocess.run(
        [str(a) for a in args], cwd=ROOT, env={**os.environ, **(add_env or {})},
    )
    return done.returncode


def said(*args, add_env=None):
    """RUN CAPTURED; ANSWER (returncode, stdout)"""
    done = subprocess.run(
        [str(a) for a in args], cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, **(add_env or {})},
    )
    return done.returncode, done.stdout.strip()


SAY = threading.Lock()


def run_tagged(tag, *args, add_env=None, cwd=None):
    """RUN WITH EVERY LINE TAGGED, SO PARALLEL BUILDS READ AS SEPARATE STREAMS.

    STREAMED, NOT CAPTURED AT THE END: mo-deploy KILLS A COMMAND THAT GOES
    SILENT, AND A WHEEL TAKES MINUTES
    """
    with SAY:
        print(f"+ [{tag}] " + " ".join(str(a) for a in args), flush=True)
    proc = subprocess.Popen(
        [str(a) for a in args], cwd=cwd or ROOT, env={**os.environ, **(add_env or {})},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    for line in proc.stdout:
        with SAY:
            print(f"[{tag}] " + line.rstrip(), flush=True)
    return proc.wait()


def newest_github_run(ref):
    rc, out = said(
        "gh", "run", "list", "--workflow", "wheels.yml", "--branch", ref,
        "--limit", "1", "--json", "databaseId,status,conclusion",
    )
    if rc:
        sys.exit("gh run list failed; is gh authenticated?")
    runs = json.loads(out or "[]")
    return runs[0] if runs else None


def dispatch_github(ref):
    """START THE macos BUILD ON GITHUB; ANSWER THE RUN ID TO COLLECT LATER"""
    before = (newest_github_run(ref) or {}).get("databaseId")
    if run("gh", "workflow", "run", "wheels.yml", "--ref", ref):
        sys.exit(f"could not dispatch wheels.yml on {ref}; is {ref} pushed?")
    for _ in range(20):
        time.sleep(6)
        now = newest_github_run(ref)
        if now and now["databaseId"] != before:
            print(f"github run {now['databaseId']} started on {ref}", flush=True)
            return now["databaseId"]
        print("waiting for the github run to appear", flush=True)
    sys.exit("dispatched, but no new run appeared on " + ref)


def collect_github(run_id, deadline_minutes=30):
    """WAIT FOR THE RUN; COPY ITS macos WHEELS INTO dist/"""
    deadline = time.monotonic() + deadline_minutes * 60
    while True:
        rc, out = said("gh", "run", "view", str(run_id), "--json", "status,conclusion")
        if rc:
            sys.exit(f"gh run view {run_id} failed")
        state = json.loads(out)
        if state["status"] == "completed":
            break
        if time.monotonic() > deadline:
            sys.exit(f"github run {run_id} still {state['status']} after {deadline_minutes} minutes")
        print(f"github run {run_id}: {state['status']}", flush=True)
        time.sleep(20)
    if state["conclusion"] != "success":
        sys.exit(f"github run {run_id} finished {state['conclusion']}; no macos wheels")

    scratch = ROOT / "build" / "github-wheels"
    File(str(scratch)).delete()
    if run("gh", "run", "download", str(run_id), "--pattern", "wheels-macos-*", "--dir", scratch):
        sys.exit("gh run download failed")
    [sdist] = DIST.glob("*.tar.gz")
    version = sdist.name[len("mo_dots-"):-len(".tar.gz")]
    wheels = sorted(scratch.rglob("*.whl"))
    strangers = [w.name for w in wheels if not w.name.startswith(f"mo_dots-{version}-")]
    if strangers:
        sys.exit(
            f"github built {' '.join(strangers)}, not {version}: "
            "push the version commit before --github"
        )
    for wheel in wheels:
        shutil.copy2(wheel, DIST)
    File(str(scratch)).delete()


def gen_setup():
    """ROOT setup.py: THE SYNCED TRANSLATOR COPY RENDERS packaging/setuptools.json
    (IN-DEPLOY mo-deploy ALREADY WROTE IT). THE EXTENSION IS optional=True;
    THE SMOKE IN EVERY BINARY-WHEEL TEST ASSERTS THE ACCELERATOR, WHICH MAKES
    IT REQUIRED THERE; MO_DOTS_NO_EXTENSIONS DROPS IT FOR THE PURE WHEEL"""
    if SETUP.exists():
        return
    if run(sys.executable, ROOT / "packaging" / "gen_setup.py", ROOT):
        sys.exit("packaging/gen_setup.py failed")


def sdist_has_speedups():
    [sdist] = DIST.glob("*.tar.gz")
    with tarfile.open(sdist) as tar:
        return any(name.endswith("mo_dots/_speedups.c") for name in tar.getnames())


def buildable_platforms(skip_linux):
    """LINUX WHEELS BUILD IN A CONTAINER; macos NEEDS A MAC AND IS NOT HERE"""
    here = CIBUILDWHEEL_PLATFORM[sys.platform]
    found = [here]
    if here != "linux" and not skip_linux:
        if run("docker", "version"):
            sys.exit("docker does not answer; linux wheels need it (or --skip-linux)")
        found.append("linux")
    return found


def build_identifiers(platform, env):
    """CIBUILDWHEEL'S OWN ANSWER TO WHAT IT WOULD BUILD HERE"""
    rc, out = said(
        sys.executable, "-m", "cibuildwheel", ".", "--platform", platform,
        "--print-build-identifiers", add_env=env,
    )
    if rc or not out:
        sys.exit(f"cibuildwheel has no build identifiers for {platform}")
    return out.split()


def wheel_jobs(skip_linux):
    """EVERY LOCAL WHEEL AS (identifier, env), ONE cibuildwheel CALL EACH"""
    jobs = []
    for platform in buildable_platforms(skip_linux):
        if platform == "linux":
            envs = [
                {**suite_env(), "CIBW_ARCHS_LINUX": "x86_64"},
                # aarch64 COMPILES AND SMOKES UNDER qemu (docker desktop binfmt)
                {**CIBW_ENV, "CIBW_ARCHS_LINUX": "aarch64"},
            ]
        else:
            envs = [suite_env()]
        for env in envs:
            jobs.extend((identifier, env) for identifier in build_identifiers(platform, env))
    return jobs


def source_copy(temp):
    """A TREE PER WORKER: cibuildwheel BUILDS IN PLACE, AND build/ AND setup.py
    ARE SHARED STATE THAT CONCURRENT BUILDS OVERWRITE.

    shutil FOR THE COPY, NOT File.copy: THE ignore LIST SKIPS .git, WHICH
    File.copy WOULD WALK BYTE BY BYTE
    """
    where = Path(temp.os_path) / ROOT.name
    shutil.copytree(
        ROOT, where,
        ignore=shutil.ignore_patterns(".git", "build", "dist", "*.egg-info", "__pycache__", ".venv", "venv"),
    )
    return where


def build_matrix(jobs, width):
    """BUILD THE MATRIX width AT A TIME; ANSWER THE IDENTIFIERS THAT FAILED"""

    def one(identifier, env, source):
        return run_tagged(
            identifier, sys.executable, "-m", "cibuildwheel", source,
            f"--only={identifier}", "--output-dir", DIST, add_env=env, cwd=source,
        )

    print(f"{len(jobs)} wheels, {width} at a time", flush=True)
    failed = []
    # EXITING THE TempDirectory HANDS THE TREE TO A PATIENT DELETE THREAD
    with ExitStack() as temps:
        sources = [
            source_copy(temps.enter_context(TempDirectory()))
            for _ in range(min(width, len(jobs)))
        ]
        # THE FIRST ALONE: THE cibuildwheel CACHES (nuget pythons, virtualenv
        # pyz) ARE SHARED, AND A COLD DOWNLOAD RACES
        identifier, env = jobs[0]
        if one(identifier, env, sources[0]):
            return [identifier]

        todo = queue.Queue()
        for job in jobs[1:]:
            todo.put(job)
        stop = threading.Event()

        def worker(source):
            while not stop.is_set():
                try:
                    identifier, env = todo.get_nowait()
                except queue.Empty:
                    return
                if one(identifier, env, source):
                    failed.append(identifier)
                    stop.set()  # NO NEW WORK; THE LIVE BUILDS STILL FINISH

        threads = [threading.Thread(target=worker, args=(source,)) for source in sources]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    return failed


def main():
    parse = argparse.ArgumentParser(description=__doc__)
    parse.add_argument("--only", default="", metavar="ID", help="one cibuildwheel identifier, eg cp313-win_amd64")
    parse.add_argument("--skip-linux", action="store_true", help="build no linux wheels; docker not needed")
    parse.add_argument("--jobs", type=int, default=8, metavar="N", help="how many wheels to build at once")
    parse.add_argument(
        "--github", nargs="?", const="", default=None, metavar="REF",
        help="also build macos on github: dispatch wheels.yml on REF (default: current branch), wait, download",
    )
    args = parse.parse_args()
    if args.jobs < 1:
        sys.exit("--jobs must be at least 1")

    if run(sys.executable, "-m", "pip", "install", "--quiet", "build", "cibuildwheel"):
        sys.exit("pip install build cibuildwheel failed")

    # NAME THE REF NOW, DISPATCH AFTER THE LOCAL WHEELS PASS
    github_ref = None
    if args.github is not None:
        github_ref = args.github
        if not github_ref:
            rc, github_ref = said("git", "rev-parse", "--abbrev-ref", "HEAD")
            if rc or not github_ref:
                sys.exit("cannot name the current branch for --github")

    File(str(DIST)).delete()
    File(str(ROOT / "build")).delete()
    for egg in ROOT.glob("*.egg-info"):
        File(str(egg)).delete()
    # SAME EXCLUSIONS mo-deploy WRITES, SO A REHEARSAL SDIST MATCHES A RELEASE
    (ROOT / "MANIFEST.in").write_text("global-exclude tests/*\nglobal-exclude MANIFEST.in\n")

    try:
        gen_setup()
        if run(sys.executable, "-m", "build", "--wheel", add_env={"MO_DOTS_NO_EXTENSIONS": "1"}):
            sys.exit("pure wheel failed")

        if run(sys.executable, "-m", "build", "--sdist"):
            sys.exit("sdist failed")
        if not sdist_has_speedups():
            sys.exit("sdist is missing mo_dots/_speedups.c; source installs would be pure-only")

        if args.only:
            env = CIBW_ENV if "aarch64" in args.only else suite_env()
            if run(sys.executable, "-m", "cibuildwheel", ".", f"--only={args.only}", "--output-dir", DIST, add_env=env):
                sys.exit(f"cibuildwheel {args.only} failed")
        else:
            failed = build_matrix(wheel_jobs(args.skip_linux), args.jobs)
            if failed:
                sys.exit("cibuildwheel failed: " + " ".join(failed))
    finally:
        SETUP.unlink(missing_ok=True)
        (ROOT / "MANIFEST.in").unlink(missing_ok=True)

    # EVERY LOCAL WHEEL PASSED; THE MACS CAN SPEND A RUN NOW
    if github_ref is not None:
        collect_github(dispatch_github(github_ref))

    made = sorted(p.name for p in DIST.iterdir())
    print("\n".join(["built:", *("    " + name for name in made)]))

    expected = ["-py3-none-any.whl", ".tar.gz"]
    if github_ref is not None:
        expected.append("macosx")
    if not args.only:
        expected.append("-win_amd64.whl")
        if not args.skip_linux:
            expected.append("manylinux")
    missing = [kind for kind in expected if not any(kind in name for name in made)]
    if missing:
        sys.exit("the release would be partial; nothing built for: " + " ".join(missing))


if __name__ == "__main__":
    main()
