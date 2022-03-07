import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .exceptions import DvcRenderException

if TYPE_CHECKING:
    from .base import StrPath


class TemplateNotFoundError(DvcRenderException):
    def __init__(self, path):
        super().__init__(f"Template '{path}' not found.")


class NoFieldInDataError(DvcRenderException):
    def __init__(self, field_name):
        super().__init__(
            f"Field '{field_name}' does not exist in provided data."
        )


class TemplateContentDoesNotMatch(DvcRenderException):
    def __init__(self, template_name: str, path: str):
        super().__init__(
            f"Template '{path}' already exists "
            f"and its content is different than '{template_name}' content. "
            "Remove it manually if you want to recreate it."
        )


class Template:
    INDENT = 4
    SEPARATORS = (",", ": ")
    EXTENSION = ".json"
    ANCHOR = "<DVC_METRIC_{}>"

    DEFAULT_CONTENT: Optional[Dict[str, Any]] = None
    DEFAULT_NAME: Optional[str] = None

    def __init__(self, content=None, name=None):
        if content:
            self.content = content
        else:
            self.content = (
                json.dumps(
                    self.DEFAULT_CONTENT,
                    indent=self.INDENT,
                    separators=self.SEPARATORS,
                )
                + "\n"
            )

        self.name = name or self.DEFAULT_NAME
        assert self.content and self.name
        self.filename = Path(self.name).with_suffix(self.EXTENSION)

    @classmethod
    def anchor(cls, name):
        "Get ANCHOR formatted with name."
        return cls.ANCHOR.format(name.upper())

    def has_anchor(self, name) -> bool:
        "Check if ANCHOR formatted with name is in content."
        return self.anchor_str(name) in self.content

    @classmethod
    def fill_anchor(cls, content, name, value) -> str:
        "Replace anchor `name` with `value` in content."
        value_str = json.dumps(
            value, indent=cls.INDENT, separators=cls.SEPARATORS, sort_keys=True
        )
        return content.replace(cls.anchor_str(name), value_str)

    @classmethod
    def anchor_str(cls, name) -> str:
        "Get string wrapping ANCHOR formatted with name."
        return f'"{cls.anchor(name)}"'

    @staticmethod
    def check_field_exists(data, field):
        "Raise NoFieldInDataError if `field` not in `data`."
        if not any(field in row for row in data):
            raise NoFieldInDataError(field)


class SimpleLinearTemplate(Template):
    DEFAULT_NAME = "simple"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "mark": {"type": "line"},
        "encoding": {
            "x": {
                "field": Template.anchor("x"),
                "type": "quantitative",
                "title": Template.anchor("x_label"),
            },
            "y": {
                "field": Template.anchor("y"),
                "type": "quantitative",
                "title": Template.anchor("y_label"),
                "scale": {"zero": False},
            },
            "color": {"field": "rev", "type": "nominal"},
        },
    }


class ConfusionTemplate(Template):
    DEFAULT_NAME = "confusion"
    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "facet": {"field": "rev", "type": "nominal"},
        "spec": {
            "transform": [
                {
                    "aggregate": [{"op": "count", "as": "xy_count"}],
                    "groupby": [Template.anchor("y"), Template.anchor("x")],
                },
                {
                    "impute": "xy_count",
                    "groupby": ["rev", Template.anchor("y")],
                    "key": Template.anchor("x"),
                    "value": 0,
                },
                {
                    "impute": "xy_count",
                    "groupby": ["rev", Template.anchor("x")],
                    "key": Template.anchor("y"),
                    "value": 0,
                },
                {
                    "joinaggregate": [
                        {"op": "max", "field": "xy_count", "as": "max_count"}
                    ],
                    "groupby": [],
                },
                {
                    "calculate": "datum.xy_count / datum.max_count",
                    "as": "percent_of_max",
                },
            ],
            "encoding": {
                "x": {
                    "field": Template.anchor("x"),
                    "type": "nominal",
                    "sort": "ascending",
                    "title": Template.anchor("x_label"),
                },
                "y": {
                    "field": Template.anchor("y"),
                    "type": "nominal",
                    "sort": "ascending",
                    "title": Template.anchor("y_label"),
                },
            },
            "layer": [
                {
                    "mark": "rect",
                    "width": 300,
                    "height": 300,
                    "encoding": {
                        "color": {
                            "field": "xy_count",
                            "type": "quantitative",
                            "title": "",
                            "scale": {"domainMin": 0, "nice": True},
                        }
                    },
                },
                {
                    "mark": "text",
                    "encoding": {
                        "text": {"field": "xy_count", "type": "quantitative"},
                        "color": {
                            "condition": {
                                "test": "datum.percent_of_max > 0.5",
                                "value": "white",
                            },
                            "value": "black",
                        },
                    },
                },
            ],
        },
    }


