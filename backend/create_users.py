from sqlalchemy import text
from database import engine
from security import hash_password

# Demo accounts. Change these passwords before showing the project outside your team.
USERS = [
    ("admin", "Admin@123", "admin"),
    ("operator", "Operator@123", "operator"),
    ("viewer", "Viewer@123", "viewer"),
]

with engine.begin() as conn:
    for username, password, role in USERS:
        conn.execute(
            text("INSERT INTO users (username, password_hash, role) VALUES (:u, :p, :r) "
                 "ON DUPLICATE KEY UPDATE password_hash = :p, role = :r"),
            {"u": username, "p": hash_password(password), "r": role},
        )
        print(f"Created user: {username} ({role})")