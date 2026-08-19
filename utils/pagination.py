"""Pagination helpers."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, List, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1
