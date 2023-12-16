import json
import os

import pytest
from dvc_render.vega_templates import (
    TEMPLATES,
    LinearTemplate,
    ScatterTemplate,
    Template,
    TemplateContentDoesNotMatchError,
    TemplateNotFoundError,
    dump_templates,
    find_value,
    get_template,
)

# pylint: disable=missing-function-docstring, unused-argument


def test_raise_on_no_template():
    with pytest.raises(TemplateNotFoundError):
        get_template("non_existing_template.json")


@pytest.mark.parametrize(
    ("template_path", "target_name"),
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
def test_get_template_from_dir(tmp_path, monkeypatch, template_path, target_name):
    monkeypatch.chdir(tmp_path)
    template_content = {"template_content": "foo"}
    template_path = tmp_path / template_path
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text(json.dumps(template_content), encoding="utf-8")
    assert get_template(target_name, ".dvc/plots").content == template_content


def test_get_template_exact_match(tmp_path):
    template_path = tmp_path / "foodir" / "bar_template.json"
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text("bar", encoding="utf-8")
    with pytest.raises(TemplateNotFoundError):
        # This was unexpectedly working when using rglob({template_name}*)
        # and could cause bugs.
        get_template("bar", "foodir")


def test_get_template_from_file(tmp_path):
    template_content = {"template_content": "foo"}
    template_path = tmp_path / "foo/bar.json"
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text(json.dumps(template_content), encoding="utf-8")
    assert get_template(template_path).content == template_content


def test_get_template_fs(tmp_path, mocker):
    template_content = {"template_content": "foo"}
    template_path = tmp_path / "foo/bar.json"
    os.makedirs(template_path.parent, exist_ok=True)
    template_path.write_text(json.dumps(template_content), encoding="utf-8")
    fs = mocker.MagicMock()
    mocker.patch("json.load", return_value={})
    get_template(template_path, fs=fs)
    fs.open.assert_called()
    fs.exists.assert_called()


def test_get_default_template():
    assert get_template(None).content == LinearTemplate().content


@pytest.mark.parametrize(
    ("targets", "expected_templates"),
    (
        ([None, TEMPLATES]),
        (["linear", "scatter"], [ScatterTemplate, LinearTemplate]),
    ),
)
def test_init(tmp_path, targets, expected_templates):
    output = tmp_path / "plots"
    dump_templates(output, targets)

    assert set(os.listdir(output)) == {
        cls.DEFAULT_NAME + ".json" for cls in expected_templates
    }


def test_raise_on_init_modified(tmp_path):
    dump_templates(output=tmp_path, targets=["linear"])

    with open(tmp_path / "linear.json", "a", encoding="utf-8") as fd:
        fd.write("modification")

    with pytest.raises(TemplateContentDoesNotMatchError):
        dump_templates(output=tmp_path, targets=["linear"])


def test_escape_special_characters():
    value = "foo.bar[2]"
    assert Template.escape_special_characters(value) == "foo\\.bar\\[2\\]"


@pytest.mark.parametrize(
    ("content_dict", "value_name"),
    [
        ({"key": "value"}, "value"),
        ({"key": {"subkey": "value"}}, "value"),
        ({"key": [{"subkey": "value"}]}, "value"),
        ({"key1": [{"subkey": "foo"}], "key2": {"subkey2": "value"}}, "value"),
    ],
)
def test_find_value(content_dict, value_name):
    assert find_value(content_dict, value_name)
