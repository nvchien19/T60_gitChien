"""Run from repo root: python -m scripts.manage_users create --email ... --role doctor --name ..."""
import argparse
import asyncio
from getpass import getpass

from sqlalchemy import delete

from interface.backend.db.models.tables import AuthSession, User
from interface.backend.db.session import SessionLocal
from interface.backend.services.auth_service import find_user, hash_password


async def manage(args):
    async with SessionLocal() as db:
        user = await find_user(db, args.email)
        if args.action == "create":
            if user:
                raise ValueError("Email đã tồn tại")
            email = args.email.strip().lower()
            if "@" not in email or len(email) > 254 or not email.split("@", 1)[1]:
                raise ValueError("Email không hợp lệ")
            name = args.name.strip()
            if not name or len(name) > 150:
                raise ValueError("Tên cần từ 1 đến 150 ký tự")
            password = getpass("Mật khẩu mới (ít nhất 12 ký tự): ")
            if not 12 <= len(password) <= 256 or password != getpass("Nhập lại mật khẩu: "):
                raise ValueError("Mật khẩu không hợp lệ hoặc không khớp")
            db.add(User(email=email, name=name, role=args.role, password_hash=hash_password(password)))
        else:
            if not user:
                raise ValueError("Không tìm thấy tài khoản")
            if args.action == "disable":
                user.active = False
            else:
                password = getpass("Mật khẩu mới (ít nhất 12 ký tự): ")
                if not 12 <= len(password) <= 256 or password != getpass("Nhập lại mật khẩu: "):
                    raise ValueError("Mật khẩu không hợp lệ hoặc không khớp")
                user.password_hash = hash_password(password)
            await db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        await db.commit()
        print("Đã cập nhật tài khoản.")


def main():
    parser = argparse.ArgumentParser(description="Quản lý tài khoản bác sĩ / dược sĩ")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ["create", "reset-password", "disable"]:
        command = sub.add_parser(action)
        command.add_argument("--email", required=True)
        if action == "create":
            command.add_argument("--role", choices=["doctor", "pharmacist"], required=True)
            command.add_argument("--name", required=True)
    try:
        asyncio.run(manage(parser.parse_args()))
    except ValueError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