class NormalizedConfusionTemplate(Template):
    DEFAULT_NAME = "confusion_normalized"
    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "facet": {"field": "rev", "type": "nominal"},
        "spec": {
            "transform": [
                {
                    "aggregate": [{"op": "count", "as": "xy_count"}],
                    "groupby": [Template.anchor("y"), Template.anchor("x")],
                },
                {
                    "impute": "xy_count",
                    "groupby": ["rev", Template.anchor("y")],
                    "key": Template.anchor("x"),
                    "value": 0,
                },
                {
                    "impute": "xy_count",
                    "groupby": ["rev", Template.anchor("x")],
                    "key": Template.anchor("y"),
                    "value": 0,
                },
                {
                    "joinaggregate": [
                        {"op": "sum", "field": "xy_count", "as": "sum_y"}
                    ],
                    "groupby": [Template.anchor("y")],
                },
                {
                    "calculate": "datum.xy_count / datum.sum_y",
                    "as": "percent_of_y",
                },
            ],
            "encoding": {
                "x": {
                    "field": Template.anchor("x"),
                    "type": "nominal",
                    "sort": "ascending",
                    "title": Template.anchor("x_label"),
                },
                "y": {
                    "field": Template.anchor("y"),
                    "type": "nominal",
                    "sort": "ascending",
                    "title": Template.anchor("y_label"),
                },
            },
            "layer": [
                {
                    "mark": "rect",
                    "width": 300,
                    "height": 300,
                    "encoding": {
                        "color": {
                            "field": "percent_of_y",
                            "type": "quantitative",
                            "title": "",
                            "scale": {"domain": [0, 1]},
                        }
                    },
                },
                {
                    "mark": "text",
                    "encoding": {
                        "text": {
                            "field": "percent_of_y",
                            "type": "quantitative",
                            "format": ".2f",
                        },
                        "color": {
                            "condition": {
                                "test": "datum.percent_of_y > 0.5",
                                "value": "white",
                            },
                            "value": "black",
                        },
                    },
                },
            ],
        },
    }


class ScatterTemplate(Template):
    DEFAULT_NAME = "scatter"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "layer": [
            {
                "encoding": {
                    "x": {
                        "field": Template.anchor("x"),
                        "type": "quantitative",
                        "title": Template.anchor("x_label"),
                    },
                    "y": {
                        "field": Template.anchor("y"),
                        "type": "quantitative",
                        "title": Template.anchor("y_label"),
                        "scale": {"zero": False},
                    },
                    "color": {"field": "rev", "type": "nominal"},
                },
                "layer": [
                    {"mark": "point"},
                    {
                        "selection": {
                            "label": {
                                "type": "single",
                                "nearest": True,
                                "on": "mouseover",
                                "encodings": ["x"],
                                "empty": "none",
                                "clear": "mouseout",
                            }
                        },
                        "mark": "point",
                        "encoding": {
                            "opacity": {
                                "condition": {
                                    "selection": "label",
                                    "value": 1,
                                },
                                "value": 0,
                            }
                        },
                    },
                ],
            },
            {
                "transform": [{"filter": {"selection": "label"}}],
                "layer": [
                    {
                        "encoding": {
                            "text": {
                                "type": "quantitative",
                                "field": Template.anchor("y"),
                            },
                            "x": {
                                "field": Template.anchor("x"),
                                "type": "quantitative",
                            },
                            "y": {
                                "field": Template.anchor("y"),
                                "type": "quantitative",
                            },
                        },
                        "layer": [
                            {
                                "mark": {
                                    "type": "text",
                                    "align": "left",
                                    "dx": 5,
                                    "dy": -5,
                                },
                                "encoding": {
                                    "color": {
                                        "type": "nominal",
                                        "field": "rev",
                                    }
                                },
                            }
                        ],
                    }
                ],
            },
        ],
    }


