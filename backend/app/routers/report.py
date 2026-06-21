from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Project, TestReport, ReportDetail
from ..schemas import ReportResponse, ReportDetailResponse

router = APIRouter(prefix="/api/projects/{project_id}/reports", tags=["测试报告"])


@router.get("", response_model=list[ReportResponse])
async def list_reports(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestReport)
        .where(TestReport.project_id == project_id)
        .options(selectinload(TestReport.details))
        .order_by(TestReport.id.desc())
    )
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(project_id: int, report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TestReport)
        .where(TestReport.id == report_id, TestReport.project_id == project_id)
        .options(selectinload(TestReport.details))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)
