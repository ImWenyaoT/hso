"""manuscript schema 基础测试。"""

from __future__ import annotations

from hso.models import BibEntry, DraftedSection, Outline, SectionPlan


class TestSectionPlan:
    def test_construction_with_defaults(self) -> None:
        sp = SectionPlan(section_id="intro", title="Introduction")
        assert sp.subtopics == []
        assert sp.planned_artifacts == []
        assert sp.cited_paper_ids == []
        assert sp.notes is None


class TestOutline:
    def test_construction(self) -> None:
        o = Outline(
            title="X",
            abstract_focus="Focus",
            keywords=["a", "b"],
            sections=[SectionPlan(section_id="intro", title="Introduction")],
        )
        assert o.title == "X"
        assert len(o.sections) == 1


class TestDraftedSection:
    def test_construction(self) -> None:
        d = DraftedSection(section_id="intro", title="Introduction", body="body")
        assert d.used_paper_ids == []
        assert d.used_artifact_ids == []


class TestBibEntry:
    def test_construction(self) -> None:
        e = BibEntry(key="smith2024x", paper_id="doi:1", bibtex="@article{smith2024x,...}")
        assert e.key == "smith2024x"
        assert e.paper_id == "doi:1"
