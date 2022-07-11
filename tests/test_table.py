from dvc_render.table import TableRenderer

# pylint: disable=missing-function-docstring


def test_generate_html():
    datapoints = [
        {"foo": 1, "bar": 2},
    ]
    html = TableRenderer(datapoints, "metrics.json").generate_html()
    assert "<p>metrics_json</p>" in html
    assert '<tr><th style="text-align: right;">  foo</th>' in html
    assert '<th style="text-align: right;">  bar</th></tr>' in html
    assert '<td style="text-align: right;">    1</td>' in html
    assert '<td style="text-align: right;">    2</td>' in html


def test_generate_markdown():
    datapoints = [
        {"foo": 1, "bar": 2},
    ]
    md = TableRenderer(datapoints, "metrics.json").generate_markdown()
    assert "metrics.json\n\n" in md
    assert "|   foo |   bar |" in md
    assert "|-------|-------|" in md
    assert "|     1 |     2 |" in md
