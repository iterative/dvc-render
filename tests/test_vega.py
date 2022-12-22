import json

import pytest

from dvc_render.vega import BadTemplateError, VegaRenderer
from dvc_render.vega_templates import NoFieldInDataError, Template

# pylint: disable=missing-function-docstring, C1803


@pytest.mark.parametrize(
    "extension, matches",
    (
        (".csv", True),
        (".json", True),
        (".tsv", True),
        (".yaml", True),
        (".jpg", False),
        (".gif", False),
        (".jpeg", False),
        (".png", False),
        (".svg", False),
    ),
)
def test_matches(extension, matches):
    assert VegaRenderer.matches("file" + extension, {}) == matches


def test_init_empty():
    renderer = VegaRenderer(None, None)

    assert renderer.datapoints == []
    assert renderer.name == ""
    assert renderer.properties == {}

    assert renderer.generate_html() == ""
    assert renderer.generate_markdown("foo") == ""


def test_default_template_mark():
    datapoints = [
        {"first_val": 100, "second_val": 100, "val": 2},
        {"first_val": 200, "second_val": 300, "val": 3},
    ]

    plot_content = json.loads(VegaRenderer(datapoints, "foo").partial_html())

    assert plot_content["mark"] == {
        "type": "line",
        "point": True,
        "tooltip": {"content": "data"},
    }


def test_choose_axes():
    props = {"x": "first_val", "y": "second_val"}
    datapoints = [
        {"first_val": 100, "second_val": 100, "val": 2},
        {"first_val": 200, "second_val": 300, "val": 3},
    ]

    plot_content = json.loads(
        VegaRenderer(datapoints, "foo", **props).partial_html()
    )

    assert plot_content["data"]["values"] == [
        {
            "val": 2,
            "first_val": 100,
            "second_val": 100,
        },
        {
            "val": 3,
            "first_val": 200,
            "second_val": 300,
        },
    ]
    assert plot_content["encoding"]["x"]["field"] == "first_val"
    assert plot_content["encoding"]["y"]["field"] == "second_val"


def test_confusion():
    datapoints = [
        {"predicted": "B", "actual": "A"},
        {"predicted": "A", "actual": "A"},
    ]
    props = {"template": "confusion", "x": "predicted", "y": "actual"}

    plot_content = json.loads(
        VegaRenderer(datapoints, "foo", **props).partial_html()
    )

    assert plot_content["data"]["values"] == [
        {"predicted": "B", "actual": "A"},
        {"predicted": "A", "actual": "A"},
    ]
    assert plot_content["spec"]["transform"][0]["groupby"] == [
        "actual",
        "predicted",
    ]
    assert plot_content["spec"]["encoding"]["x"]["field"] == "predicted"
    assert plot_content["spec"]["encoding"]["y"]["field"] == "actual"


def test_bad_template():
    datapoints = [{"val": 2}, {"val": 3}]
    props = {"template": Template("name", "content")}
    renderer = VegaRenderer(datapoints, "foo", **props)
    with pytest.raises(BadTemplateError):
        renderer.get_filled_template()
    renderer.get_filled_template(skip_anchors=["data"])


def test_raise_on_wrong_field():
    datapoints = [{"val": 2}, {"val": 3}]
    props = {"x": "no_val"}
    renderer = VegaRenderer(datapoints, "foo", **props)
    with pytest.raises(NoFieldInDataError):
        renderer.get_filled_template()
    renderer.get_filled_template(strict=False)


@pytest.mark.parametrize("name", ["foo", "foo/bar", "foo/bar.tsv"])
def test_generate_markdown(tmp_dir, mocker, name):
    import matplotlib.pyplot

    plot = mocker.spy(matplotlib.pyplot, "plot")
    title = mocker.spy(matplotlib.pyplot, "title")
    xlabel = mocker.spy(matplotlib.pyplot, "xlabel")
    ylabel = mocker.spy(matplotlib.pyplot, "ylabel")
    savefig = mocker.spy(matplotlib.pyplot, "savefig")

    props = {"x": "first_val", "y": "second_val", "title": "FOO"}
    datapoints = [
        {"first_val": 100.0, "second_val": 100.0, "val": 2.0},
        {"first_val": 200.0, "second_val": 300.0, "val": 3.0},
    ]
    renderer = VegaRenderer(datapoints, name, **props)

    (tmp_dir / "output").mkdir()
    renderer.generate_markdown(tmp_dir / "output" / "report.md")

    assert (tmp_dir / "output" / renderer.name).with_suffix(".png").exists()
    plot.assert_called_with(
        "first_val",
        "second_val",
        data={
            "first_val": [100.0, 200.0],
            "second_val": [100.0, 300.0],
            "val": [2, 3],
        },
    )
    title.assert_called_with("FOO")
    xlabel.assert_called_with("first_val")
    ylabel.assert_called_with("second_val")
    savefig.assert_called_with((tmp_dir / "output" / name).with_suffix(".png"))


def test_unsupported_template():
    datapoints = [
        {"predicted": "B", "actual": "A"},
        {"predicted": "A", "actual": "A"},
    ]
    props = {"template": "confusion", "x": "predicted", "y": "actual"}

    renderer = VegaRenderer(datapoints, "foo", **props)

    # Skip with warning instead of raising exception
    with pytest.warns(
        match="`generate_markdown` can only be used with `LinearTemplate`"
    ):
        out = renderer.generate_markdown("output")
    assert out == ""


def test_escape_special_characters():
    datapoints = [
        {"foo.bar[0]": 0, "foo.bar[1]": 3},
        {"foo.bar[0]": 1, "foo.bar[1]": 4},
    ]
    props = {"template": "simple", "x": "foo.bar[0]", "y": "foo.bar[1]"}
    renderer = VegaRenderer(datapoints, "foo", **props)
    filled = json.loads(renderer.get_filled_template())
    # data is not escaped
    assert filled["data"]["values"][0] == datapoints[0]
    # field and title yes
    assert filled["encoding"]["x"]["field"] == "foo\\.bar\\[0\\]"
    assert filled["encoding"]["x"]["title"] == "foo.bar[0]"
    assert filled["encoding"]["y"]["field"] == "foo\\.bar\\[1\\]"
    assert filled["encoding"]["y"]["title"] == "foo.bar[1]"
