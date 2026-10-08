import re
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def validate_workspace_name(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("Workspace name cannot be empty.")

    if not slugify(value):
        raise ValueError("Workspace name must contain at least one letter or number.")

    return value


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_workspace_name(value)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_workspace_name(value)
