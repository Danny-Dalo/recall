
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries


from dotenv import load_dotenv
from openai import OpenAI


from routes import upload, search



load_dotenv()
client = OpenAI()
database_url = os.getenv("DATABASE_URL")


pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"

app = FastAPI()
app.include_router(upload.upload_router)
app.include_router(search.search_router)


import secrets
@app.get("/")
def home(request : Request) -> HTMLResponse:

    
    session_id = request.cookies.get("session_id") # has to match name of the set cookie
    if not session_id:
        session_id = secrets.token_urlsafe(32)


    content = f"""
                <body>
                <form action="/upload" enctype="multipart/form-data" method="post">
                <input name=file type="file">
                <input type="submit">
                </form>
    
                <form action = "/search" method="post">
                <label>search chat:</label>
                <input type="text" name="query">
                <input type="submit">
                </form>
    
                <p>session id is: {session_id}</p>
                </body>
            """

    response = HTMLResponse(content=content)
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


