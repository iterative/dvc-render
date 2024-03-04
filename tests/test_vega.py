import json
import os
from typing import Any

import pytest
from dvc_render.vega import OPTIONAL_ANCHOR_RANGES, BadTemplateError, VegaRenderer
from dvc_render.vega_templates import NoFieldInDataError, Template

# pylint: disable=missing-function-docstring, C1803, C0302


@pytest.mark.parametrize(
    ("extension", "matches"),
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
    assert VegaRenderer.matches("file" + extension) == matches


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
    ("bad_content", "good_content"),
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
def test_bad_template_on_missing_data(tmp_path, bad_content, good_content):
    template_path = tmp_path / "bar.json"
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text(json.dumps(bad_content), encoding="utf-8")
    datapoints = [{"val": 2}, {"val": 3}]
    renderer = VegaRenderer(datapoints, "foo", template=template_path)

    with pytest.raises(BadTemplateError):
        renderer.get_filled_template()

    template_path.write_text(json.dumps(good_content), encoding="utf-8")
    renderer = VegaRenderer(datapoints, "foo", template=template_path)
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
def test_generate_markdown(tmp_path, mocker, name, to_file):
    # pylint: disable-msg=too-many-locals
    import matplotlib.pyplot as plt

    plot = mocker.spy(plt, "plot")
    title = mocker.spy(plt, "title")
    xlabel = mocker.spy(plt, "xlabel")
    ylabel = mocker.spy(plt, "ylabel")
    savefig = mocker.spy(plt, "savefig")

    props = {"x": "first_val", "y": "second_val", "title": "FOO"}
    datapoints = [
        {"first_val": 100.0, "second_val": 100.0, "val": 2.0},
        {"first_val": 200.0, "second_val": 300.0, "val": 3.0},
    ]
    renderer = VegaRenderer(datapoints, name, **props)

    if to_file:
        report_folder = tmp_path / "output"
        report_folder.mkdir()
        md = renderer.generate_markdown(tmp_path / "output" / "report.md")
        output_file = (tmp_path / "output" / renderer.name).with_suffix(".png")
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


def test_fill_anchor_in_string(tmp_path):
    y = "lab"
    x = "SR"
    template_content = {
        "data": {"values": Template.anchor("data")},
        "transform": [
            {"joinaggregate": [{"op": "mean", "field": "lab", "as": "mean_y"}]},
            {
                "calculate": "pow(datum.<DVC_METRIC_Y> - " "datum.<DVC_METRIC_X>,2)",
                "as": "SR",
            },
            {"joinaggregate": [{"op": "sum", "field": "SR", "as": "SSR"}]},
        ],
        "encoding": {
            "x": {"field": Template.anchor("x")},
            "y": {"field": Template.anchor("y")},
        },
    }
    template_path = tmp_path / "custom.json"
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text(json.dumps(template_content), encoding="utf-8")
    datapoints = [
        {x: "B", y: "A"},
        {x: "A", y: "A"},
    ]
    props = {"template": template_path, "x": x, "y": y}

    renderer = VegaRenderer(datapoints, "foo", **props)
    filled = renderer.get_filled_template()
    assert filled["transform"][1]["calculate"] == "pow(datum.lab - datum.SR,2)"
    assert filled["encoding"]["x"]["field"] == x
    assert filled["encoding"]["y"]["field"] == y


@pytest.mark.parametrize(
    (
        "anchors_y_definitions",
        "datapoints",
        "y",
        "expected_dp_keys",
        "stroke_dash_encoding",
        "pivot_field",
        "group_by",
    ),
    (
        pytest.param(
            [{"filename": "test", "field": "acc"}],
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
            ["rev", "acc", "step"],
            {},
            "datum.rev",
            ["rev"],
            id="single_source",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
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
            ["rev", "acc", "step", "filename"],
            {
                "field": "filename",
                "scale": {
                    "domain": ["test", "train"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:2],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.filename",
            ["rev", "filename"],
            id="multi_filename",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc"},
                {"filename": "test", "field": "acc_norm"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "acc": "0.05",
                    "acc_norm": "0.04",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.1",
                    "acc": "0.1",
                    "acc_norm": "0.09",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "acc": "0.05",
                    "acc_norm": "0.04",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.09",
                    "acc": "0.1",
                    "acc_norm": "0.09",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 2,
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "dvc_inferred_y_value", "acc", "acc_norm", "step", "field"],
            {
                "field": "field",
                "scale": {
                    "domain": ["acc", "acc_norm"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:2],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.field",
            ["rev", "field"],
            id="multi_field",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc_norm"},
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "acc": "0.05",
                    "acc_norm": "0.02",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.1",
                    "acc": "0.01",
                    "acc_norm": "0.07",
                    "filename": "test",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "acc": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.09",
                    "acc": "0.09",
                    "filename": "train",
                    "field": "acc",
                    "step": 2,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.02",
                    "acc": "0.05",
                    "acc_norm": "0.02",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.07",
                    "acc": "0.01",
                    "acc_norm": "0.07",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 2,
                },
            ],
            "dvc_inferred_y_value",
            [
                "rev",
                "dvc_inferred_y_value",
                "acc",
                "acc_norm",
                "step",
                "filename::field",
            ],
            {
                "field": "filename::field",
                "scale": {
                    "domain": ["test::acc", "test::acc_norm", "train::acc"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:3],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            "datum.rev + '::' + datum.filename + '::' + datum.field",
            ["rev", "filename::field"],
            id="multi_filename_field",
        ),
    ),
)
def test_optional_anchors_linear(  # noqa: PLR0913
    anchors_y_definitions,
    datapoints,
    y,
    expected_dp_keys,
    stroke_dash_encoding,
    pivot_field,
    group_by,
):  # pylint: disable=too-many-arguments
    props = {
        "anchors_y_definitions": anchors_y_definitions,
        "revs_with_datapoints": ["B"],
        "template": "linear",
        "x": "step",
        "y": y,
    }

    expected_datapoints = _get_expected_datapoints(datapoints, expected_dp_keys)

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["data"]["values"] == expected_datapoints
    assert plot_content["encoding"]["color"] == {
        "field": "rev",
        "scale": {"domain": ["B"], "range": OPTIONAL_ANCHOR_RANGES["color"][0:1]},
    }
    assert plot_content["encoding"]["strokeDash"] == stroke_dash_encoding
    assert plot_content["layer"][3]["transform"][0]["calculate"] == pivot_field
    assert plot_content["layer"][0]["transform"][0]["groupby"] == group_by


# https://github.com/iterative/dvc-render/issues/149
def test_no_revs_with_datapoints():
    datapoints = [
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
            "rev": "C",
            "acc": "0.05",
            "filename": "test",
            "field": "acc",
            "step": 1,
        },
        {
            "rev": "C",
            "acc": "0.1",
            "filename": "test",
            "field": "acc",
            "step": 2,
        },
        {
            "rev": "D",
            "acc": "0.05",
            "filename": "test",
            "field": "acc",
            "step": 1,
        },
        {
            "rev": "D",
            "acc": "0.1",
            "filename": "test",
            "field": "acc",
            "step": 2,
        },
        {
            "acc": "0.05",
            "filename": "test",
            "field": "acc",
            "step": 1,
        },
        {
            "acc": "0.05",
            "filename": "test",
            "field": "acc",
            "step": 2,
        },
    ]

    props = {
        "anchors_y_definitions": [{"filename": "test", "field": "acc"}],
        "template": "linear",
        "x": "step",
        "y": "acc",
    }

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["encoding"]["color"] == {
        "field": "rev",
        "scale": {
            "domain": ["B", "C", "D"],
            "range": OPTIONAL_ANCHOR_RANGES["color"][0:3],
        },
    }


# https://github.com/iterative/studio/issues/8851
def test_linear_tooltip_groupby():
    datapoints = [
        {
            "filename": "roc.json",
            "fpr": 0.00399400898652022,
            "tpr": 0.193158953722334,
            "rev": "main",
            "threshold": 0.84,
        },
        {
            "filename": "roc.json",
            "fpr": 0.00399400898652022,
            "tpr": 0.2012072434607646,
            "rev": "main",
            "threshold": 0.829854797979798,
        },
        {
            "filename": "roc.json",
            "fpr": 0.00399400898652022,
            "tpr": 0.20724346076458752,
            "rev": "main",
            "threshold": 0.8266666666666667,
        },
    ]

    props = {
        "anchors_y_definitions": [{"filename": "test", "field": "fpr"}],
        "revs_with_datapoints": ["main"],
        "template": "linear",
        "x": "fpr",
        "y": "tpr",
    }

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["layer"][3]["transform"][1]["op"] == "mean"


@pytest.mark.parametrize(
    (
        "anchors_y_definitions",
        "datapoints",
        "y",
        "expected_dp_keys",
        "row_encoding",
        "group_by_y",
        "group_by_x",
    ),
    (
        pytest.param(
            [{"filename": "test", "field": "predicted"}],
            [
                {
                    "rev": "B",
                    "predicted": "0.05",
                    "actual": "0.5",
                    "filename": "test",
                    "field": "predicted",
                },
                {
                    "rev": "B",
                    "predicted": "0.9",
                    "actual": "0.9",
                    "filename": "test",
                    "field": "predicted",
                },
            ],
            "predicted",
            ["rev", "predicted", "actual"],
            {},
            ["rev", "predicted"],
            ["rev", "actual"],
            id="single_source",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "predicted"},
                {"filename": "train", "field": "predicted"},
            ],
            [
                {
                    "rev": "B",
                    "predicted": "0.05",
                    "actual": "0.5",
                    "filename": "test",
                    "field": "predicted",
                },
                {
                    "rev": "B",
                    "predicted": "0.9",
                    "actual": "0.9",
                    "filename": "train",
                    "field": "predicted",
                },
            ],
            "predicted",
            ["rev", "predicted", "actual"],
            {"field": "filename", "sort": []},
            ["rev", "filename", "predicted"],
            ["rev", "filename", "actual"],
            id="multi_filename",
        ),
        pytest.param(
            [
                {"filename": "data", "field": "predicted_test"},
                {"filename": "data", "field": "predicted_train"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "predicted_train": "0.05",
                    "predicted_test": "0.9",
                    "actual": "0.5",
                    "filename": "data",
                    "field": "predicted_test",
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.9",
                    "predicted_train": "0.05",
                    "predicted_test": "0.9",
                    "actual": "0.5",
                    "filename": "data",
                    "field": "predicted_train",
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "dvc_inferred_y_value", "actual"],
            {"field": "field", "sort": []},
            ["rev", "field", "dvc_inferred_y_value"],
            ["rev", "field", "actual"],
            id="multi_field",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "predicted_test"},
                {"filename": "train", "field": "predicted_train"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "predicted_test": "0.05",
                    "actual": "0.5",
                    "filename": "test",
                    "field": "predicted_test",
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.9",
                    "predicted_test": "0.9",
                    "actual": "0.9",
                    "filename": "test",
                    "field": "predicted_test",
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.9",
                    "predicted_train": "0.9",
                    "actual": "0.9",
                    "filename": "train",
                    "field": "predicted_train",
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.9",
                    "predicted_train": "0.9",
                    "actual": "0.9",
                    "filename": "train",
                    "field": "predicted_train",
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "predicted", "actual"],
            {"field": "filename::field", "sort": []},
            ["rev", "filename::field", "dvc_inferred_y_value"],
            ["rev", "filename::field", "actual"],
            id="multi_filename_field",
        ),
    ),
)
def test_optional_anchors_confusion(  # noqa: PLR0913
    anchors_y_definitions,
    datapoints,
    y,
    expected_dp_keys,
    row_encoding,
    group_by_y,
    group_by_x,
):  # pylint: disable=too-many-arguments
    props = {
        "anchors_y_definitions": anchors_y_definitions,
        "revs_with_datapoints": ["B"],
        "template": "confusion",
        "x": "actual",
        "y": y,
    }

    expected_datapoints = _get_expected_datapoints(datapoints, expected_dp_keys)

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["data"]["values"] == expected_datapoints
    assert plot_content["facet"]["row"] == row_encoding
    assert plot_content["spec"]["transform"][0]["groupby"] == [y, "actual"]
    assert plot_content["spec"]["transform"][1]["groupby"] == group_by_y
    assert plot_content["spec"]["transform"][2]["groupby"] == group_by_x
    assert plot_content["spec"]["layer"][0]["width"] == 300
    assert plot_content["spec"]["layer"][0]["height"] == 300


@pytest.mark.parametrize(
    (
        "anchors_y_definitions",
        "datapoints",
        "y",
        "expected_dp_keys",
        "shape_encoding",
        "tooltip_encoding",
    ),
    (
        pytest.param(
            [{"filename": "test", "field": "acc"}],
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "filename": "test",
                    "field": "acc",
                    "loss": 0.1,
                },
            ],
            "acc",
            ["rev", "acc", "loss"],
            {},
            [{"field": "rev"}, {"field": "loss"}, {"field": "acc"}],
            id="single_source",
        ),
        pytest.param(
            [
                {"filename": "train", "field": "acc"},
                {"filename": "test", "field": "acc"},
            ],
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "filename": "train",
                    "field": "acc",
                    "loss": "0.0001",
                },
                {
                    "rev": "B",
                    "acc": "0.06",
                    "filename": "test",
                    "field": "acc",
                    "loss": "200121",
                },
            ],
            "acc",
            ["rev", "acc", "filename", "loss"],
            {
                "field": "filename",
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
                "scale": {
                    "domain": ["test", "train"],
                    "range": OPTIONAL_ANCHOR_RANGES["shape"][0:2],
                },
            },
            [
                {"field": "rev"},
                {"field": "loss"},
                {"field": "acc"},
                {"field": "filename"},
            ],
            id="multi_filename",
        ),
        pytest.param(
            [
                {"filename": "data", "field": "train_acc"},
                {"filename": "data", "field": "test_acc"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "test_acc": "0.05",
                    "train_acc": "0.06",
                    "filename": "data",
                    "field": "test_acc",
                    "loss": 0.1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.06",
                    "test_acc": "0.05",
                    "train_acc": "0.06",
                    "filename": "data",
                    "field": "train_acc",
                    "loss": 0.1,
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "dvc_inferred_y_value", "train_acc", "test_acc", "loss"],
            {
                "field": "field",
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
                "scale": {
                    "domain": ["test_acc", "train_acc"],
                    "range": OPTIONAL_ANCHOR_RANGES["shape"][0:2],
                },
            },
            [
                {"field": "rev"},
                {"field": "loss"},
                {"field": "dvc_inferred_y_value"},
                {"field": "field"},
            ],
            id="multi_field",
        ),
        pytest.param(
            [
                {"filename": "train", "field": "train_acc"},
                {"filename": "test", "field": "test_acc"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "test_acc": "0.05",
                    "filename": "test",
                    "field": "test_acc",
                    "loss": 0.1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.06",
                    "train_acc": "0.06",
                    "filename": "train",
                    "field": "train_acc",
                    "loss": 0.1,
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "dvc_inferred_y_value", "train_acc", "test_acc", "loss"],
            {
                "field": "filename::field",
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
                "scale": {
                    "domain": ["test::test_acc", "train::train_acc"],
                    "range": OPTIONAL_ANCHOR_RANGES["shape"][0:2],
                },
            },
            [
                {"field": "rev"},
                {"field": "loss"},
                {"field": "dvc_inferred_y_value"},
                {"field": "filename::field"},
            ],
            id="multi_filename_field",
        ),
    ),
)
def test_optional_anchors_scatter(  # noqa: PLR0913
    anchors_y_definitions,
    datapoints,
    y,
    expected_dp_keys,
    shape_encoding,
    tooltip_encoding,
):  # pylint: disable=too-many-arguments
    props = {
        "anchors_y_definitions": anchors_y_definitions,
        "revs_with_datapoints": ["B"],
        "template": "scatter",
        "x": "loss",
        "y": y,
    }

    expected_datapoints = _get_expected_datapoints(datapoints, expected_dp_keys)

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    assert plot_content["data"]["values"] == expected_datapoints
    assert plot_content["encoding"]["color"] == {
        "field": "rev",
        "scale": {"domain": ["B"], "range": OPTIONAL_ANCHOR_RANGES["color"][0:1]},
    }
    assert plot_content["encoding"]["shape"] == shape_encoding
    assert plot_content["encoding"]["tooltip"] == tooltip_encoding
    assert plot_content["params"] == [
        {
            "name": "grid",
            "select": "interval",
            "bind": "scales",
        }
    ]


