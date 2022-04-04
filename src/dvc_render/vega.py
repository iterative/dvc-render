from copy import deepcopy
from typing import List, Optional

from .base import Renderer
from .exceptions import DvcRenderException
from .vega_templates import get_template


class BadTemplateError(DvcRenderException):
    pass


class VegaRenderer(Renderer):
    """Renderer for vega plots."""

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

    def __init__(self, datapoints: List, name: str, **properties):
        super().__init__(datapoints, name, **properties)
        self.template = get_template(
            self.properties.get("template", None),
            self.properties.get("template_dir", None),
        )

    def get_filled_template(
        self, skip_anchors: Optional[List[str]] = None, strict: bool = True
    ) -> str:
        """Returns a functional vega specification"""
        if not self.datapoints:
            return ""

        if skip_anchors is None:
            skip_anchors = []

        content = deepcopy(self.template.content)

        if strict:
            if self.properties.get("x"):
                self.template.check_field_exists(
                    self.datapoints, self.properties.get("x")
                )
            if self.properties.get("y"):
                self.template.check_field_exists(
                    self.datapoints, self.properties.get("y")
                )
        self.properties.setdefault("title", "")
        self.properties.setdefault("x_label", self.properties.get("x"))
        self.properties.setdefault("y_label", self.properties.get("y"))
        self.properties.setdefault("data", self.datapoints)

        names = ["title", "x", "y", "x_label", "y_label", "data"]
        for name in names:
            if name in skip_anchors:
                continue
            value = self.properties.get(name)
            if value is None:
                continue
            if name == "data":
                if self.template.anchor_str(name) not in self.template.content:
                    anchor = self.template.anchor(name)
                    raise BadTemplateError(
                        f"Template '{self.template.name}' "
                        f"is not using '{anchor}' anchor"
                    )
            content = self.template.fill_anchor(content, name, value)

        return content

    def partial_html(self) -> str:
        return self.get_filled_template()
