from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Project
from ..schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from ..services.git_service import clone_project, pull_project

router = APIRouter(prefix="/api/projects", tags=["项目管理"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.id.desc()))
    projects = result.scalars().all()
    resp = []
    for p in projects:
        resp.append(ProjectResponse(
            id=p.id,
            name=p.name,
            git_url=p.git_url,
            case_dir=p.case_dir,
            clone_dir=p.clone_dir,
            status=p.status,
            case_count=0,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))
    return resp


@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(
        name=data.name,
        git_url=data.git_url,
        case_dir=data.case_dir or ".",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    try:
        clone_dir = clone_project(project.id, project.git_url)
        project.clone_dir = clone_dir
        project.status = 1
        await db.commit()
        await db.refresh(project)
    except Exception as e:
        project.status = 0
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Git clone failed: {str(e)}")

    return ProjectResponse(
        id=project.id,
        name=project.name,
        git_url=project.git_url,
        case_dir=project.case_dir,
        clone_dir=project.clone_dir,
        status=project.status,
        case_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.name is not None:
        project.name = data.name
    if data.git_url is not None:
        project.git_url = data.git_url
    if data.case_dir is not None:
        project.case_dir = data.case_dir

    await db.commit()
    await db.refresh(project)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        git_url=project.git_url,
        case_dir=project.case_dir,
        clone_dir=project.clone_dir,
        status=project.status,
        case_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/refresh")
async def refresh_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.clone_dir:
        raise HTTPException(status_code=400, detail="Project not cloned yet")
    try:
        pull_project(project.clone_dir)
        return {"message": "Project refreshed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Git pull failed: {str(e)}")
