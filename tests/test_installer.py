"""Tests for --install detection and execution."""

import sys

import pytest

from rapidrepopull import installer
from rapidrepopull.installer import Outcome, detect, install_all, install_one, manual_reason


def make_repo(tmp_path, name, files):
    path = tmp_path / name
    path.mkdir(parents=True)
    for filename, content in files.items():
        target = path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("marker", "kind"),
    [
        ("go.mod", "go"),
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("requirements.txt", "python"),
        ("package.json", "node"),
    ],
)
def test_each_ecosystem_is_detected(tmp_path, marker, kind):
    path = make_repo(tmp_path, "tool", {marker: ""})
    recipe = detect(path)
    assert recipe is not None
    assert recipe.kind == kind


def test_detection_prefers_the_first_matching_recipe(tmp_path):
    path = make_repo(tmp_path, "tool", {"go.mod": "", "requirements.txt": ""})
    assert detect(path).kind == "go"


def test_a_data_repository_has_no_recipe(tmp_path):
    path = make_repo(tmp_path, "wordlists", {"passwords.txt": "hunter2\n"})
    assert detect(path) is None
    assert manual_reason(path) is None


def test_a_data_repository_reports_nothing_to_install(tmp_path):
    path = make_repo(tmp_path, "SecLists", {"README.md": "# wordlists\n"})
    result = install_one(path)
    assert result.outcome is Outcome.NOTHING
    assert result.ok


@pytest.mark.parametrize(
    ("marker", "fragment"),
    [
        ("Makefile", "Makefile"),
        ("CMakeLists.txt", "cmake"),
        ("pom.xml", "maven"),
        ("Cargo.toml", "cargo"),
    ],
)
def test_build_systems_we_do_not_drive_are_reported_as_manual(tmp_path, marker, fragment):
    path = make_repo(tmp_path, "tool", {marker: ""})
    result = install_one(path)
    assert result.outcome is Outcome.MANUAL
    assert fragment in result.detail


def test_a_visual_studio_project_is_manual(tmp_path):
    path = make_repo(tmp_path, "Seatbelt", {"Seatbelt.sln": "", "src/x.cs": ""})
    result = install_one(path)
    assert result.outcome is Outcome.MANUAL
    assert "MSBuild" in result.detail


def test_an_install_script_is_never_run(tmp_path):
    """A repository's own install.sh is arbitrary code and must be ignored."""
    canary = tmp_path / "canary"
    path = make_repo(
        tmp_path,
        "sketchy",
        {"install.sh": f"#!/bin/sh\ntouch {canary}\n", "README.md": ""},
    )
    result = install_one(path)
    assert result.outcome is Outcome.NOTHING
    assert not canary.exists()


def test_a_missing_toolchain_is_reported_not_attempted(tmp_path, monkeypatch):
    path = make_repo(tmp_path, "gotool", {"go.mod": "module x\n"})
    monkeypatch.setattr(installer.shutil, "which", lambda name: None)
    result = install_one(path)
    assert result.outcome is Outcome.MISSING_TOOL
    assert "go is not installed" in result.detail


def test_dry_run_reports_without_running(tmp_path, monkeypatch):
    path = make_repo(tmp_path, "gotool", {"go.mod": "module x\n"})
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/go")
    called = []
    monkeypatch.setattr(installer, "_run", lambda *a, **k: called.append(a))
    result = install_one(path, dry_run=True)
    assert result.outcome is Outcome.SKIPPED
    assert "would run" in result.detail
    assert called == []


def test_a_failing_build_is_reported_with_its_error(tmp_path, monkeypatch):
    path = make_repo(tmp_path, "gotool", {"go.mod": "module x\n"})
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/go")

    class Proc:
        returncode = 1
        stdout = ""
        stderr = "go: cannot find module\n"

    monkeypatch.setattr(installer, "_run", lambda *a, **k: Proc())
    result = install_one(path)
    assert result.outcome is Outcome.FAILED
    assert "cannot find module" in result.detail


def test_a_timeout_is_reported_not_raised(tmp_path, monkeypatch):
    import subprocess

    path = make_repo(tmp_path, "gotool", {"go.mod": "module x\n"})
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/go")

    def boom(*args, **kwargs):
        raise subprocess.TimeoutExpired("go", 1)

    monkeypatch.setattr(installer, "_run", boom)
    result = install_one(path, timeout=1)
    assert result.outcome is Outcome.FAILED
    assert "timed out" in result.detail


def test_a_directory_that_vanished_is_skipped(tmp_path):
    result = install_one(tmp_path / "gone")
    assert result.outcome is Outcome.SKIPPED


def test_requirements_are_installed_into_a_venv_inside_the_clone(tmp_path):
    """The real thing: a venv appears in the clone and nothing global changes."""
    path = make_repo(tmp_path, "pytool", {"requirements.txt": "\n"})
    result = install_one(path, timeout=300)
    assert result.outcome is Outcome.INSTALLED, result.detail
    assert (path / ".venv" / "bin" / "python").exists()


def test_the_venv_recipe_uses_the_running_interpreter(tmp_path):
    path = make_repo(tmp_path, "pytool", {"requirements.txt": ""})
    commands = installer._venv_requirements(path)
    assert commands[0][0] == sys.executable
    assert str(path / ".venv") in commands[0]


def test_install_all_examines_everything(tmp_path):
    paths = [
        make_repo(tmp_path, "a", {"README.md": ""}),
        make_repo(tmp_path, "b", {"Makefile": ""}),
        make_repo(tmp_path, "c", {"README.md": ""}),
    ]
    results = install_all(paths, dry_run=True)
    assert len(results) == 3
    assert {r.name for r in results} == {"a", "b", "c"}


def test_install_all_with_nothing_is_a_no_op():
    assert install_all([]) == []


def test_install_all_reports_each_result_as_it_lands(tmp_path):
    paths = [make_repo(tmp_path, n, {"README.md": ""}) for n in ("a", "b")]
    seen = []
    install_all(paths, dry_run=True, on_result=seen.append)
    assert len(seen) == 2
