"""PaperProvider 抽象：所有检索源实现此接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from hso.models import Paper, SearchQuery


class PaperProvider(ABC):
    """检索源抽象。子类只负责把单源结果映射为标准 Paper，不做筛选/去重。"""

    name: str

    @abstractmethod
    def search(self, query: SearchQuery) -> list[Paper]:
        """同步检索接口，返回 Paper 列表。

        Args:
            query: 标准检索请求。
        """
        raise NotImplementedError
