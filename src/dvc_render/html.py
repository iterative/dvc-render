from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .exceptions import DvcRenderException

if TYPE_CHECKING:
    from .base import Renderer, StrPath


PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
    {refresh_tag}
    <title>DVC Plot</title>
    {scripts}
    <style>
        table {
            border-spacing: 15px;
        }
    </style>
</head>
<body>
    {plot_divs}
</body>
</html>"""


class MissingPlaceholderError(DvcRenderException):
    def __init__(self, placeholder):
        super().__init__(f"HTML template has to contain '{placeholder}'.")


class HTML:
    SCRIPTS_PLACEHOLDER = "scripts"
    PLOTS_PLACEHOLDER = "plot_divs"
    PLOTS_PLACEHOLDER_FORMAT_STR = f"{{{PLOTS_PLACEHOLDER}}}"
    REFRESH_PLACEHOLDER = "refresh_tag"
    REFRESH_TAG = '<meta http-equiv="refresh" content="{}">'

    def __init__(
        self,
        template: Optional[str] = None,
        refresh_seconds: Optional[int] = None,
    ):
        template = template or PAGE_HTML
        if self.PLOTS_PLACEHOLDER_FORMAT_STR not in template:
            raise MissingPlaceholderError(self.PLOTS_PLACEHOLDER_FORMAT_STR)

        self.template = template
        self.elements: List[str] = []
        self.scripts: str = ""
        self.refresh_tag = ""
        if refresh_seconds is not None:
            self.refresh_tag = self.REFRESH_TAG.format(refresh_seconds)

    def with_scripts(self, scripts: str) -> "HTML":
        "Extend scripts element."
        if scripts not in self.scripts:
            self.scripts += f"\n{scripts}"
        return self

    def with_element(self, html: str) -> "HTML":
        "Adds custom html element."
        self.elements.append(html)
        return self

    def embed(self) -> str:
        "Format HTML template with all elements."
        kwargs = {
            self.SCRIPTS_PLACEHOLDER: self.scripts,
            self.PLOTS_PLACEHOLDER: "\n".join(self.elements),
            self.REFRESH_PLACEHOLDER: self.refresh_tag,
        }
        for placeholder, value in kwargs.items():
            self.template = self.template.replace(
                "{" + placeholder + "}", value
            )
        return self.template


def render_html(
    renderers: List["Renderer"],
    output_file: "StrPath",
    template_path: Optional["StrPath"] = None,
    refresh_seconds: Optional[int] = None,
) -> "StrPath":
    "User renderers to fill an HTML template and write to path."
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)

    page_html = None
    if template_path:
        with open(template_path, encoding="utf-8") as fobj:
            page_html = fobj.read()

    document = HTML(page_html, refresh_seconds=refresh_seconds)

    for renderer in renderers:
        document.with_scripts(renderer.SCRIPTS)
        document.with_element(renderer.generate_html(html_path=output_path))

    output_path.write_text(document.embed(), encoding="utf8")

    return output_file
