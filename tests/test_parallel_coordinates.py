import json

from dvc_render.html import render_html
from dvc_render.plotly import ParallelCoordinatesRenderer

# pylint: disable=C0116, W1514, W0212, R0903


def expected_format(result):
    assert "data" in result
    assert "layout" in result
    assert isinstance(result["data"], list)
    assert result["data"][0]["type"] == "parcoords"
    assert isinstance(result["data"][0]["dimensions"], list)
    return True


def test_scalar_columns():
    datapoints = [
        {"col-1": "0.1", "col-2": "1", "col-3": ""},
        {"col-1": "2", "col-2": "0.2", "col-3": "0"},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints)

    result = json.loads(renderer.partial_html())

    assert expected_format(result)

    assert result["data"][0]["dimensions"][0] == {
        "label": "col-1",
        "values": [0.1, 2.0],
    }
    assert result["data"][0]["dimensions"][1] == {
        "label": "col-2",
        "values": [1.0, 0.2],
    }
    assert result["data"][0]["dimensions"][2] == {
        "label": "col-3",
        "values": [None, 0],
    }


def test_categorical_columns():
    datapoints = [
        {"col-1": "foo", "col-2": ""},
        {"col-1": "bar", "col-2": "foobar"},
        {"col-1": "foo", "col-2": ""},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints)

    result = json.loads(renderer.partial_html())

    assert expected_format(result)

    assert result["data"][0]["dimensions"][0] == {
        "label": "col-1",
        "values": [1, 0, 1],
        "tickvals": [1, 0, 1],
        "ticktext": ["foo", "bar", "foo"],
    }
    assert result["data"][0]["dimensions"][1] == {
        "label": "col-2",
        "values": [1, 0, 1],
        "tickvals": [1, 0, 1],
        "ticktext": ["Missing", "foobar", "Missing"],
    }


def test_mixed_columns():
    datapoints = [
        {"categorical": "foo", "scalar": "0.1"},
        {"categorical": "bar", "scalar": "2"},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints)

    result = json.loads(renderer.partial_html())

    assert expected_format(result)

    assert result["data"][0]["dimensions"][0] == {
        "label": "categorical",
        "values": [1, 0],
        "tickvals": [1, 0],
        "ticktext": ["foo", "bar"],
    }
    assert result["data"][0]["dimensions"][1] == {
        "label": "scalar",
        "values": [0.1, 2.0],
    }


def test_color_by_scalar():
    datapoints = [
        {"categorical": "foo", "scalar": "0.1"},
        {"categorical": "bar", "scalar": "2"},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints, color_by="scalar")

    result = json.loads(renderer.partial_html())

    assert expected_format(result)
    assert result["data"][0]["line"] == {
        "color": [0.1, 2.0],
        "showscale": True,
        "colorbar": {"title": "scalar"},
    }


def test_color_by_categorical():
    datapoints = [
        {"categorical": "foo", "scalar": "0.1"},
        {"categorical": "bar", "scalar": "2"},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints, color_by="categorical")

    result = json.loads(renderer.partial_html())

    assert expected_format(result)
    assert result["data"][0]["line"] == {
        "color": [1, 0],
        "showscale": True,
        "colorbar": {
            "title": "categorical",
            "tickmode": "array",
            "tickvals": [1, 0],
            "ticktext": ["foo", "bar"],
        },
    }


def test_write_parallel_coordinates(tmp_dir):
    datapoints = [
        {"categorical": "foo", "scalar": "0.1"},
        {"categorical": "bar", "scalar": "2"},
    ]

    renderer = ParallelCoordinatesRenderer(datapoints)
    html_path = render_html(
        renderers=[renderer], output_file=tmp_dir / "index.html"
    )

    html_text = html_path.read_text()

    assert ParallelCoordinatesRenderer.SCRIPTS in html_text

    div = ParallelCoordinatesRenderer.DIV.format(
        id="pcp", partial=renderer.partial_html()
    )
    assert div in html_text


def test_fill_value():
    datapoints = [
        {"categorical": "foo", "scalar": "-"},
        {"categorical": "-", "scalar": "2"},
    ]
    renderer = ParallelCoordinatesRenderer(datapoints, fill_value="-")

    result = json.loads(renderer.partial_html())

    assert expected_format(result)

    assert result["data"][0]["dimensions"][0] == {
        "label": "categorical",
        "values": [0, 1],
        "tickvals": [0, 1],
        "ticktext": ["foo", "Missing"],
    }
    assert result["data"][0]["dimensions"][1] == {
        "label": "scalar",
        "values": [None, 2.0],
    }


def test_str_cast():
    class Foo:
        def __str__(self):
            return "1"

    datapoints = [{"foo": Foo()}]
    renderer = ParallelCoordinatesRenderer(datapoints, fill_value="-")

    result = renderer._get_plotly_data()
    assert result["data"][0]["dimensions"][0]["values"] == [1.0]
