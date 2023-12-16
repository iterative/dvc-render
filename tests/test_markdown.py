import pytest
from dvc_render.markdown import (
    PAGE_MARKDOWN,
    Markdown,
    MissingPlaceholderError,
    render_markdown,
)

# pylint: disable=missing-function-docstring, R0801


CUSTOM_PAGE_MARKDOWN = """# CUSTOM REPORT

{renderers}
"""


@pytest.mark.parametrize(
    ("template", "page_elements", "expected_page"),
    [
        (
            None,
            ["content"],
            PAGE_MARKDOWN.replace("{renderers}", "content"),
        ),
        (
            CUSTOM_PAGE_MARKDOWN,
            ["content"],
            CUSTOM_PAGE_MARKDOWN.format(renderers="content"),
        ),
    ],
)
def test_markdown(template, page_elements, expected_page):
    page = Markdown(template)
    page.elements = page_elements

    result = page.embed()

    assert result == expected_page


def test_no_placeholder():
    template = "# Missing Placeholder"

    with pytest.raises(MissingPlaceholderError):
        Markdown(template)


def test_render_markdown_to_file(tmp_path):
    output_file = tmp_path / "report"
    assert output_file == render_markdown([], output_file)


def test_render_markdown_no_file():
    assert "# DVC Report" in render_markdown([])
