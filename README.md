# GitHub Workflows

This repository contains reusable GitHub Actions workflows for Nethermind projects.

## Docker Image Workflows

### Build and Publish

The workflow for building and publishing Docker images to Artifactory.

**Implementation:** [`.github/workflows/publish-docker.yaml`](.github/workflows/publish-docker.yaml)  
**Example:** [`examples/publish-docker.yml`](examples/publish-docker.yml)

Features:
- Multi-platform builds (linux/amd64, linux/arm64)
- Automatic tagging based on git refs
- Security scanning with Trivy
- Build provenance attestation
- Caching support
- Publishes to dev environment

Build Process:
1. Build image without pushing
2. Run Trivy vulnerability scan (CRITICAL,HIGH)
3. Push to registry if scan passes
4. Create and upload attestation

### Promote

The workflow for promoting Docker images between environments (dev → staging → prod).

**Implementation:** [`.github/workflows/promote-docker.yaml`](.github/workflows/promote-docker.yaml)  
**Example:** [`examples/promote-docker.yml`](examples/promote-docker.yml)

Features:
- Promotes images between environments
- Maintains build provenance attestation
- Supports multiple tags promotion
- Detailed promotion summary

## Actions

### Get Group Topic

Located in [`.github/actions/get-group-topic/action.yaml`](.github/actions/get-group-topic/action.yaml)

A utility action that determines the appropriate group name for Artifactory repositories based on repository topics.

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