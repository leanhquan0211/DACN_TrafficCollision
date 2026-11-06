"""Chạy dashboard local đọc kết quả đồ án, không mở hoặc điều khiển train.

Cài requirements-dashboard.txt trong .venv-dashboard rồi chạy file này.
API chỉ cấp ID media đã đăng ký; nếu đã build frontend thì phục vụ cùng cổng.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from src.dashboard_data import DashboardStore


def create_app(root: Path = ROOT):
    """Factory cho test bằng fixture tạm, không cần dataset hoặc GPU."""
    store = DashboardStore(root)
    app = FastAPI(title="Traffic Observatory", docs_url="/api/docs", redoc_url=None)
    app.state.store = store

    def checked(fn, *args):
        try:
            return fn(*args)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        except (OSError, KeyError) as exc:
            raise HTTPException(422, "Artifact thiếu hoặc không đọc được; xem dữ liệu nguồn.") from exc

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": "read_only", "training_controls": False}

    @app.get("/api/runs")
    def runs():
        return store.runs()

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        return checked(store.run, run_id)

    @app.get("/api/runs/{run_id}/dataset")
    def dataset(run_id: str, split: str = Query("all", pattern="^(all|train|val|test|reserve)$")):
        return checked(store.dataset, run_id, split)

    @app.get("/api/kaggle")
    def kaggle(version: int = Query(12, ge=1, le=10000)):
        return store.cloud(version)

    @app.get("/api/runs/{run_id}/cases")
    def cases(run_id: str, kind: str = Query("all", pattern="^(all|tp|fp|fn)$"),
              search: str = Query("", max_length=100), offset: int = Query(0, ge=0), limit: int = Query(24, ge=1, le=100)):
        return checked(store.cases, run_id, kind, search, offset, limit)

    @app.get("/api/temporal")
    def temporal():
        return store.temporal()

    @app.get("/api/documents")
    def documents():
        return store.documents()

    @app.get("/api/project")
    def project():
        return store.project()

    @app.get("/api/explore")
    def explore():
        return checked(store.explore)

    @app.get("/api/artifacts")
    def artifacts():
        return checked(store.artifacts)

    @app.get("/api/media/{key}")
    def media(key: str):
        path = store.media_path(key)
        if path is None:
            raise HTTPException(404, "Media không có trong danh mục; tải lại trang nguồn.")
        # FileResponse hỗ trợ byte range để video có thể tua mà không tải cả file.
        return FileResponse(path, content_disposition_type="inline")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Không có API này")
        dist = (root / "frontend/dist").resolve()
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise HTTPException(404)
        if target.is_file():
            return FileResponse(target)
        if (dist / "index.html").is_file():
            return FileResponse(dist / "index.html")
        raise HTTPException(404, "Chưa build frontend. Chạy npm run build trong frontend hoặc dùng Vite dev.")

    return app


def main():
    parser = argparse.ArgumentParser(description="Local read-only dashboard; no training or downloads")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
