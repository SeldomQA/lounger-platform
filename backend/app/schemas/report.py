from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ReportDetailResponse(BaseModel):
    id: int
    class_name: str
    name: str
    run_time: str
    result: str
    system_out: str
    system_err: str
    failure_out: str
    error_out: str
    skipped_message: str

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    project_id: int
    name: str
    passed: int
    error: int
    failure: int
    skipped: int
    tests: int
    run_time: str
    created_at: datetime
    details: List[ReportDetailResponse] = []

    model_config = {"from_attributes": True}
