import base64
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from warnings import warn

from .base import Renderer
from .utils import list_dict_to_dict_list
from .vega_templates import BadTemplateError, LinearTemplate, Template, get_template

FIELD_SEPARATOR = "::"
FILENAME = "filename"
FIELD = "field"
FILENAME_FIELD = [FILENAME, FIELD]
CONCAT_FIELDS = FIELD_SEPARATOR.join(FILENAME_FIELD)


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

        self._split_content: Dict[str, str] = {}

    def get_filled_template(
        self,
        split_anchors: Optional[List[str]] = None,
        strict: bool = True,
        as_string: bool = True,
    ) -> Union[str, Dict[str, Any]]:
        """Returns a functional vega specification"""
        self.template.reset()
        if not self.datapoints:
            return {}

        if split_anchors is None:
            split_anchors = []

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

        varied_keys = self._process_optional_anchors(split_anchors)
        self._update_datapoints(varied_keys)

        names = ["title", "x", "y", "x_label", "y_label", "data"]
        for name in names:
            value = self.properties.get(name)
            if value is None:
                continue

            if name in split_anchors:
                self._set_split_content(name, value)
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

    def get_partial_filled_template(self):
        """
        Returns a partially filled template along with the split out anchor content
        """
        content = self.get_filled_template(
            split_anchors=[
                "color",
                "data",
                "shape",
                "stroke_dash",
                "title",
                "x_label",
                "y_label",
                "zoom_and_pan",
            ],
            strict=True,
        )
        return content, {"anchor_definitions": self._split_content}

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

    def get_revs(self):
        """
        Returns all revisions that were collected.
        Potentially will include revisions that have no datapoints
        """
        return self.properties.get("anchor_revs", [])

    def _process_optional_anchors(self, split_anchors: List[str]):
        optional_anchors = [
            anchor
            for anchor in [
                "color",
                "group_by_x",
                "group_by_y",
                "group_by",
                "pivot_field",
                "row",
                "shape",
                "stroke_dash",
                "zoom_and_pan",
            ]
            if self.template.has_anchor(anchor)
        ]
        if not optional_anchors:
            return None

        self._fill_color(split_anchors, optional_anchors)
        self._fill_zoom_and_pan(split_anchors, optional_anchors)

        y_definitions = self.properties.get("anchors_y_definitions", [])
        is_single_source = len(y_definitions) <= 1

        if is_single_source:
            self._process_single_source_plot(split_anchors, optional_anchors)
            return []

        return self._process_multi_source_plot(
            split_anchors, optional_anchors, y_definitions
        )

    def _fill_color(self, split_anchors: List[str], optional_anchors: List[str]):
        all_revs = self.get_revs()
        self._fill_optional_anchor_mapping(
            split_anchors,
            optional_anchors,
            "rev",
            "color",
            all_revs,
        )

    def _fill_zoom_and_pan(self, split_anchors: List[str], optional_anchors: List[str]):
        name = "zoom_and_pan"
        encoding = {"name": "grid", "select": "interval", "bind": "scales"}
        if "zoom_and_pan" not in optional_anchors:
            return

        optional_anchors.remove("zoom_and_pan")

        if name in split_anchors:
            self._set_split_content(name, encoding)
            return

        self.template.fill_anchor(name, encoding)

    def _process_single_source_plot(
        self, split_anchors: List[str], optional_anchors: List[str]
    ):
        self._fill_group_by(split_anchors, optional_anchors, ["rev"])
        self._fill_optional_anchor(
            split_anchors, optional_anchors, "pivot_field", "datum.rev"
        )
        for anchor in optional_anchors:
            self.template.fill_anchor(anchor, {})

    def _process_multi_source_plot(
        self,
        split_anchors: List[str],
        optional_anchors: List[str],
        y_definitions: List[Dict[str, str]],
    ):
        varied_keys, domain = self._collect_variations(y_definitions)

        self._fill_optional_multi_source_anchors(
            split_anchors, optional_anchors, varied_keys, domain
        )
        return varied_keys

    def _collect_variations(
        self, y_definitions: List[Dict[str, str]]
    ) -> Tuple[List[str], List[str]]:
        varied_values = defaultdict(set)
        for defn in y_definitions:
            for key in FILENAME_FIELD:
                varied_values[key].add(defn.get(key, None))
            varied_values[CONCAT_FIELDS].add(
                FIELD_SEPARATOR.join([defn.get(FILENAME, ""), defn.get(FIELD, "")])
            )

        varied_keys = []

        for filename_or_field in FILENAME_FIELD:
            value_set = varied_values[filename_or_field]
            num_values = len(value_set)
            if num_values == 1:
                continue
            varied_keys.append(filename_or_field)

        domain = self._get_domain(varied_keys, varied_values)

        return varied_keys, domain

    def _fill_optional_multi_source_anchors(
        self,
        split_anchors: List[str],
        optional_anchors: List[str],
        varied_keys: List[str],
        domain: List[str],
    ):
        if not optional_anchors:
            return

        grouped_keys = ["rev", *varied_keys]
        self._fill_group_by(split_anchors, optional_anchors, grouped_keys)

        self._fill_optional_anchor(
            split_anchors,
            optional_anchors,
            "pivot_field",
            " + '::' + ".join([f"datum.{key}" for key in grouped_keys]),
        )

        concat_field = FIELD_SEPARATOR.join(varied_keys)
        self._fill_optional_anchor(
            split_anchors, optional_anchors, "row", {"field": concat_field}
        )

        if not optional_anchors:
            return

        for anchor in ["stroke_dash", "shape"]:
            self._fill_optional_anchor_mapping(
                split_anchors, optional_anchors, concat_field, anchor, domain
            )

    def _fill_group_by(
        self,
        split_anchors: List[str],
        optional_anchors: List[str],
        grouped_keys: List[str],
    ):
        self._fill_optional_anchor(
            split_anchors, optional_anchors, "group_by", grouped_keys
        )
        self._fill_optional_anchor(
            split_anchors,
            optional_anchors,
            "group_by_x",
            [*grouped_keys, self.properties.get("x")],
        )
        self._fill_optional_anchor(
            split_anchors,
            optional_anchors,
            "group_by_y",
            [*grouped_keys, self.properties.get("y")],
        )

    def _fill_optional_anchor(
        self,
        split_anchors: List[str],
        optional_anchors: List[str],
        name: str,
        value: Any,
    ):
        if name not in optional_anchors:
            return

        optional_anchors.remove(name)

        if name in split_anchors:
            return

        self.template.fill_anchor(name, value)

    def _get_domain(self, varied_keys: List[str], varied_values: Dict[str, set]):
        if len(varied_keys) == 2:
            domain = list(varied_values[CONCAT_FIELDS])
        else:
            filename_or_field = varied_keys[0]
            domain = list(varied_values[filename_or_field])

        domain.sort()
        return domain

    def _fill_optional_anchor_mapping(
        self,
        split_anchors: List[str],
        optional_anchors: List[str],
        field: str,
        name: str,
        domain: List[str],
    ):  # pylint: disable=too-many-arguments
        if name not in optional_anchors:
            return

        optional_anchors.remove(name)

        encoding = self._get_optional_anchor_mapping(field, name, domain)

        if name in split_anchors:
            self._set_split_content(name, encoding)
            return

        self.template.fill_anchor(name, encoding)

    def _get_optional_anchor_mapping(
        self,
        field: str,
        name: str,
        domain: List[str],
    ):
        full_range_values: List[Any] = self._optional_anchor_ranges.get(name, [])
        anchor_range_values = full_range_values.copy()

        anchor_range = []
        for _ in range(len(domain)):
            if not anchor_range_values:
                anchor_range_values = full_range_values.copy()
            range_value = anchor_range_values.pop(0)
            anchor_range.append(range_value)

        legend = (
            {"legend": {"symbolFillColor": "transparent", "symbolStrokeColor": "grey"}}
            if name != "color"
            else {}
        )

        return {
            "field": field,
            "scale": {"domain": domain, "range": anchor_range},
            **legend,
        }

    def _update_datapoints(self, varied_keys: Optional[List[str]] = None):
        if varied_keys is None:
            return

        if len(varied_keys) == 2:
            to_concatenate = varied_keys
            to_remove = varied_keys
        else:
            to_concatenate = []
            to_remove = [key for key in FILENAME_FIELD if key not in varied_keys]

        for datapoint in self.datapoints:
            if to_concatenate:
                concat_key = FIELD_SEPARATOR.join(to_concatenate)
                datapoint[concat_key] = FIELD_SEPARATOR.join(
                    [datapoint.get(k) for k in to_concatenate]
                )
            for key in to_remove:
                datapoint.pop(key, None)

    def _set_split_content(self, name: str, value: Any):
        self._split_content[Template.anchor(name)] = (
            value if isinstance(value, str) else json.dumps(value)
        )
