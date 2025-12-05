"""
清空数据库记录脚本

使用方法：
1. 备份数据库（如果需要）
2. 运行: python clear_database.py
"""

import sqlite3
from pathlib import Path

# 数据库文件路径（自动检测）
from pathlib import Path

if Path("instance/app.db").exists():
    DB_PATH = "instance/app.db"
elif Path("app.db").exists():
    DB_PATH = "app.db"
else:
    DB_PATH = "instance/app.db"  # 默认使用instance目录


def clear_database():
    """清空数据库中的所有记录"""
    if not Path(DB_PATH).exists():
        print(f"数据库文件 {DB_PATH} 不存在")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("开始清空数据库记录...")

        # 删除所有历史记录
        cursor.execute("DELETE FROM histories")
        deleted_histories = cursor.rowcount
        print(f"  已删除 {deleted_histories} 条历史记录")

        # 可选：删除所有用户（如果需要）
        # cursor.execute("DELETE FROM users")
        # deleted_users = cursor.rowcount
        # print(f"  已删除 {deleted_users} 个用户")

        conn.commit()
        print("\n数据库清空完成！")

    except Exception as e:
        conn.rollback()
        print(f"\n清空数据库失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    confirm = input("确定要清空数据库中的所有记录吗？(yes/no): ")
    if confirm.lower() == "yes":
        clear_database()
    else:
        print("操作已取消")