@pytest.mark.parametrize(
    ("revs", "datapoints"),
    (
        pytest.param(
            ["B"],
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
            ],
            id="rev_count_1",
        ),
        pytest.param(
            ["B", "C", "D", "E", "F"],
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "C",
                    "acc": "0.1",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "D",
                    "acc": "0.06",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "E",
                    "acc": "0.6",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "F",
                    "acc": "1.0",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
            ],
            id="rev_count_5",
        ),
        pytest.param(
            ["B", "C", "D", "E", "F", "G", "H", "I", "J"],
            [
                {
                    "rev": "B",
                    "acc": "0.05",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "C",
                    "acc": "0.1",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "D",
                    "acc": "0.06",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "E",
                    "acc": "0.6",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "F",
                    "acc": "1.0",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "G",
                    "acc": "0.006",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "H",
                    "acc": "0.00001",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "I",
                    "acc": "0.8",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
                {
                    "rev": "J",
                    "acc": "0.001",
                    "step": "1",
                    "filename": "acc",
                    "field": "acc",
                },
            ],
            id="rev_count_9",
        ),
    ),
)
def test_color_anchor(revs, datapoints):
    props = {
        "anchors_y_definitions": [{"filename": "acc", "field": "acc"}],
        "revs_with_datapoints": revs,
        "template": "linear",
        "x": "step",
        "y": "acc",
    }

    renderer = VegaRenderer(datapoints, "foo", **props)
    plot_content = renderer.get_filled_template()

    colors = OPTIONAL_ANCHOR_RANGES["color"]
    color_range = colors[0 : len(revs)]
    if len(revs) > len(colors):
        color_range.extend(colors[0 : len(revs) - len(colors)])

    assert plot_content["encoding"]["color"] == {
        "field": "rev",
        "scale": {
            "domain": revs,
            "range": color_range,
        },
    }


