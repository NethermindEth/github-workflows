#!/usr/bin/env python3
"""Print the shell body of one step of a workflow, so the tests exercise the shipped code.

The watchdog's logic lives inline in the workflow rather than in a script file next to
it, because a reusable workflow runs in the *caller's* checkout: a script file in this
repository is simply not on disk when the workflow runs somewhere else, and the ways
around that (checking this repository out again at a ref the called workflow cannot
reliably know) add a failure mode to a thing whose entire job is to still be working.

Inline code is normally the end of testing, which is how a watchdog quietly stops
watching. So the tests read the step back out of the YAML and run that. One copy, and
the suite is pinned to the text that actually ships.
"""

import sys

import yaml


def main() -> int:
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} WORKFLOW JOB_ID STEP_ID", file=sys.stderr)
        return 2

    workflow_path, job_id, step_id = sys.argv[1:4]

    with open(workflow_path, encoding="utf-8") as handle:
        workflow = yaml.safe_load(handle)

    job = workflow.get("jobs", {}).get(job_id)
    if job is None:
        print(f"no job {job_id!r} in {workflow_path}", file=sys.stderr)
        return 1

    for step in job.get("steps", []):
        if step.get("id") != step_id:
            continue
        run = step.get("run")
        if run is None:
            print(f"step {step_id!r} has no run: block", file=sys.stderr)
            return 1
        sys.stdout.write(run)
        return 0

    print(f"no step {step_id!r} in job {job_id!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
