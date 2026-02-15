# Release Candidate Build (mission-1771186081212)

Date: 2026-02-16

## Build

Commands run:
- `python -m build`
- `powershell -File scripts/build_rc.ps1 -SkipBuild`

Result:
- sdist and wheel built successfully under `dist/`.
- SHA256 manifest written:
  - `reports/launch-readiness/mission-1771186081212/rc/rc_build_manifest.json`

## Notes

- Removed setuptools deprecation warnings by switching to SPDX license string in `pyproject.toml` and removing deprecated license classifier.
- `start_spark.bat` entrypoint calls `python -m spark.cli up` and then prints service status.
