"""
用户认证模块
"""

from flask import jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from datetime import timedelta
from user_models import db, User


def register_user(username, email, password):
    """
    注册新用户
    Returns: (success: bool, message: str, user: User or None)
    """
    # 验证输入
    if not username or not email or not password:
        return False, "用户名、邮箱和密码不能为空", None

    if len(password) < 6:
        return False, "密码长度至少为6位", None

    # 检查用户名是否已存在
    if User.query.filter_by(username=username).first():
        return False, "用户名已存在", None

    # 检查邮箱是否已存在
    if User.query.filter_by(email=email).first():
        return False, "邮箱已被注册", None

    # 创建新用户
    try:
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return True, "注册成功", user
    except Exception as e:
        db.session.rollback()
        return False, f"注册失败: {str(e)}", None


def authenticate_user(username, password):
    """
    验证用户登录
    Returns: (success: bool, message: str, user: User or None)
    """
    if not username or not password:
        return False, "用户名和密码不能为空", None

    user = User.query.filter_by(username=username).first()

    if not user:
        return False, "用户名或密码错误", None

    if not user.is_active:
        return False, "账户已被禁用", None

    if not user.check_password(password):
        return False, "用户名或密码错误", None

    return True, "登录成功", user


def create_tokens(user):
    """
    为用户创建JWT tokens
    Returns: dict with access_token and refresh_token
    """
    # Flask-JWT-Extended要求identity必须是字符串
    user_id_str = str(user.id)
    access_token = create_access_token(
        identity=user_id_str, expires_delta=timedelta(hours=24)
    )
    refresh_token = create_refresh_token(
        identity=user_id_str, expires_delta=timedelta(days=30)
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


def get_current_user():
    """
    获取当前登录用户（需要在JWT保护的上下文中调用）
    Returns: User or None
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            # JWT identity是字符串，需要转换为整数来查询数据库
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            return User.query.get(user_id_int)
    except Exception:
        pass
    return None
