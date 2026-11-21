"""Provision a platform administrator interactively."""

import getpass
import sys
from pathlib import Path

from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.auth import create_user  # noqa: E402
from app.db import Store, engine  # noqa: E402

email = input("Email address: ").strip()
name = input("Name: ").strip()
password = getpass.getpass("Password (10 characters minimum): ")
if "@" not in email or len(password) < 10:
    raise SystemExit("A valid email and longer password are required.")
with Session(engine) as session:
    store = Store(session)
    user = create_user(store, email, name, password, role="Super Admin")
    store.put("system", "user", user["id"], {**user, "verified": True})
    session.commit()
print("Administrator created.")
