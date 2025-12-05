import os
import json
import time
import re
from flask import Flask, request, jsonify, Response, stream_with_context, g, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    get_jwt_identity,
    create_refresh_token,
    verify_jwt_in_request,
)
from dotenv import load_dotenv

from model import Evaluator, Polisher
from telemetry import log_event, new_request_id, LOG_FILE
from user_models import db, User
from auth import register_user, authenticate_user, create_tokens, get_current_user
from history_service import (
    save_history,
    get_user_histories,
    get_history_by_id,
    delete_history,
)
from question_bank import get_question_bank

load_dotenv()

app = Flask(__name__)
# 启用 CORS，允许前端跨域访问
CORS(app)

# 数据库配置
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///app.db"  # 默认使用SQLite
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# JWT配置
app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY", "your-secret-key-change-in-production"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # 由create_access_token控制
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = False  # 由create_refresh_token控制
# JWT默认从Authorization header中读取Bearer token，无需额外配置

# 初始化扩展
db.init_app(app)
jwt = JWTManager(app)


# JWT错误处理器
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token已过期，请重新登录"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"error": f"无效的Token: {str(error)}"}), 422


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({"error": "缺少认证Token，请先登录"}), 401


@jwt.needs_fresh_token_loader
def token_not_fresh_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token需要刷新"}), 401


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
    question = None
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            question = payload.get("question")
    log_event(
        "api.request.done",
        request_id=getattr(g, "request_id", None),
        route=request.path,
        method=request.method,
        status=response.status_code,
        duration_ms=duration_ms,
        question=question,
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


# ==================== 用户认证相关路由 ====================


@app.route("/auth/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    success, message, user = register_user(username, email, password)

    if success:
        tokens = create_tokens(user)
        return jsonify({"message": message, "user": user.to_dict(), **tokens}), 201
    else:
        return jsonify({"error": message}), 400


@app.route("/auth/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    success, message, user = authenticate_user(username, password)

    if success:
        tokens = create_tokens(user)
        return jsonify({"message": message, "user": user.to_dict(), **tokens}), 200
    else:
        return jsonify({"error": message}), 401


@app.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """刷新访问令牌"""
    user_id = get_jwt_identity()
    # JWT identity是字符串，需要转换为整数来查询数据库
    user_id_int = int(user_id) if isinstance(user_id, str) else user_id
    user = User.query.get(user_id_int)

    if not user or not user.is_active:
        return jsonify({"error": "用户不存在或已被禁用"}), 401

    from flask_jwt_extended import create_access_token
    from datetime import timedelta

    # 确保identity是字符串
    new_token = create_access_token(
        identity=str(user_id_int), expires_delta=timedelta(hours=24)
    )

    return jsonify({"access_token": new_token, "token_type": "Bearer"}), 200


@app.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user_info():
    """获取当前用户信息"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    return jsonify({"user": user.to_dict(include_email=True)}), 200


# ==================== 历史记录相关路由 ====================


@app.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    """获取用户历史记录（分页）"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "用户不存在"}), 404

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        result = get_user_histories(user.id, page=page, per_page=per_page)
        return jsonify(result), 200
    except Exception as e:
        log_event(
            "history.get.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            error_type=type(e).__name__,
        )
        return jsonify({"error": f"获取历史记录失败: {str(e)}"}), 500


@app.route("/history/<path:history_id>", methods=["GET"])
@jwt_required()
def get_history_detail(history_id):
    """
    获取单条历史记录详情（需要用户token）
    只支持通过以下方式查询（不允许使用主键id）：
    - global_id（UUID字符串）：/history/550e8400-e29b-41d4-a716-446655440000
    - user_sequence（用户内部序号，整数）：/history/5
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    history = get_history_by_id(history_id, user.id)
    if not history:
        return jsonify({"error": "历史记录不存在或无权限"}), 404

    return jsonify({"history": history.to_dict()}), 200


@app.route("/history/<path:history_id>", methods=["DELETE"])
@jwt_required()
def delete_history_route(history_id):
    """
    删除历史记录（需要用户token）
    只支持通过以下方式查询（不允许使用主键id）：
    - global_id（UUID字符串）：/history/550e8400-e29b-41d4-a716-446655440000
    - user_sequence（用户内部序号，整数）：/history/5
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    success, message = delete_history(history_id, user.id)

    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400


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


@app.route("/api/question/list", methods=["GET"])
@app.route("/question/list", methods=["GET"])  # 兼容代理路径
def get_question_list():
    """获取题目列表（从题库）

    为了兼容前端，返回格式为 { files: string[] }，其中files是题目ID的字符串数组

    Query参数:
        only_valid: 是否只返回有效题目，默认true
        offset: 偏移量，默认0
        limit: 限制数量，默认不限制
        format: 返回格式，可选值：
            - "simple" (默认): 返回 { files: string[] } 格式（兼容前端）
            - "detailed": 返回详细格式 { questions: [...], total: ... }

    Returns:
        JSON: 题目列表
    """
    try:
        question_bank = get_question_bank()
        only_valid = request.args.get("only_valid", "true").lower() == "true"
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", None, type=int)
        format_type = request.args.get("format", "simple").lower()

        questions, total = question_bank.get_question_list(
            only_valid=only_valid,
            offset=offset,
            limit=limit,
        )

        if format_type == "detailed":
            # 返回详细格式
            return (
                jsonify(
                    {
                        "questions": questions,
                        "total": total,
                        "offset": offset,
                        "limit": limit,
                    }
                ),
                200,
            )
        else:
            # 返回简单格式（兼容前端）：只返回题目ID的字符串数组
            files = [q["id"] for q in questions]
            return jsonify({"files": files}), 200
    except Exception as e:
        log_event(
            "get_question_list.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            error_type=type(e).__name__,
        )
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/question/statistics", methods=["GET"])
@app.route("/question/statistics", methods=["GET"])  # 兼容代理路径
def get_question_statistics():
    """获取题库统计信息

    Returns:
        JSON: 统计信息，包含总数、有效数、无效数
    """
    try:
        question_bank = get_question_bank()
        stats = question_bank.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        log_event(
            "get_question_statistics.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            error_type=type(e).__name__,
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/question/markdown", methods=["GET"])
@app.route("/question/markdown", methods=["GET"])  # 兼容代理路径
def get_question_markdown():
    """获取题目的markdown格式（原始TPO.json格式）
    可以直接传给大模型使用

    Query参数:
        question: 题名（字符串），必填
        format: 返回格式，可选值：
            - "dict" (默认): 返回字典格式 {"instruction": "...", "teacher": "...", "students": [...]}
            - "string": 返回完整字符串格式

    Returns:
        JSON: markdown格式的题目数据
    """
    try:
        question_name = request.args.get("question")
        if not question_name:
            return jsonify({"error": "参数 'question' 是必需的"}), 400

        format_type = request.args.get("format", "dict").lower()

        question_bank = get_question_bank()
        result = question_bank.get_question_markdown(
            question_id=question_name,
            only_valid=True,
            as_string=(format_type == "string"),
        )

        if result is None:
            return jsonify({"error": f"题目不存在或无效: {question_name}"}), 404

        if format_type == "string":
            return jsonify({"markdown": result}), 200
        else:
            return jsonify(result), 200
    except Exception as e:
        log_event(
            "get_question_markdown.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            error_type=type(e).__name__,
        )
        return jsonify({"error": str(e)}), 500


@app.route("/api/question", methods=["GET"])
@app.route("/question", methods=["GET"])  # 兼容代理路径
def get_question():
    """获取题目数据
    从题库加载题目数据

    Query参数:
        question: 题名（字符串），必填

    Returns:
        JSON: 题目数据，格式如下：
        {
            "id": "44",
            "subject": "sociology",
            "instruction": "...",
            "professor": {
                "name": "Doctor Achebe",
                "avatar": "",
                "prompt": "..."
            },
            "students": [
                {
                    "name": "Claire",
                    "avatar": "",
                    "response": "..."
                },
                ...
            ]
        }
    """
    try:
        question_name = request.args.get("question")
        if not question_name:
            return jsonify({"error": "参数 'question' 是必需的"}), 400

        question_bank = get_question_bank()
        question = question_bank.get_question(question_name, only_valid=True)

        if not question:
            return jsonify({"error": f"题目不存在或无效: {question_name}"}), 404

        # 解析subject（从instruction中提取）
        instruction = question.instruction
        subject_match = re.search(
            r"teaching a class on (\w+)", instruction, re.IGNORECASE
        )
        subject = subject_match.group(1) if subject_match else "unknown"

        result = {
            "id": question.id,
            "subject": subject,
            "instruction": question.instruction,
            "professor": {
                "name": question.teacher,
                "avatar": "",
                "prompt": question.teacher_content,
            },
            "students": [
                {
                    "name": student.get("name", ""),
                    "avatar": "",
                    "response": student.get("content", ""),
                }
                for student in question.students
            ],
        }
        return jsonify(result), 200
    except Exception as e:
        log_event(
            "get_question.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            error_type=type(e).__name__,
        )
        return jsonify({"error": str(e)}), 500


# 保留旧的同步接口作为备用
@app.route("/grade_and_polish_sync", methods=["POST"])
def grade_and_polish_sync():
    """
    同步接口（备用）
    请求体示例:
    {
        "answer": "...学生作文...",
        "question": "44"   # 题名（字符串），必填
    }
    如果用户已登录（通过Authorization header传递JWT token），会自动保存历史记录
    """
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    question = data.get("question")

    if not answer:
        return jsonify({"error": "field 'answer' is required"}), 400

    if not question:
        return jsonify({"error": "field 'question' is required"}), 400

    # 尝试获取当前用户（可选，未登录也能使用）
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        current_user = get_current_user()
    except Exception:
        pass

    try:
        evaluator = Evaluator(question=question)
        comment = evaluator.generate_response(answer)

        polisher = Polisher(answer, comment)
        polished_answer = polisher.generate_response()

        # 如果用户已登录，保存历史记录
        if current_user:
            try:
                save_history(
                    user_id=current_user.id,
                    answer=answer,
                    question=question,  # 保存题名
                    comment=comment,
                    polished_answer=polished_answer,
                )
            except Exception as e:
                log_event(
                    "grade_and_polish_sync.history_save_error",
                    request_id=getattr(g, "request_id", None),
                    error=str(e),
                    user_id=current_user.id,
                )

        return jsonify({"comment": comment, "polished_answer": polished_answer})
    except Exception as e:
        log_event(
            "grade_and_polish_sync.error",
            request_id=getattr(g, "request_id", None),
            error=str(e),
            question=question,
            user_id=current_user.id if current_user else None,
        )
        return jsonify({"error": str(e)}), 500


@app.route("/grade_and_polish", methods=["POST"])
def grade_and_polish():
    """
    流式传输接口，使用 Server-Sent Events (SSE)
    请求体示例:
    {
        "answer": "...学生作文...",
        "question": "44"   # 题名（字符串），必填
    }
    如果用户已登录（通过Authorization header传递JWT token），会自动保存历史记录
    """
    data = request.get_json(silent=True) or {}
    answer = data.get("answer")
    question = data.get("question")

    if not answer:
        return jsonify({"error": "field 'answer' is required"}), 400

    if not question:
        return jsonify({"error": "field 'question' is required"}), 400

    # 尝试获取当前用户（可选，未登录也能使用）
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        current_user = get_current_user()
    except Exception:
        pass

    def generate():
        history_id = None
        try:
            log_event(
                "grade_and_polish.start",
                request_id=getattr(g, "request_id", None),
                question=question,
                user_id=current_user.id if current_user else None,
            )

            # 如果用户已登录，先创建历史记录（用于获取ID）
            if current_user:
                try:
                    # 先创建一条空的历史记录，后续再更新
                    success, message, history = save_history(
                        user_id=current_user.id,
                        answer=answer,
                        question=question,  # 保存题名
                        comment="",  # 暂时为空，后续更新
                        polished_answer="",  # 暂时为空，后续更新
                    )
                    if success and history:
                        # 使用global_id作为history_id返回（不暴露主键）
                        history_id = history.global_id
                        # 发送历史记录ID
                        yield f"data: {json.dumps({'type': 'history_id', 'history_id': history_id})}\n\n"
                except Exception as e:
                    log_event(
                        "grade_and_polish.history_create_error",
                        request_id=getattr(g, "request_id", None),
                        error=str(e),
                        user_id=current_user.id,
                    )

            # 发送开始评估通知
            yield f"data: {json.dumps({'type': 'status', 'stage': 'evaluating', 'message': '开始评估作文...'})}\n\n"

            evaluator = Evaluator(question=question)
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

            # 如果用户已登录，更新历史记录
            if current_user and history_id:
                try:
                    # 使用get_history_by_id以支持多种ID类型
                    history = get_history_by_id(history_id, current_user.id)
                    if history:
                        history.comment = comment
                        history.polished_answer = polished_answer
                        db.session.commit()
                        yield f"data: {json.dumps({'type': 'history_saved', 'message': '历史记录已保存', 'history_id': history_id})}\n\n"
                except Exception as e:
                    db.session.rollback()
                    log_event(
                        "grade_and_polish.history_update_error",
                        request_id=getattr(g, "request_id", None),
                        error=str(e),
                        user_id=current_user.id,
                        history_id=history_id,
                    )

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            log_event(
                "grade_and_polish.done",
                request_id=getattr(g, "request_id", None),
                question=question,
                comment_chars=len(comment),
                polished_chars=len(polished_answer),
                user_id=current_user.id if current_user else None,
            )

        except Exception as e:
            log_event(
                "grade_and_polish.error",
                request_id=getattr(g, "request_id", None),
                error=str(e),
                question=question,
                user_id=current_user.id if current_user else None,
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


@app.route("/grade_and_polish/<path:history_id>", methods=["GET"])
@jwt_required()
def get_grade_and_polish_stream(history_id):
    """
    通过历史记录ID获取流式评分结果（需要用户token）
    用于重新连接或查看正在进行的评分
    只支持通过以下方式查询（不允许使用主键id）：
    - global_id（UUID字符串）
    - user_sequence（用户内部序号，整数）
    """
    # 获取当前用户（必须登录）
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "需要登录"}), 401

    # 获取历史记录
    history = get_history_by_id(history_id, current_user.id)

    if not history:
        return jsonify({"error": "历史记录不存在"}), 404

    # 如果已有完整结果，直接返回
    if history.comment and history.polished_answer:

        def generate_complete():
            yield f"data: {json.dumps({'type': 'comment_complete', 'comment': history.comment})}\n\n"
            yield f"data: {json.dumps({'type': 'polished_complete', 'polished_answer': history.polished_answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return Response(
            stream_with_context(generate_complete()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # 如果还没有完整结果，重新执行评分
    def generate():
        try:
            # history.question现在统一为题名
            evaluator = Evaluator(question=history.question)
            comment_stream = evaluator.generate_response(history.answer, stream=True)

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

            yield f"data: {json.dumps({'type': 'comment_complete', 'comment': comment})}\n\n"

            yield f"data: {json.dumps({'type': 'status', 'stage': 'polishing', 'message': '开始润色作文...'})}\n\n"

            polisher = Polisher(history.answer, comment)
            polished_stream = polisher.generate_response(stream=True)

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

            yield f"data: {json.dumps({'type': 'polished_complete', 'polished_answer': polished_answer})}\n\n"

            # 更新历史记录
            try:
                history.comment = comment
                history.polished_answer = polished_answer
                db.session.commit()
                yield f"data: {json.dumps({'type': 'history_saved', 'message': '历史记录已保存', 'history_id': history_id})}\n\n"
            except Exception as e:
                db.session.rollback()
                log_event(
                    "grade_and_polish_stream_by_id.history_update_error",
                    request_id=getattr(g, "request_id", None),
                    error=str(e),
                    user_id=current_user.id,
                    history_id=history_id,
                )

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            log_event(
                "grade_and_polish_stream_by_id.error",
                request_id=getattr(g, "request_id", None),
                error=str(e),
                history_id=history_id,
                user_id=current_user.id if current_user else None,
            )
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    # 确保数据库表已创建
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000, debug=True)
