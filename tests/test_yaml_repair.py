"""Tests for recovering model responses that contain non-YAML separator lines."""

import yaml

from pr_agent.algo.utils import load_yaml, remove_foreign_separator_lines

SUGGESTIONS_KEYS = ["relevant_file", "suggestion_content", "existing_code", "improved_code"]

# The shape a model produced in the wild: valid YAML with a markdown-style horizontal rule
# emitted between two sequence items.
RESPONSE_WITH_SEPARATOR = """\
code_suggestions:
- relevant_file: |
    src/client.py
  language: python
  suggestion_content: |
    Use a context manager for the HTTP client.
  existing_code: |
    client = httpx.Client(base_url=base_url)
  improved_code: |
    with httpx.Client(base_url=base_url) as client:
        ...
  one_sentence_summary: |
    Close the client deterministically.
  label: |
    best practice
=======
  relevant_file: |
    src/other.py
  language: python
  suggestion_content: |
    Second suggestion.
  existing_code: |
    x = 1
  improved_code: |
    x = 2
  one_sentence_summary: |
    Bump x.
  label: |
    possible issue
"""


def _load(text):
    return load_yaml(text, keys_fix_yaml=SUGGESTIONS_KEYS,
                     first_key="code_suggestions", last_key="label")


def test_response_with_separator_is_unparseable_without_repair():
    try:
        yaml.safe_load(RESPONSE_WITH_SEPARATOR)
    except yaml.YAMLError:
        return
    raise AssertionError("expected the raw response to be invalid YAML")


def test_separator_between_items_keeps_both_entries_intact():
    data = _load(RESPONSE_WITH_SEPARATOR)
    assert data is not None, "the response should be recovered"
    suggestions = data["code_suggestions"]
    assert len(suggestions) == 2, "both suggestions should survive the repair"
    # each suggestion keeps its own file: merging them would attribute suggestion #2's code
    # to suggestion #1's file
    assert suggestions[0]["relevant_file"].strip() == "src/client.py"
    assert suggestions[0]["existing_code"].strip() == "client = httpx.Client(base_url=base_url)"
    assert suggestions[1]["relevant_file"].strip() == "src/other.py"
    assert suggestions[1]["existing_code"].strip() == "x = 1"


def test_incomplete_trailing_item_is_kept_separate_not_merged():
    # the model omitted 'relevant_file' from the second entry; it must not inherit the first's
    response = RESPONSE_WITH_SEPARATOR.replace("  relevant_file: |\n    src/other.py\n", "")
    data = _load(response)
    suggestions = data["code_suggestions"]
    assert len(suggestions) == 2
    assert suggestions[0]["relevant_file"].strip() == "src/client.py"
    assert "relevant_file" not in suggestions[1]


def test_document_separator_is_not_treated_as_a_foreign_line():
    text = "---\nkey: value\n"
    assert remove_foreign_separator_lines(text) == text


def test_separator_outside_a_sequence_is_dropped():
    text = "review:\n  summary: |\n    ok\n***\n"
    assert remove_foreign_separator_lines(text) == "review:\n  summary: |\n    ok\n"


def test_separator_inside_a_block_scalar_is_left_alone():
    # a markdown rule that is genuinely part of the suggested code must survive untouched
    text = (
        "code_suggestions:\n"
        "- relevant_file: |\n"
        "    README.md\n"
        "  improved_code: |\n"
        "    Title\n"
        "    =====\n"
        "    body\n"
    )
    assert remove_foreign_separator_lines(text) == text
    data = yaml.safe_load(text)
    assert data["code_suggestions"][0]["improved_code"] == "Title\n=====\nbody\n"


def test_text_without_separators_is_unchanged():
    text = "code_suggestions:\n- relevant_file: |\n    a.py\n  label: |\n    other\n"
    assert remove_foreign_separator_lines(text) == text


def test_indented_sequence_items_keep_their_alignment():
    text = (
        "root:\n"
        "  items:\n"
        "  - name: |\n"
        "      first\n"
        "    label: a\n"
        "  =====\n"
        "    name: |\n"
        "      second\n"
        "    label: b\n"
    )
    data = yaml.safe_load(remove_foreign_separator_lines(text))
    assert [item["name"].strip() for item in data["root"]["items"]] == ["first", "second"]
    assert [item["label"] for item in data["root"]["items"]] == ["a", "b"]
