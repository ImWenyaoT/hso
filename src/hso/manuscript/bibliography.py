"""BibTeX 生成 + 正文 \\cite{paper:<id>} 占位 → 真实 cite key 解析。"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import cast

from hso.models import BibEntry, Paper

logger = logging.getLogger(__name__)

_CITE_PATTERN = re.compile(r"\\cite\{paper:([^}]+)\}")


def _slugify(s: str) -> str:
    """简单 slugify：去标点，保留字母数字。"""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _first_author_surname(paper: Paper) -> str:
    """从首作者全名中粗略取姓（取最后一个 token，西文姓在后）。中文名返回原串。"""
    if not paper.authors:
        return "anon"
    full = paper.authors[0].name.strip()
    tokens = full.split()
    return _slugify(tokens[-1] if tokens else full) or "anon"


def _first_title_word(paper: Paper) -> str:
    """从标题取首个 stopword 之外的词。"""
    stopwords = {"a", "an", "the", "on", "of", "for", "to", "in", "and", "or"}
    for word in re.findall(r"[A-Za-z]+", paper.title or ""):
        slug = word.lower()
        if slug not in stopwords:
            return cast(str, slug)
    return "paper"


def _generate_key(paper: Paper) -> str:
    """生成 cite key：<surname><year><firstword>。冲突由调用方加后缀。"""
    year = str(paper.published_at.year) if paper.published_at else "nodate"
    return f"{_first_author_surname(paper)}{year}{_first_title_word(paper)}"


def _format_authors_bibtex(paper: Paper) -> str:
    """BibTeX author 字段：'A and B and C'。"""
    if not paper.authors:
        return ""
    return " and ".join(a.name for a in paper.authors)


def _escape_braces(s: str) -> str:
    """简单转义 BibTeX 字段值中的 {} %。"""
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _paper_to_bibtex(paper: Paper, key: str) -> str:
    """生成单条 @article。preprint 用 @misc。"""
    fields: list[tuple[str, str]] = []
    fields.append(("title", _escape_braces(paper.title)))
    if paper.authors:
        fields.append(("author", _format_authors_bibtex(paper)))
    if paper.published_at:
        fields.append(("year", str(paper.published_at.year)))
    if paper.venue and paper.venue.name:
        fields.append(("journal", _escape_braces(paper.venue.name)))
    if paper.doi:
        fields.append(("doi", paper.doi))
    if paper.url:
        fields.append(("url", paper.url))
    if paper.arxiv_id:
        fields.append(("note", f"arXiv:{paper.arxiv_id}"))

    entry_type = "article" if paper.venue and paper.venue.type == "journal" else "misc"
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields)
    return f"@{entry_type}{{{key},\n{body}\n}}"


def papers_to_bib_entries(papers: Iterable[Paper]) -> list[BibEntry]:
    """生成 BibEntry 列表，自动处理 cite key 冲突（追加 a/b/c）。

    Args:
        papers: Paper 列表。

    Returns:
        list[BibEntry]，与输入顺序一致。
    """
    entries: list[BibEntry] = []
    used: dict[str, int] = {}
    for paper in papers:
        base = _generate_key(paper)
        used[base] = used.get(base, 0) + 1
        if used[base] == 1:
            key = base
        else:
            suffix = chr(ord("a") + used[base] - 2)  # 第 2 次用 a, 第 3 次用 b
            key = f"{base}{suffix}"
        entries.append(
            BibEntry(key=key, paper_id=paper.paper_id, bibtex=_paper_to_bibtex(paper, key))
        )
    return entries


def render_bibfile(entries: Iterable[BibEntry]) -> str:
    """把 BibEntry 列表拼成 .bib 文件内容。"""
    return "\n\n".join(e.bibtex for e in entries) + "\n"


def resolve_citekeys(body: str, entries: Iterable[BibEntry]) -> tuple[str, list[str]]:
    """把 LaTeX body 中的 \\cite{paper:<paper_id>} 替换成 \\cite{<bibtex_key>}。

    Returns:
        (resolved_body, unresolved_paper_ids)。未匹配的 paper_id 会被原样保留，
        但同时收集进 ``unresolved_paper_ids`` 让调用方告警。
    """
    by_paper_id = {e.paper_id: e.key for e in entries}
    unresolved: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        paper_id = match.group(1)
        if paper_id in by_paper_id:
            return f"\\cite{{{by_paper_id[paper_id]}}}"
        unresolved.append(paper_id)
        return match.group(0)

    resolved = _CITE_PATTERN.sub(_sub, body)
    return resolved, unresolved


def check_citation_consistency(
    body: str, declared_paper_ids: Iterable[str]
) -> tuple[set[str], set[str]]:
    """检查正文 \\cite 占位与 plan/declared 列表是否一致。

    Returns:
        (in_body_only, in_declared_only)：分别是仅出现在正文 / 仅出现在 declared 列表中的 paper_id。
        理想情况两个集合都为空。
    """
    body_ids = set(_CITE_PATTERN.findall(body))
    declared = set(declared_paper_ids)
    return body_ids - declared, declared - body_ids
