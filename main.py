from typing import Annotated
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import re

import os

import pgvector, psycopg




database_url = os.getenv("DATABASE_URL")


pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"

app = FastAPI()


@app.post("/upload")
async def upload_file(file : Annotated[UploadFile, File()] = None):
    if not file:
        return {"message" : "no file has been uploaded"}
    else:
        read_file = await file.read()
        chat_string = read_file.decode("utf-8") # decode bytes to regular string
        

        text_blocks = re.findall(pattern, chat_string, re.DOTALL)
        # NOTE findall() returns a list of tuples; it is seen as list of lists in response because JSON does not recognize tuples

        chat = []
        keys = ["date", "time", "sender", "message"]
        for index, text in enumerate(text_blocks, start=1):
            
            message_details = dict(zip(keys, text))
            message_details["message_id"] = index
            
            chat.append(
                message_details
                )

        chunks = chunk_chat(chat)

        
      



            
        return chunks



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



def chunk_chat(chat):

    messages = (f"\n{data["sender"]}: {data["message"]}" for data in chat)
    chunks_to_embed = []
    chunk_info = []

    
    for chunk_slice in range(0, len(messages), 5):
        chunks_to_embed.append(messages[chunk_slice: chunk_slice + 5])

    for index, chunk in enumerate(chunks_to_embed, start=1):
        chunk_info.append({
            "chunk_id" : index,
            "messages" : chunk,
        })




    return chunk_info


