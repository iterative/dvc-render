# pylint: disable=missing-function-docstring, R0801
import os

import pytest
from dvc_render.html import (
    HTML,
    PAGE_HTML,
    MissingPlaceholderError,
    _order_image_per_step,
    render_html,
)
from dvc_render.image import ImageRenderer
from dvc_render.vega import VegaRenderer

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
    ("template", "page_elements", "expected_page"),
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


def test_render_html_with_custom_template(mocker, tmp_path):
    output_file = tmp_path / "output_file"

    render_html(mocker.MagicMock(), output_file)
    assert output_file.read_text() == PAGE_HTML.replace("{plot_divs}", "").replace(
        "{scripts}", ""
    ).replace("{refresh_tag}", "")

    render_html(mocker.MagicMock(), output_file, CUSTOM_PAGE_HTML)
    assert output_file.read_text() == CUSTOM_PAGE_HTML.format(plot_divs="")

    custom_template = tmp_path / "custom_template"
    custom_template.write_text(CUSTOM_PAGE_HTML)
    render_html(mocker.MagicMock(), output_file, custom_template)
    assert output_file.read_text() == CUSTOM_PAGE_HTML.format(plot_divs="")


def test_order_image_per_step():
    image_per_step_dir = "dvclive"
    other_image_dir = "static"

    def create_renderer(filename: str) -> ImageRenderer:
        return ImageRenderer(
            [
                {
                    "filename": filename,
                    "rev": "workspace",
                    "src": filename,
                }
            ],
            filename,
        )

    r1 = VegaRenderer([], "dvc.yaml::Loss")
    r2 = VegaRenderer([], "dvc.yaml::Accuracy")
    r3 = create_renderer(os.path.join(image_per_step_dir, "0.jpg"))
    r4 = create_renderer(os.path.join(image_per_step_dir, "1.jpg"))
    r5 = create_renderer(os.path.join(image_per_step_dir, "2.jpg"))
    r6 = create_renderer(os.path.join(image_per_step_dir, "10.jpg"))
    r7 = create_renderer(os.path.join(other_image_dir, "a_file.jpg"))
    r8 = create_renderer(os.path.join(other_image_dir, "z_file.jpg"))

    renderers = [r7, r3, r5, r8, r1, r6, r4, r2]

    assert sorted(renderers, key=_order_image_per_step) == [
        r1,
        r2,
        r3,
        r4,
        r5,
        r6,
        r7,
        r8,
    ]


def test_no_placeholder():
    template = "<head></head><body></body>"

    with pytest.raises(MissingPlaceholderError):
        HTML(template)
