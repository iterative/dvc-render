import base64
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from warnings import warn

from .base import Renderer
from .utils import list_dict_to_dict_list
from .vega_templates import BadTemplateError, LinearTemplate, get_template


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
        self._optional_anchor_ranges: Dict[
            str,
            Union[
                List[str],
                List[List[int]],
            ],
        ] = {
            "stroke_dash": [[1, 0], [8, 8], [8, 4], [4, 4], [4, 2], [2, 1], [1, 1]],
            "color": [
                "#945dd6",
                "#13adc7",
                "#f46837",
                "#48bb78",
                "#4299e1",
                "#ed8936",
                "#f56565",
            ],
            "shape": ["square", "circle", "triangle", "diamond"],
        }
        self._optional_anchor_values: Dict[
            str,
            Dict[str, Dict[str, str]],
        ] = defaultdict(dict)

    def get_filled_template(
        self,
        skip_anchors: Optional[List[str]] = None,
        strict: bool = True,
        as_string: bool = True,
    ) -> Union[str, Dict[str, Any]]:
        """Returns a functional vega specification"""
        self.template.reset()
        if not self.datapoints:
            return {}

        if skip_anchors is None:
            skip_anchors = []

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

        self._fill_optional_anchors(skip_anchors)

        names = ["title", "x", "y", "x_label", "y_label", "data"]
        for name in names:
            if name in skip_anchors:
                continue
            value = self.properties.get(name)
            if value is None:
                continue
            if name == "data":
                if not self.template.has_anchor(name):
                    anchor = self.template.anchor(name)
                    raise BadTemplateError(
                        f"Template '{self.template.name}' "
                        f"is not using '{anchor}' anchor"
                    )
            elif name in {"x", "y"}:
                value = self.template.escape_special_characters(value)
            self.template.fill_anchor(name, value)

        if as_string:
            return json.dumps(self.template.content)

        return self.template.content

    def partial_html(self, **kwargs) -> str:
        return self.get_filled_template()  # type: ignore

    def generate_markdown(self, report_path=None) -> str:
        if not isinstance(self.template, LinearTemplate):
            warn("`generate_markdown` can only be used with `LinearTemplate`")
            return ""
        try:
            from matplotlib import pyplot as plt
        except ImportError as e:
            raise ImportError("matplotlib is required for `generate_markdown`") from e

        data = list_dict_to_dict_list(self.datapoints)
        if data:
            if report_path:
                report_folder = Path(report_path).parent
                output_file = report_folder / self.name
                output_file = output_file.with_suffix(".png")
                output_file.parent.mkdir(exist_ok=True, parents=True)
            else:
                output_file = io.BytesIO()  # type: ignore

            x = self.properties.get("x")
            y = self.properties.get("y")
            data[x] = list(map(float, data[x]))
            data[y] = list(map(float, data[y]))

            if x is not None and y is not None:
                plt.title(self.properties.get("title", Path(self.name).stem))
                plt.xlabel(self.properties.get("x_label", x))
                plt.ylabel(self.properties.get("y_label", y))
                plt.plot(x, y, data=data)
                plt.tight_layout()
                plt.savefig(output_file)
                plt.close()

                if report_path:
                    return f"\n![{self.name}]({output_file.relative_to(report_folder)})"

                base64_str = base64.b64encode(
                    output_file.getvalue()  # type: ignore
                ).decode()
                src = f"data:image/png;base64,{base64_str}"

                return f"\n![{self.name}]({src})"

        return ""

    def _fill_optional_anchors(self, skip_anchors: List[str]):
        optional_anchors = [
            anchor
            for anchor in [
                "row",
                "group_by",
                "pivot_field",
                "color",
                "stroke_dash",
                "shape",
            ]
            if anchor not in skip_anchors and self.template.has_anchor(anchor)
        ]
        if not optional_anchors:
            return

        self._fill_color(optional_anchors)

        if not optional_anchors:
            return

        y_defn = self.properties.get("anchors_y_defn", [])

        if len(y_defn) <= 1:
            self._fill_optional_anchor(optional_anchors, "group_by", ["rev"])
            self._fill_optional_anchor(optional_anchors, "pivot_field", "rev")
            for anchor in optional_anchors:
                self.template.fill_anchor(anchor, {})
            self._update_datapoints(to_remove=["filename", "field"])
            return

        keys, variations = self._collect_variations(y_defn)
        grouped_keys = ["rev", *keys]
        concat_field = "::".join(keys)
        self._fill_optional_anchor(optional_anchors, "group_by", grouped_keys)
        self._fill_optional_anchor(
            optional_anchors,
            "pivot_field",
            "+ '::'".join([f"datum.{key}" for key in grouped_keys]),
        )
        # concatenate grouped_keys together
        self._fill_optional_anchor(optional_anchors, "row", {"field": concat_field})

        if not optional_anchors:
            return

        if len(keys) == 2:
            self._update_datapoints(
                to_remove=["filename", "field"], to_concatenate=[["filename", "field"]]
            )
            domain = ["::".join([d.get("filename"), d.get("field")]) for d in y_defn]
        else:
            filenameOrField = keys[0]
            to_remove = ["filename", "field"]
            to_remove.remove(filenameOrField)
            self._update_datapoints(to_remove=to_remove)

            domain = list(variations[filenameOrField])

        stroke_dash_scale = self._set_optional_anchor_scale(
            optional_anchors, concat_field, "stroke_dash", domain
        )
        self._fill_optional_anchor(optional_anchors, "stroke_dash", stroke_dash_scale)

        shape_scale = self._set_optional_anchor_scale(
            optional_anchors, concat_field, "shape", domain
        )
        self._fill_optional_anchor(optional_anchors, "shape", shape_scale)

    def _fill_color(self, optional_anchors: List[str]):
        all_revs = self.properties.get("anchor_revs", [])
        self._fill_optional_anchor(
            optional_anchors,
            "color",
            {
                "field": "rev",
                "scale": {
                    "domain": list(all_revs),
                    "range": self._optional_anchor_ranges.get("color", [])[
                        : len(all_revs)
                    ],
                },
            },
        )

    def _collect_variations(
        self, y_defn: List[Dict[str, str]]
    ) -> Tuple[List[str], Dict[str, set]]:
        variations = defaultdict(set)
        for defn in y_defn:
            for key in ["filename", "field"]:
                variations[key].add(defn.get(key, None))

        valuesMatchVariations = []
        lessValuesThanVariations = []

        for filenameOrField, valueSet in variations.items():
            num_values = len(valueSet)
            if num_values == 1:
                continue
            if num_values == len(y_defn):
                valuesMatchVariations.append(filenameOrField)
                continue
            lessValuesThanVariations.append(filenameOrField)

        if valuesMatchVariations:
            valuesMatchVariations.extend(lessValuesThanVariations)
            valuesMatchVariations.sort(reverse=True)
            return valuesMatchVariations, variations

        lessValuesThanVariations.sort(reverse=True)
        return lessValuesThanVariations, variations

    def _fill_optional_anchor(self, optional_anchors: List[str], name: str, value: Any):
        if name not in optional_anchors:
            return

        optional_anchors.remove(name)
        self.template.fill_anchor(name, value)

    def _set_optional_anchor_scale(
        self, optional_anchors: List[str], field: str, name: str, domain: List[str]
    ):
        if name not in optional_anchors:
            return {"field": field, "scale": {"domain": [], "range": []}}

        full_range_values: List[Any] = self._optional_anchor_ranges.get(name, [])
        anchor_range_values = full_range_values.copy()
        anchor_range = []

        for domain_value in domain:
            if not anchor_range_values:
                anchor_range_values = full_range_values.copy()
            range_value = anchor_range_values.pop(0)
            self._optional_anchor_values[name][domain_value] = range_value
            anchor_range.append(range_value)

        return {"field": field, "scale": {"domain": domain, "range": anchor_range}}

    def _update_datapoints(
        self,
        to_concatenate: Optional[List[List[str]]] = None,
        to_remove: Optional[List[str]] = None,
    ):
        if to_concatenate is None:
            to_concatenate = []
        if to_remove is None:
            to_remove = []

        for datapoint in self.datapoints:
            for keys in to_concatenate:
                concat_key = "::".join(keys)
                datapoint[concat_key] = "::".join([datapoint.get(k) for k in keys])
            for key in to_remove:
                datapoint.pop(key, None)
