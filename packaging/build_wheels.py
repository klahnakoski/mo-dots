#!/usr/bin/env python
"""Fill dist/ with everything a release uploads: sdist, pure wheel, binary wheels.

Ported from mo-black's packaging/deploy.py, minus mypyc, versioning and upload:
mo-deploy owns the version (baked into packaging/setup.py) and the twine step.
Run standalone to rehearse a release; mo-deploy runs it in pypi() because this
file exists.

- sdist: setup.py with the C extension optional=True, so a source install
  compiles when it can and falls back to pure python when it cannot
- pure wheel (py3-none-any): no extension; what pip takes on platforms with no
  binary wheel (macos - CI wheels need a Mac), same behavior as before
- binary wheels: cibuildwheel, windows natively, linux via docker; every wheel
  runs the smoke (C accelerator asserted active) then the full suite, except
  aarch64 under qemu which keeps the smoke only
- macos wheels: --github dispatches .github/workflows/wheels.yml (which builds
  on real Macs), waits, and downloads just the macos artifacts into dist/; the
  ref must be pushed and carry the same version as packaging/setup.py

    python packaging/build_wheels.py                    # everything local
    python packaging/build_wheels.py --github           # plus macos, via gh
    python packaging/build_wheels.py --only cp313-win_amd64
    python packaging/build_wheels.py --skip-linux       # no docker
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SETUP = ROOT / "setup.py"
PACKAGING = ROOT / "packaging"

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
    requires = " ".join(
        line.strip()
        for line in (ROOT / "tests" / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
    return {
        **CIBW_ENV,
        "CIBW_TEST_SOURCES": "tests",
        "CIBW_TEST_REQUIRES": requires,
        # THE REQUIRES ARE MANAGED PACKAGES PINNING mo-dots==<LAST RELEASE>,
        # AND pip INSTALLS THEM AFTER THE WHEEL: REINSTALL THE WHEEL LAST
        # (SAME REASON mo-deploy run_tests INSTALLS SELF AGAIN)
        "CIBW_TEST_COMMAND": (
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


def said(*args):
    """RUN CAPTURED; ANSWER (returncode, stdout)"""
    done = subprocess.run(
        [str(a) for a in args], cwd=ROOT, capture_output=True, text=True,
    )
    return done.returncode, done.stdout.strip()


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
    shutil.rmtree(scratch, ignore_errors=True)
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
    shutil.rmtree(scratch, ignore_errors=True)


def gen_setup(extension):
    """WRITE ROOT setup.py; extension IS none, optional OR required"""
    shutil.copyfile(PACKAGING / "setup.py", SETUP)
    if extension == "none":
        return
    args = [sys.executable, PACKAGING / "add_speedups.py", SETUP]
    if extension == "required":
        args.append("--required")
    if run(*args):
        sys.exit("add_speedups failed")


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


def main():
    parse = argparse.ArgumentParser(description=__doc__)
    parse.add_argument("--only", default="", metavar="ID", help="one cibuildwheel identifier, eg cp313-win_amd64")
    parse.add_argument("--skip-linux", action="store_true", help="build no linux wheels; docker not needed")
    parse.add_argument(
        "--github", nargs="?", const="", default=None, metavar="REF",
        help="also build macos on github: dispatch wheels.yml on REF (default: current branch), wait, download",
    )
    args = parse.parse_args()

    if run(sys.executable, "-m", "pip", "install", "--quiet", "build", "cibuildwheel"):
        sys.exit("pip install build cibuildwheel failed")

    # DISPATCH FIRST, SO THE MACS BUILD WHILE THIS MACHINE DOES
    github_run = None
    if args.github is not None:
        ref = args.github
        if not ref:
            rc, ref = said("git", "rev-parse", "--abbrev-ref", "HEAD")
            if rc or not ref:
                sys.exit("cannot name the current branch for --github")
        github_run = dispatch_github(ref)

    shutil.rmtree(DIST, ignore_errors=True)
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    for egg in ROOT.glob("*.egg-info"):
        shutil.rmtree(egg, ignore_errors=True)
    # SAME EXCLUSIONS mo-deploy WRITES, SO A REHEARSAL SDIST MATCHES A RELEASE
    (ROOT / "MANIFEST.in").write_text("global-exclude tests/*\nglobal-exclude MANIFEST.in\n")

    try:
        gen_setup("none")
        if run(sys.executable, "-m", "build", "--wheel"):
            sys.exit("pure wheel failed")

        gen_setup("optional")
        if run(sys.executable, "-m", "build", "--sdist"):
            sys.exit("sdist failed")
        if not sdist_has_speedups():
            sys.exit("sdist is missing mo_dots/_speedups.c; source installs would be pure-only")

        gen_setup("required")
        if args.only:
            env = CIBW_ENV if "aarch64" in args.only else suite_env()
            if run(sys.executable, "-m", "cibuildwheel", ".", f"--only={args.only}", "--output-dir", DIST, add_env=env):
                sys.exit(f"cibuildwheel {args.only} failed")
        else:
            for platform in buildable_platforms(args.skip_linux):
                if platform == "linux":
                    runs = [
                        {**suite_env(), "CIBW_ARCHS_LINUX": "x86_64"},
                        # aarch64 COMPILES AND SMOKES UNDER qemu (docker desktop binfmt)
                        {**CIBW_ENV, "CIBW_ARCHS_LINUX": "aarch64"},
                    ]
                else:
                    runs = [suite_env()]
                for env in runs:
                    if run(sys.executable, "-m", "cibuildwheel", ".", "--platform", platform, "--output-dir", DIST, add_env=env):
                        sys.exit(f"cibuildwheel {platform} failed")
    finally:
        SETUP.unlink(missing_ok=True)
        (ROOT / "MANIFEST.in").unlink(missing_ok=True)

    if github_run:
        collect_github(github_run)

    made = sorted(p.name for p in DIST.iterdir())
    print("\n".join(["built:", *("    " + name for name in made)]))

    expected = ["-py3-none-any.whl", ".tar.gz"]
    if github_run:
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
