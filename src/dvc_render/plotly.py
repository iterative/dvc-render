import json
from typing import List

from .base import Renderer


class PlotlyRenderer(Renderer):
    """Renderer using plotly.js mimicking VegaRenderer"""

    TYPE = "plotly"

    DIV = """
    <div id = "{id}">
        <script type = "text/javascript">
            var plotly_data = {partial};
            Plotly.newPlot("{id}", plotly_data.data, plotly_data.layout);
        </script>
    </div>
    """

    EXTENSIONS = {".json"}

    SCRIPTS = """
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    """

    # pylint: disable=W0231
    def __init__(self, datapoints: List, name: str, **properties):
        super().__init__(datapoints, name, **properties)

    def convert_datapoints(self, datapoints):
        """Convert from dvc-render format to plotly json format"""
        traces = {}
        for datapoint in datapoints:
            revision = datapoint.get("dvc_data_version_info", {}).get(
                "revision", "workspace"
            )
            if revision not in traces:
                traces[revision] = {"name": revision, "x": [], "y": []}
            for axis in ("x", "y"):
                value = datapoint[self.properties[axis]]
                traces[revision][axis].append(value)
        traces = list(traces.values())

        template = self.properties.pop("template", "linear")
        for trace in traces:
            trace["type"] = template

        layout = {
            "title": self.properties.get("title", ""),
            "xaxis": {
                "title": self.properties.get("x_label", self.properties.get("x"))
            },
            "yaxis": {
                "title": self.properties.get("y_label", self.properties.get("y"))
            },
        }

        return {"data": traces, "layout": layout}

    def partial_html(self, **kwargs) -> str:
        return json.dumps(self.convert_datapoints(self.datapoints))
