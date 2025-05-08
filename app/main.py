from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routes import auth_routes, user_routes
from app.auth import get_current_user

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 掛載路由
app.include_router(auth_routes.router, prefix="/auth")
app.include_router(user_routes.router, prefix="/users")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def search_page(request: Request, user: str = Depends(get_current_user)):
    return templates.TemplateResponse("search.html", {"request": request})

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    return templates.TemplateResponse("change_password.html", {"request": request})