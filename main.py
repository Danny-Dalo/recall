from typing import Annotated
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import re

pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*)"

app = FastAPI()


@app.post("/upload")
async def upload_file(file : Annotated[UploadFile, File()] = None):
    if not file:
        return {"message" : "no file has been uploaded"}
    else:
        read_file = await file.read()
        chat_string = read_file.decode("utf-8") # decode bytes to regular string

        text_blocks = re.findall(pattern, chat_string)
        # NOTE findall() returns a list of tuples; it is seen as list of lists in response because JSON does not recognize tuples

        chats = []
        keys = ["date", "time", "sender", "message"]
        for text in text_blocks:
            chats.append(dict(zip(keys, text)))

            
        return chats





@app.get("/")
def home():
    content = """
            <body>
            <form action="/upload" enctype="multipart/form-data" method="post">
            <input name=file type="file">
            <input type="submit">
            </form>
            </body>
        """
    return HTMLResponse(content=content)