class SmoothLinearTemplate(Template):
    DEFAULT_NAME = "smooth"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "mark": {"type": "line"},
        "encoding": {
            "x": {
                "field": Template.anchor("x"),
                "type": "quantitative",
                "title": Template.anchor("x_label"),
            },
            "y": {
                "field": Template.anchor("y"),
                "type": "quantitative",
                "title": Template.anchor("y_label"),
                "scale": {"zero": False},
            },
            "color": {"field": "rev", "type": "nominal"},
        },
        "transform": [
            {
                "loess": Template.anchor("y"),
                "on": Template.anchor("x"),
                "groupby": ["rev"],
                "bandwidth": 0.3,
            }
        ],
    }


class LinearTemplate(Template):
    DEFAULT_NAME = "linear"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "layer": [
            {
                "encoding": {
                    "x": {
                        "field": Template.anchor("x"),
                        "type": "quantitative",
                        "title": Template.anchor("x_label"),
                    },
                    "y": {
                        "field": Template.anchor("y"),
                        "type": "quantitative",
                        "title": Template.anchor("y_label"),
                        "scale": {"zero": False},
                    },
                    "color": {"field": "rev", "type": "nominal"},
                },
                "layer": [
                    {"mark": "line"},
                    {
                        "selection": {
                            "label": {
                                "type": "single",
                                "nearest": True,
                                "on": "mouseover",
                                "encodings": ["x"],
                                "empty": "none",
                                "clear": "mouseout",
                            }
                        },
                        "mark": "point",
                        "encoding": {
                            "opacity": {
                                "condition": {
                                    "selection": "label",
                                    "value": 1,
                                },
                                "value": 0,
                            }
                        },
                    },
                ],
            },
            {
                "transform": [{"filter": {"selection": "label"}}],
                "layer": [
                    {
                        "mark": {"type": "rule", "color": "gray"},
                        "encoding": {
                            "x": {
                                "field": Template.anchor("x"),
                                "type": "quantitative",
                            }
                        },
                    },
                    {
                        "encoding": {
                            "text": {
                                "type": "quantitative",
                                "field": Template.anchor("y"),
                            },
                            "x": {
                                "field": Template.anchor("x"),
                                "type": "quantitative",
                            },
                            "y": {
                                "field": Template.anchor("y"),
                                "type": "quantitative",
                            },
                        },
                        "layer": [
                            {
                                "mark": {
                                    "type": "text",
                                    "align": "left",
                                    "dx": 5,
                                    "dy": -5,
                                },
                                "encoding": {
                                    "color": {
                                        "type": "nominal",
                                        "field": "rev",
                                    }
                                },
                            }
                        ],
                    },
                ],
            },
        ],
    }


TEMPLATES = [
    SimpleLinearTemplate,
    LinearTemplate,
    ConfusionTemplate,
    NormalizedConfusionTemplate,
    ScatterTemplate,
    SmoothLinearTemplate,
]


def _find_template(
    template_name: str, template_dir: Optional[str] = None
) -> Optional["StrPath"]:
    if template_dir:
        for template_path in Path(template_dir).rglob(f"{template_name}*"):
            return template_path

    template_path = Path(template_name)
    if template_path.exists():
        return template_path.resolve()

    return None


def get_template(
    template: Union[Optional[str], Template] = None,
    template_dir: Optional[str] = None,
) -> Template:
    """Return template instance based on given template arg.

    If template is already an instance, return it.
    If template is None, return default `linear` template.
    If template is a path, will try to find it as absolute
    path or inside template_dir.
    If template matches one of the DEFAULT_NAMEs in TEMPLATES,
    return an instance of the one matching.
    """
    if isinstance(template, Template):
        return template

    if template is None:
        template = "linear"

    template_path = _find_template(template, template_dir)

    if template_path:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Template(content, name=template)

    for template_cls in TEMPLATES:
        if template_cls.DEFAULT_NAME == template:
            return template_cls()

    raise TemplateNotFoundError(template)


def dump_templates(output: "StrPath", targets: Optional[List] = None) -> None:
    "Write TEMPLATES in `.json` format to `output`."
    output = Path(output)
    output.mkdir(exist_ok=True)

    if targets:
        templates = [
            template
            for template in TEMPLATES
            if template.DEFAULT_NAME in targets
        ]
    else:
        templates = TEMPLATES

    for template_cls in templates:
        template = template_cls()
        path = output / template.filename

        if path.exists():
            content = path.read_text(encoding="utf-8")
            if content != template.content:
                raise TemplateContentDoesNotMatch(
                    template.DEFAULT_NAME or "", path
                )
        else:
            path.write_text(template.content, encoding="utf-8")
