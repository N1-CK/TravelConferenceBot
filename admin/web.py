import io

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from database import db

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Основная админ-панель"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.post("/upload_whitelist")
async def upload_whitelist(file: UploadFile = File(...)):
    """Загрузка whitelist из CSV/Excel"""
    content = await file.read()

    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    # Добавление в БД
    for _, row in df.iterrows():
        await db.add_to_whitelist(
            username=row['username'],
            telegram_id=row.get('telegram_id'),
            company=row.get('company'),
            role=row.get('role')
        )

    return {"message": f"Добавлено {len(df)} пользователей"}


@app.get("/requests/{request_type}")
async def get_requests(request_type: str, status: str = None):
    """Получение заявок с фильтрацией"""
    requests = await db.get_requests_by_type(request_type, status)
    return requests