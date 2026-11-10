"""Unit tests for the eval-script pure helpers.

These mock nothing and call no network: they exercise only the hit-rate
calculation, question loading, and scored/no-source partitioning.
"""
import json
from pathlib import Path

from eval.run_eval import hit_rate_percent, is_hit, load_questions, partition_questions


def test_load_questions_reads_json_array(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps([{"question": "q?", "expected_filename": "a.txt"}]))
    assert load_questions(path) == [{"question": "q?", "expected_filename": "a.txt"}]


def test_partition_questions_separates_null_expected():
    questions = [
        {"question": "q1", "expected_filename": "a.txt"},
        {"question": "q2", "expected_filename": None},
        {"question": "q3", "expected_filename": "b.txt"},
        {"question": "q4", "expected_filename": None},
    ]
    scored, no_source = partition_questions(questions)
    assert [q["question"] for q in scored] == ["q1", "q3"]
    assert [q["question"] for q in no_source] == ["q2", "q4"]


def test_is_hit_matches_filename():
    assert is_hit("a.txt", ["b.txt", "a.txt", "c.txt"]) is True
    assert is_hit("a.txt", ["b.txt", "c.txt"]) is False
    assert is_hit("a.txt", []) is False
    assert is_hit(None, ["a.txt"]) is False


def test_hit_rate():
    assert hit_rate_percent(0, 0) == 0.0
    assert hit_rate_percent(0, 10) == 0.0
    assert hit_rate_percent(10, 10) == 100.0
    assert hit_rate_percent(13, 17) == 76.5
