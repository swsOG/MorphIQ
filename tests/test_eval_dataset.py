"""Tests for the committed golden manifest and dataset loader."""

import json
from collections import Counter

from eval import config
from eval import dataset


def test_manifest_loads_with_minimum_cases():
    cases = dataset.load_cases()
    assert len(cases) >= 120


def test_at_least_twenty_cases_per_doc_type():
    counts = Counter(c.doc_type for c in dataset.load_cases())
    for doc_type in config.DOC_TYPES:
        assert counts[doc_type] >= 20, f"{doc_type} has only {counts[doc_type]} cases"


def test_every_case_has_valid_recording_and_ground_truth():
    for case in dataset.load_cases():
        assert case.recording.get("detection"), f"{case.id} missing detection recording"
        assert "extraction" in case.recording, f"{case.id} missing extraction recording"
        # Extraction recording must be valid JSON.
        json.loads(case.recording["extraction"])
        assert isinstance(case.expected_fields, dict)
        assert isinstance(case.required_fields, list)


def test_edge_cases_are_represented():
    edges = Counter(c.edge_case for c in dataset.load_cases())
    for expected_edge in ("poor_ocr", "rotated", "multi_page", "missing_fields",
                          "other_type", "detection_error"):
        assert edges[expected_edge] > 0, f"no '{expected_edge}' edge cases in dataset"
