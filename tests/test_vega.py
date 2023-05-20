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

    assert renderer.generate_markdown("foo") == ""


def test_default_template_mark():
    datapoints = [
        {"first_val": 100, "second_val": 100, "val": 2},
        {"first_val": 200, "second_val": 300, "val": 3},
    ]

    plot_content = VegaRenderer(datapoints, "foo").get_filled_template(as_string=False)

    assert plot_content["layer"][0]["mark"] == "line"

    assert plot_content["layer"][1]["mark"] == {"type": "line", "opacity": 0.2}

    assert plot_content["layer"][2]["mark"] == {
        "type": "circle",
        "size": 10,
        "tooltip": {"content": "encoding"},
    }


def test_choose_axes():
    props = {"x": "first_val", "y": "second_val"}
    datapoints = [
        {"first_val": 100, "second_val": 100, "val": 2},
        {"first_val": 200, "second_val": 300, "val": 3},
    ]

    plot_content = VegaRenderer(datapoints, "foo", **props).get_filled_template(
        as_string=False
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
    assert plot_content["layer"][0]["encoding"]["x"]["field"] == "first_val"
    assert plot_content["layer"][0]["encoding"]["y"]["field"] == "second_val"


def test_confusion():
    datapoints = [
        {"predicted": "B", "actual": "A"},
        {"predicted": "A", "actual": "A"},
    ]
    props = {"template": "confusion", "x": "predicted", "y": "actual"}

    plot_content = VegaRenderer(datapoints, "foo", **props).get_filled_template(
        as_string=False
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


def test_bad_template_on_init():
    with pytest.raises(BadTemplateError):
        Template("name", "content")


@pytest.mark.parametrize(
    "bad_content,good_content",
    (
        (
            {"data": {"values": "BAD_ANCHOR"}},
            {"data": {"values": Template.anchor("data")}},
        ),
        (
            {"mark": {"type": "bar"}, "data": {"values": "BAD_ANCHOR"}},
            {"mark": {"type": "bar"}, "data": {"values": Template.anchor("data")}},
        ),
        (
            {"repeat": ["quintile"], "spec": {"data": {"values": "BAD_ANCHOR"}}},
            {
                "repeat": ["quintile"],
                "spec": {"data": {"values": Template.anchor("data")}},
            },
        ),
    ),
)
def test_bad_template_on_missing_data(tmp_dir, bad_content, good_content):
    tmp_dir.gen("bar.json", json.dumps(bad_content))
    datapoints = [{"val": 2}, {"val": 3}]
    renderer = VegaRenderer(datapoints, "foo", template="bar.json")

    with pytest.raises(BadTemplateError):
        renderer.get_filled_template()

    tmp_dir.gen("bar.json", json.dumps(good_content))
    renderer = VegaRenderer(datapoints, "foo", template="bar.json")
    assert renderer.get_filled_template()


def test_raise_on_wrong_field():
    datapoints = [{"val": 2}, {"val": 3}]
    props = {"x": "no_val"}
    renderer = VegaRenderer(datapoints, "foo", **props)
    with pytest.raises(NoFieldInDataError):
        renderer.get_filled_template()
    renderer.get_filled_template(strict=False)


@pytest.mark.parametrize("name", ["foo", "foo/bar", "foo/bar.tsv"])
@pytest.mark.parametrize("to_file", [True, False])
def test_generate_markdown(tmp_dir, mocker, name, to_file):
    # pylint: disable-msg=too-many-locals
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

    if to_file:
        report_folder = tmp_dir / "output"
        report_folder.mkdir()
        md = renderer.generate_markdown(tmp_dir / "output" / "report.md")
        output_file = (tmp_dir / "output" / renderer.name).with_suffix(".png")
        assert output_file.exists()
        savefig.assert_called_with(output_file)
        assert f"![{name}]({output_file.relative_to(report_folder)})" in md
    else:
        md = renderer.generate_markdown()
        assert f"![{name}](data:image/png;base64," in md

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
    filled = renderer.get_filled_template(as_string=False)
    # data is not escaped
    assert filled["data"]["values"][0] == datapoints[0]
    # field and title yes
    assert filled["encoding"]["x"]["field"] == "foo\\.bar\\[0\\]"
    assert filled["encoding"]["x"]["title"] == "foo.bar[0]"
    assert filled["encoding"]["y"]["field"] == "foo\\.bar\\[1\\]"
    assert filled["encoding"]["y"]["title"] == "foo.bar[1]"
