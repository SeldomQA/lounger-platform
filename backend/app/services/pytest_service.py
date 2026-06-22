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
_project_running: set[int] = set()
_project_lock = threading.Lock()

_SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    _SUBPROCESS_FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP


def _tmp_dir(project_dir: str) -> Path:
    project_path = Path(project_dir).resolve()
    tmp = Path(tempfile.gettempdir()) / "lounger_platform" / project_path.name
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


class ProjectAlreadyRunning(Exception):
    pass


def is_project_running(project_id: int) -> bool:
    with _project_lock:
        return project_id in _project_running


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _get_yaml_case_metadata(scan_dir: str) -> dict:
    """Scan datas/ directory for YAML test case metadata, similar to lounger web_runner."""
    scan_path = Path(scan_dir)
    datas_dir = scan_path / "datas"
    if not datas_dir.is_dir():
        return {}

    import yaml
    metadata = {}
    for yaml_file in sorted(datas_dir.rglob("*.yaml")):
        if not (yaml_file.stem.startswith("test_") or yaml_file.stem.endswith("_test")):
            continue
        filename = yaml_file.stem
        rel_path = str(yaml_file.resolve())
        try:
            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for idx, block in enumerate(data):
            if not isinstance(block, dict) or "teststeps" not in block:
                continue
            steps = block["teststeps"]
            if not steps:
                continue
            first_step = steps[0]
            display_name = first_step.get("step") or first_step.get("name") or f"测试用例 {idx + 1}"
            step_name = first_step.get("name") or "step_1"
            case_id = f"{filename}::case_{idx + 1}_{step_name}"
            metadata[case_id] = {
                "file": rel_path,
                "name": display_name,
                "description": display_name,
            }
    return metadata


def _enrich_yaml_cases(cases: list[dict], scan_dir: str) -> list[dict]:
    """Enrich pytest-collected cases with YAML datas/ metadata, mirroring lounger web_runner."""
    metadata = _get_yaml_case_metadata(scan_dir)
    if not metadata:
        return cases

    yaml_pattern = re.compile(r'^test_api\.py::test_api\[(.+?::case_\d+_.+?)\]$')
    for case in cases:
        nodeid = case.get("nodeid", "")
        m = yaml_pattern.match(nodeid)
        if m:
            param_key = m.group(1)
            if param_key in metadata:
                meta = metadata[param_key]
                case["file"] = meta["file"]
                case["name"] = meta["name"]
                case["description"] = meta["description"]
    return cases


def collect_cases(project_dir: str) -> list[dict]:
    scan_dir = str(Path(project_dir).resolve())
    tmpdir = _tmp_dir(project_dir)

    wrapper = tmpdir / "_collect_wrapper.py"
    wrapper.write_text(f"""\
import sys
sys.path.insert(0, {json.dumps(scan_dir)})
from lounger.utils.collect import get_test_cases
import json
cases = get_test_cases({json.dumps(scan_dir)})
print(json.dumps(cases, ensure_ascii=False))
""", encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(wrapper)],
            cwd=scan_dir,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("用例收集超时（30秒），请检查项目是否包含大量测试用例")

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        error_msg = stderr or stdout or f"进程退出码: {result.returncode}"
        raise RuntimeError(f"用例收集失败: {error_msg[:500]}")

    if not stdout:
        return []

    lines = stdout.split("\n")
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            try:
                raw_cases = json.loads(line)
                return _enrich_yaml_cases(raw_cases, scan_dir)
            except json.JSONDecodeError:
                pass

    raise RuntimeError(
        f"无法解析收集结果，请检查项目配置\nstdout: {stdout[:300]}"
    )


def start_run(project_dir: str, nodeids: list[str], project_id: int, task_run_id: int = 0) -> str:
    with _project_lock:
        if project_id in _project_running:
            raise ProjectAlreadyRunning(
                f"项目 {project_id} 已有用例正在执行中，请等待完成后再试"
            )
        _project_running.add(project_id)

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


def stop_run(run_id: str) -> bool:
    with _runs_lock:
        info = _active_runs.get(run_id)
        if info is None:
            return False
        proc = info.get("_process")
        project_id = info.get("project_id", 0)
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    with _project_lock:
        _project_running.discard(project_id)
    return True


def _execute_tests(run_id: str, project_dir: str, nodeids: list[str], project_id: int):
    try:
        cwd = str(Path(project_dir).resolve())
        print(f"[pytest_service] _execute_tests: run_id={run_id}, project_dir={project_dir}", file=sys.stderr)

        tmpdir = _tmp_dir(project_dir)
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
                creationflags=_SUBPROCESS_FLAGS,
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

        print(f"[pytest_service] Starting subprocess for run_id={run_id}", file=sys.stderr)

        def _reader_thread(proc, log_queue_p, logs_list, runs_lock_p, run_id_p):
            try:
                for raw_line in iter(proc.stdout.readline, ""):
                    clean = strip_ansi(raw_line)
                    log_queue_p.put(clean)
                    with runs_lock_p:
                        logs_list.append(clean)
            except ValueError:
                pass

        reader = threading.Thread(
            target=_reader_thread,
            args=(proc, log_queue, _active_runs[run_id]["logs"], _runs_lock, run_id),
            daemon=True,
        )
        reader.start()

        proc.wait()
        reader.join(timeout=5)

        print(f"[pytest_service] Process exited with code {proc.returncode} for run_id={run_id}", file=sys.stderr)

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
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[pytest_service] FATAL: _execute_tests crashed: {e}", file=sys.stderr)
        with _runs_lock:
            info = _active_runs.get(run_id)
            if info:
                info["status"] = "error"
                info["error"] = str(e)
        _update_task_run_status(run_id, "error")
    finally:
        with _project_lock:
            _project_running.discard(project_id)


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
    print(f"[pytest_service] _save_report_for_run: project_id={project_id}, report_path={report_path}, run_id={run_id}, exit_code={exit_code}", file=sys.stderr)

    if not Path(report_path).exists():
        print(f"[pytest_service] Report file not found: {report_path}", file=sys.stderr)
        _update_task_run_status(run_id, "error")
        return
    try:
        parsed = report_service.parse_junit_xml(report_path)
        print(f"[pytest_service] Parsed report: tests={parsed['tests']}, passed={parsed['passed']}", file=sys.stderr)
    except Exception as e:
        print(f"[pytest_service] Failed to parse report: {e}", file=sys.stderr)
        return

    task_run_id = 0
    if run_id:
        with _runs_lock:
            info = _active_runs.get(run_id)
            if info:
                task_run_id = info.get("task_run_id", 0)

    async def _save():
        try:
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
                        run_log=detail.get("run_log", ""),
                        run_date=detail.get("run_date", ""),
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
                print(f"[pytest_service] Report saved: id={report.id}, task_run_id={task_run_id}", file=sys.stderr)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[pytest_service] Failed to save report to database: {e}", file=sys.stderr)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_save())
    finally:
        loop.close()
