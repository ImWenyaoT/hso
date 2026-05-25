"""ElsevierTemplate 渲染测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from hso.manuscript import ElsevierTemplate, ManuscriptSection
from hso.manuscript.template import (
    Affiliation,
    ManuscriptDocument,
    TemplateAuthor,
)


@pytest.fixture
def doc() -> ManuscriptDocument:
    return ManuscriptDocument(
        title="A Diffusion Approach to Image Editing",
        authors=[
            TemplateAuthor(name="Alice Wang", affiliation_id="a", email="alice@example.org"),
            TemplateAuthor(name="Bob Chen", affiliation_id="a"),
        ],
        affiliations=[
            Affiliation(id="a", organization="Test Lab", country="China"),
        ],
        abstract="We propose a novel method.",
        keywords=["diffusion", "image editing"],
        sections=[
            ManuscriptSection(id="intro", title="Introduction", body="Some intro text."),
            ManuscriptSection(id="method", title="Method", body="Some method text."),
        ],
        journal="Pattern Recognition",
    )


class TestRender:
    def test_renders_documentclass(self, doc: ManuscriptDocument) -> None:
        out = ElsevierTemplate().render(doc)
        assert "\\documentclass[review,12pt,a4paper]{elsarticle}" in out

    def test_includes_frontmatter(self, doc: ManuscriptDocument) -> None:
        out = ElsevierTemplate().render(doc)
        assert "\\begin{frontmatter}" in out
        assert "\\end{frontmatter}" in out
        assert "A Diffusion Approach to Image Editing" in out
        assert "\\begin{abstract}" in out

    def test_includes_authors_and_emails(self, doc: ManuscriptDocument) -> None:
        out = ElsevierTemplate().render(doc)
        assert "Alice Wang" in out
        assert "Bob Chen" in out
        assert "alice@example.org" in out

    def test_includes_keywords_with_sep(self, doc: ManuscriptDocument) -> None:
        out = ElsevierTemplate().render(doc)
        assert "diffusion" in out
        assert "image editing" in out
        assert "\\sep" in out  # Elsevier 关键字分隔符

    def test_includes_sections_with_labels(self, doc: ManuscriptDocument) -> None:
        out = ElsevierTemplate().render(doc)
        assert "\\section{Introduction}" in out
        assert "\\label{sec:intro}" in out
        assert "Some method text." in out

    def test_bibliography_toggle(self, doc: ManuscriptDocument) -> None:
        out_with = ElsevierTemplate().render(doc)
        assert "\\bibliography{refs}" in out_with

        doc_no_bib = doc.model_copy(update={"has_bibliography": False})
        out_without = ElsevierTemplate().render(doc_no_bib)
        assert "\\bibliography" not in out_without

    def test_render_to_file(self, doc: ManuscriptDocument, tmp_path: Path) -> None:
        path = tmp_path / "out" / "main.tex"
        ElsevierTemplate().render_to_file(doc, path)
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        assert "\\documentclass" in text


class TestStrictUndefined:
    def test_missing_field_raises(self, tmp_path: Path) -> None:
        # 写一个用未知变量的模板，应抛 UndefinedError
        bad_template = tmp_path / "bad.tex.j2"
        bad_template.write_text("Hello {{ unknown_var }}", encoding="utf-8")
        from jinja2.exceptions import UndefinedError

        tmpl = ElsevierTemplate(template_dir=tmp_path)
        doc = ManuscriptDocument(
            title="t",
            authors=[],
            affiliations=[],
            abstract="a",
            sections=[],
        )
        with pytest.raises(UndefinedError):
            tmpl.render(doc, template_name="bad.tex.j2")