@pytest.mark.parametrize(
    (
        "anchors_y_definitions",
        "datapoints",
        "y",
        "expected_dp_keys",
        "stroke_dash_encoding",
    ),
    (
        pytest.param(
            [{"filename": "test", "field": "acc"}],
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
            ["rev", "acc", "step"],
            {},
            id="single_source",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
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
                    "acc": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
            ],
            "acc",
            ["rev", "acc", "step", "field"],
            {
                "field": "filename",
                "scale": {
                    "domain": ["test", "train"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:2],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            id="multi_filename",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc"},
                {"filename": "test", "field": "acc_norm"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "acc": "0.05",
                    "acc_norm": "0.04",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "acc": "0.05",
                    "acc_norm": "0.04",
                    "filename": "test",
                    "field": "acc_norm",
                    "step": 1,
                },
            ],
            "dvc_inferred_y_value",
            ["rev", "dvc_inferred_y_value", "acc", "acc_norm", "step", "field"],
            {
                "field": "field",
                "scale": {
                    "domain": ["acc", "acc_norm"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:2],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            id="multi_field",
        ),
        pytest.param(
            [
                {"filename": "test", "field": "acc_norm"},
                {"filename": "test", "field": "acc"},
                {"filename": "train", "field": "acc"},
            ],
            [
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.05",
                    "acc": "0.05",
                    "acc_norm": "0.02",
                    "filename": "test",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.04",
                    "acc": "0.04",
                    "filename": "train",
                    "field": "acc",
                    "step": 1,
                },
                {
                    "rev": "B",
                    "dvc_inferred_y_value": "0.02",
                    "filename": "test",
                    "acc": "0.05",
                    "acc_norm": "0.02",
                    "field": "acc_norm",
                    "step": 1,
                },
            ],
            "dvc_inferred_y_value",
            [
                "rev",
                "dvc_inferred_y_value",
                "acc",
                "acc_norm",
                "step",
                "filename::field",
            ],
            {
                "field": "filename::field",
                "scale": {
                    "domain": ["test::acc", "test::acc_norm", "train::acc"],
                    "range": OPTIONAL_ANCHOR_RANGES["stroke_dash"][0:3],
                },
                "legend": {
                    "symbolFillColor": "transparent",
                    "symbolStrokeColor": "grey",
                },
            },
            id="multi_filename_field",
        ),
    ),
)
def test_partial_filled_template(
    anchors_y_definitions,
    datapoints,
    y,
    expected_dp_keys,
    stroke_dash_encoding,
):
    title = f"{y} by step"
    props = {
        "anchors_y_definitions": anchors_y_definitions,
        "revs_with_datapoints": ["B"],
        "template": "linear",
        "title": title,
        "x": "step",
        "y": y,
    }

    expected_split = {
        Template.anchor("color"): {
            "field": "rev",
            "scale": {"domain": ["B"], "range": OPTIONAL_ANCHOR_RANGES["color"][0:1]},
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
    datapoints: list[dict[str, Any]], expected_dp_keys: list[str]
):
    expected_datapoints: list[dict[str, Any]] = []
    for datapoint in datapoints:
        expected_datapoint = {}
        for key in expected_dp_keys:
            if key == "filename::field":
                expected_datapoint[key] = (
                    f"{datapoint['filename']}::{datapoint['field']}"
                )
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
