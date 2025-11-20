import os
import json
import time
from flask import Flask, request, jsonify, Response, stream_with_context, g, send_file
from flask_cors import CORS
from dotenv import load_dotenv

from model import Evaluator, Polisher
from telemetry import log_event, new_request_id, LOG_FILE

load_dotenv()

app = Flask(__name__)
# 启用 CORS，允许前端跨域访问
CORS(app)

@app.before_request
def _start_request():
    g.request_id = new_request_id()
    g.start_time = time.perf_counter()
    log_event(
        "api.request.start",
        request_id=g.request_id,
        route=request.path,
        method=request.method,
    )

@app.after_request
def _after_request(response):
    duration_ms = None
    if hasattr(g, "start_time"):
        duration_ms = int((time.perf_counter() - g.start_time) * 1000)
    question_file = None
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            question_file = payload.get("question_file")
    log_event(
        "api.request.done",
        request_id=getattr(g, "request_id", None),
        route=request.path,
        method=request.method,
        status=response.status_code,
        duration_ms=duration_ms,
        question_file=question_file,
    )
    return response

@app.errorhandler(Exception)
def _handle_error(e):
    log_event(
        "api.request.error",
        request_id=getattr(g, "request_id", None),
        route=getattr(request, "path", None),
        method=getattr(request, "method", None),
        error_type=type(e).__name__,
        error=str(e),
    )
    return jsonify({"error": "internal error"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/logs/telemetry", methods=["GET"])
def download_logs():
    """下载遥测日志文件。"""
    if not LOG_FILE.exists():
        return jsonify({"error": "log file not found"}), 404
    # 使用一次性读取避免代理端对流式响应解析错误
    with open(LOG_FILE, "rb") as f:
        data = f.read()
    resp = Response(data, mimetype="text/plain")
    resp.headers["Content-Disposition"] = "attachment; filename=telemetry.log"
    resp.headers["Cache-Control"] = "no-store"
    return resp


# 保留旧的同步接口作为备用
@app.route("/grade_and_polish_sync", methods=["POST"])
def grade_and_polish_sync():
    """
    同步接口（备用）
    请求体示例:
    {
        "answer": "...学生作文...",
        "question_file": "test.yaml"   # 可选，默认 test.yaml
    }
    """
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    question_file = data.get("question_file", "test.yaml")

    if not answer:
        return jsonify({"error": "field 'answer' is required"}), 400

    try:
        evaluator = Evaluator(question_file=question_file)
        comment = evaluator.generate_response(answer)

        polisher = Polisher(answer, comment)
        polished_answer = polisher.generate_response()

        return jsonify({"comment": comment, "polished_answer": polished_answer})
    except Exception as e:
        log_event(
            "grade_and_polish_sync.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            question_file=question_file,
        )
        return jsonify({"error": str(e)}), 500


@app.route("/grade_and_polish", methods=["POST"])
def grade_and_polish():
    """
    流式传输接口，使用 Server-Sent Events (SSE)
    请求体示例:
    {
        "answer": "...学生作文...",
        "question_file": "test.yaml"   # 可选，默认 test.yaml
    }
    """
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    question_file = data.get("question_file", "test.yaml")

    if not answer:
        return jsonify({"error": "field 'answer' is required"}), 400

    def generate():
        try:
            log_event(
                "grade_and_polish.start",
                request_id=getattr(g, "request_id", None),
                question_file=question_file,
            )
            # 发送开始评估通知
            yield f"data: {json.dumps({'type': 'status', 'stage': 'evaluating', 'message': '开始评估作文...'})}\n\n"

            evaluator = Evaluator(question_file=question_file)
            comment_stream = evaluator.generate_response(answer, stream=True)

            # 流式接收评估结果
            comment = ""
            yield f"data: {json.dumps({'type': 'status', 'stage': 'evaluating', 'message': '正在生成评语...'})}\n\n"

            for chunk in comment_stream:
                if (
                    chunk.choices
                    and len(chunk.choices) > 0
                    and chunk.choices[0].delta.content
                ):
                    content = chunk.choices[0].delta.content
                    comment += content
                    yield f"data: {json.dumps({'type': 'comment_chunk', 'content': content})}\n\n"

            # 发送评估完成通知
            yield f"data: {json.dumps({'type': 'comment_complete', 'comment': comment})}\n\n"

            # 发送开始润色通知
            yield f"data: {json.dumps({'type': 'status', 'stage': 'polishing', 'message': '开始润色作文...'})}\n\n"

            polisher = Polisher(answer, comment)
            polished_stream = polisher.generate_response(stream=True)

            # 流式接收润色结果
            polished_answer = ""
            yield f"data: {json.dumps({'type': 'status', 'stage': 'polishing', 'message': '正在生成润色后的作文...'})}\n\n"

            for chunk in polished_stream:
                if (
                    chunk.choices
                    and len(chunk.choices) > 0
                    and chunk.choices[0].delta.content
                ):
                    content = chunk.choices[0].delta.content
                    polished_answer += content
                    yield f"data: {json.dumps({'type': 'polished_chunk', 'content': content})}\n\n"

            # 发送完成通知
            yield f"data: {json.dumps({'type': 'polished_complete', 'polished_answer': polished_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            log_event(
                "grade_and_polish.done",
                request_id=getattr(g, "request_id", None),
                question_file=question_file,
                comment_chars=len(comment),
                polished_chars=len(polished_answer),
            )

        except Exception as e:
            log_event(
                "grade_and_polish.error",
                request_id=getattr(g, "request_id", None),
                error=str(e),
                question_file=question_file,
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
