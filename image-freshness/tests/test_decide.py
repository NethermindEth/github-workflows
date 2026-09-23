import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

import decide  # noqa: E402

DIGEST = "sha256:" + "a" * 64
OLD_DIGEST = "sha256:" + "b" * 64
HEAD = "1" * 40
OLD = "2" * 40
NOW = "2026-09-23T12:00:00Z"
FINDING = {"issue_id": "XRAY-1", "component": "openssl", "fixed_version": "3.5.1"}


def facts(**overrides):
    base = {
        "now": NOW,
        "config": {"default_branch": "main", "max_age_days": 7},
        "event": {"name": "schedule", "ref": "refs/heads/main"},
        "repo_visibility": {"status": "ok", "value": "internal"},
        "head": {"status": "ok", "value": {"sha": HEAD, "pushed_at": "2026-09-22T12:00:00Z"}},
        "image": {"status": "ok", "value": {"digest": DIGEST, "revision": HEAD, "created": "2026-09-22T12:10:00Z", "attested": True}},
        "running": {"status": "ok", "value": {"digests": [DIGEST]}},
        "xray": {"status": "ok", "value": {"scan": "done", "findings": []}},
        "last_dispatch": {"status": "none"},
        "previous": {"status": "none"},
    }
    for key, value in overrides.items():
        base[key] = value
    return base


def with_value(name, **fields):
    f = facts()
    f[name] = copy.deepcopy(f[name])
    f[name]["value"].update(fields)
    return f


def run(f):
    return decide.decide(f)


