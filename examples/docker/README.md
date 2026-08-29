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


## Image Signing (JFrog Evidence)

The JFrog build workflow signs every pushed image with JFrog Evidence using a
managed ECDSA P-256 key. Signing is on by default and runs only when `push` is
true. Set `sign_image: false` to opt out.

### What gets signed

- Subject: the package version `${{ github.sha }}` (pushed as an immutable tag).
  JFrog attaches the Evidence to the resolved image manifest.
- Predicate type: `https://jfrog.com/evidence/signature/v1` (override with
  `predicate_type`).
- Key alias: `jfrog-evidence-image-signing` (override with `signing_key_alias`).

### Predicate shape

```json
{
  "actor": "<github-actor>",
  "workflow": "<workflow-name>",
  "run_id": "<github-run-id>",
  "commit": "<git-sha>",
  "repository": "<owner/repo>",
  "ref": "<git-ref>",
  "timestamp": "<ISO-8601 UTC>",
  "image_digest": "sha256:<manifest-digest>"
}
```

### Required secrets

| Secret | Description |
|---|---|
| `infisical_identity_id` | Infisical machine identity ID for the signing-key project |
| `infisical_project_id` | Infisical project ID (Angkor Platform) holding `DOCKER_IMAGE_SIGNING_PRIVATE_KEY` |

The private key is stored at Infisical `/github/workflows/shared/github-workflows`
(secret name `DOCKER_IMAGE_SIGNING_PRIVATE_KEY`) and fetched at runtime.

### Offline verification

```bash
jf evd verify \
  --package-name <image> \
  --package-version <git-sha> \
  --package-repo-name <docker-repo> \
  --public-keys ./jfrog-evidence-image-signing.pub
```

Public key: [`keys/jfrog-evidence-image-signing.pub`](../../keys/jfrog-evidence-image-signing.pub).

### Key rotation

1. Generate a new ECDSA P-256 pair:
   ```bash
   openssl ecparam -name prime256v1 -genkey -noout -out private.pem
   openssl ec -in private.pem -pubout -out public.pem
   ```
2. Replace `DOCKER_IMAGE_SIGNING_PRIVATE_KEY` at Infisical
   `/github/workflows/shared/github-workflows` (Angkor Platform project).
3. Commit the new public key to `keys/jfrog-evidence-image-signing.pub`.
4. Update the Kyverno policy (ANG-2397) with the new public key.
5. Keep the old public key until all images signed with it have aged out of
   admission-controlled clusters, then remove it.

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