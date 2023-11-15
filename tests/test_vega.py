import json
from typing import Any, Dict, List

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

    plot_content = VegaRenderer(datapoints, "foo").get_filled_template()

    assert plot_content["layer"][0]["layer"][0]["mark"] == "line"

    assert plot_content["layer"][1]["mark"] == {"type": "line", "opacity": 0.2}

    assert plot_content["layer"][2]["mark"] == {"type": "circle", "size": 10}


def test_choose_axes():
    props = {"x": "first_val", "y": "second_val"}
    datapoints = [
        {"first_val": 100, "second_val": 100, "val": 2},
        {"first_val": 200, "second_val": 300, "val": 3},
    ]

    plot_content = VegaRenderer(datapoints, "foo", **props).get_filled_template()

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
    assert plot_content["layer"][0]["encoding"]["y"]["field"] == "second_val"


def test_confusion():
    datapoints = [
        {"predicted": "B", "actual": "A"},
        {"predicted": "A", "actual": "A"},
    ]
    props = {"template": "confusion", "x": "predicted", "y": "actual"}

    plot_content = VegaRenderer(datapoints, "foo", **props).get_filled_template()

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
    filled = renderer.get_filled_template()
    # data is not escaped
    assert filled["data"]["values"][0] == datapoints[0]
    # field and title yes
    assert filled["encoding"]["x"]["field"] == "foo\\.bar\\[0\\]"
    assert filled["encoding"]["x"]["title"] == "foo.bar[0]"
    assert filled["encoding"]["y"]["field"] == "foo\\.bar\\[1\\]"
    assert filled["encoding"]["y"]["title"] == "foo.bar[1]"


def test_fill_anchor_in_string(tmp_dir):
    y = "lab"
    x = "SR"
    tmp_dir.gen(
        "custom.json",
        json.dumps(
            {
                "data": {"values": Template.anchor("data")},
                "transform": [
                    {"joinaggregate": [{"op": "mean", "field": "lab", "as": "mean_y"}]},
                    {
                        "calculate": "pow("
                        + "datum.<DVC_METRIC_Y> - datum.<DVC_METRIC_X>,2"
                        + ")",
                        "as": "SR",
                    },
                    {"joinaggregate": [{"op": "sum", "field": "SR", "as": "SSR"}]},
                ],
                "encoding": {
                    "x": {"field": Template.anchor("x")},
                    "y": {"field": Template.anchor("y")},
                },
            },
        ),
    )
    datapoints = [
        {x: "B", y: "A"},
        {x: "A", y: "A"},
    ]
    props = {"template": "custom.json", "x": x, "y": y}

    renderer = VegaRenderer(datapoints, "foo", **props)
    filled = renderer.get_filled_template()
    assert filled["transform"][1]["calculate"] == "pow(datum.lab - datum.SR,2)"
    assert filled["encoding"]["x"]["field"] == x
    assert filled["encoding"]["y"]["field"] == y


@pytest.mark.parametrize(
    ",".join(
        [
            "datapoints",
            "y",
            "anchors_y_definitions",
            "expected_dp_keys",
            "color_encoding",
            "stroke_dash_encoding",
            "pivot_field",
            "group_by",
        ]
    ),
    (
        (
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "acc": "0.1",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
            ],
            "acc",
            [{"filename": "test", "field": "acc"}],
            ["rev", "acc", "step"],
            {
                "field": "rev",
                "scale": {"domain": ["B"], "range": ["#945dd6"]},
            },
            {},
            "datum.rev",
            ["rev"],
        ),
        (
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "acc": "0.1",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "acc": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "acc": "0.09",
                    "filename": "train",
                    "field": "acc",
                    "step": 2,
                },
            ],
            "acc",
            [
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
            ["rev", "acc", "step", "filename"],
            {
                "field": "rev",
                "scale": {"domain": ["B"], "range": ["#945dd6"]},
            },
            {
                "field": "filename",
                "scale": {"domain": ["test", "train"], "range": [[1, 0], [8, 8]]},
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.filename",
            ["rev", "filename"],
        ),
        (
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.1",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "filename": "train",
                    "field": "acc_norm",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.09",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 2,
                },
            ],
            "dvc_inferred_y_value",
            [
                {"filename": "test", "field": "acc"},
                {"filename": "test", "field": "acc_norm"},
            ],
            ["rev", "dvc_inferred_y_value", "step", "field"],
            {
                "field": "rev",
                "scale": {"domain": ["B"], "range": ["#945dd6"]},
            },
            {
                "field": "field",
                "scale": {"domain": ["acc", "acc_norm"], "range": [[1, 0], [8, 8]]},
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.field",
            ["rev", "field"],
        ),
        (
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.1",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.09",
                    "filename": "train",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.02",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.07",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 2,
                },
            ],
            "dvc_inferred_y_value",
            [
                {"filename": "test", "field": "acc_norm"},
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
            ["rev", "dvc_inferred_y_value", "step", "filename::field"],
            {
                "field": "rev",
                "scale": {"domain": ["B"], "range": ["#945dd6"]},
            },
            {
                "field": "filename::field",
                "scale": {
                    "domain": ["test::acc", "test::acc_norm", "train::acc"],
                    "range": [[1, 0], [8, 8], [8, 4]],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.filename + '::' + datum.field",
            ["rev", "filename::field"],
        ),
    ),
)
def test_optional_anchors_linear(
    datapoints,
    y,
    anchors_y_definitions,
    expected_dp_keys,
    color_encoding,
    stroke_dash_encoding,
    pivot_field,
    group_by,
):  # pylint: disable=too-many-arguments
    props = {
        "template": "linear",
        "x": "step",
        "y": y,
        "revs_with_datapoints": ["B"],
        "anchors_y_definitions": anchors_y_definitions,
    }

    expected_datapoints = _get_expected_datapoints(datapoints, expected_dp_keys)

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["data"]["values"] == expected_datapoints
    assert plot_content["encoding"]["color"] == color_encoding
    assert plot_content["encoding"]["strokeDash"] == stroke_dash_encoding
    assert plot_content["layer"][3]["transform"][0]["calculate"] == pivot_field
    assert plot_content["layer"][0]["transform"][0]["groupby"] == group_by


