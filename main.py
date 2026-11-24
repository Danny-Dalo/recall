from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import secrets
import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries


from openai import OpenAI
from config import settings

from routes import upload, search

client = OpenAI()
database_url = settings.database_url



app = FastAPI()

app.mount(path="/static", app=StaticFiles(directory="static"), name="static")

app.include_router(upload.upload_router)
app.include_router(search.search_router)



templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request : Request) -> HTMLResponse:

    
    session_id = request.cookies.get("session_id") # has to match name of the set cookie


    if not session_id:
        session_id = secrets.token_urlsafe(32)


    
    response = templates.TemplateResponse(
        request=request,
        name="main.html"
    )
    
    response.set_cookie(
        key = "session_id",
        value = session_id,
        httponly=True
    )

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute("""
        INSERT INTO workspace(session_id)
        VALUES (%s)
        ON CONFLICT(session_id)
        DO NOTHING
    """, params=(session_id,))


    return response



