from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from ..database import get_db
from ..models import Project, TestCase
from ..schemas import TestCaseResponse, CaseTreeNode, RunRequest, RunResponse
from ..services import pytest_service

router = APIRouter(prefix="/api/projects/{project_id}/cases", tags=["用例管理"])


def _build_case_tree(cases: list[dict], project_dir: str) -> dict:
    base = Path(project_dir).resolve()
    root = {
        "name": base.name,
        "type": "dir",
        "relpath": "",
        "children": [],
        "total_cases": 0,
    }

    for c in cases:
        filepath = c.get("file", "")
        try:
            rel = Path(filepath).resolve().relative_to(base)
        except (ValueError, OSError):
            rel = Path(Path(filepath).name)

        parts = rel.parts
        if not parts:
            continue

        current = root
        for i, part in enumerate(parts[:-1]):
            found = None
            for child in current.get("children", []):
                if child["type"] == "dir" and child["name"] == part:
                    found = child
                    break
            if found is None:
                found = {
                    "name": part,
                    "type": "dir",
                    "relpath": str(Path(*parts[:i + 1])),
                    "children": [],
                    "total_cases": 0,
                }
                current.setdefault("children", []).append(found)
            current = found

        filename = parts[-1]
        file_node = None
        for child in current.get("children", []):
            if child["type"] == "file" and child["name"] == filename:
                file_node = child
                break
        if file_node is None:
            file_node = {
                "name": filename,
                "type": "file",
                "relpath": str(rel),
                "cases": [],
            }
            current.setdefault("children", []).append(file_node)
        file_node.setdefault("cases", []).append(c)

    def _compute_counts(node: dict) -> int:
        if node["type"] == "file":
            node["case_count"] = len(node["cases"])
            node["cases"].sort(key=lambda x: x.get("name", ""))
            return node["case_count"]
        total = 0
        for child in node.get("children", []):
            total += _compute_counts(child)
        node["total_cases"] = total
        return total

    def _sort_tree(node: dict) -> None:
        if "children" in node:
            node["children"].sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["name"].lower()))
            for child in node["children"]:
                _sort_tree(child)

    _compute_counts(root)
    _sort_tree(root)
    return root


@router.get("", response_model=list[TestCaseResponse])
async def get_cases(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestCase).where(TestCase.project_id == project_id)
    )
    cases = result.scalars().all()
    return [TestCaseResponse.model_validate(c) for c in cases]


@router.get("/tree")
async def get_case_tree(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestCase).where(TestCase.project_id == project_id)
    )
    cases = result.scalars().all()

    flat = []
    for c in cases:
        flat.append({
            "id": c.id,
            "file": c.file,
            "nodeid": c.nodeid,
            "name": c.name,
            "description": c.description or "",
            "markers": c.markers or [],
        })

    project = await db.get(Project, project_id)
    if not project or not project.clone_dir:
        return {"tree": {}, "flat": flat}

    tree = _build_case_tree(flat, project.clone_dir)
    return {"tree": tree, "flat": flat}


@router.post("/collect")
async def collect_cases(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.clone_dir:
        raise HTTPException(status_code=400, detail="Project not cloned yet")

    raw_cases = pytest_service.collect_cases(project.clone_dir, project.case_dir)

    await db.execute(delete(TestCase).where(TestCase.project_id == project_id))
    await db.flush()

    for case_data in raw_cases:
        tc = TestCase(
            project_id=project_id,
            file=case_data.get("file", ""),
            nodeid=case_data.get("nodeid", ""),
            name=case_data.get("name", ""),
            description=case_data.get("description") or "",
            markers=case_data.get("markers") or [],
        )
        db.add(tc)

    await db.commit()
    return {"message": "Cases collected", "count": len(raw_cases)}


@router.post("/run")
async def run_cases(project_id: int, payload: RunRequest, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.clone_dir:
        raise HTTPException(status_code=400, detail="Project not cloned")

    if not payload.nodeids:
        raise HTTPException(status_code=400, detail="No test cases selected")

    run_id = pytest_service.start_run(project.clone_dir, payload.nodeids, project_id)
    return {"run_id": run_id, "count": len(payload.nodeids)}
