"""
用户系统数据库模型
"""

import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """用户模型"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # 关联关系：一个用户有多条历史记录
    histories = db.relationship(
        "History", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        """设置密码（加密存储）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_email=False):
        """转换为字典（用于JSON响应）"""
        data = {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }
        if include_email:
            data["email"] = self.email
        return data


class History(db.Model):
    """历史记录模型"""

    __tablename__ = "histories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    # ID系统：支持两种查询方式
    global_id = db.Column(
        db.String(36), unique=True, nullable=False, index=True
    )  # 全局唯一ID（UUID）
    user_sequence = db.Column(
        db.Integer, nullable=False, index=True
    )  # 用户内部序号（从1开始）

    # 请求相关字段
    answer = db.Column(db.Text, nullable=False)  # 原始答案
    question = db.Column(db.String(255), nullable=False)  # 题名（字符串）

    # 结果相关字段
    comment = db.Column(db.Text)  # 评语
    polished_answer = db.Column(db.Text)  # 润色后的答案

    # 元数据
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # 关联关系已在User模型中定义

    def to_dict(self):
        """转换为字典（用于JSON响应）"""
        return {
            "id": self.id,
            "global_id": self.global_id,
            "user_sequence": self.user_sequence,
            "user_id": self.user_id,
            "answer": self.answer,
            "question": self.question,
            "comment": self.comment,
            "polished_answer": self.polished_answer,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
