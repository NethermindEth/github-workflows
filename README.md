# GitHub Workflows

This repository contains reusable GitHub Actions workflows for Nethermind projects.

The workflows follow a simple name convention:
- technology-action-flavor.yaml

For example:
- docker-build-push-dockerhub.yaml.  Docker is the technology, build-push is the action, dockerhub is the flavor.


## Releases

You can use individual releases like `v1.11.6` like so:

```yaml
jobs:
  build:
    uses: NethermindEth/github-workflows/.github/workflows/docker-build-push-jfrog.yaml@v1.11.6
```

Alternatively, you can use the current `stable` release, which will get automatically updated as
the maintainers decide to do so:

```yaml
jobs:
  build:
    uses: NethermindEth/github-workflows/.github/workflows/docker-build-push-jfrog.yaml@stable
```

We do not recommend you track a branch like `main`.

## Creating a new stable tag

The stable tag is a manual process, which must be decided _after_ the version has been validated in
at least a few repositories. To do so, simply:

> [!WARNING]
> The `stable` tag **must** be a lightweight tag. Annotated tags break nested reusable workflow
> resolution in GitHub Actions (see [community discussion](https://github.com/orgs/community/discussions/48693)).
```shell
NEW_STABLE_VERSION=v9.8.7  # Replace with the new version
git tag -f --no-sign stable "$(git rev-parse $NEW_STABLE_VERSION^{})"
git push origin -f refs/tags/stable
```

## Docker Image Workflows

Read about it in the [examples/docker/README.md](examples/docker/README.md) file.

## AI Review Workflow

Read about it in the [examples/ai-review/README.md](examples/ai-review/README.md) file.

## Deploy Gate Watchdog

Catches the case where a build-and-push workflow has been failing on the release branch
and nobody noticed, so production is still serving an old image. Read about it in the
[examples/watchdog/README.md](examples/watchdog/README.md) file.

## Working on this repository

```shell
tests/lint_workflows.sh                      # actionlint over the workflows
tests/deploy-gate-watchdog/run_tests.sh      # watchdog behaviour
```

Both are exactly what CI runs. `tests/lint_workflows.sh` needs Go; the watchdog tests
need python3 with the pin in [tests/requirements.txt](tests/requirements.txt).


## License

Copyright (c) 2025 Nethermind - All rights reserved
See [LICENSE](LICENSE) file for details.
