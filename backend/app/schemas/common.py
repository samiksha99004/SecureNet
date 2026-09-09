"""
SecureNet Backend — Common Schemas

Shared request/response models used across multiple endpoints.
"""

from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response matching frontend contract"""
    data: List[T]
    total: int
    page: int
    pageSize: int = Field(..., alias="page_size")
    totalPages: int = Field(..., alias="total_pages")
    
    class Config:
        populate_by_name = True


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Simple message response"""
    message: str


# ── API Error ─────────────────────────────────────────────────────────────────

class ApiError(BaseModel):
    """Structured error response"""
    status: int
    code: str
    message: str
    details: Optional[dict] = None


# ── Query Parameters ──────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    """Pagination query parameters"""
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100, alias="page_size")


class SortParams(BaseModel):
    """Sorting parameters"""
    sortBy: str = Field(default="timestamp", alias="sort_by")
    sortOrder: str = Field(default="desc", pattern="^(asc|desc)$", alias="sort_order")


class DateRangeParams(BaseModel):
    """Date range filter"""
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")
