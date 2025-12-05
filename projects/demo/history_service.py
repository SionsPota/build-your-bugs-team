"""
历史记录服务模块
"""

from datetime import datetime
from user_models import db, History, User
from flask import jsonify


def save_history(user_id, answer, question_file, comment=None, polished_answer=None):
    """
    保存历史记录
    Returns: (success: bool, message: str, history: History or None)
    """
    try:
        history = History(
            user_id=user_id,
            answer=answer,
            question_file=question_file,
            comment=comment,
            polished_answer=polished_answer,
        )
        db.session.add(history)
        db.session.commit()
        return True, "历史记录保存成功", history
    except Exception as e:
        db.session.rollback()
        return False, f"保存历史记录失败: {str(e)}", None


def get_user_histories(user_id, page=1, per_page=20):
    """
    获取用户的历史记录（分页）
    Returns: (histories: list, total: int, page: int, per_page: int, pages: int)
    """
    query = History.query.filter_by(user_id=user_id).order_by(History.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    histories = [h.to_dict() for h in pagination.items]

    return {
        "histories": histories,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    }


def get_history_by_id(history_id, user_id):
    """
    根据ID获取历史记录（确保属于当前用户）
    Returns: History or None
    """
    history = History.query.filter_by(id=history_id, user_id=user_id).first()
    return history


def delete_history(history_id, user_id):
    """
    删除历史记录（确保属于当前用户）
    Returns: (success: bool, message: str)
    """
    history = History.query.filter_by(id=history_id, user_id=user_id).first()
    if not history:
        return False, "历史记录不存在或无权限"

    try:
        db.session.delete(history)
        db.session.commit()
        return True, "删除成功"
    except Exception as e:
        db.session.rollback()
        return False, f"删除失败: {str(e)}"
