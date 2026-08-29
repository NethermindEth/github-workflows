# JFrog Evidence Image Signing — Design (ANG-2396)

## Summary

Sign every Docker image produced by CI with JFrog Evidence using a managed
ECDSA key pair, so downstream Kubernetes admission control (ANG-2397, Kyverno)
can verify image provenance before allowing a workload to start.

Signing is implemented with explicit `jf evd create` and a managed key — **not**
the keyless `actions/attest-build-provenance` path. The keyless path is avoided
because (a) it depends on RFC3161 timestamping by a TSA that may be absent from
the public Sigstore TUF root for private repos, currently mishandled by
Kyverno's newer `ImageValidatingPolicy` API (kyverno/kyverno#16054), and (b)
using GitHub's private Sigstore instance with Kyverno requires a cluster-wide
TUF override that constrains verification of other signing sources
(kyverno/kyverno#11618). A managed key gives a self-contained chain of trust
entirely within JFrog and a stable public key to wire into Kyverno.

**Scope:** Docker images only. Language packages, generic artifacts, and release
bundles are explicitly out of scope for this iteration.

## Motivation

- ANG-2397 needs a verifiable, digest-bound provenance signal on every image.
- A managed key pair keeps the trust chain inside JFrog + GitHub, avoiding the
  Sigstore/TUF coupling that breaks Kyverno verification for private repos.

## Architecture

All signing logic lives in the **reusable workflow**
`NethermindEth/github-workflows/.github/workflows/docker-build-push-jfrog.yaml`.
New steps run **after** the existing `Build and push` step, gated on
`inputs.push == true && inputs.sign_image == true`. Every repo consuming the
reusable workflow gets signing for free.

`angkor-platform-aws-sts` (pushing to `angkor-oci-local`) is the pilot.

### Why the reusable workflow, not the caller

Signing must apply to *every* image produced by CI. Centralising it in the
reusable workflow means one implementation, one key convention, and no
copy-paste per repo. Consumers opt out with `sign_image: false`.

### Why not modify the build action

`NethermindEth/github-action-image-build-and-push` exposes **no outputs** (no
digest, no tags). Rather than fork that action, the reusable workflow resolves
the digest itself post-push via `docker buildx imagetools inspect`. Self-contained
and avoids a cross-repo dependency.

## Evidence subject: how the digest pin works

The ticket's acceptance criteria mandate the **package form**
(`--package-name` / `--package-version` / `--package-repo-name`). JFrog's docs
confirm this form attaches evidence to the **resolved manifest**, not to the
mutable tag reference. Therefore, if `--package-version` is an **immutable,
unique-per-commit tag** (`${{ github.sha }}`), the evidence is bound to that
exact manifest — effectively digest-pinned.

To guarantee the tag exists and is unique, the workflow ensures the full
`${{ github.sha }}` is in the pushed tag set. The real sha256 manifest digest is
additionally resolved and recorded (in the predicate + job summary) so ANG-2397
has the exact digest, even though the `jf evd create` subject is the SHA tag.

A harder pin (`--subject-repo-path <repo>/<image>/<sha-tag>/manifest.json
--subject-sha256 <digest>`) is available but deliberately not used in this
iteration: it diverges from the acceptance-criteria command and the package form
already binds to the resolved manifest.

## New reusable-workflow inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `sign_image` | boolean | `true` | Opt-out toggle for Evidence signing |
| `signing_key_alias` | string | `jfrog-evidence-image-signing` | JFrog key alias used at create + verify time |
| `predicate_type` | string | `https://jfrog.com/evidence/signature/v1` | Custom predicate-type URI |

## New reusable-workflow secrets

| Secret | Required when signing | Description |
|---|---|---|
| `infisical_identity_id` | yes | Infisical machine identity ID (OIDC) for the signing-key project |
| `infisical_project_id` | yes | Infisical project ID holding the private signing key |

The private key is stored at a **shared** Infisical path (Angkor Platform project)
`/github/workflows/shared/github-workflows` (key name
`DOCKER_IMAGE_SIGNING_PRIVATE_KEY`), not the per-repo `/github/workflows/<repo>`
path, so a single signing key serves all consumers. Fetched via a `secret-path`
override on `get_infisical_secrets`.

## Step sequence (added after `Build and push`)

All steps gated on `inputs.push == true && inputs.sign_image == true`.

1. **Ensure SHA tag pushed** — the full `${{ github.sha }}` is passed in the
   build action's tag set so a deterministic, unique, immutable tag exists to
   sign and to inspect.

2. **Resolve image digest**
   ```bash
   IMAGE_DIGEST=$(docker buildx imagetools inspect \
     "${JFROG_URL}/${IMAGE_NAME}:${GITHUB_SHA}" \
     --format '{{json .Manifest.Digest}}' | jq -r .)
   ```
   Returns the OCI index digest for multi-arch images, the image manifest digest
   for single-arch. This is the immutable reference Kyverno resolves to.

3. **Fetch private key** — `NethermindEth/github-workflows/get_infisical_secrets`
   with a `secret-path` override pointing at the shared signing-key path. Exports
   the PEM as a masked env var (`add-mask` line-by-line per the existing pattern).

4. **Generate predicate** — injection-safe (`env:` block + `jq`, never inline
   `${{ }}` in `run:`), writes `predicate.json`:
   ```json
   {
     "actor": "<github.actor>",
     "workflow": "<github.workflow>",
     "run_id": "<github.run_id>",
     "commit": "<github.sha>",
     "repository": "<github.repository>",
     "ref": "<github.ref>",
     "timestamp": "<ISO-8601 UTC>",
     "image_digest": "sha256:<digest>"
   }
   ```
   `image_digest` is added beyond the ticket's shape so ANG-2397 gets the exact
   digest. Predicate contents are not policy-relevant yet (Kyverno verifies only
   that signed Evidence exists); switching to SLSA Provenance later is cheap.

5. **Sign**
   ```bash
   jf evd create \
     --package-name "${IMAGE_NAME}" \
     --package-version "${GITHUB_SHA}" \
     --package-repo-name "${REPO_NAME}" \
     --predicate ./predicate.json \
     --predicate-type "${PREDICATE_TYPE}" \
     --key "${PRIVATE_KEY}" \
     --key-alias "${SIGNING_KEY_ALIAS}"
   ```
   JFrog auth is inherited from the existing `setup-jfrog-cli` OIDC step
   (evidence create requires access-token/OIDC auth — basic auth is rejected).

6. **Job summary** — write image, SHA tag, resolved digest, predicate-type, and
   key alias to `$GITHUB_STEP_SUMMARY` for traceability.

## Key management

### Generation (once, ECDSA P-256)

```bash
openssl ecparam -name prime256v1 -genkey -noout -out private.pem
openssl ec -in private.pem -pubout -out public.pem
```

ECDSA P-256 is the cosign/Kyverno standard and compact. RSA is acceptable but
larger; ed25519 is supported by `jf evd` but less universally consumed.

### Distribution

- **Private key** → Infisical `/github/workflows/shared/github-workflows`
  (`DOCKER_IMAGE_SIGNING_PRIVATE_KEY`, Angkor Platform project), CI-accessible via
  OIDC machine identity. Never committed.
- **Public key** → committed to
  `github-workflows/keys/jfrog-evidence-image-signing.pub`. Stable, versioned URL
  for Kyverno / ArgoCD to consume.

### Key-alias convention

`jfrog-evidence-image-signing` — matches the public-key filename and the
`--key-alias` passed to both `jf evd create` and `jf evd verify`.

### Rotation procedure

1. Generate a new ECDSA P-256 pair (commands above).
2. Replace the private key value in the Infisical shared path.
3. Commit the new public key to
   `github-workflows/keys/jfrog-evidence-image-signing.pub` (optionally a
   date-suffixed name during overlap).
4. Update the downstream Kyverno policy (ANG-2397) with the new public key.
5. Keep the old public key available until all previously-signed images have
   aged out of admission-controlled clusters, then remove it.

## Verification (acceptance)

Offline, with the matching public key:

```bash
jf evd verify \
  --package-name "${IMAGE_NAME}" \
  --package-version "${GITHUB_SHA}" \
  --package-repo-name "${REPO_NAME}" \
  --public-keys ./public.pem
```

No JFrog auth required for offline verify with `--public-keys` (purely
client-side).

## Prerequisites (ops, not automated by this change)

- Artifactory instance has the **Evidence** feature enabled (subscription gated).
- JFrog CLI ≥ 2.65.0 for `jf evd` (setup-jfrog-cli installs latest — satisfied).
- ECDSA key pair generated; private key uploaded to Infisical; public key
  committed.
- Infisical machine identity + project for the signing key, bound to the calling
  repos via OIDC.

## Files touched

- `github-workflows/.github/workflows/docker-build-push-jfrog.yaml` — new inputs,
  secrets, and signing steps.
- `github-workflows/keys/jfrog-evidence-image-signing.pub` — public key.
- `github-workflows/docs/docker/` — signing usage + key rotation docs.
- `angkor-platform-aws-sts/.github/workflows/docker-build-push.yaml` — bump
  reusable-workflow version ref once released; pass Infisical secrets if not
  org-level.

## Acceptance criteria mapping

| Criterion | Satisfied by |
|---|---|
| ECDSA/RSA key pair generated; private in CI secret store; public consumable by Kyverno | ECDSA P-256; private → Infisical; public → committed `.pub` |
| Predicate JSON generated at runtime with CI provenance fields + custom predicate-type URI | Step 4 |
| Signs every image immediately after push via `jf evd create` package form | Steps 5, gated on `push && sign_image` |
| Evidence appears on Docker package in Artifactory Evidence tab | Step 5 result (manual verification at pilot) |
| Out-of-cluster `jf evd verify` with public key succeeds | Verification section |
| Predicate shape, predicate-type URI, key-alias convention documented | This doc |
| Key rotation procedure documented | Rotation section |
| At least one pilot image signed + verified end-to-end | `angkor-platform-aws-sts` pilot |
| Only Docker images signed this iteration | Scope section |

## Out of scope

- Non-Docker artifact types (packages, generic artifacts, release bundles).
- Kyverno admission policy (ANG-2397).
- Infisical / JFrog / key-pair infrastructure provisioning (documented as
  prerequisites).
