"""Pydantic DTOs for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
import re


class StartRequest(BaseModel):
    """Request for POST /api/interview/start."""

    anonymous_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("anonymous_id")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MessageRequest(BaseModel):
    """Request for POST /api/interview/message."""

    session_id: str
    message: str = Field(..., min_length=1, max_length=10000)

    @field_validator("session_id")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator("message")
    @classmethod
    def strip_message_whitespace(cls, v: str) -> str:
        return v.strip()


class EndRequest(BaseModel):
    """Request for POST /api/interview/end."""

    session_id: str

    @field_validator("session_id")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError("Invalid session_id format")
        return v


class EndResponse(BaseModel):
    """Response for POST /api/interview/end."""

    summary: str
    message_count: int


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    detail: str | None = None
