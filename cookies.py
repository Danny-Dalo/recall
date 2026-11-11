from fastapi import FastAPI, Cookie, Response
from typing import Literal
from pydantic import BaseModel
import secrets, json


app = FastAPI()

allowed_themes = Literal["light", "dark", "grey", "blue"]

class CookieResponse(BaseModel):
    theme : allowed_themes
    name : str | None = None


sessions = {}

@app.get("/set-theme")
def set_theme(name : str, theme : allowed_themes, response : Response) -> CookieResponse:

    session_id = secrets.token_urlsafe(32)

    sessions[session_id] = {
        "name" : name,
        "theme" : theme
    }

    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly = True,
        secure = True,
        samesite="lax",
        max_age=15
    )

    print(sessions)



    return CookieResponse(
        theme=theme,
        name=name
    )





@app.get("/my-theme")
def get_theme(session_id : str = Cookie(default=None)):
    user_data = sessions.get(session_id)
    
    if not session_id:
        return "session not found"

    if not user_data:
        return "data not found"

    

    return f"Hi {user_data["name"]}, your theme is {user_data["theme"]}"
    



@app.get("/")
def home():
    return {"message" : "hello"}