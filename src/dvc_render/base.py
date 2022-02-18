import abc
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, Union

if TYPE_CHECKING:
    from os import PathLike

StrPath = Union[str, "PathLike[str]"]


class Renderer(abc.ABC):

    DIV = """
    <div id="{id}">
      {partial}
    </div>
    """

    EXTENSIONS: Iterable[str] = {}

    def __init__(self, datapoints: Dict, name: str, **properties):
        self.datapoints = datapoints
        self.name = name
        self.properties = properties

    @abc.abstractmethod
    def partial_html(self) -> str:
        """
        Us this method to generate HTML content,
        to fill `{partial}` inside self.DIV.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def TYPE(self):  # pylint: disable=missing-function-docstring
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def SCRIPTS(self):  # pylint: disable=missing-function-docstring
        raise NotImplementedError

    @staticmethod
    def remove_special_chars(string: str) -> str:
        "Ensure string is valid HTML id."
        return string.translate(
            {ord(c): "_" for c in r"!@#$%^&*()[]{};,<>?\/:.|`~=_+"}
        )

    def generate_html(self) -> str:
        "Return `DIV` formatted with `partial_html`."
        partial = self.partial_html()

        div_id = self.remove_special_chars(self.name)
        div_id = f"plot_{div_id}"

        return self.DIV.format(id=div_id, partial=partial)

    @classmethod
    def matches(
        cls, filename, properties  # pylint: disable=unused-argument
    ) -> bool:
        "Check if the Renderer is suitable."
        return Path(filename).suffix in cls.EXTENSIONS
