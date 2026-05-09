"""Elsevier ``elsarticle.cls`` LaTeX 模板填充器。"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from pydantic import BaseModel, ConfigDict, Field


class Affiliation(BaseModel):
    """作者单位。"""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="LaTeX label，例如 'a' / 'b'，会被作者引用")
    organization: str
    country: str = ""


class TemplateAuthor(BaseModel):
    """模板视角的作者（与 Paper.authors 区分）。"""

    model_config = ConfigDict(extra="ignore")

    name: str
    affiliation_id: str = Field(description="对应 Affiliation.id")
    email: str | None = None


class ManuscriptSection(BaseModel):
    """渲染到 LaTeX 的单一章节内容。"""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="LaTeX label，例如 'intro' / 'method'")
    title: str = Field(description="人类可读章节名")
    body: str = Field(description="章节正文 LaTeX 代码")


class ManuscriptDocument(BaseModel):
    """完整的 manuscript 渲染入参。"""

    model_config = ConfigDict(extra="ignore")

    title: str
    authors: list[TemplateAuthor]
    affiliations: list[Affiliation]
    abstract: str
    keywords: list[str] = Field(default_factory=list)
    sections: list[ManuscriptSection]
    journal: str = "Journal Name"
    bib_basename: str = Field(default="refs", description=".bib 文件名（不含扩展名）")
    has_bibliography: bool = True


def _builtin_template_dir() -> Path:
    """定位包内置模板目录。"""
    return Path(__file__).parent / "templates"


class ElsevierTemplate:
    """elsarticle.cls 模板渲染器。"""

    def __init__(self, template_dir: Path | None = None) -> None:
        """初始化。

        Args:
            template_dir: jinja2 模板目录。默认走包内置 ``templates/``。
        """
        self._template_dir = template_dir or _builtin_template_dir()
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(disabled_extensions=("j2", "tex")),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(self, doc: ManuscriptDocument, template_name: str = "elsevier.tex.j2") -> str:
        """渲染并返回 LaTeX 源代码字符串。

        Args:
            doc: 文档数据。
            template_name: 模板文件名；默认 elsevier.tex.j2。
        """
        template = self._env.get_template(template_name)
        return template.render(**doc.model_dump())

    def render_to_file(
        self,
        doc: ManuscriptDocument,
        output_path: Path,
        template_name: str = "elsevier.tex.j2",
    ) -> Path:
        """渲染并写入文件，返回写入路径。"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(doc, template_name), encoding="utf-8")
        return output_path


# 导出未在 __init__ 直接 re-export 的子类型
__all__ = [
    "Affiliation",
    "ElsevierTemplate",
    "ManuscriptDocument",
    "ManuscriptSection",
    "TemplateAuthor",
]
