from copy import deepcopy
from pathlib import Path
from typing import List, Optional
from warnings import warn

from .base import Renderer
from .exceptions import DvcRenderException
from .utils import list_dict_to_dict_list
from .vega_templates import LinearTemplate, get_template


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
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5.2.0"></script>
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
            elif name in {"x", "y"}:
                value = self.template.escape_special_characters(value)
            content = self.template.fill_anchor(content, name, value)

        return content

    def partial_html(self, **kwargs) -> str:
        return self.get_filled_template()

    def generate_markdown(self, report_path=None) -> str:
        if not isinstance(self.template, LinearTemplate):
            warn("`generate_markdown` can only be used with `LinearTemplate`")
            return ""
        try:
            from matplotlib import pyplot as plt
        except ImportError as e:
            raise ImportError(
                "matplotlib is required for `generate_markdown`"
            ) from e

        data = list_dict_to_dict_list(self.datapoints)
        if data:
            report_folder = Path(report_path).parent
            output_file = report_folder / self.name
            output_file = output_file.with_suffix(".png")
            output_file.parent.mkdir(exist_ok=True, parents=True)

            x = self.properties.get("x")
            y = self.properties.get("y")
            data[x] = list(map(float, data[x]))
            data[y] = list(map(float, data[y]))

            plt.title(self.properties.get("title", output_file.stem))
            plt.xlabel(self.properties.get("x_label", x))
            plt.ylabel(self.properties.get("y_label", y))
            plt.plot(x, y, data=data)
            plt.tight_layout()
            plt.savefig(output_file)
            plt.close()

            return (
                f"\n![{self.name}]({output_file.relative_to(report_folder)})"
            )
        return ""
