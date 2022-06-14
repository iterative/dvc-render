from .base import Renderer

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None


class TableRenderer(Renderer):
    """Renderer for tables."""

    TYPE = "table"
    DIV = """
        <div id="{id}" style="text-align: center; padding: 10x">
            <p>{id}</p>
            <div style="display: flex;justify-content: center;">
                {partial}
            </div>
        </div>"""

    SCRIPTS = ""

    EXTENSIONS = {".yml", ".yaml", ".json"}

    def partial_html(self, **kwargs) -> str:
        # From list of dicts to dict of lists
        data = {
            k: [datapoint[k] for datapoint in self.datapoints]
            for k in self.datapoints[0]
        }
        if tabulate is None:
            raise ImportError(f"{self.__class__} requires `tabulate`.")
        return tabulate(data, headers="keys", tablefmt="html")
