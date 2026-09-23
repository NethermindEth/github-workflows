.PHONY: test lint unit
test: lint unit ## everything CI runs

lint:
	tests/lint_workflows.sh

unit:
	python3 -m unittest discover -s image-freshness/tests