class RuleTests(unittest.TestCase):
    def assertDecision(self, result, action, rule, reason):
        self.assertEqual((result["action"], result["rule"], result["reason"]), (action, rule, reason))

    # rule 1
    def test_refuses_push_event(self):
        self.assertDecision(run(facts(event={"name": "push", "ref": "refs/heads/main"})), "fail", 1, "refused: runs only on schedule from the default branch")

    def test_refuses_other_branch(self):
        self.assertDecision(run(facts(event={"name": "schedule", "ref": "refs/heads/feature"})), "fail", 1, "refused: runs only on schedule from the default branch")

    def test_refuses_workflow_dispatch(self):
        self.assertDecision(run(facts(event={"name": "workflow_dispatch", "ref": "refs/heads/main"})), "fail", 1, "refused: runs only on schedule from the default branch")

    # rule 2
    def test_max_age_bounds(self):
        for bad in (0, 8, -1, "7", True, None):
            f = facts(config={"default_branch": "main", "max_age_days": bad})
            self.assertDecision(run(f), "fail", 2, f"invalid max_age_days: {bad!r}")
        for good in (1, 7):
            f = facts(config={"default_branch": "main", "max_age_days": good})
            self.assertEqual(run(f)["rule"], 18)

    # rule 3
    def test_error_fact_fails_closed(self):
        f = facts(xray={"status": "error", "detail": "HTTP 500 from /xray/api/v1/violations"})
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: xray: HTTP 500 from /xray/api/v1/violations")

    def test_missing_fact_fails_closed(self):
        f = facts()
        del f["previous"]
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: previous: missing")

    def test_unknown_status_fails_closed(self):
        f = facts(running={"status": "maybe"})
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: running: unexpected status 'maybe'")

    def test_bad_digest_fails_closed(self):
        f = with_value("image", digest="latest")
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: image: invalid digest: 'latest'")

    def test_bad_timestamp_fails_closed(self):
        f = with_value("image", created="2026-09-22 12:10:00")
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: image.created: expected RFC3339 UTC timestamp, got '2026-09-22 12:10:00'")

    def test_unknown_dispatch_status_fails_closed(self):
        f = facts(last_dispatch={"status": "ok", "value": {"status": "timed_out", "created_at": NOW, "url": "u"}})
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: last_dispatch: invalid status: 'timed_out'")

    def test_unknown_visibility_fails_closed(self):
        f = facts(repo_visibility={"status": "ok", "value": "secret"})
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: repo_visibility: unexpected value 'secret'")

    def test_empty_running_digests_fails_closed(self):
        f = with_value("running", digests=[])
        self.assertDecision(run(f), "fail", 3, "fact gathering failed: running: invalid digests: []")

    # rule 4
    def test_image_not_found(self):
        f = facts(image={"status": "not_found", "detail": "angkor-oci-local-prod/x:main"}, xray={"status": "error", "detail": "no digest"})
        self.assertDecision(run(f), "fail", 4, "image not found: angkor-oci-local-prod/x:main")

    # rule 5
    def test_unattested_image(self):
        self.assertDecision(run(with_value("image", attested=False)), "fail", 5, f"provenance check failed for {DIGEST}")

    # rule 6
    def test_future_created(self):
        self.assertDecision(run(with_value("image", created="2026-09-23T12:05:01Z")), "fail", 6, "timestamp in the future: image.created")

    def test_created_within_skew_is_allowed(self):
        self.assertEqual(run(with_value("image", created="2026-09-23T12:05:00Z"))["rule"], 18)

    def test_future_push(self):
        self.assertDecision(run(with_value("head", pushed_at="2026-09-24T00:00:00Z")), "fail", 6, "timestamp in the future: head.pushed_at")

    # rule 7
    def test_behind_main_after_grace(self):
        f = with_value("image", revision=OLD)
        f["head"]["value"]["pushed_at"] = "2026-09-23T11:00:00Z"
        self.assertDecision(run(f), "fail", 7, "image revision 2222222 behind main 1111111: build for HEAD failed or never ran")

    def test_behind_main_within_grace(self):
        f = with_value("image", revision=OLD)
        f["head"]["value"]["pushed_at"] = "2026-09-23T11:00:01Z"
        self.assertEqual(run(f)["rule"], 18)

    # rule 8
    def test_deploy_stalled(self):
        f = with_value("running", digests=[OLD_DIGEST])
        self.assertDecision(run(f), "fail", 8, f"deployed {OLD_DIGEST} != registry {DIGEST}: image-updater or ArgoCD stalled")

    def test_deploy_within_grace(self):
        f = with_value("running", digests=[OLD_DIGEST])
        f["image"]["value"]["created"] = "2026-09-23T11:30:01Z"
        self.assertEqual(run(f)["rule"], 18)

    def test_running_disabled_skips_rule_8(self):
        self.assertEqual(run(facts(running={"status": "disabled"}))["rule"], 18)

    # rules 9-10
    def test_scan_pending_within_grace(self):
        f = with_value("xray", scan="pending")
        f["image"]["value"]["created"] = "2026-09-23T10:00:01Z"
        f["running"]["value"]["digests"] = [DIGEST]
        self.assertDecision(run(f), "ok", 9, "scan pending")

    def test_scan_pending_too_long(self):
        f = with_value("xray", scan="pending")
        f["image"]["value"]["created"] = "2026-09-23T10:00:00Z"
        self.assertDecision(run(f), "fail", 10, "image not scanned by Xray after 2h")

    # rules 11-13
    def dispatch(self, status, created_at):
        return {"status": "ok", "value": {"status": status, "created_at": created_at, "url": "https://github.com/o/r/actions/runs/1"}}

    def test_rebuild_in_progress(self):
        f = facts(last_dispatch=self.dispatch("queued", "2026-09-23T11:00:01Z"))
        self.assertDecision(run(f), "ok", 11, "rebuild in progress")

    def test_rebuild_stuck(self):
        f = facts(last_dispatch=self.dispatch("in_progress", "2026-09-23T11:00:00Z"))
        self.assertDecision(run(f), "fail", 12, "rebuild stuck: https://github.com/o/r/actions/runs/1")

    def test_rebuild_failed_recently(self):
        f = facts(last_dispatch=self.dispatch("failure", "2026-09-22T12:00:01Z"))
        self.assertDecision(run(f), "fail", 13, "rebuild failed: https://github.com/o/r/actions/runs/1")

    def test_old_failure_is_ignored(self):
        f = facts(last_dispatch=self.dispatch("failure", "2026-09-22T12:00:00Z"))
        self.assertEqual(run(f)["rule"], 18)

    def test_cancelled_dispatch_counts_as_none(self):
        f = facts(last_dispatch=self.dispatch("cancelled", "2026-09-23T11:59:00Z"))
        self.assertEqual(run(f)["rule"], 18)

    # rules 14-16
    def test_findings_trigger_rebuild(self):
        result = run(with_value("xray", findings=[FINDING]))
        self.assertDecision(result, "rebuild", 16, "fixable findings: 1")
        self.assertEqual(result["rebuild_findings_hash"], decide.findings_hash([FINDING]))

    def test_same_findings_after_rebuild_fail(self):
        f = with_value("xray", findings=[FINDING])
        f["previous"] = {"status": "ok", "value": {"rebuild_findings_hash": decide.findings_hash([FINDING])}}
        result = run(f)
        self.assertDecision(result, "fail", 14, "findings survived a rebuild: needs a code change or an upstream fix: 1")
        self.assertEqual(result["rebuild_findings_hash"], decide.findings_hash([FINDING]))

    def test_new_findings_after_rebuild_rebuild_again(self):
        other = dict(FINDING, issue_id="XRAY-2")
        f = with_value("xray", findings=[FINDING, other])
        f["previous"] = {"status": "ok", "value": {"rebuild_findings_hash": decide.findings_hash([FINDING])}}
        self.assertEqual(run(f)["rule"], 16)

    def test_findings_hash_ignores_order(self):
        other = dict(FINDING, issue_id="XRAY-2")
        self.assertEqual(decide.findings_hash([FINDING, other]), decide.findings_hash([other, FINDING]))

    def test_rate_limited_after_recent_rebuild(self):
        f = with_value("xray", findings=[FINDING])
        f["last_dispatch"] = self.dispatch("success", "2026-09-23T06:00:01Z")
        f["previous"] = {"status": "ok", "value": {"rebuild_findings_hash": None}}
        self.assertDecision(run(f), "ok", 15, "rebuild rate-limited until 2026-09-23T12:00:01Z")

    def test_rate_limit_expires(self):
        f = with_value("xray", findings=[FINDING])
        f["last_dispatch"] = self.dispatch("success", "2026-09-23T06:00:00Z")
        self.assertEqual(run(f)["rule"], 16)

    def test_hash_carried_while_waiting(self):
        f = with_value("xray", findings=[FINDING])
        f["last_dispatch"] = self.dispatch("in_progress", "2026-09-23T11:30:00Z")
        f["previous"] = {"status": "ok", "value": {"rebuild_findings_hash": "sha256:prev"}}
        result = run(f)
        self.assertEqual((result["rule"], result["rebuild_findings_hash"]), (11, "sha256:prev"))

    def test_hash_reset_when_clean(self):
        f = facts(previous={"status": "ok", "value": {"rebuild_findings_hash": "sha256:prev"}})
        self.assertIsNone(run(f)["rebuild_findings_hash"])

    # rules 17-18
    def test_max_age_rebuild(self):
        f = with_value("image", created="2026-09-16T11:59:59Z")
        f["head"]["value"]["pushed_at"] = "2026-09-16T11:00:00Z"
        self.assertDecision(run(f), "rebuild", 17, "max age exceeded: 7d")

    def test_exactly_max_age_is_fresh(self):
        f = with_value("image", created="2026-09-16T12:00:00Z")
        f["head"]["value"]["pushed_at"] = "2026-09-16T11:00:00Z"
        self.assertDecision(run(f), "ok", 18, "fresh")

    def test_first_run_fresh(self):
        self.assertDecision(run(facts()), "ok", 18, "fresh")

    # details visibility
    def test_details_hidden_for_public_repos(self):
        f = with_value("xray", findings=[FINDING])
        f["repo_visibility"] = {"status": "ok", "value": "public"}
        result = run(f)
        self.assertEqual((result["findings_count"], result["details"]), (1, []))

    def test_details_shown_for_internal_repos(self):
        self.assertEqual(run(with_value("xray", findings=[FINDING]))["details"], [FINDING])


class CliTests(unittest.TestCase):
    def cli(self, content):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write(content)
        try:
            proc = subprocess.run([sys.executable, os.path.join(HERE, "..", "decide.py"), handle.name], capture_output=True, text=True, check=False)
        finally:
            os.unlink(handle.name)
        return proc.returncode, json.loads(proc.stdout)

    def test_cli_prints_decision(self):
        code, out = self.cli(json.dumps(facts()))
        self.assertEqual((code, out["action"], out["rule"]), (0, "ok", 18))

    def test_cli_malformed_json_fails_closed(self):
        code, out = self.cli("{not json")
        self.assertEqual((code, out["action"], out["rule"]), (0, "fail", 3))
        self.assertTrue(out["reason"].startswith("fact gathering failed: input: "))

    def test_cli_non_object_fails_closed(self):
        code, out = self.cli("[]")
        self.assertEqual(out["reason"], "fact gathering failed: input: top level is not an object")


if __name__ == "__main__":
    unittest.main()
