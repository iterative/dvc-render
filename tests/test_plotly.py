import json

from dvc_render.plotly import PlotlyRenderer

# pylint: disable=missing-function-docstring,

DVCLIVE_DATAPOINTS = [
    {
        "step": "0",
        "bar": "4.16",
        "dvc_data_version_info": {
            "revision": "workspace",
            "filename": "dvclive/plots/metrics/bar.tsv",
            "field": "bar",
        },
    },
    {
        "step": "1",
        "bar": "inf",
        "dvc_data_version_info": {
            "revision": "workspace",
            "filename": "dvclive/plots/metrics/bar.tsv",
            "field": "bar",
        },
    },
    {
        "step": "2",
        "bar": "2.38",
        "dvc_data_version_info": {
            "revision": "workspace",
            "filename": "dvclive/plots/metrics/bar.tsv",
            "field": "bar",
        },
    },
    {
        "step": "0",
        "bar": "1.35",
        "dvc_data_version_info": {
            "revision": "HEAD~1",
            "filename": "dvclive/plots/metrics/bar.tsv",
            "field": "bar",
        },
    },
    {
        "step": "1",
        "bar": "0.64",
        "dvc_data_version_info": {
            "revision": "HEAD~1",
            "filename": "dvclive/plots/metrics/bar.tsv",
            "field": "bar",
        },
    },
]


def test_plotly_type():
    props = {"x": "step", "y": "bar", "template": "scatter"}

    plot_content = json.loads(
        PlotlyRenderer(DVCLIVE_DATAPOINTS, "bar", **props).partial_html()
    )

    assert plot_content == {
        "data": [
            {
                "x": ["0", "1", "2"],
                "y": ["4.16", "inf", "2.38"],
                "type": "scatter",
                "name": "workspace",
            },
            {
                "x": ["0", "1"],
                "y": ["1.35", "0.64"],
                "type": "scatter",
                "name": "HEAD~1",
            },
        ],
        "layout": {"title": "", "xaxis": {"title": "step"}, "yaxis": {"title": "bar"}},
    }


def test_plotly_layout():
    props = {"x": "step", "y": "bar", "title": "TITLE"}

    plot_content = json.loads(
        PlotlyRenderer(DVCLIVE_DATAPOINTS, "foo", **props).partial_html()
    )

    assert plot_content == {
        "data": [
            {
                "x": ["0", "1", "2"],
                "y": ["4.16", "inf", "2.38"],
                "type": "linear",
                "name": "workspace",
            },
            {
                "x": ["0", "1"],
                "y": ["1.35", "0.64"],
                "type": "linear",
                "name": "HEAD~1",
            },
        ],
        "layout": {
            "title": "TITLE",
            "xaxis": {"title": "step"},
            "yaxis": {"title": "bar"},
        },
    }
