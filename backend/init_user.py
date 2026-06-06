"""
初始化默认用户的脚本（仅在 admin 不存在时创建）
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def init_user():
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("Admin user already exists, skip initialization.")
            return

        print("Creating default admin user...")
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            email="admin@example.com"
        )
        db.add(admin)
        db.commit()
        print("Admin user created successfully (username: admin, password: admin123).")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_user()
