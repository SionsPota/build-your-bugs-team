"""
数据库初始化脚本
用于创建数据库表和初始数据
"""

from app import app
from user_models import db, User


def init_database():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功！")

        # 可选：创建管理员用户
        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_password = "admin123"  # 生产环境请修改

        existing_admin = User.query.filter_by(username=admin_username).first()
        if not existing_admin:
            admin = User(username=admin_username, email=admin_email)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"管理员用户创建成功: {admin_username} / {admin_password}")
        else:
            print(f"管理员用户已存在: {admin_username}")


if __name__ == "__main__":
    init_database()
