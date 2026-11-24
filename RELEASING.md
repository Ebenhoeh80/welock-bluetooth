# Releasing WeLock Smart Lock BLE

How a release is made, step by step, so it does not depend on anyone's memory. Versions follow
[Semantic Versioning](https://semver.org/): a breaking change raises the major version, a new
feature the minor version, a fix the patch version.

## 1. Prepare

1. Check that everything meant for the release is merged to `main` and CI is green.
2. In `CHANGELOG.md`, rename `[Unreleased]` to `[x.y.z] - YYYY-MM-DD` and start a new empty
   `[Unreleased]` section above it. The section's text becomes the release notes.
3. Set the new version in `custom_components/welock_ble/manifest.json`, `pyproject.toml` and `EXPECTED_VERSION` in `tests/test_manifest.py`. The tests assert that all three agree and that `CHANGELOG.md` has a matching, non-empty section.

## 2. Check locally

`scripts/check.sh` (or `powershell -File scripts\check.ps1` on Windows) runs a local subset of the CI steps.
The Home Assistant tests (`tests_ha/`, job `ha-tests`, coverage gate and mypy) run only in the CI or in a Python 3.14 environment with Home Assistant; xenon and mypy are optional locally. Or by hand:

```bash
python -m ruff check custom_components tests tools tests_ha
python -m black --check custom_components tests tests_ha tools
python -m pytest -m "not live"
```
The unit tests run without Home Assistant (it is stubbed). The Home Assistant wiring (entities, options, the unlock path) is checked on a live system after the release; see step 7.

## 3. Pull request

Open a pull request with the changelog and version change, wait for **all** CI checks
(`CI` with `lint-and-test` for Python 3.10–3.13, `ha-tests` with coverage ≥ 95 % and mypy,
`Hassfest validation`, HACS `validate` and CodeQL `analyze`) and squash-merge it.

## 4. Tag

Create the tag on the merge commit of `main` and push it:

```bash
git checkout main && git pull
git tag vX.Y.Z
git push origin vX.Y.Z
```

The tag **must** be `v` plus the version in `manifest.json`. A suffix such as `-rc.1` makes it a
pre-release (set the same suffix in the manifest version).

## 5. What the workflow does

The tag starts `.github/workflows/release-zip.yml`, which calls the shared workflow in
[`Ebenhoeh80/.github`](https://github.com/Ebenhoeh80/.github). It checks that the tag matches the
manifest version, builds `welock_ble.zip` (integration files at the zip root, as HACS expects with
`zip_release`), and creates or updates the GitHub release with the matching changelog section and
the zip attached. If the tag and the version differ, the workflow fails and nothing is published.

## 6. Verify the release

- The release page shows the changelog text and the `welock_ble.zip` asset.
- HACS offers the new version (use *Update information* on the repository if it is slow).

## 7. Update and check a live system

Take a Home Assistant backup first. Then update through HACS, restart Home Assistant, and check that
the lock (`lock.<name>`) is available, the unlock counters and the unlock history record the new version's attempts, and a few real unlocks work (look at the knob).

## 8. After the release

- If the repository is in the HACS default catalog and a review asked for the change, answer in the
  pull request there.
- Ask yourself whether the README, the translations and the roadmap section still match.
