from app.database import SessionLocal, Base, engine
from app.models import User
from app.auth import get_password_hash

# 建立資料表
Base.metadata.create_all(bind=engine)

db = SessionLocal()

username = input("Enter superuser username: ")
password = input("Enter superuser password: ")

# 檢查是否已存在
existing = db.query(User).filter(User.username == username).first()
if existing:
    print("User already exists")
else:
    superuser = User(
        username=username,
        hashed_password=get_password_hash(password),
        is_superuser=True,
    )
    db.add(superuser)
    db.commit()
    print(f"Superuser '{username}' created successfully")

db.close()
