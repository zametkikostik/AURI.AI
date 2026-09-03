"""Pydantic schemas for meetings and recordings."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    workspace_id: UUID | None = None
    language: str = "en"
    is_private: bool = False
    scheduled_at: datetime | None = None
    source: str = "upload"
    meeting_url: str | None = None


class MeetingUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    language: str | None = None
    is_private: bool | None = None
    status: str | None = None


class RecordingOut(BaseModel):
    id: UUID
    meeting_id: UUID
    storage_key: str
    content_type: str
    file_size_bytes: int | None
    duration_seconds: float | None
    status: str
    original_filename: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptOut(BaseModel):
    id: UUID
    meeting_id: UUID
    full_text: str
    language: str | None
    confidence: float | None
    provider: str
    status: str
    speakers: list | None
    processing_time_seconds: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingOut(BaseModel):
    id: UUID
    title: str
    description: str | None
    organization_id: UUID
    workspace_id: UUID | None
    owner_id: UUID
    status: str
    source: str
    language: str
    is_private: bool
    duration_seconds: int | None
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    executive_summary: str | None
    topics: list | None
    action_items: list | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MeetingDetailOut(MeetingOut):
    recordings: list[RecordingOut] = []
    transcript: TranscriptOut | None = None


class MeetingListOut(BaseModel):
    items: list[MeetingOut]
    total: int
    page: int
    page_size: int
