from dvc_render.base import Renderer

# pylint: disable=missing-function-docstring


def test_remove_special_characters():
    special_chars = r"!@#$%^&*()[]{};,<>?\/:.|`~=_+ "
    dirty = f"plot_name{special_chars}"
    assert Renderer.remove_special_chars(dirty) == "plot_name" + "_" * len(
        special_chars
    )
