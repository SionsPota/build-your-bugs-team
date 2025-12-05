"""
数据库初始化脚本
用于创建数据库表和初始数据
"""

import sqlite3
import uuid
from pathlib import Path
from app import app
from user_models import db, User


def migrate_existing_database():
    """为现有数据库添加新字段（如果表已存在）"""
    # 确定数据库路径
    db_path = None
    if Path("instance/app.db").exists():
        db_path = "instance/app.db"
    elif Path("app.db").exists():
        db_path = "app.db"

    if not db_path:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='histories'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(histories)")
        columns = [col[1] for col in cursor.fetchall()]

        # 添加global_id字段
        if "global_id" not in columns:
            print("为现有数据库添加 global_id 字段...")
            cursor.execute("ALTER TABLE histories ADD COLUMN global_id TEXT")
            # 为现有记录生成global_id
            cursor.execute("SELECT id FROM histories WHERE global_id IS NULL")
            rows = cursor.fetchall()
            for row in rows:
                history_id = row[0]
                new_global_id = str(uuid.uuid4())
                cursor.execute(
                    "UPDATE histories SET global_id = ? WHERE id = ?",
                    (new_global_id, history_id),
                )
            print(f"  已为 {len(rows)} 条记录生成 global_id")

        # 添加user_sequence字段
        if "user_sequence" not in columns:
            print("为现有数据库添加 user_sequence 字段...")
            cursor.execute("ALTER TABLE histories ADD COLUMN user_sequence INTEGER")
            # 为每个用户的记录分配序号
            cursor.execute("SELECT DISTINCT user_id FROM histories")
            user_ids = [row[0] for row in cursor.fetchall()]

            for user_id in user_ids:
                cursor.execute(
                    "SELECT id FROM histories WHERE user_id = ? ORDER BY created_at ASC",
                    (user_id,),
                )
                histories = cursor.fetchall()
                for sequence, (history_id,) in enumerate(histories, start=1):
                    cursor.execute(
                        "UPDATE histories SET user_sequence = ? WHERE id = ?",
                        (sequence, history_id),
                    )
            print(f"  已为 {len(user_ids)} 个用户的记录分配 user_sequence")

        # 迁移question_file字段到question字段
        if "question_file" in columns and "question" not in columns:
            print("迁移 question_file 字段到 question 字段...")
            # 添加新字段
            cursor.execute("ALTER TABLE histories ADD COLUMN question TEXT")
            # 复制数据：如果question_file是数字字符串，直接复制；否则尝试提取题名
            cursor.execute("SELECT id, question_file FROM histories")
            rows = cursor.fetchall()
            for history_id, question_file_value in rows:
                if question_file_value:
                    # 如果question_file是数字字符串（题名），直接使用
                    # 否则保持原值（兼容旧数据）
                    cursor.execute(
                        "UPDATE histories SET question = ? WHERE id = ?",
                        (question_file_value, history_id),
                    )
            print(f"  已迁移 {len(rows)} 条记录的 question 字段")

            # 删除旧字段（SQLite不支持直接删除列，需要重建表）
            print("  注意：SQLite不支持直接删除列，question_file字段将保留但不再使用")
            print("  如需完全删除，请手动重建表或使用迁移工具")

        # 创建索引
        try:
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_histories_global_id ON histories(global_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_histories_user_sequence ON histories(user_id, user_sequence)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_histories_question ON histories(question)"
            )
        except Exception as e:
            print(f"  索引创建警告: {e}")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"迁移现有数据库时出错: {e}")
    finally:
        conn.close()


def init_database():
    """初始化数据库"""
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("数据库表创建成功！")

        # 如果表已存在，尝试迁移现有数据库
        # migrate_existing_database()

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
