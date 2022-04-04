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
    ),
)
def test_matches(extension, matches):
    filename = "file" + extension
    assert ImageRenderer.matches(filename, {}) == matches


def test_render(tmp_dir):
    tmp_dir.gen("workspace_file.jpg", b"content")
    datapoints = [
        {
            "filename": "file.jpg",
            "rev": "workspace",
            "src": "workspace_file.jpg",
        }
    ]
    filename = "file.jpg"

    html = ImageRenderer(datapoints, filename).generate_html()

    assert "<p>file.jpg</p>" in html
    assert '<img src="workspace_file.jpg">' in html


def test_render_empty():
    html = ImageRenderer(None, None).generate_html()
    assert html == ""
