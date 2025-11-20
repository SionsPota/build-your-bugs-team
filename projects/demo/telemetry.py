import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

"""轻量级 JSON 遥测记录器，输出到 stdout 和 log/telemetry.log。"""

LOG_DIR = Path(__file__).parent / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "telemetry.log"

# 独立的 telemetry logger，打印一行一个 JSON，方便收集与 grep。
logger = logging.getLogger("telemetry")
if not logger.handlers:
    formatter = logging.Formatter("%(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

logger.setLevel(logging.INFO)
logger.propagate = False


def new_request_id() -> str:
    """生成 request id 用于链路关联。"""
    return uuid.uuid4().hex


def log_event(event: str, **kwargs: Optional[Any]) -> None:
    """输出结构化遥测事件。None 字段自动忽略。"""
    payload: Dict[str, Any] = {"ts": time.time(), "event": event}
    for key, value in kwargs.items():
        if value is None:
            continue
        payload[key] = value
    logger.info(json.dumps(payload, ensure_ascii=False))
