#!/usr/bin/env python3
"""
简单的模型评分/润色评测脚本。

用法：
    python test_model/eval_models.py path/to/config.yaml
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from model import CommentParser, Evaluator, Polisher


def load_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_sample_path(path: str) -> Tuple[str, int, int]:
    """
    将文件名解析为 question_id、expected_score、variant。
    约定文件名形如：44_5_2.txt
    """
    stem = Path(path).stem
    m = re.match(r"(\\d+)_(\\d+)_(\\d+)", stem)
    if not m:
        raise ValueError(f"Unexpected filename format: {path}")
    qid, expected, variant = m.groups()
    return qid, int(expected), int(variant)


def load_samples(pattern: str) -> List[Dict]:
    samples = []
    for p in sorted(glob.glob(pattern)):
        qid, expected, variant = parse_sample_path(p)
        text = Path(p).read_text(encoding="utf-8").strip()
        samples.append(
            {
                "path": p,
                "question_id": qid,
                "expected": expected,
                "variant": variant,
                "text": text,
            }
        )
    if not samples:
        raise RuntimeError(f"No samples matched pattern: {pattern}")
    return samples


def rankdata(seq: List[float]) -> List[float]:
    """
    简单实现：对序列做升序排名，处理并列时取平均名次。
    """
    sorted_idx = sorted(range(len(seq)), key=lambda i: seq[i])
    ranks = [0.0] * len(seq)
    i = 0
    while i < len(seq):
        j = i
        # 找到并列段
        while j + 1 < len(seq) and seq[sorted_idx[j + 1]] == seq[sorted_idx[i]]:
            j += 1
        avg_rank = (i + j + 2) / 2.0  # 名次从1开始
        for k in range(i, j + 1):
            ranks[sorted_idx[k]] = avg_rank
        i = j + 1
    return ranks


def spearman_corr(x: List[float], y: List[float]) -> Optional[float]:
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = rankdata(x), rankdata(y)
    mean_x, mean_y = statistics.mean(rx), statistics.mean(ry)
    cov = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    denom_x = math.sqrt(sum((a - mean_x) ** 2 for a in rx))
    denom_y = math.sqrt(sum((b - mean_y) ** 2 for b in ry))
    if denom_x == 0 or denom_y == 0:
        return None
    return cov / (denom_x * denom_y)


def order_non_violation(y_true: List[int], y_pred: List[int]) -> bool:
    # 检查任意两条样本，预测排序是否与真实排序方向一致（允许并列）
    n = len(y_true)
    for i in range(n):
        for j in range(i + 1, n):
            if (y_true[i] - y_true[j]) * (y_pred[i] - y_pred[j]) < 0:
                return False
    return True


def update_confusion(cm: Dict, y_true: int, y_pred: int):
    cm.setdefault(y_true, {}).setdefault(y_pred, 0)
    cm[y_true][y_pred] += 1


def main():
    argp = argparse.ArgumentParser(description="Evaluate grading/polishing models on local samples (direct LLM calls).")
    argp.add_argument("config", help="YAML config path (LLM base_url/api_key/model)")
    args = argp.parse_args()

    cfg = load_config(args.config)

    # 将配置写入环境变量，Evaluator/Polisher 会读取
    if cfg.get("api_key"):
        os.environ["DASHSCOPE_API_KEY"] = cfg["api_key"]
    if cfg.get("base_url"):
        os.environ["DASHSCOPE_BASE_URL"] = cfg["base_url"]
    if cfg.get("model_name"):
        os.environ["DASHSCOPE_MODEL"] = cfg["model_name"]

    samples = load_samples(cfg.get("dataset_glob", "test_answer/*.txt"))

    parser = CommentParser()
    evaluator_cache: Dict[str, Evaluator] = {}

    records = []
    confusion = {}
    deltas = []

    for sample in samples:
        # 复用同一题目的 Evaluator，避免重复加载题库
        if sample["question_id"] not in evaluator_cache:
            evaluator_cache[sample["question_id"]] = Evaluator(question=sample["question_id"])
        ev = evaluator_cache[sample["question_id"]]

        comment = ev.generate_response(sample["text"])
        parsed_comment = parser.parse_complete(comment)
        pred = parsed_comment.get("score")
        update_confusion(confusion, sample["expected"], pred)

        record = {
            "path": sample["path"],
            "expected": sample["expected"],
            "pred": pred,
            "polished_pred": None,
            "delta": None,
        }

        if cfg.get("evaluate_polished", True):
            polisher = Polisher(sample["text"], comment)
            polished = polisher.generate_response()
            polished_comment = ev.generate_response(polished)
            polished_parsed = parser.parse_complete(polished_comment)
            polished_score = polished_parsed.get("score")
            record["polished_pred"] = polished_score
            if pred is not None and polished_score is not None:
                record["delta"] = polished_score - pred
                deltas.append(record["delta"])

        records.append(record)

    y_true = [r["expected"] for r in records if r["pred"] is not None]
    y_pred = [r["pred"] for r in records if r["pred"] is not None]

    if not y_true:
        raise RuntimeError("No valid predictions to evaluate.")

    exact_acc = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    mae = sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)
    mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true)
    bias = sum((p - t) for t, p in zip(y_true, y_pred)) / len(y_true)
    spearman = spearman_corr(y_true, y_pred)
    order_ok = order_non_violation(y_true, y_pred)

    drop_stats = None
    if deltas:
        drop_stats = {
            "non_drop_rate": sum(1 for d in deltas if d >= 0) / len(deltas),
            "improve_rate": sum(1 for d in deltas if d > 0) / len(deltas),
            "avg_delta": statistics.mean(deltas),
            "min_delta": min(deltas),
            "max_delta": max(deltas),
        }

    report = {
        "model": cfg.get("model_name", "unknown"),
        "samples": len(records),
        "metrics": {
            "exact_acc": exact_acc,
            "mae": mae,
            "mse": mse,
            "bias": bias,
            "spearman": spearman,
            "order_non_violation": order_ok,
        },
        "polisher": drop_stats,
        "confusion": confusion,
        "details": records,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
