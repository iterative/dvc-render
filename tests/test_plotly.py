import json

from dvc_render.plotly import PlotlyRenderer

# pylint: disable=missing-function-docstring,


def test_plotly_partial_html():
    props = {"x": "first_val", "y": "second_val", "template": "scatter"}
    datapoints = [
        {"first_val": 1, "second_val": 2, "rev": "workspace"},
        {"first_val": 3, "second_val": 4, "rev": "workspace"},
        {"first_val": 5, "second_val": 6, "rev": "HEAD"},
        {"first_val": 7, "second_val": 8, "rev": "HEAD"},
    ]

    plot_content = json.loads(PlotlyRenderer(datapoints, "foo", **props).partial_html())

    assert plot_content == {
        "data": [
            {"x": [1, 3], "y": [2, 4], "type": "scatter", "name": "workspace"},
            {"x": [5, 7], "y": [6, 8], "type": "scatter", "name": "HEAD"},
        ],
        "layout": {
            "title": "",
            "xaxis": {"title": "first_val"},
            "yaxis": {"title": "second_val"},
        },
    }


def test_plotly_layout():
    props = {"x": "first_val", "y": "second_val", "title": "TITLE"}
    datapoints = [
        {"first_val": 1, "second_val": 2, "rev": "workspace"},
        {"first_val": 3, "second_val": 4, "rev": "workspace"},
        {"first_val": 5, "second_val": 6, "rev": "HEAD"},
        {"first_val": 7, "second_val": 8, "rev": "HEAD"},
    ]

    plot_content = json.loads(PlotlyRenderer(datapoints, "foo", **props).partial_html())

    assert plot_content == {
        "data": [
            {"x": [1, 3], "y": [2, 4], "type": "linear", "name": "workspace"},
            {"x": [5, 7], "y": [6, 8], "type": "linear", "name": "HEAD"},
        ],
        "layout": {
            "title": "TITLE",
            "xaxis": {"title": "first_val"},
            "yaxis": {"title": "second_val"},
        },
    }
