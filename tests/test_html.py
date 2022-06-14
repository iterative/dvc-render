import pytest

from dvc_render.html import HTML, PAGE_HTML, MissingPlaceholderError

# pylint: disable=missing-function-docstring, R0801


CUSTOM_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>TITLE</title>
    <script type="text/javascript" src="vega"></script>
    <script type="text/javascript" src="vega-lite"></script>
    <script type="text/javascript" src="vega-embed"></script>
</head>
<body>
    {plot_divs}
</body>
</html>"""

CSS_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>TITLE</title>
    <script type="text/javascript" src="vega"></script>
    <script type="text/javascript" src="vega-lite"></script>
    <script type="text/javascript" src="vega-embed"></script>
    <style>
        .test-malformed{
            color: red;
        }
    </style>
</head>
<body>
    {plot_divs}
</body>
</html>"""


@pytest.mark.parametrize(
    "template,page_elements,expected_page",
    [
        (
            None,
            ["content"],
            PAGE_HTML.replace("{plot_divs}", "content")
            .replace("{scripts}", "")
            .replace("{refresh_tag}", ""),
        ),
        (
            CUSTOM_PAGE_HTML,
            ["content"],
            CUSTOM_PAGE_HTML.format(plot_divs="content"),
        ),
        (
            CSS_PAGE_HTML,
            ["content"],
            CSS_PAGE_HTML.replace("{plot_divs}", "content"),
        ),
    ],
)
def test_html(template, page_elements, expected_page):
    page = HTML(template)
    page.elements = page_elements

    result = page.embed()

    assert result == expected_page


def test_no_placeholder():
    template = "<head></head><body></body>"

    with pytest.raises(MissingPlaceholderError):
        HTML(template)
