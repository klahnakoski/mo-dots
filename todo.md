# todo

- Register `.github/workflows/publish.yml`, environment `pypi`, as a Trusted Publisher on pypi.org (mo-dots → Manage → Publishing); until then its publish step is refused.
- mo-deploy's pypi() still twines `dist/*`; for this repo it should push the version commit and `gh workflow run publish.yml --ref dev` instead. A release mixing twine uploads with the workflow's shows "Incomplete Provenance". See https://docs.pypi.org/attestations/producing-attestations/
