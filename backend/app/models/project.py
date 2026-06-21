import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, comment="项目名称")
    git_url = Column(String(512), default="", comment="Git 仓库地址")
    clone_dir = Column(String(512), default="", comment="本地克隆/项目目录")
    status = Column(Integer, default=0, comment="状态: 0=待克隆, 1=就绪, 2=执行中")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    test_cases = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("TestReport", back_populates="project", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    file = Column(String(512), nullable=False, comment="文件路径(相对路径)")
    nodeid = Column(String(512), nullable=False, comment="pytest nodeid")
    name = Column(String(256), nullable=False, comment="用例名称")
    description = Column(Text, default="", comment="用例描述")
    markers = Column(JSON, default=list, comment="标签列表")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="test_cases")


class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(256), nullable=False, comment="报告名称")
    passed = Column(Integer, default=0, comment="通过数")
    error = Column(Integer, default=0, comment="错误数")
    failure = Column(Integer, default=0, comment="失败数")
    skipped = Column(Integer, default=0, comment="跳过数")
    tests = Column(Integer, default=0, comment="总数")
    run_time = Column(String(64), default="0", comment="运行时长")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="reports")
    details = relationship("ReportDetail", back_populates="report", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(128), nullable=False, comment="任务名称")
    description = Column(Text, default="", comment="任务描述")
    nodeids = Column(JSON, default=list, comment="选中的用例 nodeid 列表")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    project = relationship("Project")
    runs = relationship("TaskRun", back_populates="task", cascade="all, delete-orphan")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    status = Column(String(32), default="pending", comment="运行状态: pending/running/completed/error")
    exit_code = Column(Integer, nullable=True, comment="退出码")
    run_id = Column(String(64), default="", comment="pytest_service 的 run_id")
    run_time = Column(String(64), default="0", comment="运行时长")
    total = Column(Integer, default=0, comment="总用例数")
    passed = Column(Integer, default=0, comment="通过数")
    failure = Column(Integer, default=0, comment="失败数")
    error = Column(Integer, default=0, comment="错误数")
    skipped = Column(Integer, default=0, comment="跳过数")
    report_id = Column(Integer, ForeignKey("test_reports.id"), nullable=True, comment="关联报告")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="runs")
    project = relationship("Project")
    report = relationship("TestReport")


class ReportDetail(Base):
    __tablename__ = "report_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("test_reports.id"), nullable=False)
    class_name = Column(String(512), default="", comment="用例类名")
    name = Column(String(256), default="", comment="用例名称")
    run_time = Column(String(64), default="0", comment="运行时长(秒)")
    result = Column(String(32), default="", comment="结果: passed/failed/error/skipped")
    system_out = Column(Text, default="", comment="标准输出")
    system_err = Column(Text, default="", comment="错误输出")
    failure_out = Column(Text, default="", comment="失败信息")
    error_out = Column(Text, default="", comment="错误信息")
    skipped_message = Column(Text, default="", comment="跳过原因")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("TestReport", back_populates="details")
