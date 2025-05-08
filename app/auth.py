from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS = {
    "admin": {
        "hashed_password": "$2b$12$hjLjJgHwP4qKECQOw3y/.eqsLTzQw3WO21fJkzfuBhJqvh2HCp7i.", 
        "is_superuser": True
    },
    "user1": {
        "hashed_password": "$2b$12$QEHSecQSKLvfqZb/VFFx1.IPrXXBQHb1vIaNmFQsTRztlrgbVT0Lq",
        "is_superuser": False
    }
}
