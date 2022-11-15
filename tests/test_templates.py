import os

import pytest

from dvc_render.vega_templates import (
    TEMPLATES,
    LinearTemplate,
    ScatterTemplate,
    Template,
    TemplateContentDoesNotMatch,
    TemplateNotFoundError,
    dump_templates,
    get_template,
)

# pylint: disable=missing-function-docstring, unused-argument


def test_raise_on_no_template():
    with pytest.raises(TemplateNotFoundError):
        get_template("non_existing_template.json")


@pytest.mark.parametrize(
    "template_path, target_name",
    [
        (os.path.join(".dvc", "plots", "template.json"), "template"),
        (os.path.join(".dvc", "plots", "template.json"), "template.json"),
        (
            os.path.join(".dvc", "plots", "subdir", "template.json"),
            os.path.join("subdir", "template.json"),
        ),
        (
            os.path.join(".dvc", "plots", "subdir", "template.json"),
            os.path.join("subdir", "template"),
        ),
        ("template.json", "template.json"),
    ],
)
def test_get_template_from_dir(tmp_dir, template_path, target_name):
    tmp_dir.gen(template_path, "template_content")
    assert (
        get_template(target_name, ".dvc/plots").content == "template_content"
    )


def test_get_template_exact_match(tmp_dir):
    tmp_dir.gen(os.path.join("foodir", "bar_template.json"), "bar")
    with pytest.raises(TemplateNotFoundError):
        # This was unexpectedly working when using rglob({template_name}*)
        # and could cause bugs.
        get_template("bar", "foodir")


def test_get_template_from_file(tmp_dir):
    tmp_dir.gen("foo/bar.json", "template_content")
    assert get_template("foo/bar.json").content == "template_content"


def test_get_template_fs(tmp_dir, mocker):
    tmp_dir.gen("foo/bar.json", "template_content")
    fs = mocker.MagicMock()
    get_template("foo/bar.json", fs=fs)
    fs.open.assert_called()
    fs.exists.assert_called()


def test_get_default_template():
    assert get_template(None).content == LinearTemplate().content


@pytest.mark.parametrize(
    "targets,expected_templates",
    (
        ([None, TEMPLATES]),
        (["linear", "scatter"], [ScatterTemplate, LinearTemplate]),
    ),
)
def test_init(tmp_dir, targets, expected_templates):
    output = "plots"
    dump_templates(output, targets)

    assert set(os.listdir(output)) == {
        cls.DEFAULT_NAME + ".json" for cls in expected_templates
    }


def test_raise_on_init_modified(tmp_dir):
    dump_templates(output=".", targets=["linear"])

    with open(tmp_dir / "linear.json", "a", encoding="utf-8") as fd:
        fd.write("modification")

    with pytest.raises(TemplateContentDoesNotMatch):
        dump_templates(output=".", targets=["linear"])


def test_escape_special_characters():
    value = "foo.bar[2]"
    assert Template.escape_special_characters(value) == "foo\\.bar\\[2\\]"
