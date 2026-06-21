import asyncio
import json
import queue

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .database import init_db
from .routers import project_router, case_router, report_router, task_router
from .services import pytest_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="lounger-platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)
app.include_router(case_router)
app.include_router(report_router)
app.include_router(task_router)


@app.get("/api/stream/{run_id}")
async def stream_logs(run_id: str, request: Request):
    run_info = pytest_service.get_run_info(run_id)
    if run_info is None:
        return StreamingResponse(
            _empty_stream("Run not found"),
            media_type="text/event-stream",
        )

    async def event_generator():
        log_queue = run_info["queue"]
        sent_count = 0

        with pytest_service._runs_lock:
            existing = list(run_info["logs"])

        for line in existing[sent_count:]:
            yield _sse_msg({"line": line})
            sent_count += 1

        while True:
            if await request.is_disconnected():
                break
            try:
                line = log_queue.get_nowait()
                yield _sse_msg({"line": line})
                sent_count += 1
            except queue.Empty:
                with pytest_service._runs_lock:
                    status = run_info["status"]
                if status in ("completed", "error"):
                    exit_code = run_info.get("exit_code", -1)
                    yield _sse_msg({
                        "line": "",
                        "done": True,
                        "exit_code": exit_code,
                        "status": status,
                    })
                    break
                await asyncio.sleep(0.5)
                yield _sse_msg({"heartbeat": True})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def _sse_msg(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def _empty_stream(message: str):
    yield _sse_msg({"error": message, "done": True})
