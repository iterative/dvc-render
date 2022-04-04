import json

import pytest
from funcy import first  # type: ignore

from dvc_render.vega import BadTemplateError, VegaRenderer
from dvc_render.vega_templates import NoFieldInDataError, Template

# pylint: disable=missing-function-docstring, C1803


def test_init_empty():
    renderer = VegaRenderer(None, None)

    assert renderer.datapoints == []
    assert renderer.name == ""
    assert renderer.properties == {}

    assert renderer.generate_html() == ""


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
    assert (
        first(plot_content["layer"])["encoding"]["x"]["field"] == "first_val"
    )
    assert (
        first(plot_content["layer"])["encoding"]["y"]["field"] == "second_val"
    )


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
    ),
)
def test_matches(extension, matches):
    assert VegaRenderer.matches("file" + extension, {}) == matches
