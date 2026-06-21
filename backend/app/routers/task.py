from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Project, Task, TaskRun, TestReport
from ..schemas import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse
from ..services import pytest_service

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["任务管理"])


@router.get("")
async def list_tasks(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    count_q = select(func.count()).select_from(Task).where(Task.project_id == project_id)
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [TaskResponse.model_validate(t) for t in result.scalars().all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=TaskResponse)
async def create_task(project_id: int, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = Task(
        project_id=project_id,
        name=data.name,
        description=data.description,
        nodeids=data.nodeids or [],
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(project_id: int, task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(project_id: int, task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if data.name is not None:
        task.name = data.name
    if data.description is not None:
        task.description = data.description
    if data.nodeids is not None:
        task.nodeids = data.nodeids

    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(project_id: int, task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}


@router.post("/{task_id}/run")
async def run_task(project_id: int, task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    project = await db.get(Project, project_id)
    if not project or not project.clone_dir:
        raise HTTPException(status_code=400, detail="Project directory not found")

    nodeids = task.nodeids or []
    if not nodeids:
        raise HTTPException(status_code=400, detail="No test cases in this task")

    # Create task run record
    task_run = TaskRun(
        task_id=task_id,
        project_id=project_id,
        status="running",
        total=len(nodeids),
    )
    db.add(task_run)
    await db.commit()
    await db.refresh(task_run)

    # Start the test run
    try:
        run_id = pytest_service.start_run(
            project.clone_dir,
            nodeids,
            project_id,
            task_run_id=task_run.id,
        )
    except pytest_service.ProjectAlreadyRunning as e:
        task_run.status = "error"
        task_run.exit_code = -1
        await db.commit()
        raise HTTPException(status_code=409, detail=str(e))

    task_run.run_id = run_id
    await db.commit()
    await db.refresh(task_run)

    return {
        "run_id": run_id,
        "task_run_id": task_run.id,
        "count": len(nodeids),
    }


@router.get("/{task_id}/runs", response_model=list[TaskRunResponse])
async def list_task_runs(project_id: int, task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskRun)
        .where(TaskRun.task_id == task_id, TaskRun.project_id == project_id)
        .order_by(TaskRun.id.desc())
    )
    return [TaskRunResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/runs/all")
async def list_all_task_runs(
    project_id: int,
    task_name: str = Query(default="", description="按任务名称筛选"),
    date_from: str = Query(default="", description="起始日期 YYYY-MM-DD"),
    date_to: str = Query(default="", description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskRun).where(TaskRun.project_id == project_id)

    if task_name:
        query = query.join(Task, TaskRun.task_id == Task.id).where(Task.name.ilike(f"%{task_name}%"))
    if date_from:
        query = query.where(TaskRun.created_at >= date_from)
    if date_to:
        query = query.where(TaskRun.created_at <= f"{date_to} 23:59:59")

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(TaskRun.id.desc()).offset(offset).limit(page_size)
    )
    items = [TaskRunResponse.model_validate(r) for r in result.scalars().all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}
