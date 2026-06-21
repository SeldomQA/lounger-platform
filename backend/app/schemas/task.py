from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TaskCreate(BaseModel):
    name: str = Field(..., max_length=128, description="任务名称")
    description: str = Field(default="", description="任务描述")
    nodeids: List[str] = Field(default=[], description="选中的用例 nodeid 列表")


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodeids: Optional[List[str]] = None


class TaskResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    nodeids: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskRunResponse(BaseModel):
    id: int
    task_id: int
    project_id: int
    status: str
    exit_code: Optional[int] = None
    run_id: str = ""
    run_time: str = "0"
    total: int = 0
    passed: int = 0
    failure: int = 0
    error: int = 0
    skipped: int = 0
    report_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskRunCreate(BaseModel):
    pass
