#!/usr/bin/env python3
"""Image freshness decision (ANG-3523).

Pure function from a facts document to a decision. No I/O besides reading the
facts file and printing the decision, so every rule is unit-testable. Rules are
evaluated in order and the first match wins; nothing unknown maps to "ok".

Usage: decide.py FACTS_JSON  ->  prints the decision JSON on stdout.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone

MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

FUTURE_SKEW = 5 * MINUTE
BEHIND_MAIN_GRACE = HOUR
DEPLOY_GRACE = 30 * MINUTE
SCAN_GRACE = 2 * HOUR
DISPATCH_STUCK = HOUR
DISPATCH_FAILURE_WINDOW = DAY
REBUILD_RATE_LIMIT = 6 * HOUR

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
DISPATCH_STATUSES = {"queued", "in_progress", "success", "failure", "cancelled"}


class FactError(Exception):
    def __init__(self, fact, detail):
        super().__init__(f"{fact}: {detail}")
        self.fact = fact
        self.detail = detail


def parse_time(fact, value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FactError(fact, f"expected RFC3339 UTC timestamp, got {value!r}")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise FactError(fact, f"expected RFC3339 UTC timestamp, got {value!r}") from exc


def typed(facts, name, allowed):
    fact = facts.get(name)
    if not isinstance(fact, dict) or "status" not in fact:
        raise FactError(name, "missing")
    status = fact["status"]
    if status == "error":
        raise FactError(name, str(fact.get("detail", "unspecified error")))
    if status not in allowed:
        raise FactError(name, f"unexpected status {status!r}")
    return status, fact.get("value")


def require(fact, value, key, pattern=None):
    if not isinstance(value, dict) or key not in value:
        raise FactError(fact, f"missing {key}")
    item = value[key]
    if pattern is not None and (not isinstance(item, str) or not pattern.match(item)):
        raise FactError(fact, f"invalid {key}: {item!r}")
    return item


def findings_hash(findings):
    keys = sorted(
        (f["issue_id"], f["component"], f.get("fixed_version") or "")
        for f in findings
    )
    return "sha256:" + hashlib.sha256(json.dumps(keys).encode()).hexdigest()


def decision(action, rule, reason, **extra):
    out = {"action": action, "rule": rule, "reason": reason}
    out.update(extra)
    return out


def decide(facts):
    event = facts.get("event") or {}
    config = facts.get("config") or {}
    default_branch = config.get("default_branch")
    if event.get("name") != "schedule" or not default_branch or event.get("ref") != f"refs/heads/{default_branch}":
        return decision("fail", 1, "refused: runs only on schedule from the default branch")

    max_age_days = config.get("max_age_days")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or not 1 <= max_age_days <= 7:
        return decision("fail", 2, f"invalid max_age_days: {max_age_days!r}")

    try:
        return evaluate(facts, default_branch, max_age_days)
    except FactError as exc:
        return decision("fail", 3, f"fact gathering failed: {exc.fact}: {exc.detail}")


def evaluate(facts, default_branch, max_age_days):
    now = parse_time("now", facts.get("now"))

    _, visibility = typed(facts, "repo_visibility", {"ok"})
    if visibility not in {"public", "private", "internal"}:
        raise FactError("repo_visibility", f"unexpected value {visibility!r}")
    show_details = visibility in {"private", "internal"}

    _, head = typed(facts, "head", {"ok"})
    head_sha = require("head", head, "sha", SHA)
    head_pushed = parse_time("head.pushed_at", require("head", head, "pushed_at"))

    # Every later fact is about the image, so a missing image is reported as
    # itself rather than as whichever dependent lookup failed first.
    image_status, image = typed(facts, "image", {"ok", "not_found"})
    if image_status == "not_found":
        ref = facts["image"].get("detail")
        if not isinstance(ref, str) or not ref:
            raise FactError("image", "not_found without the image reference in detail")
        return decision("fail", 4, f"image not found: {ref}")

    running_status, running = typed(facts, "running", {"ok", "disabled"})
    _, xray = typed(facts, "xray", {"ok"})
    dispatch_status, dispatch = typed(facts, "last_dispatch", {"ok", "none"})
    previous_status, previous = typed(facts, "previous", {"ok", "none"})

    digest = require("image", image, "digest", DIGEST)
    revision = require("image", image, "revision", SHA)
    created = parse_time("image.created", require("image", image, "created"))
    attested = require("image", image, "attested")
    if not isinstance(attested, bool):
        raise FactError("image", f"invalid attested: {attested!r}")

    running_digests = []
    if running_status == "ok":
        running_digests = require("running", running, "digests")
        if not isinstance(running_digests, list) or not running_digests or not all(
            isinstance(d, str) and DIGEST.match(d) for d in running_digests
        ):
            raise FactError("running", f"invalid digests: {running_digests!r}")

    scan = require("xray", xray, "scan")
    if scan not in {"done", "pending"}:
        raise FactError("xray", f"invalid scan: {scan!r}")
    findings = require("xray", xray, "findings")
    if not isinstance(findings, list) or not all(
        isinstance(f, dict) and isinstance(f.get("issue_id"), str) and isinstance(f.get("component"), str)
        for f in findings
    ):
        raise FactError("xray", "invalid findings")

    last = None
    if dispatch_status == "ok":
        status = require("last_dispatch", dispatch, "status")
        if status not in DISPATCH_STATUSES:
            raise FactError("last_dispatch", f"invalid status: {status!r}")
        if status != "cancelled":
            last = {
                "status": status,
                "created": parse_time("last_dispatch.created_at", require("last_dispatch", dispatch, "created_at")),
                "url": require("last_dispatch", dispatch, "url"),
            }

    previous_hash = None
    if previous_status == "ok":
        previous_hash = (previous or {}).get("rebuild_findings_hash")
        if previous_hash is not None and not isinstance(previous_hash, str):
            raise FactError("previous", f"invalid rebuild_findings_hash: {previous_hash!r}")

    current_hash = findings_hash(findings) if findings else None
    details = findings if show_details else []
    common = {"findings_count": len(findings), "details": details}

    def out(action, rule, reason, carry=True):
        rebuild_hash = previous_hash if (carry and findings) else None
        return decision(action, rule, reason, rebuild_findings_hash=rebuild_hash, **common)

    if not attested:
        return out("fail", 5, f"provenance check failed for {digest}")

    for label, when in (("image.created", created), ("head.pushed_at", head_pushed)):
        if when > now + FUTURE_SKEW:
            return out("fail", 6, f"timestamp in the future: {label}")

    image_age = now - created

    if revision != head_sha and now - head_pushed >= BEHIND_MAIN_GRACE:
        return out("fail", 7, f"image revision {revision[:7]} behind {default_branch} {head_sha[:7]}: build for HEAD failed or never ran")

    stale_running = sorted(d for d in running_digests if d != digest)
    if stale_running and image_age >= DEPLOY_GRACE:
        return out("fail", 8, f"deployed {stale_running[0]} != registry {digest}: image-updater or ArgoCD stalled")

    if scan == "pending":
        if image_age < SCAN_GRACE:
            return out("ok", 9, "scan pending")
        return out("fail", 10, "image not scanned by Xray after 2h")

    if last and last["status"] in {"queued", "in_progress"}:
        if now - last["created"] < DISPATCH_STUCK:
            return out("ok", 11, "rebuild in progress")
        return out("fail", 12, f"rebuild stuck: {last['url']}")

    if last and last["status"] == "failure" and now - last["created"] < DISPATCH_FAILURE_WINDOW:
        return out("fail", 13, f"rebuild failed: {last['url']}")

    if findings:
        if previous_hash is not None and previous_hash == current_hash:
            return out("fail", 14, f"findings survived a rebuild: needs a code change or an upstream fix: {len(findings)}")
        if last and last["status"] == "success" and now - last["created"] < REBUILD_RATE_LIMIT:
            until = (last["created"] + REBUILD_RATE_LIMIT).strftime("%Y-%m-%dT%H:%M:%SZ")
            return out("ok", 15, f"rebuild rate-limited until {until}")
        return decision("rebuild", 16, f"fixable findings: {len(findings)}", rebuild_findings_hash=current_hash, **common)

    if image_age > timedelta(days=max_age_days):
        return out("rebuild", 17, f"max age exceeded: {image_age.days}d", carry=False)

    return out("ok", 18, "fresh", carry=False)


def main(argv):
    if len(argv) != 2:
        print("usage: decide.py FACTS_JSON", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as handle:
            facts = json.load(handle)
        if not isinstance(facts, dict):
            raise ValueError("top level is not an object")
        result = decide(facts)
    except (OSError, ValueError) as exc:
        result = decision("fail", 3, f"fact gathering failed: input: {exc}")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
