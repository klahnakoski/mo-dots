# todo

- Register `.github/workflows/publish.yml`, environment `pypi`, as a Trusted Publisher on pypi.org (mo-dots → Manage → Publishing); until then its publish step is refused.
- mo-deploy's pypi() still twines `dist/*`; for this repo it should push the release tag to master and `gh workflow run publish.yml --ref <tag>` instead (publish.yml refuses any other ref). A release mixing twine uploads with the workflow's shows "Incomplete Provenance". See https://docs.pypi.org/attestations/producing-attestations/
