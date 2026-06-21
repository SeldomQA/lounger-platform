from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TestCaseResponse(BaseModel):
    id: int
    project_id: int
    file: str
    nodeid: str
    name: str
    description: str = ""
    markers: list = []

    model_config = {"from_attributes": True}


class CaseTreeNode(BaseModel):
    name: str
    type: str
    relpath: str = ""
    children: list = []
    total_cases: int = 0
    case_count: int = 0
    cases: list = []


class RunRequest(BaseModel):
    nodeids: list[str] = []


class RunResponse(BaseModel):
    run_id: str
    count: int
