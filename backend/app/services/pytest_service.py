import asyncio
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import REPORTS_DIR
from ..database import async_session
from ..models import TestReport, ReportDetail, TaskRun
from . import report_service

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_active_runs: dict = {}
_runs_lock = threading.Lock()


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def collect_cases(project_dir: str, case_dir: str = ".") -> list[dict]:
    scan_dir = str(Path(project_dir) / case_dir)
    tmpdir = Path(project_dir) / ".lounger_platform"
    tmpdir.mkdir(parents=True, exist_ok=True)

    wrapper = tmpdir / "_collect_wrapper.py"
    wrapper.write_text(f"""\
import os, sys
sys.path.insert(0, {json.dumps(project_dir)})
import pytest_req.log
from lounger.utils.collect import get_test_cases
import json
cases = get_test_cases({json.dumps(scan_dir)})
print(json.dumps(cases, ensure_ascii=False))
""", encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(wrapper)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = result.stdout.strip()
        if not stdout:
            return []
        lines = stdout.split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass
        return json.loads(stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"[pytest_service] Failed to collect cases: {e}", file=sys.stderr)
        return []


def start_run(project_dir: str, nodeids: list[str], project_id: int, task_run_id: int = 0) -> str:
    run_id = uuid.uuid4().hex[:8]
    log_queue: queue.Queue = queue.Queue()

    with _runs_lock:
        _active_runs[run_id] = {
            "queue": log_queue,
            "status": "running",
            "logs": [],
            "nodeids": nodeids,
            "exit_code": None,
            "project_id": project_id,
            "task_run_id": task_run_id,
        }

    t = threading.Thread(
        target=_execute_tests,
        args=(run_id, project_dir, nodeids, project_id),
        daemon=True,
    )
    t.start()
    return run_id


def get_run_status(run_id: str) -> Optional[dict]:
    with _runs_lock:
        info = _active_runs.get(run_id)
        if info is None:
            return None
        return {
            "status": info["status"],
            "nodeids": info["nodeids"],
            "log_count": len(info["logs"]),
            "exit_code": info.get("exit_code"),
        }


def get_run_queue(run_id: str) -> Optional[queue.Queue]:
    with _runs_lock:
        info = _active_runs.get(run_id)
        return info["queue"] if info else None


def get_run_info(run_id: str) -> Optional[dict]:
    with _runs_lock:
        return _active_runs.get(run_id)


def _execute_tests(run_id: str, project_dir: str, nodeids: list[str], project_id: int):
    print(f"[_execute_tests] run_id={run_id}, project_dir={project_dir}, nodeids={nodeids}", flush=True)
    cwd = str(Path(project_dir).resolve())
    tmpdir = Path(cwd) / ".lounger_platform"
    tmpdir.mkdir(parents=True, exist_ok=True)
    target_file = tmpdir / f"_run_{run_id}.json"

    target_payload = [{"nodeid": nid} for nid in nodeids]
    target_file.write_text(json.dumps(target_payload, indent=2), encoding="utf-8")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"report_{project_id}_{timestamp}.xml"
    report_path = str(REPORTS_DIR / report_name)

    wrapper = tmpdir / f"_run_wrapper_{run_id}.py"
    wrapper.write_text(f"""\
import os, sys
sys.path.insert(0, {json.dumps(cwd)})
import pytest_req.log
import pytest
sys.exit(pytest.console_main())
""", encoding="utf-8")

    cmd = [
        sys.executable, str(wrapper),
        "--run-json", str(target_file),
        "-v", "-s",
        "--tb=short",
        "--color=yes",
        f"--junit-xml={report_path}",
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd,
            env=env,
        )
    except FileNotFoundError:
        with _runs_lock:
            _active_runs[run_id]["status"] = "error"
            _active_runs[run_id]["error"] = "pytest not found"
        _update_task_run_status(run_id, "error")
        return

    with _runs_lock:
        _active_runs[run_id]["_process"] = proc
        _active_runs[run_id]["report_path"] = report_path

    log_queue = _active_runs[run_id]["queue"]

    for raw_line in iter(proc.stdout.readline, ""):
        clean = strip_ansi(raw_line)
        log_queue.put(clean)
        with _runs_lock:
            _active_runs[run_id]["logs"].append(clean)

    proc.wait()

    summary = f"\n── 执行完成 (exit code: {proc.returncode}) ──\n"
    log_queue.put(summary)
    with _runs_lock:
        _active_runs[run_id]["logs"].append(summary)
        _active_runs[run_id]["status"] = "completed"
        _active_runs[run_id]["exit_code"] = proc.returncode

    _save_report_for_run(project_id, report_path, run_id, proc.returncode)

    try:
        target_file.unlink()
    except OSError:
        pass


def _update_task_run_status(run_id: str, status: str):
    task_run_id = 0
    with _runs_lock:
        info = _active_runs.get(run_id)
        if info:
            task_run_id = info.get("task_run_id", 0)
    if not task_run_id:
        return

    async def _update():
        async with async_session() as db:
            task_run = await db.get(TaskRun, task_run_id)
            if task_run:
                task_run.status = status
                await db.commit()

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_update())
    finally:
        loop.close()


def _save_report_for_run(project_id: int, report_path: str, run_id: str = "", exit_code: int = 0):
    print(f"[_save_report_for_run] report_path={report_path}", flush=True)
    if not Path(report_path).exists():
        print(f"[_save_report_for_run] file not found: {report_path}", flush=True)
        _update_task_run_status(run_id, "error")
        return
    try:
        parsed = report_service.parse_junit_xml(report_path)
    except Exception as e:
        print(f"[_save_report_for_run] parse failed: {e}", flush=True)
        return

    task_run_id = 0
    if run_id:
        with _runs_lock:
            info = _active_runs.get(run_id)
            if info:
                task_run_id = info.get("task_run_id", 0)

    async def _save():
        async with async_session() as db:
            report = TestReport(
                project_id=project_id,
                name=f"Report_{project_id}",
                passed=parsed["passed"],
                error=parsed["errors"],
                failure=parsed["failures"],
                skipped=parsed["skipped"],
                tests=parsed["tests"],
                run_time=parsed["time"],
            )
            db.add(report)
            await db.flush()

            for detail in parsed["details"]:
                rd = ReportDetail(
                    report_id=report.id,
                    class_name=detail["class_name"],
                    name=detail["name"],
                    run_time=detail["run_time"],
                    result=detail["result"],
                    system_out=detail["system_out"],
                    system_err=detail["system_err"],
                    failure_out=detail["failure_out"],
                    error_out=detail["error_out"],
                    skipped_message=detail["skipped_message"],
                )
                db.add(rd)

            if task_run_id:
                task_run = await db.get(TaskRun, task_run_id)
                if task_run:
                    task_run.status = "completed" if exit_code == 0 else "error"
                    task_run.exit_code = exit_code
                    task_run.passed = parsed["passed"]
                    task_run.failure = parsed["failures"]
                    task_run.error = parsed["errors"]
                    task_run.skipped = parsed["skipped"]
                    task_run.total = parsed["tests"]
                    task_run.run_time = parsed["time"]
                    task_run.report_id = report.id

            await db.commit()

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_save())
    finally:
        loop.close()
