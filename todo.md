# todo

- Add `.github/workflows/publish.yml`: on dispatch, CI builds the sdist, the pure wheel and the windows/macos/linux binary wheels (no tests), then publishes all of them to PyPI with `pypa/gh-action-pypi-publish@release/v1` (`id-token: write`), so releases carry attestations and show "Full provenance". Register the workflow as a Trusted Publisher on pypi.org (Manage → Publishing). Every file in a release must go through it; a mix with twine token uploads shows "Incomplete Provenance". See https://docs.pypi.org/attestations/producing-attestations/
