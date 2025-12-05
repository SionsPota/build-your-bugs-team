"""
数据库迁移脚本：为历史记录表添加score字段并升级现有数据

使用方法：
    python migrate_add_score.py

功能：
    1. 为histories表添加score字段（如果不存在）
    2. 解析现有记录的comment，提取score并更新到数据库
"""

import os
import sys
from pathlib import Path
from app import app
from user_models import db, History
from model import CommentParser


def migrate_add_score_field():
    """为histories表添加score字段（如果不存在）"""
    # 检查字段是否已存在
    try:
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("histories")]

        if "score" in columns:
            print("✓ score字段已存在，跳过添加字段步骤")
            return True
    except Exception as e:
        print(f"警告：检查字段时出错: {str(e)}，将尝试添加字段")

    print("正在添加score字段...")
    try:
        # 使用SQLAlchemy的DDL来添加字段
        from sqlalchemy import text

        with db.engine.connect() as conn:
            # 根据数据库类型选择不同的SQL语句
            db_url = str(db.engine.url)
            if "sqlite" in db_url.lower():
                # SQLite不支持ALTER TABLE ADD COLUMN IF NOT EXISTS，需要先检查
                conn.execute(text("ALTER TABLE histories ADD COLUMN score INTEGER"))
            elif "postgresql" in db_url.lower():
                conn.execute(text("ALTER TABLE histories ADD COLUMN score INTEGER"))
            elif "mysql" in db_url.lower():
                conn.execute(text("ALTER TABLE histories ADD COLUMN score INT"))
            else:
                # 默认使用SQLite语法
                conn.execute(text("ALTER TABLE histories ADD COLUMN score INTEGER"))
            conn.commit()

        print("✓ score字段添加成功")
        return True
    except Exception as e:
        # 如果字段已存在，忽略错误
        error_msg = str(e).lower()
        if (
            "duplicate" in error_msg
            or "already exists" in error_msg
            or "duplicate column" in error_msg
        ):
            print("✓ score字段已存在（通过错误信息检测）")
            return True
        print(f"✗ 添加score字段失败: {str(e)}")
        return False


def upgrade_existing_records():
    """升级现有记录：从comment中解析score并更新"""
    print("\n开始升级现有记录...")

    # 查询所有有comment但没有score的记录
    histories = History.query.filter(
        History.comment.isnot(None),
        History.comment != "",
        (History.score.is_(None) | (History.score == 0)),
    ).all()

    if not histories:
        print("✓ 没有需要升级的记录")
        return True

    print(f"找到 {len(histories)} 条需要升级的记录")

    parser = CommentParser()
    updated_count = 0
    failed_count = 0

    for i, history in enumerate(histories, 1):
        try:
            # 解析comment获取score
            parsed_comment = parser.parse_complete(history.comment)
            score = parsed_comment.get("score")

            if score is not None:
                history.score = score
                updated_count += 1
                if i % 10 == 0:
                    print(f"  已处理 {i}/{len(histories)} 条记录...")
            else:
                # 如果解析不出score，设置为None（保持NULL）
                history.score = None
                failed_count += 1
        except Exception as e:
            print(f"  ✗ 处理记录 ID={history.id} 时出错: {str(e)}")
            failed_count += 1
            continue

    # 提交所有更改
    try:
        db.session.commit()
        print(f"\n✓ 升级完成！")
        print(f"  - 成功更新: {updated_count} 条")
        print(f"  - 解析失败: {failed_count} 条")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"\n✗ 提交更改失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("数据库迁移脚本：添加score字段并升级现有数据")
    print("=" * 60)

    with app.app_context():
        # 确保数据库表已创建
        db.create_all()

        # 步骤1：添加score字段
        if not migrate_add_score_field():
            print("\n迁移失败：无法添加score字段")
            sys.exit(1)

        # 步骤2：升级现有记录
        if not upgrade_existing_records():
            print("\n迁移失败：无法升级现有记录")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("迁移完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()