@pytest.mark.parametrize(
    "datapoints,y,anchors_y_definitions,expected_dp_keys,stroke_dash_encoding",
    (
        (
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "acc": "0.1",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
            ],
            "acc",
            [{"filename": "test", "field": "acc"}],
            ["rev", "acc", "step"],
            {},
        ),
        (
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "filename": "train",
                    "field": "acc_norm",
                    "step": 1,
                },
            ],
            "dvc_inferred_y_value",
            [
                {"filename": "test", "field": "acc"},
                {"filename": "test", "field": "acc_norm"},
            ],
            ["rev", "dvc_inferred_y_value", "step", "field"],
            {
                "field": "field",
                "scale": {"domain": ["acc", "acc_norm"], "range": [[1, 0], [8, 8]]},
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
        ),
        (
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.02",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 1,
                },
            ],
            "dvc_inferred_y_value",
            [
                {"filename": "test", "field": "acc_norm"},
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
            ["rev", "dvc_inferred_y_value", "step", "filename::field"],
            {
                "field": "filename::field",
                "scale": {
                    "domain": ["test::acc", "test::acc_norm", "train::acc"],
                    "range": [[1, 0], [8, 8], [8, 4]],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
        ),
    ),
)
def test_partial_filled_template(
    datapoints,
    y,
    anchors_y_definitions,
    expected_dp_keys,
    stroke_dash_encoding,
):
    title = f"{y} by step"
    props = {
        "template": "linear",
        "x": "step",
        "y": y,
        "revs_with_datapoints": ["B"],
        "anchors_y_definitions": anchors_y_definitions,
        "title": title,
    }

    expected_split = {
        Template.anchor("color"): {
            "field": "rev",
            "scale": {"domain": ["B"], "range": ["#945dd6"]},
        },
        Template.anchor("data"): _get_expected_datapoints(datapoints, expected_dp_keys),
        Template.anchor("plot_height"): 300,
        Template.anchor("plot_width"): 300,
        Template.anchor("title"): title,
        Template.anchor("x_label"): "step",
        Template.anchor("y_label"): y,
        Template.anchor("zoom_and_pan"): {
            "name": "grid",
            "select": "interval",
            "bind": "scales",
        },
    }

    split_anchors = [
        Template.anchor("color"),
        Template.anchor("data"),
    ]
    if len(anchors_y_definitions) > 1:
        split_anchors.append(Template.anchor("stroke_dash"))
        expected_split[Template.anchor("stroke_dash")] = stroke_dash_encoding

    content, split = VegaRenderer(
        datapoints, "foo", **props
    ).get_partial_filled_template()

    content_str = json.dumps(content)

    for anchor in split_anchors:
        assert anchor in content_str
    for key, value in split["anchor_definitions"].items():
        assert value == expected_split[key]


def _get_expected_datapoints(
    datapoints: List[Dict[str, Any]], expected_dp_keys: List[str]
):
    expected_datapoints: List[Dict[str, Any]] = []
    for datapoint in datapoints:
        expected_datapoint = {}
        for key in expected_dp_keys:
            if key == "filename::field":
                expected_datapoint[
                    key
                ] = f"{datapoint['filename']}::{datapoint['field']}"
            else:
                value = datapoint.get(key)
                if value is None:
                    continue
                expected_datapoint[key] = value
        expected_datapoints.append(expected_datapoint)

    return datapoints


def test_partial_html():
    props = {"x": "x", "y": "y"}
    datapoints = [
        {"x": 100, "y": 100, "val": 2},
        {"x": 200, "y": 300, "val": 3},
    ]

    assert isinstance(VegaRenderer(datapoints, "foo", **props).partial_html(), str)
