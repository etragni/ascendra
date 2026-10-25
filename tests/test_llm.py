import pytest

from ascendra.llm import LLMError, extract_json


def test_extract_json_with_fences():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_error():
    with pytest.raises(LLMError):
        extract_json("no json here")
