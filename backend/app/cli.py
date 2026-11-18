"""
Operator CLI for account management - the production path for creating
accounts, since demo seeding is off by default.

    python -m app.cli create-user alice --role employee
    python -m app.cli create-user hr_lead --role hr_admin
    python -m app.cli reset-password alice
    python -m app.cli list-users

Passwords are prompted for interactively (never echoed, never in shell
history); pass --password-stdin to pipe one in from a script instead.
"""
import argparse
import getpass
import sys

from . import models
from .database import Base, SessionLocal, engine
from .users import ROLES, UserError, create_user, reset_password


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Password: ")
    if getpass.getpass("Confirm password: ") != first:
        raise UserError("Passwords didn't match.")
    return first


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Smiley account management")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-user", help="create a new account")
    create.add_argument("username")
    create.add_argument("--role", choices=ROLES, default="employee")
    create.add_argument("--password-stdin", action="store_true")

    reset = sub.add_parser("reset-password", help="set a new password and sign the user out everywhere")
    reset.add_argument("username")
    reset.add_argument("--password-stdin", action="store_true")

    sub.add_parser("list-users", help="list all accounts")

    args = parser.parse_args(argv)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.command == "list-users":
            for u in db.query(models.User).order_by(models.User.username):
                print(f"{u.username:<24} {u.role}")
        elif args.command == "create-user":
            user = create_user(db, args.username, _read_password(args.password_stdin), args.role)
            print(f"Created {user.role} '{user.username}'.")
        elif args.command == "reset-password":
            reset_password(db, args.username, _read_password(args.password_stdin))
            print(f"Password for '{args.username}' updated; existing sessions revoked.")
        return 0
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
