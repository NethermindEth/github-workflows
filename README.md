# GitHub Workflows

This repository contains reusable GitHub Actions workflows for Nethermind projects.

## Docker Image Workflows

### Build and Publish

Features:
- Multi-platform builds (linux/amd64, linux/arm64 by default)
- Automatic repository naming based on group name
- OIDC authentication with JFrog
- Flexible build configuration (context, dockerfile path, build args, secrets)
- Build attestation support
- Custom additional tags

#### JFrog Artifactory

The workflow for building and publishing Docker images to JFrog Artifactory.

**Implementation:** [`.github/workflows/docker-build-push-jfrog.yaml`](.github/workflows/docker-build-push-jfrog.yaml)  
**Example:** [`examples/docker-build-push-jfrog.yml`](examples/docker-build-push-jfrog.yml)

#### Docker Hub

The workflow for building and publishing Docker images to Docker Hub.

**Implementation:** [`.github/workflows/docker-build-push-dockerhub.yaml`](.github/workflows/docker-build-push-dockerhub.yaml)  
**Example:** [`examples/docker-build-push-dockerhub.yml`](examples/docker-build-push-dockerhub.yml)

### Promote

The workflow for promoting Docker images between environments (dev → staging → prod).

Features:
- Promotes images between environments
- Maintains build provenance attestation
- Supports multiple tags promotion
- Detailed promotion summary

#### JFrog Artifactory

**Implementation:** [`.github/workflows/docker-promote-jfrog.yaml`](.github/workflows/docker-promote-jfrog.yaml)  
**Example:** [`examples/docker-promote-jfrog.yml`](examples/docker-promote-jfrog.yml)

#### Docker Hub

**Implementation:** [`.github/workflows/docker-promote-dockerhub.yaml`](.github/workflows/docker-promote-dockerhub.yaml)  
**Example:** [`examples/docker-promote-dockerhub.yml`](examples/docker-promote-dockerhub.yml)


## Environment Flow

Docker images follow this promotion path:

dev (build) → staging (promotion) → prod (promotion)

Each environment has its own Artifactory repository:
- `{group}-oci-local-dev`
- `{group}-oci-local-staging`
- `{group}-oci-local-prod`

## Security

All workflows include:
- SHA pinned action versions
- Build provenance attestation
- Minimal permissions model

## License

Copyright (c) 2025 Nethermind - All rights reserved

This is an internal repository containing proprietary workflows and examples.
See [LICENSE](LICENSE) file for details.