# Toolkit Integration CI Design

## Purpose
This document designs how changes should run tests that depend on digitone-syx-toolkit.

It does not implement CI changes.

## Current state
Current behavior in changes:

- normal changes tests do not require toolkit
- toolkit-dependent tests use pytest.importorskip
- this avoids local failures when toolkit is not installed
- but important integration behavior may be skipped in CI

Observed CI baseline in this repository:

- .github/workflows/pytest.yml exists
- current job runs pytest -q after pip install '.[test]'
- toolkit is not installed in that workflow
- therefore toolkit-dependent tests can be skipped silently

## Current toolkit-dependent test inventory
Primary Track 8 toolkit-dependent tests in current scope are listed below.

| Test file | Toolkit module required | What it validates | Current skip behavior | Product relevance |
|---|---|---|---|---|
| tests/test_track8_toolkit_loader_validation.py | digitone_syx_toolkit.events_yaml | real loader validation of generated Track 8 events YAML | pytest.importorskip("digitone_syx_toolkit.events_yaml") | high |
| tests/test_track8_sysex_export.py | digitone_syx_toolkit.events_to_syx | SysEx bytes generation and determinism for Track 8 flow | pytest.importorskip("digitone_syx_toolkit.events_to_syx") | high |
| tests/test_track8_fixture_generation.py | digitone_syx_toolkit.events_to_syx | fixture writer optional real toolkit path and .syx generation | pytest.importorskip("digitone_syx_toolkit.events_to_syx") | medium-high |
| tests/test_track8_product_like_fixture_generation.py | digitone_syx_toolkit.events_yaml and digitone_syx_toolkit.events_to_syx | product-like fixture validation and optional real .syx generation | pytest.importorskip("digitone_syx_toolkit.events_yaml") and pytest.importorskip("digitone_syx_toolkit.events_to_syx") | high |

Notes:

- Additional toolkit-related tests exist outside this Phase R2 minimum list.
- This design document focuses on the required Track 8 product-relevant inventory.

## Test categories
### Core tests

- no toolkit dependency
- must run on every PR
- must block merge

### Toolkit integration tests

- require digitone-syx-toolkit
- validate loader and SysEx generation
- should run in CI once dependency setup is available
- should eventually block product export PRs

### Fixture artifact tests

- verify committed fixtures exist and match contracts
- may not need toolkit if checking static files
- should run on every PR

### Hardware/manual tests

- require Digitone II
- not suitable for normal CI
- should remain manual validation logs

## CI strategy options
### Option A: Continue optional skip only
Description:

- keep current importorskip behavior
- no CI change

Pros:

- zero setup
- no secrets
- no cross-repo checkout

Cons:

- important tests may be skipped silently
- weak confidence before Phase 5B

### Option B: Add separate toolkit integration CI job
Description:

- keep normal test job unchanged
- add second job
- checkout emnyeca/changes
- checkout emnyeca/digitone-syx-toolkit
- install both editable
- run toolkit-dependent tests

Pros:

- clear separation
- normal tests remain fast
- integration becomes visible
- no monorepo needed

Cons:

- workflow complexity
- cross-repo checkout permissions
- possible branch/ref coordination problem

### Option C: Manual workflow dispatch
Description:

- add workflow that can be run manually
- installs toolkit and runs integration tests

Pros:

- low pressure
- useful before releases and reviews

Cons:

- not automatic
- can be forgotten

### Option D: Scheduled integration workflow
Description:

- nightly or weekly integration job
- installs toolkit main and runs integration tests

Pros:

- detects drift between repos

Cons:

- may fail unrelated to active PR
- does not protect each PR

### Option E: Pin toolkit as dependency
Description:

- changes CI installs a pinned toolkit ref or version
- integration tests run as normal

Pros:

- reproducible
- closer to product packaging

Cons:

- requires dependency/version policy
- still cross-repo release friction

## Recommendation
Short term:

- Add a separate toolkit integration CI job in a later implementation phase.
- Keep normal core pytest job unchanged.
- The integration job should checkout both repositories and install both editable.
- Initially run on pull_request and workflow_dispatch.
- It may be non-required and advisory for the first iteration.

