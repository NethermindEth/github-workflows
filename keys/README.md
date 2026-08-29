# Signing Keys

## jfrog-evidence-image-signing.pub

ECDSA P-256 public key for verifying JFrog Evidence on Docker images signed by
`.github/workflows/docker-build-push-jfrog.yaml`.

- **Key alias (JFrog `--key-alias`):** `jfrog-evidence-image-signing`
- **Private key location:** Infisical project Angkor Platform, path
  `/github/workflows/shared/github-workflows` (secret name
  `DOCKER_IMAGE_SIGNING_PRIVATE_KEY`). Never committed.
- **Consumed by:** Kyverno admission policy (ANG-2397) and offline
  `jf evd verify --public-keys`.

Rotation: see [`examples/docker/README.md`](../examples/docker/README.md) →
"Image Signing (JFrog Evidence)" → "Key rotation".
