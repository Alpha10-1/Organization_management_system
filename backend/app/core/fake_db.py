from app.core.security import get_password_hash

fake_users_db = {
    "admin@org.com": {
        "id": 1,
        "name": "Admin User",
        "email": "admin@org.com",
        "role": "admin",
        "disabled": False,
        "hashed_password": get_password_hash("Admin123!"),
    },
    "staff@org.com": {
        "id": 2,
        "name": "Staff User",
        "email": "staff@org.com",
        "role": "staff",
        "disabled": False,
        "hashed_password": get_password_hash("Staff123!"),
    },
}

def get_next_user_id():
    if not fake_users_db:
        return 1
    return max(user["id"] for user in fake_users_db.values()) + 1