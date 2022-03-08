from copy import deepcopy
from typing import Dict

from .base import Renderer
from .exceptions import DvcRenderException
from .vega_templates import get_template


class BadTemplateError(DvcRenderException):
    pass


class VegaRenderer(Renderer):
    TYPE = "vega"

    DIV = """
    <div id = "{id}">
        <script type = "text/javascript">
            var spec = {partial};
            vegaEmbed('#{id}', spec);
        </script>
    </div>
    """

    SCRIPTS = """
    <script src="https://cdn.jsdelivr.net/npm/vega@5.20.2"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5.1.0"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6.18.2"></script>
    """

    EXTENSIONS = {".yml", ".yaml", ".json", ".csv", ".tsv"}

    def __init__(self, datapoints: Dict, name: str, **properties):
        super().__init__(datapoints, name, **properties)
        self.template = get_template(
            self.properties.get("template", None),
            self.properties.get("template_dir", None),
        )

    def _fill_properties(self, content: str) -> str:
        self.properties.setdefault("title", "")
        self.properties.setdefault("x_label", self.properties.get("x"))
        self.properties.setdefault("y_label", self.properties.get("y"))

        names = ["title", "x", "y", "x_label", "y_label"]
        for name in names:
            value = self.properties.get(name)
            if value is not None:
                content = self.template.fill_anchor(content, name, value)
        return content

    def partial_html(self) -> str:
        content = deepcopy(self.template.content)
        if self.template.anchor_str("data") not in self.template.content:
            anchor = self.template.anchor("data")
            raise BadTemplateError(
                f"Template '{self.template.name}' "
                f"is not using '{anchor}' anchor"
            )

        if self.properties.get("x"):
            self.template.check_field_exists(
                self.datapoints, self.properties.get("x")
            )
        if self.properties.get("y"):
            self.template.check_field_exists(
                self.datapoints, self.properties.get("y")
            )

        content = self._fill_properties(content)
        content = self.template.fill_anchor(content, "data", self.datapoints)

        return content
