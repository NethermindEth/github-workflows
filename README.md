# GitHub Workflows

This repository contains reusable GitHub Actions workflows and templates for Nethermind projects.

## Docker Image Workflows

### Build and Publish

The workflow for building and publishing Docker images to Artifactory.

**Template:** [`.github/workflow-templates/publish-docker-template.yml`](.github/workflow-templates/publish-docker-template.yml)  
**Implementation:** [`.github/workflows/publish-docker.yaml`](.github/workflows/publish-docker.yaml)

Features:
- Multi-platform builds (linux/amd64, linux/arm64)
- Automatic tagging based on git refs
- Build provenance attestation
- Caching support
- Publishes to dev environment

### Promote

The workflow for promoting Docker images between environments (dev → staging → prod).

**Template:** [`.github/workflow-templates/promote-docker-template.yml`](.github/workflow-templates/promote-docker-template.yml)  
**Implementation:** [`.github/workflows/promote-docker.yaml`](.github/workflows/promote-docker.yaml)

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

Copyright (c) 2024 Nethermind - All rights reserved

This is an internal repository containing proprietary workflows and templates.
See [LICENSE](LICENSE) file for details.