#!/usr/bin/env python3
"""Sync Amiqus records into Vanta as background check evidence.

Reads records from the Amiqus ID API, filters them down to the people who count
as personnel background checks, maps them onto Vanta's background check
connector schema and pushes them with a single PUT.

The Vanta endpoint is a full "state of the world" sync: every record absent from
the payload is deleted on Vanta's side. The script therefore refuses to apply an
implausibly small payload unless explicitly told otherwise, and runs in dry-run
mode unless --apply is passed.

Standard library only - no pip install on the runner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

DEFAULT_AMIQUS_BASE_URL = "https://id.amiqus.co/api/v2"
DEFAULT_AMIQUS_APP_URL = "https://id.amiqus.co"
# Regional hostnames (api.eu.vanta.com, api.aus.vanta.com) only 308-redirect here
# and break auth when called directly - see developer.vanta.com/reference/overview
DEFAULT_VANTA_BASE_URL = "https://api.vanta.com"
VANTA_SCOPE = "connectors.self:write-resource"
PAGE_LIMIT = 100
MAX_PAGES = 200

# Amiqus record status -> Vanta background check status.
# Vanta accepts exactly: INCOMPLETE, IN_PROGRESS, COMPLETE.
STATUS_MAP = {
    "complete": "COMPLETE",
    "reviewed": "COMPLETE",
    "started": "IN_PROGRESS",
    "waiting": "IN_PROGRESS",
    "amendments": "IN_PROGRESS",
    "paused": "IN_PROGRESS",
    "pending": "IN_PROGRESS",
    "incomplete": "INCOMPLETE",
    "empty": "INCOMPLETE",
    "expired": "INCOMPLETE",
}
DEFAULT_STATUS = "INCOMPLETE"


class SyncError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: Any = None,
    retries: int = 3,
) -> Any:
    """Minimal JSON HTTP client with retry on 429 and 5xx."""
    data = None
    headers = dict(headers or {})
    headers.setdefault("Accept", "application/json")
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload) if payload.strip() else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = min(2 ** attempt * 5, 60)
                print(f"  {method} {url} -> HTTP {exc.code}, retrying in {wait}s")
                time.sleep(wait)
                last_error = exc
                continue
            raise SyncError(f"{method} {url} failed: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(2 ** attempt)
                last_error = exc
                continue
            raise SyncError(f"{method} {url} failed: {exc}") from exc
    raise SyncError(f"{method} {url} failed after {retries} attempts: {last_error}")


# --------------------------------------------------------------------------- #
# Amiqus
# --------------------------------------------------------------------------- #


def fetch_amiqus_records(
    base_url: str, token: str, max_pages: int = MAX_PAGES
) -> list[dict[str, Any]]:
    """Page through GET /records with the client object expanded."""
    records: list[dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {token}"}
    seen_ids: set[Any] = set()

    for page in range(1, max_pages + 1):
        query = urllib.parse.urlencode(
            {"page": page, "limit": PAGE_LIMIT, "expand": "client"}
        )
        payload = request_json(f"{base_url}/records?{query}", headers=headers)
        batch = payload.get("data") if isinstance(payload, dict) else payload
        if not batch:
            break
        new = [r for r in batch if r.get("id") not in seen_ids]
        seen_ids.update(r.get("id") for r in batch)
        records.extend(new)
        print(f"  page {page}: {len(batch)} record(s)")
        if len(batch) < PAGE_LIMIT or not new:
            break
    else:
        if max_pages == MAX_PAGES:
            raise SyncError(
                f"Stopped after {max_pages} pages - pagination looks wrong, refusing to sync a partial set"
            )
        print(f"  reached --max-pages={max_pages}; this is a partial set, dry run only")

    return records


def fetch_amiqus_record(base_url: str, token: str, record_id: str) -> dict[str, Any]:
    """GET a single record, for testing against one known person."""
    payload = request_json(
        f"{base_url}/records/{urllib.parse.quote(str(record_id))}?expand=client",
        headers={"Authorization": f"Bearer {token}"},
    )
    record = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(record, dict) or not record.get("id"):
        raise SyncError(f"Amiqus returned no usable record for id {record_id}")
    return record


def client_of(record: dict[str, Any]) -> dict[str, Any]:
    client = record.get("client")
    return client if isinstance(client, dict) else {}


def full_name(record: dict[str, Any]) -> str:
    """Amiqus returns client.name either as a string or as an object."""
    name = client_of(record).get("name")
    if isinstance(name, str):
        return name.strip()
    if isinstance(name, dict):
        parts = [name.get("first_name"), name.get("middle_name"), name.get("last_name")]
        joined = " ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())
        if joined:
            return joined
    for key in ("display_name", "full_name"):
        value = client_of(record).get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def email_of(record: dict[str, Any]) -> str:
    for source in (client_of(record), record):
        value = source.get("email")
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def completion_date(record: dict[str, Any]) -> str | None:
    """Latest step completion, falling back to the record's own timestamps."""
    stamps = [
        step.get("completed_at")
        for step in record.get("steps") or []
        if isinstance(step, dict) and step.get("completed_at")
    ]
    if stamps:
        return max(stamps)
    for key in ("completed_at", "reviewed_at", "declaration_confirmed_at", "updated_at"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


# --------------------------------------------------------------------------- #
# Filtering and mapping
# --------------------------------------------------------------------------- #


def keep(
    record: dict[str, Any],
    *,
    email_domains: list[str],
    emails: list[str],
    reference_regex: re.Pattern[str] | None,
    include_archived: bool,
    statuses: list[str],
) -> tuple[bool, str]:
    if not include_archived and record.get("archived_at"):
        return False, "archived"

    status = (record.get("status") or "").lower()
    if statuses and status not in statuses:
        return False, f"status={status or 'unknown'}"

    email = email_of(record)
    if not email:
        return False, "no email"
    if emails and email not in emails:
        return False, "email not in --emails"
    if email_domains and not any(email.endswith("@" + d) for d in email_domains):
        return False, f"email domain not in {','.join(email_domains)}"

    if reference_regex is not None:
        reference = record.get("reference") or ""
        if not reference_regex.search(str(reference)):
            return False, "reference did not match filter"

    if not full_name(record):
        return False, "no client name"

    return True, ""


def to_vanta_resource(record: dict[str, Any], app_url: str) -> dict[str, Any]:
    record_id = record.get("id")
    status = STATUS_MAP.get((record.get("status") or "").lower(), DEFAULT_STATUS)
    name = full_name(record)

    resource: dict[str, Any] = {
        "uniqueId": f"amiqus-record-{record_id}",
        "displayName": f"{name} - Amiqus record {record_id}",
        "externalUrl": f"{app_url}/records/{record_id}",
        "fullName": name,
        "email": email_of(record),
        "status": status,
    }
    if status == "COMPLETE":
        completed = completion_date(record)
        if completed:
            resource["completionDate"] = completed
    return resource


# --------------------------------------------------------------------------- #
# Vanta
# --------------------------------------------------------------------------- #


def vanta_token(base_url: str, client_id: str, client_secret: str) -> str:
    payload = request_json(
        f"{base_url}/oauth/token",
        method="POST",
        body={
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": VANTA_SCOPE,
            "grant_type": "client_credentials",
        },
    )
    token = payload.get("access_token")
    if not token:
        raise SyncError("Vanta token response did not contain an access_token")
    return token


def push_to_vanta(
    base_url: str, token: str, resource_id: str, resources: list[dict[str, Any]]
) -> Any:
    return request_json(
        f"{base_url}/v1/resources/background_check_connector",
        method="PUT",
        headers={"Authorization": f"Bearer {token}"},
        body={"resourceId": resource_id, "resources": resources},
    )


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def summarise(
    resources: list[dict[str, Any]],
    skipped: list[tuple[Any, str]],
    applied: bool,
    subset: str = "",
) -> str:
    counts: dict[str, int] = {}
    for resource in resources:
        counts[resource["status"]] = counts.get(resource["status"], 0) + 1

    lines = [
        "## Amiqus -> Vanta background check sync",
        "",
        f"**Mode:** {'apply' if applied else 'dry run (no write to Vanta)'}"
        + (f" - **subset:** {subset}" if subset else ""),
        "",
        "| Status | Records |",
        "| --- | --- |",
    ]
    for status in ("COMPLETE", "IN_PROGRESS", "INCOMPLETE"):
        lines.append(f"| {status} | {counts.get(status, 0)} |")
    lines += [
        f"| **Total pushed** | **{len(resources)}** |",
        f"| Skipped by filters | {len(skipped)} |",
    ]
    return "\n".join(lines) + "\n"


def redact(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace names and emails with stable placeholders so a raw dump is shareable."""
    out = []
    for index, record in enumerate(records, start=1):
        copy = json.loads(json.dumps(record))
        client = copy.get("client")
        if isinstance(client, dict):
            if isinstance(client.get("name"), dict):
                for key in list(client["name"]):
                    if key.endswith("name") and isinstance(client["name"][key], str):
                        client["name"][key] = f"{key}-{index}"
            elif isinstance(client.get("name"), str):
                client["name"] = f"Person {index}"
            for key in ("email", "phone", "date_of_birth", "display_name", "full_name"):
                if client.get(key):
                    client[key] = f"redacted-{index}"
        if copy.get("email"):
            copy["email"] = f"redacted-{index}@example.invalid"
        return_keys = ("perform_url",)
        for key in return_keys:
            if copy.get(key):
                copy[key] = "redacted"
        out.append(copy)
    return out


def preview_table(resources: list[dict[str, Any]], limit: int = 50) -> str:
    if not resources:
        return "No records matched the filters.\n"
    lines = ["| Status | Name | Email | Completed | Amiqus record |", "| --- | --- | --- | --- | --- |"]
    for resource in resources[:limit]:
        lines.append(
            "| {status} | {fullName} | {email} | {completed} | {uniqueId} |".format(
                completed=resource.get("completionDate", "-"), **resource
            )
        )
    if len(resources) > limit:
        lines.append(f"| ... | {len(resources) - limit} more | | | |")
    return "\n".join(lines) + "\n"


def write_step_summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def env_or_fail(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SyncError(f"Environment variable {name} is required but empty")
    return value


def split_csv(value: str | None) -> list[str]:
    return [item.strip().lower() for item in (value or "").split(",") if item.strip()]


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually write to Vanta; without it the script only reports what it would push",
    )
    parser.add_argument("--amiqus-base-url", default=DEFAULT_AMIQUS_BASE_URL)
    parser.add_argument("--amiqus-app-url", default=DEFAULT_AMIQUS_APP_URL)
    parser.add_argument("--vanta-base-url", default=DEFAULT_VANTA_BASE_URL)
    parser.add_argument(
        "--email-domains",
        default="",
        help="comma separated list; only records whose client email is on one of these domains are synced",
    )
    parser.add_argument(
        "--reference-regex",
        default="",
        help="optional regex the Amiqus record reference must match",
    )
    parser.add_argument(
        "--statuses",
        default="",
        help="comma separated Amiqus record statuses to include (default: all)",
    )
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument(
        "--min-records",
        type=int,
        default=1,
        help="refuse to apply a payload smaller than this; the Vanta PUT deletes everything not listed",
    )
    parser.add_argument(
        "--fixture",
        default="",
        help="read Amiqus records from a local JSON file instead of the API (testing only)",
    )
    parser.add_argument("--output", default="", help="write the Vanta payload to this file")
    parser.add_argument(
        "--save-raw",
        default="",
        help="write the raw Amiqus records to this file, for checking field shapes before a first apply",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="with --save-raw, replace names and emails with placeholders so the dump is shareable",
    )
    parser.add_argument(
        "--record-ids",
        default="",
        help="comma separated Amiqus record IDs; fetches only those instead of listing everything",
    )
    parser.add_argument(
        "--emails",
        default="",
        help="comma separated client emails; keeps only these people (use your own for a single-person test)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="keep at most N records after filtering, for a small bulk test",
    )
    parser.add_argument(
        "--partial-apply",
        action="store_true",
        help=(
            "acknowledge that --record-ids/--emails/--limit/--max-pages make the payload a subset, "
            "and that applying it deletes every other background check in Vanta"
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES,
        help="stop after this many Amiqus pages; use a small value for a quick smoke test (dry run only)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    email_domains = split_csv(args.email_domains)
    emails = split_csv(args.emails)
    record_ids = [item.strip() for item in args.record_ids.split(",") if item.strip()]
    statuses = split_csv(args.statuses)

    subset_reasons = []
    if record_ids:
        subset_reasons.append(f"--record-ids ({len(record_ids)})")
    if emails:
        subset_reasons.append(f"--emails ({len(emails)})")
    if args.limit:
        subset_reasons.append(f"--limit {args.limit}")
    if args.max_pages != MAX_PAGES:
        subset_reasons.append(f"--max-pages {args.max_pages}")
    reference_regex = re.compile(args.reference_regex) if args.reference_regex else None

    if args.fixture:
        with open(args.fixture, encoding="utf-8") as handle:
            records = json.load(handle)
        print(f"Loaded {len(records)} record(s) from fixture {args.fixture}")
    elif record_ids:
        token = env_or_fail("AMIQUS_TOKEN")
        print(f"Fetching {len(record_ids)} record(s) by ID...")
        records = [
            fetch_amiqus_record(args.amiqus_base_url, token, record_id)
            for record_id in record_ids
        ]
    else:
        print("Fetching Amiqus records...")
        records = fetch_amiqus_records(
            args.amiqus_base_url, env_or_fail("AMIQUS_TOKEN"), max_pages=args.max_pages
        )
        print(f"Fetched {len(records)} record(s) from Amiqus")

    if args.save_raw:
        dump = redact(records) if args.redact else records
        with open(args.save_raw, "w", encoding="utf-8") as handle:
            json.dump(dump, handle, indent=2, sort_keys=True)
        print(
            f"Raw Amiqus records written to {args.save_raw}"
            + ("" if args.redact else " - contains personal data, do not commit or share")
        )

    resources: list[dict[str, Any]] = []
    skipped: list[tuple[Any, str]] = []
    for record in records:
        wanted, reason = keep(
            record,
            email_domains=email_domains,
            emails=emails,
            reference_regex=reference_regex,
            include_archived=args.include_archived,
            statuses=statuses,
        )
        if wanted:
            resources.append(to_vanta_resource(record, args.amiqus_app_url.rstrip("/")))
        else:
            skipped.append((record.get("id"), reason))

    resources.sort(key=lambda r: r["uniqueId"])

    if args.limit and len(resources) > args.limit:
        print(f"Limiting to the first {args.limit} of {len(resources)} matching record(s)")
        resources = resources[: args.limit]

    print(f"\n{len(resources)} record(s) map to Vanta background checks, {len(skipped)} skipped")
    for record_id, reason in skipped[:20]:
        print(f"  skipped record {record_id}: {reason}")
    if len(skipped) > 20:
        print(f"  ... and {len(skipped) - 20} more")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(resources, handle, indent=2, sort_keys=True)
        print(f"Payload written to {args.output}")

    summary = summarise(
        resources, skipped, applied=args.apply, subset=", ".join(subset_reasons)
    )
    print("\n" + summary)
    if not args.apply:
        print(preview_table(resources))
    write_step_summary(summary)

    if not args.apply:
        print("Dry run - nothing written to Vanta. Re-run with --apply to sync.")
        return 0

    if subset_reasons and not args.partial_apply:
        raise SyncError(
            "Refusing to apply a deliberately narrowed payload ("
            + ", ".join(subset_reasons)
            + "). The Vanta sync deletes every background check not in the payload, so this would "
            "wipe everyone else. Pass --partial-apply if the connector is empty or you mean it."
        )
    if subset_reasons:
        print(
            "::warning::Applying a subset ("
            + ", ".join(subset_reasons)
            + "); every background check not in this payload is now deleted in Vanta."
        )

    if len(resources) < args.min_records:
        raise SyncError(
            f"Refusing to apply: {len(resources)} record(s) is below --min-records={args.min_records}. "
            "The Vanta sync deletes every background check not present in the payload."
        )

    print("Requesting Vanta access token...")
    token = vanta_token(
        args.vanta_base_url,
        env_or_fail("VANTA_CLIENT_ID"),
        env_or_fail("VANTA_CLIENT_SECRET"),
    )
    print(f"Pushing {len(resources)} record(s) to Vanta...")
    response = push_to_vanta(
        args.vanta_base_url, token, env_or_fail("VANTA_RESOURCE_ID"), resources
    )
    print(f"Vanta responded: {json.dumps(response)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SyncError as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
