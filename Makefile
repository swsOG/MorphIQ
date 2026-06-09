.PHONY: eval eval-live eval-report test

# Build the golden dataset (synthetic PDFs) then run the offline eval + report.
# Windows users without `make` can run the two python commands directly.
eval:
	python eval/golden/generate_golden.py
	python -m eval.run_eval

# Measure the real Gemini model (requires GEMINI_API_KEY).
eval-live:
	python eval/golden/generate_golden.py
	python -m eval.run_eval --live

# Re-evaluate the threshold gate against the last results.json (no re-run).
eval-report:
	python -m eval.ci_gate

test:
	pytest -q
