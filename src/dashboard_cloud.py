"""Đọc trạng thái/log Kaggle cho dashboard bằng môi trường CLI riêng.

Không gửi notebook, tải dataset, lưu token hoặc điều khiển run. Chỉ in DTO đã
lọc; lỗi API trả mã chung thay vì đưa credential/header/raw exception ra web.
"""
from __future__ import annotations
import argparse
import contextlib
import io
import json
import re
import time


def _failure(error: Exception) -> dict:
    """Phân loại lỗi API bằng kiểu/mã HTTP, không đưa URL hay token lên web."""
    current = error
    seen = set()
    names = set()
    status_codes = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        names.add(type(current).__name__)
        code = getattr(getattr(current, "response", None), "status_code", None)
        if code is not None:
            status_codes.add(code)
        current = current.__cause__ or current.__context__
    if 401 in status_codes or 403 in status_codes:
        return {"reason": "private_access_denied", "message": "Kaggle từ chối quyền đọc notebook PRIVATE (401/403). Đăng nhập lại CLI bằng đúng tài khoản laqun0211; không gửi token vào web."}
    if "ProxyError" in names:
        return {"reason": "proxy_unreachable", "message": "Server dashboard không kết nối được proxy tới Kaggle. Hãy chạy lại server bằng terminal PowerShell của bạn; Kaggle vẫn tiếp tục chạy."}
    if "Timeout" in names or "ReadTimeout" in names or "ConnectTimeout" in names:
        return {"reason": "remote_timeout", "message": "Kaggle API quá thời gian chờ. Thử đọc lại sau; run không bị hủy."}
    if "ConnectionError" in names or "SSLError" in names:
        return {"reason": "network_unavailable", "message": "Server dashboard không kết nối được Kaggle API. Kiểm mạng/proxy local; run không bị hủy."}
    if "RuntimeError" in names and "AUTHENTICATION_REQUIRED" in str(error):
        return {"reason": "authentication_required", "message": "Cần đăng nhập Kaggle CLI bằng tài khoản laqun0211 trên máy local; không nhập token vào web."}
    return {"reason": "remote_access_failed", "message": "Không đọc được Kaggle API. Kiểm đăng nhập, quyền Notebook PRIVATE và kết nối; run không bị hủy."}


def read_snapshot(version: int):
    from scripts.kaggle_b0 import api_client, KERNEL_ID, credentials_present
    if not credentials_present():
        return {"connected": False, "reason": "authentication_required", "message": "Cần đăng nhập Kaggle trên máy local; không nhập token vào web."}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            api = api_client()
            target = KERNEL_ID + "/" + str(version)
            status = str(api.kernels_status(target))
    except Exception as error:
        return {"connected": False, **_failure(error)}
    try:
        status = str(json.loads(status).get("status", "UNKNOWN"))
    except (ValueError, AttributeError):
        status = "UNKNOWN"
    if status not in {"COMPLETE", "RUNNING", "QUEUED", "ERROR", "CANCELLED", "UNKNOWN"}:
        status = "UNKNOWN"
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            raw = api.kernels_logs(target)
        try:
            events = json.loads(raw)
            body = "".join(str(event.get("data", "")) for event in events) if isinstance(events, list) else str(raw)
        except (ValueError, TypeError):
            body = str(raw)
        from src.kaggle_recipe import EpochLogFilter
        # Chỉ phát hành dòng epoch; raw log/lỗi có thể chứa thông tin máy cá nhân.
        logs = [line for line in EpochLogFilter().feed(body, final=True) if re.match(r"^Epoch \d+", line)]
        history = []
        for line in logs:
            epoch = re.match(r"Epoch (\d+)", line)
            item = {"epoch": int(epoch[1])}
            for name, key in (("P", "precision"), ("R", "recall"), ("mAP50", "map50"), ("mAP50-95", "map95")):
                match = re.search(r"(?:^|\s)" + re.escape(name) + r"=([\d.]+)(%?)", line)
                if match:
                    item[key] = float(match[1]) / (100 if match[2] else 1)
            if all(key in item for key in ("precision", "recall", "map50", "map95")):
                history.append(item)
        return {"connected": True, "kernel": KERNEL_ID, "version": version,
                "status": status, "logs": logs[-500:], "history": history,
                "read_at": time.time(), "scope": "read_only_remote_snapshot_not_training_control"}
    except Exception as error:
        # Status đã đọc được vẫn hữu ích khi endpoint log bị chặn/trễ.
        failure = _failure(error)
        return {"connected": True, "kernel": KERNEL_ID, "version": version,
                "status": status, "logs": [], "history": [], "read_at": time.time(),
                "logs_available": False, "message": "Đã đọc trạng thái; chưa đọc được log. " + failure["message"],
                "scope": "read_only_remote_snapshot_not_training_control"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read Kaggle snapshot only")
    parser.add_argument("--version", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(read_snapshot(args.version), ensure_ascii=True))
