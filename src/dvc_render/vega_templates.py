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
    def escape_special_characters(cls, value: str) -> str:
        "Escape special characters in `value`"
        for character in (".", "[", "]"):
            value = value.replace(character, "\\" + character)
        return value

    @classmethod
    def anchor_str(cls, name) -> str:
        "Get string wrapping ANCHOR formatted with name."
        return f'"{cls.anchor(name)}"'

    @staticmethod
    def check_field_exists(data, field):
        "Raise NoFieldInDataError if `field` not in `data`."
        if not any(field in row for row in data):
            raise NoFieldInDataError(field)


class BarHorizontalSortedTemplate(Template):
    DEFAULT_NAME = "bar_horizontal_sorted"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": Template.anchor("x"),
                "type": "quantitative",
                "title": Template.anchor("x_label"),
                "scale": {"zero": False},
            },
            "y": {
                "field": Template.anchor("y"),
                "type": "nominal",
                "title": Template.anchor("y_label"),
                "sort": "-x",
            },
            "yOffset": {"field": "rev"},
            "color": {"field": "rev", "type": "nominal"},
        },
    }


class BarHorizontalTemplate(Template):
    DEFAULT_NAME = "bar_horizontal"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": Template.anchor("x"),
                "type": "quantitative",
                "title": Template.anchor("x_label"),
                "scale": {"zero": False},
            },
            "y": {
                "field": Template.anchor("y"),
                "type": "nominal",
                "title": Template.anchor("y_label"),
            },
            "yOffset": {"field": "rev"},
            "color": {"field": "rev", "type": "nominal"},
        },
    }


class ConfusionTemplate(Template):
    DEFAULT_NAME = "confusion"
    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
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
                    "selection": {
                        "label": {
                            "type": "single",
                            "on": "mouseover",
                            "encodings": ["x", "y"],
                            "empty": "none",
                            "clear": "mouseout",
                        }
                    },
                    "mark": "rect",
                    "encoding": {
                        "tooltip": [
                            {"field": Template.anchor("x"), "type": "nominal"},
                            {"field": Template.anchor("y"), "type": "nominal"},
                        ],
                        "opacity": {
                            "condition": {"selection": "label", "value": 1},
                            "value": 0,
                        },
                    },
                },
                {
                    "transform": [{"filter": {"selection": "label"}}],
                    "layer": [
                        {"mark": {"type": "rect", "color": "lightpink"}},
                    ],
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
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
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
                    "selection": {
                        "label": {
                            "type": "single",
                            "on": "mouseover",
                            "encodings": ["x", "y"],
                            "empty": "none",
                            "clear": "mouseout",
                        }
                    },
                    "mark": "rect",
                    "encoding": {
                        "tooltip": [
                            {"field": Template.anchor("x"), "type": "nominal"},
                            {"field": Template.anchor("y"), "type": "nominal"},
                        ],
                        "opacity": {
                            "condition": {"selection": "label", "value": 1},
                            "value": 0,
                        },
                    },
                },
                {
                    "transform": [{"filter": {"selection": "label"}}],
                    "layer": [
                        {"mark": {"type": "rect", "color": "lightpink"}},
                    ],
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
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
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
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "params": [
            {
                "name": "smooth",
                "value": 0.2,
                "bind": {
                    "input": "range",
                    "min": 0.001,
                    "max": 1,
                    "step": 0.01,
                },
            },
        ],
        "transform": [
            {
                "loess": Template.anchor("y"),
                "on": Template.anchor("x"),
                "groupby": ["rev"],
                "bandwidth": {"signal": "smooth"},
            }
        ],
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
                    {"mark": "line", "point": True},
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


class LinearTemplate(Template):
    DEFAULT_NAME = "linear"

    DEFAULT_CONTENT = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": Template.anchor("data")},
        "title": Template.anchor("title"),
        "width": 300,
        "height": 300,
        "mark": {
            "type": "line",
            "point": True,
            "tooltip": {"content": "data"},
        },
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


class SimpleLinearTemplate(LinearTemplate):
    DEFAULT_NAME = "simple"


TEMPLATES = [
    SimpleLinearTemplate,
    LinearTemplate,
    ConfusionTemplate,
    NormalizedConfusionTemplate,
    ScatterTemplate,
    SmoothLinearTemplate,
    BarHorizontalSortedTemplate,
    BarHorizontalTemplate,
]


def _find_template(
    template_name: str, template_dir: Optional[str] = None, fs=None
) -> Optional["StrPath"]:
    _exists = Path.exists if fs is None else fs.exists

    if template_dir:
        template_path = Path(template_dir) / template_name
        if _exists(template_path):
            return template_path
        if _exists(template_path.with_suffix(Template.EXTENSION)):
            return template_path.with_suffix(Template.EXTENSION)

    template_path = Path(template_name)
    if _exists(template_path):
        return template_path.resolve()

    return None


def get_template(
    template: Union[Optional[str], Template] = None,
    template_dir: Optional[str] = None,
    fs=None,
) -> Template:
    """Return template instance based on given template arg.

    If template is already an instance, return it.
    If template is None, return default `linear` template.
    If template is a path, will try to find it:
        - Inside `template_dir`
        - As a relative path to cwd.
    If template matches one of the DEFAULT_NAMEs in TEMPLATES,
    return an instance of the one matching.
    """
    if isinstance(template, Template):
        return template

    if template is None:
        template = "linear"

    template_path = _find_template(template, template_dir, fs)

    _open = open if fs is None else fs.open
    if template_path:
        with _open(template_path, encoding="utf-8") as f:
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
