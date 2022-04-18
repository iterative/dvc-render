from .base import Renderer


class ImageRenderer(Renderer):
    """Renderer for image plots."""

    TYPE = "image"
    DIV = """
        <div
            id="{id}"
            style="border:1px solid black;text-align:center;
            white-space: nowrap;overflow-y:hidden;">
            {partial}
        </div>"""

    TITLE_FIELD = "rev"
    SRC_FIELD = "src"

    SCRIPTS = ""

    EXTENSIONS = {".jpg", ".jpeg", ".gif", ".png"}

    def partial_html(self) -> str:
        div_content = []
        for datapoint in self.datapoints:
            div_content.append(
                f"""
                <div
                    style="border:1px dotted black;margin:2px;display:
                    inline-block;
                    overflow:hidden;margin-left:8px;">
                    <p>{datapoint[self.TITLE_FIELD]}</p>
                    <img src="{datapoint[self.SRC_FIELD]}">
                </div>
                """
            )
        if div_content:
            div_content.insert(0, f"<p>{self.name}</p>")
            return "\n".join(div_content)
        return ""
