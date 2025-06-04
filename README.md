# GitHub Workflows

This repository contains reusable GitHub Actions workflows for Nethermind projects.

The workflows follow a simple name convention:
- technology-action-flavor.yaml

For example:
- docker-build-push-dockerhub.yaml.  Docker is the technology, build-push is the action, dockerhub is the flavor.


## Docker Image Workflows

Read about it in the [examples/docker/README.md](examples/docker/README.md) file.

## Security

All workflows include:
- SHA pinned action versions
- Build provenance attestation
- Minimal permissions model

## License

Copyright (c) 2025 Nethermind - All rights reserved

This is an internal repository containing proprietary workflows and examples.
See [LICENSE](LICENSE) file for details.