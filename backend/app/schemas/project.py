from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=128)
    git_url: str = Field(..., max_length=512)
    case_dir: str = Field(default=".")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    git_url: Optional[str] = None
    case_dir: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    git_url: str
    case_dir: str
    clone_dir: str
    status: int
    case_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
