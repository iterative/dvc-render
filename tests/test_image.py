import os

import pytest

from dvc_render.image import ImageRenderer

# pylint: disable=missing-function-docstring


@pytest.mark.parametrize(
    "extension, matches",
    (
        (".csv", False),
        (".json", False),
        (".tsv", False),
        (".yaml", False),
        (".jpg", True),
        (".gif", True),
        (".jpeg", True),
        (".png", True),
        (".svg", True),
    ),
)
def test_matches(extension, matches):
    filename = "file" + extension
    assert ImageRenderer.matches(filename, {}) == matches


@pytest.mark.parametrize("html_path", [None, "/output/dir/index.html"])
@pytest.mark.parametrize(
    "src", ["relpath.jpg", "data:image;base64,encoded_image"]
)
def test_generate_html(html_path, src):
    datapoints = [
        {
            "filename": "file.jpg",
            "rev": "workspace",
            "src": src,
        }
    ]

    html = ImageRenderer(datapoints, "file.jpg").generate_html(
        html_path=html_path
    )

    assert "<p>file.jpg</p>" in html
    assert f'<img src="{src}">' in html


def test_generate_markdown():
    datapoints = [
        {
            "rev": "workspace",
            "src": "file.jpg",
        }
    ]

    md = ImageRenderer(datapoints, "file.jpg").generate_markdown()

    assert "![workspace](file.jpg)" in md


def test_invalid_generate_markdown():
    datapoints = [
        {
            "rev": "workspace",
            "src": "data:image;base64,encoded_image",
        }
    ]
    with pytest.raises(
        ValueError, match="`generate_markdown` doesn't support base64"
    ):
        ImageRenderer(datapoints, "file.jpg").generate_markdown()


@pytest.mark.parametrize(
    "html_path,img_path,expected_path",
    [
        (
            os.path.join("output", "path", "index.html"),
            os.path.join("output", "path", "with", "static", "file.jpg"),
            os.path.join("with", "static", "file.jpg"),
        ),
        (
            os.path.join("output", "one", "path", "index.html"),
            os.path.join("output", "second", "path", "file.jpg"),
            os.path.join("..", "..", "second", "path", "file.jpg"),
        ),
    ],
)
def test_render_evaluate_path(tmp_dir, html_path, img_path, expected_path):
    abs_html_path = tmp_dir / html_path
    abs_img_path = tmp_dir / img_path

    datapoints = [
        {
            "filename": "file.jpg",
            "rev": "workspace",
            "src": str(abs_img_path),
        }
    ]

    html = ImageRenderer(datapoints, "file.jpg").generate_html(
        html_path=abs_html_path
    )

    assert "<p>file.jpg</p>" in html
    assert f'<img src="{expected_path}">' in html


@pytest.mark.parametrize("method", ["generate_html", "generate_markdown"])
def test_render_empty(method):
    renderer = ImageRenderer(None, None)
    assert getattr(renderer, method)() == ""
