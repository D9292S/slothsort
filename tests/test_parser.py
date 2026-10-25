import pytest
from slothsort.categorizer import parse_llm_json


def test_parse_json_list():
    raw = '[{"original": "report.pdf", "category": "Documents", "renamed": "report.pdf", "reason": "pdf"}]'
    items = parse_llm_json(raw)
    assert len(items) == 1
    assert items[0].original == "report.pdf"
    assert items[0].category == "Documents"


def test_parse_wrapped_dict():
    raw = '{"files": [{"original": "photo.png", "category": "Images", "renamed": "photo.png", "reason": "png"}]}'
    items = parse_llm_json(raw)
    assert len(items) == 1
    assert items[0].original == "photo.png"
    assert items[0].category == "Images"


def test_parse_markdown_fenced_json():
    raw = """```json
    [
      {"original": "script.py", "category": "Code", "renamed": "script.py", "reason": "python script"}
    ]
    ```"""
    items = parse_llm_json(raw)
    assert len(items) == 1
    assert items[0].original == "script.py"
    assert items[0].category == "Code"


def test_parse_single_dict():
    raw = '{"original": "data.csv", "category": "Data", "renamed": "data.csv", "reason": "csv export"}'
    items = parse_llm_json(raw)
    assert len(items) == 1
    assert items[0].original == "data.csv"
