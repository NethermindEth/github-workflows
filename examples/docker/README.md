# Docker Image Workflows

## Build and Publish

Features:
- Multi-platform builds (linux/amd64, linux/arm64 by default)
- Automatic repository naming based on group name
- OIDC authentication with JFrog
- Flexible build configuration (context, dockerfile path, build args, secrets)
- Build attestation support
- Custom additional tags

### JFrog Artifactory

The workflow for building and publishing Docker images to JFrog Artifactory.

**Implementation:** [`.github/workflows/docker-build-push-jfrog.yaml`](../../.github/workflows/docker-build-push-jfrog.yaml)

**Simple Example:** [`examples/docker/build-push-jfrog-simple.yml`](./build-push-jfrog-simple.yml)
**Complete Example:** [`examples/docker/build-push-jfrog-complete.yml`](./build-push-jfrog-complete.yml)


### Docker Hub

The workflow for building and publishing Docker images to Docker Hub.

**Implementation:** [`.github/workflows/docker-build-push-dockerhub.yaml`](../../.github/workflows/docker-build-push-dockerhub.yaml)

**Simple Example:** [`examples/docker/build-push-dockerhub-simple.yml`](./build-push-dockerhub-simple.yml)
**Complete Example:** [`examples/docker/build-push-dockerhub-complete.yml`](./build-push-dockerhub-complete.yml)


## Promote

The workflow for promoting Docker images between environments (dev → staging → prod).

Features:
- Promotes images between environments
- Maintains build provenance attestation
- Supports multiple tags promotion
- Detailed promotion summary

### JFrog Artifactory

**Implementation:** [`.github/workflows/docker-promote-jfrog.yaml`](../../.github/workflows/docker-promote-jfrog.yaml)

**Example:** [`examples/docker/promote-jfrog.yml`](./promote-jfrog.yml)


### Docker Hub

**Implementation:** [`.github/workflows/docker-promote-dockerhub.yaml`](../../.github/workflows/docker-promote-dockerhub.yaml)
**Example:** [`examples/docker/promote-dockerhub.yml`](./promote-dockerhub.yml)


## Environment Flow - JFrog Artifactory

Docker images follow this promotion path:

dev (build) → staging (promotion) → prod (promotion)

Each environment has its own Artifactory repository:
- `{group}-oci-local-dev`
- `{group}-oci-local-staging`
- `{group}-oci-local-prod`

## Environment Flow - Docker Hub

Docker images follow this promotion path:

dev (build) → prod (promotion)

Each environment has its own Docker Hub repository:
- dev ->  `nethermindeth`
- prod -> `nethermind`