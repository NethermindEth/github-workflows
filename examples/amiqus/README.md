# Amiqus to Vanta Background Check Sync

Examples for the [`amiqus_vanta_sync`](../../amiqus_vanta_sync/action.yml) composite action, which
reads personnel records from the Amiqus ID API and pushes them into Vanta's background check
connector. Vanta then shows the check against each person on the People page and the
"Background checks are completed" test stops relying on manual evidence uploads.

## How it works

1. Pages through `GET /records?expand=client` on the Amiqus ID API (`https://id.amiqus.co/api/v2`).
2. Filters the records down to personnel — by client email domain, and optionally by record
   reference regex or record status.
3. Maps each record onto Vanta's schema and `PUT`s the whole set to
   `/v1/resources/background_check_connector` with an OAuth client-credentials token.

### Status mapping

| Amiqus record status | Vanta status |
|---|---|
| `complete`, `reviewed` | `COMPLETE` |
| `started`, `waiting`, `amendments`, `paused`, `pending` | `IN_PROGRESS` |
| `incomplete`, `empty`, `expired` | `INCOMPLETE` |
| anything unrecognised | `INCOMPLETE` |

`completionDate` is the latest step `completed_at`, falling back to the record's own
`completed_at` / `reviewed_at` / `declaration_confirmed_at` / `updated_at`.

## The sync is destructive

The Vanta endpoint is a full state-of-the-world sync: **any background check not present in the
payload is deleted in Vanta.** Two guards exist:

- `apply` defaults to `false`. A dry run fetches, filters and reports, but never calls Vanta.
- `min-records` aborts an apply whose payload is smaller than expected, so a partial Amiqus
  response or an over-eager filter cannot wipe the connector.

A narrowed payload is the dangerous case: `--record-ids`, `--emails`, `--limit` and `--max-pages`
all produce a deliberate subset, so applying one would delete everyone else. The script refuses to
combine any of them with `--apply` unless you also pass `--partial-apply`, which is only reasonable
while the connector is still empty.

Start with [`sync-vanta-dry-run.yml`](sync-vanta-dry-run.yml), read the job summary, then roll out
[`sync-vanta-scheduled.yml`](sync-vanta-scheduled.yml).

## Prerequisites

1. **Amiqus** — a personal access token or OAuth token for the Amiqus ID API.
2. **Vanta** — a private integration in the Vanta developer console with the
   `connectors.self:write-resource` scope, and a background check resource defined on it. Copy the
   generated `Resource ID`; every `PUT` references it.
3. Store `AMIQUS_TOKEN`, `VANTA_CLIENT_ID`, `VANTA_CLIENT_SECRET` and
   `VANTA_BACKGROUND_CHECK_RESOURCE_ID` in Infisical under `/github/workflows/<repo-name>`, or as
   repository secrets.

## Examples

| Example | Description |
|---|---|
| [sync-vanta-dry-run.yml](sync-vanta-dry-run.yml) | Manual dry run using repository secrets |
| [sync-vanta-scheduled.yml](sync-vanta-scheduled.yml) | Daily sync with secrets from Infisical |

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `amiqus-token` | yes | — | Amiqus ID API token |
| `vanta-client-id` | yes | — | Vanta private integration client ID |
| `vanta-client-secret` | yes | — | Vanta private integration client secret |
| `vanta-resource-id` | yes | — | Resource ID from the Vanta developer console |
| `apply` | no | `false` | `true` writes to Vanta; anything else is a dry run |
| `email-domains` | no | `""` | Comma separated domains; only matching client emails sync |
| `reference-regex` | no | `""` | Regex the Amiqus record `reference` must match |
| `statuses` | no | `""` | Comma separated Amiqus statuses to include (empty = all) |
| `include-archived` | no | `false` | Include records of archived Amiqus clients |
| `min-records` | no | `1` | Abort an apply below this record count |
| `amiqus-base-url` | no | `https://id.amiqus.co/api/v2` | Amiqus API base URL |
| `amiqus-app-url` | no | `https://id.amiqus.co` | Used to build the per-record link shown in Vanta |
| `vanta-base-url` | no | `https://api.vanta.com` | Correct for US, EU and AU tenants — the regional hostnames only redirect and break auth |

## Running it locally

The script is standard library only — no virtualenv, no pip install. Test it against the real
Amiqus API before the action is ever merged.

**1. Smoke test — one person, nothing written anywhere:**

```bash
export AMIQUS_TOKEN='...'

# by person
python3 amiqus_vanta_sync/sync.py --emails you@nethermind.io

# or by Amiqus record ID, which fetches only those records instead of listing everything
python3 amiqus_vanta_sync/sync.py --record-ids 12345

# or the first handful that match the normal filters
python3 amiqus_vanta_sync/sync.py --email-domains nethermind.io --limit 5
```

Prints the mapped records as a table plus a reason for every record it skipped, so you can check
one known person end to end before trusting the mapping on 200.

**2. Full dry run, keeping both sides for inspection:**

```bash
python3 amiqus_vanta_sync/sync.py \
  --email-domains nethermind.io \
  --save-raw /tmp/amiqus-raw.json --redact \
  --output /tmp/vanta-payload.json
```

`--output` is the exact body that would go to Vanta. `--save-raw` is what Amiqus returned, so you
can confirm the field shapes the mapping assumes — `client.name` as string vs object, which
statuses your tenant actually emits, whether `reference` is populated. **`--redact` replaces names
and emails with placeholders; without it the dump holds personal data, so do not commit or share
it.**

**3. First real apply, from your machine rather than a schedule:**

```bash
export VANTA_CLIENT_ID='...' VANTA_CLIENT_SECRET='...' VANTA_RESOURCE_ID='...'
python3 amiqus_vanta_sync/sync.py --email-domains nethermind.io --apply --min-records 20
```

Check the Vanta People page, then enable the scheduled workflow.

### Other flags

| Flag | Purpose |
|---|---|
| `--fixture records.json` | Replace the Amiqus call with a local file, for testing the mapping offline |
| `--record-ids 1,2,3` | Fetch only these Amiqus records by ID |
| `--emails a@x,b@y` | Keep only these people |
| `--limit N` | Keep at most N records after filtering |
| `--max-pages N` | Stop after N Amiqus pages |
| `--partial-apply` | Required to `--apply` any of the four above (see below) |
| `--statuses complete,reviewed` | Restrict to specific Amiqus record statuses |
| `--reference-regex '^EMP-'` | Restrict by record reference |
| `--include-archived` | Include records of archived Amiqus clients |

## References

- [Amiqus ID REST API](https://developers.amiqus.co/aqid/api-reference.html)
- [Vanta: sync all background checks](https://developer.vanta.com/reference/put-backgroundcheckconnector)
- [Vanta: build a private integration](https://developer.vanta.com/docs/quickstart/build-private-integration)
