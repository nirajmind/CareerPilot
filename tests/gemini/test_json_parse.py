def test_safe_json_parse_valid(gemini):
    data = gemini.safe_json_parse('{"a": 1}')
    assert data["a"] == 1


def test_safe_json_parse_markdown(gemini):
    data = gemini.safe_json_parse("```json\n{\"a\": 1}\n```")
    assert data["a"] == 1


def test_safe_json_parse_repair(gemini):
    data = gemini.safe_json_parse("{\"a\": 1,}")
    assert data["a"] == 1


def test_safe_json_parse_fallback(gemini):
    data = gemini.safe_json_parse("not json")
    assert "raw_text" in data