Medium term:

- Make toolkit integration job required for Track 8 export-related PRs.
- Consider scheduled drift detection against toolkit main.
- Revisit pinned dependency or monorepo after Phase 5B/5C.

Why this recommendation:

- preserves current fast core CI behavior
- makes currently skipped integration behavior explicit in CI
- matches current dependency direction (changes -> digitone-syx-toolkit)
- avoids premature repository topology changes

## Proposed CI job shape
This is a design example only and is not implemented in Phase R2.

```yaml
name: tests

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .
      - run: python -m pytest

  toolkit-integration:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout changes
        uses: actions/checkout@v4
        with:
          path: changes

      - name: Checkout digitone-syx-toolkit
        uses: actions/checkout@v4
        with:
          repository: emnyeca/digitone-syx-toolkit
          path: digitone-syx-toolkit

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: python -m pip install -e ./digitone-syx-toolkit
      - run: python -m pip install -e ./changes
      - run: python -m pytest tests/test_track8_toolkit_loader_validation.py tests/test_track8_sysex_export.py tests/test_track8_fixture_generation.py tests/test_track8_product_like_fixture_generation.py
        working-directory: changes
```

Implementation note:

- At CI implementation time, use currently supported action versions in repository workflows.

## Branch/ref policy
Toolkit ref selection options:

1. main
2. pinned SHA
3. matching branch name if it exists
4. manual workflow_dispatch input toolkit_ref

Recommendation:

Initial CI:

- use toolkit main for drift detection and product reality

Release and product stabilization:

- pin toolkit ref or version

Cross-repo feature development:

- allow workflow_dispatch input for toolkit_ref

## Failure policy
Staged policy:

Stage 1:

- toolkit integration CI is advisory and non-required

Stage 2:

- required for PRs touching:
  - src/changes/digitone/
  - tests/test_track8_*.py
  - examples/generated/track8_*
  - docs/track8-*
  - docs/hardware-validation/track8-*

Stage 3:

- required for all PRs once Track 8 export becomes product feature

Do not implement path filtering in Phase R2.

## Local developer workflow
From D:\emnye\Documents\GitHub\changes:

```powershell
python -m pip install -e .
python -m pip install -e ..\digitone-syx-toolkit
python -m pytest tests/test_track8_toolkit_loader_validation.py tests/test_track8_sysex_export.py tests/test_track8_fixture_generation.py tests/test_track8_product_like_fixture_generation.py -q
```

Optional full test run:

```powershell
python -m pytest -q
```

## Marker policy
Possible future marker:

toolkit_integration

Recommendation:

- Do not add marker in R2.
- Consider adding marker in CI implementation phase if file-level selection becomes brittle.

Rationale:

- current file-level selection is explicit and low-risk
- marker changes require touching tests and pytest config

## Relationship to Phase 5B
- Phase 5B will add minimal explicit Track 8 export API.
- Before or during Phase 5B implementation, toolkit integration CI should be planned.
- CI implementation can be Phase R2B or Phase R2-impl.
- R2 design should not block Phase 5B design, but should inform its test strategy.

## SPEC-OPEN items
- exact workflow file name
- whether integration job blocks all PRs immediately
- whether toolkit ref should be main or pinned SHA initially
- whether private repo checkout needs additional token configuration
- whether to use file-level test selection or pytest marker
- whether to split loader tests and SysEx generation tests
- whether to upload generated .syx artifacts from CI
- whether to add scheduled drift detection

## Non-goals
This phase does not:

- modify GitHub Actions
- add pytest markers
- modify runtime code
- modify pyproject
- add dependencies
- modify toolkit
- generate fixtures
- change test behavior

## Acceptance criteria
This document is acceptable if:

1. It inventories toolkit-dependent tests.
2. It defines test categories.
3. It compares CI strategy options A-E.
4. It recommends a short-term CI strategy.
5. It defines proposed CI job shape.
6. It defines branch/ref policy.
7. It defines failure policy.
8. It defines local developer workflow.
9. It lists SPEC-OPEN items.
10. It makes no runtime or CI changes.
