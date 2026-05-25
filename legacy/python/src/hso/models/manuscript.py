"""manuscript 起草过程中的数据模型：Outline / SectionPlan / DraftedSection / BibEntry。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SectionPlan(BaseModel):
    """单个章节的写作计划。Outline 的元素。"""

    model_config = ConfigDict(extra="ignore")

    section_id: str = Field(
        description="章节标识，例如 'introduction' / 'related_work' / 'method' / 'experiment' / 'conclusion'"
    )
    title: str = Field(description="人类可读章节名")
    subtopics: list[str] = Field(
        default_factory=list, description="作者打算在此章节展开的子话题，按拟定顺序"
    )
    planned_artifacts: list[str] = Field(
        default_factory=list,
        description=(
            "本章节要引用的图表 artifact_id，如 'table:main_results' / 'fig:train_loss'；"
            "drafter 会把它们渲染成 \\ref / \\includegraphics"
        ),
    )
    cited_paper_ids: list[str] = Field(
        default_factory=list,
        description="本章节将要引用的 Paper.paper_id 列表，引用按 \\cite{paper:<id>} 占位",
    )
    notes: str | None = Field(default=None, description="自由写作要点")


class Outline(BaseModel):
    """完整 manuscript 的大纲。OutlineBuilder 的产物。"""

    model_config = ConfigDict(extra="ignore")

    title: str
    abstract_focus: str = Field(description="摘要重点（1-2 句）；用于后续起草摘要")
    keywords: list[str] = Field(default_factory=list)
    sections: list[SectionPlan]


class DraftedSection(BaseModel):
    """SectionDrafter 单章节产物。"""

    model_config = ConfigDict(extra="ignore")

    section_id: str
    title: str
    body: str = Field(description="LaTeX 章节正文，引用占位为 \\cite{paper:<paper_id>}")
    used_paper_ids: list[str] = Field(
        default_factory=list, description="实际被正文引用的 paper_id 子集"
    )
    used_artifact_ids: list[str] = Field(
        default_factory=list, description="实际被正文引用的 artifact_id 子集"
    )


class BibEntry(BaseModel):
    """单条 bibtex 条目 + 与 Paper.paper_id 的映射。"""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(description="bibtex citation key，例如 'smith2024diffusion'")
    paper_id: str
    bibtex: str = Field(description="完整 @article{...} 字符串")
