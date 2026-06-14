"""Tests for the file-grouping logic."""

from local_commit.grouping import group_changes, _classify


def test_empty_changes() -> None:
    assert group_changes({"staged": [], "unstaged": [], "untracked": []}) == []


def test_single_py_file() -> None:
    changes = {
        "staged": [],
        "unstaged": [],
        "untracked": ["app/main.py"],
    }
    groups = group_changes(changes)
    assert len(groups) == 1
    assert groups[0]["label"] == "Python – app/"


def test_requirements_txt_is_dependencies() -> None:
    changes = {
        "staged": [],
        "unstaged": [],
        "untracked": ["requirements.txt"],
    }
    groups = group_changes(changes)
    assert groups[0]["label"] == "Dependencies"


def test_docker_file() -> None:
    assert "Docker" in _classify("Dockerfile")


def test_singletons_merged_when_many() -> None:
    changes = {
        "staged": [],
        "unstaged": [],
        "untracked": [
            "a.py",
            "b.js",
            "c.md",
            "d.yaml",
            "e.sh",
            "f.sql",
        ],
    }
    groups = group_changes(changes)
    # 5+ singletons should be merged into Miscellaneous
    misc = [g for g in groups if g["label"] == "Miscellaneous changes"]
    assert len(misc) == 1
    assert len(misc[0]["files"]) == 6
