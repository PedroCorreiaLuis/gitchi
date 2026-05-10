# gitchi pet check

A GitHub Action that warns when a pull request is opened against a repo
whose [gitchi](https://github.com/PedroCorreiaLuis/gitchi) pet is looking
unwell — low hunger, low health, or both.

## Usage

Drop this into `.github/workflows/pet-check.yml` in any repository:

```yaml
name: pet check

on:
  pull_request:
    branches: [main]

jobs:
  pet-check:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0   # needed so gitchi can read the root commit
      - uses: PedroCorreiaLuis/gitchi/.github/actions/check-pet@v0.5.0
        with:
          hunger-threshold: 30
          health-threshold: 50
```

The action installs `gitchi` from PyPI, computes the repo's current pet
vitals, and — if hunger or health falls below the configured threshold —
posts a sticky comment on the PR. Subsequent pushes update the same
comment instead of stacking new ones.

## Inputs

| Input                | Default                         | Notes                                              |
|----------------------|---------------------------------|----------------------------------------------------|
| `hunger-threshold`   | `30`                            | Lower hunger → starving. 30 matches gitchi's "became_hungry" event threshold. |
| `health-threshold`   | `50`                            | Lower health → fragile. 50 is the bare baseline before tests + CI bumps. |
| `comment-marker`     | `<!-- gitchi-pet-check -->`     | HTML marker used to update the existing comment instead of duplicating. |
| `github-token`       | `${{ github.token }}`           | Token used to read/post comments. Calling job needs `pull-requests: write`. |

## Why `fetch-depth: 0`?

`actions/checkout` defaults to a shallow clone, but gitchi needs the
repository's root commit to compute the pet's `age_days` and evolution
stage correctly. Setting `fetch-depth: 0` gives it the full history.
