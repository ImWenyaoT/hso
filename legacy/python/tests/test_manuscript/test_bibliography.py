"""BibTeX 生成 + cite key resolution 测试。"""

from __future__ import annotations

from datetime import date

from hso.manuscript.bibliography import (
    check_citation_consistency,
    papers_to_bib_entries,
    render_bibfile,
    resolve_citekeys,
)
from hso.models import Author, Paper, Venue


def _paper(paper_id: str, title: str, surname: str, year: int = 2024, type_: str = "journal") -> Paper:
    return Paper(
        paper_id=paper_id,
        doi=paper_id.replace("doi:", "") if paper_id.startswith("doi:") else None,
        title=title,
        authors=[Author(name=f"First {surname}")],
        venue=Venue(name="Pattern Recognition", type=type_),
        published_at=date(year, 6, 1),
        source="semanticscholar",
    )


class TestCiteKeyGeneration:
    def test_basic_key(self) -> None:
        entries = papers_to_bib_entries([_paper("doi:1", "Diffusion Models", "Smith")])
        assert entries[0].key == "smith2024diffusion"

    def test_skips_stopwords(self) -> None:
        entries = papers_to_bib_entries([_paper("doi:1", "A Survey on Editing", "Wang")])
        # 'a' / 'on' 应被跳过 → survey
        assert entries[0].key == "wang2024survey"

    def test_collision_gets_suffix(self) -> None:
        entries = papers_to_bib_entries(
            [
                _paper("doi:1", "Diffusion X", "Smith"),
                _paper("doi:2", "Diffusion Y", "Smith"),
                _paper("doi:3", "Diffusion Z", "Smith"),
            ]
        )
        assert entries[0].key == "smith2024diffusion"
        assert entries[1].key == "smith2024diffusiona"
        assert entries[2].key == "smith2024diffusionb"

    def test_no_authors_uses_anon(self) -> None:
        p = Paper(
            paper_id="x", title="Untitled work", authors=[], published_at=date(2024, 1, 1),
        )
        entries = papers_to_bib_entries([p])
        assert entries[0].key.startswith("anon2024")


class TestBibtexRendering:
    def test_journal_uses_article_entry(self) -> None:
        entries = papers_to_bib_entries([_paper("doi:1", "X Y", "Smith")])
        assert entries[0].bibtex.startswith("@article{")
        assert "title = {X Y}" in entries[0].bibtex
        assert "year = {2024}" in entries[0].bibtex
        assert "author = {First Smith}" in entries[0].bibtex

    def test_preprint_uses_misc(self) -> None:
        entries = papers_to_bib_entries(
            [_paper("doi:1", "X", "Smith", type_="preprint")]
        )
        assert entries[0].bibtex.startswith("@misc{")

    def test_render_bibfile_separates_entries(self) -> None:
        entries = papers_to_bib_entries(
            [_paper("doi:1", "A B", "Smith"), _paper("doi:2", "C D", "Wang")]
        )
        bib = render_bibfile(entries)
        assert "@article{smith2024" in bib
        assert "@article{wang2024" in bib
        # 双换行分隔
        assert "\n\n" in bib


class TestResolveCiteKeys:
    def test_replaces_paper_id_with_bibtex_key(self) -> None:
        entries = papers_to_bib_entries([_paper("doi:1", "Diffusion X", "Smith")])
        body = r"Recent work \cite{paper:doi:1} shows that..."
        resolved, unresolved = resolve_citekeys(body, entries)
        assert r"\cite{smith2024diffusion}" in resolved
        assert unresolved == []

    def test_unresolved_id_kept_and_reported(self) -> None:
        entries = papers_to_bib_entries([_paper("doi:1", "X Y", "Smith")])
        body = r"Foo \cite{paper:doi:99}."
        resolved, unresolved = resolve_citekeys(body, entries)
        assert r"\cite{paper:doi:99}" in resolved  # 原样保留
        assert unresolved == ["doi:99"]

    def test_multiple_citations(self) -> None:
        entries = papers_to_bib_entries(
            [_paper("doi:1", "A", "Smith"), _paper("doi:2", "B", "Wang")]
        )
        body = r"\cite{paper:doi:1} and \cite{paper:doi:2}."
        resolved, _ = resolve_citekeys(body, entries)
        assert "smith2024" in resolved
        assert "wang2024" in resolved


class TestCitationConsistency:
    def test_perfect_match(self) -> None:
        body = r"\cite{paper:doi:1} \cite{paper:doi:2}"
        in_body, in_declared = check_citation_consistency(body, ["doi:1", "doi:2"])
        assert in_body == set()
        assert in_declared == set()

    def test_extra_in_body(self) -> None:
        body = r"\cite{paper:doi:1} \cite{paper:doi:rogue}"
        in_body, _ = check_citation_consistency(body, ["doi:1"])
        assert in_body == {"doi:rogue"}

    def test_missing_from_body(self) -> None:
        body = r"\cite{paper:doi:1}"
        _, in_declared = check_citation_consistency(body, ["doi:1", "doi:unused"])
        assert in_declared == {"doi:unused"}
