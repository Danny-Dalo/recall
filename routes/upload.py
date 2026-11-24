import re
from datetime import datetime

from typing import Annotated

from fastapi import UploadFile, File
from fastapi import HTTPException, status
from fastapi import Cookie, APIRouter

import psycopg
from psycopg.rows import dict_row   # tells database to return query as dictionaries


from openai import OpenAI
from config import settings

from services.embed import chunk_chat, embed_chunks



client = OpenAI()
upload_router = APIRouter()
database_url = settings.database_url


chat_pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"




@upload_router.post("/upload")
async def upload_file(
    file : Annotated[UploadFile, File()] = None,
    session_id : str = Cookie(default=None)):

    if not file:
        raise HTTPException(
            status_code=404,
            detail="No file uploaded"
        )
    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=415,
            detail="Invalid file type"
        )

    try:
        read_file = await file.read()
        chat_string = read_file.decode("utf-8") # decode bytes to regular string
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="Couldn't read file. Make sure to upload a valid WhatsApp chat export."
        )
    
    
    # Returns a list of tuples that match the regex pattern
    text_blocks = re.findall(chat_pattern, chat_string, re.DOTALL)
    if not text_blocks:
        raise HTTPException(
                    status_code=422,
                    detail="Couldn't read file. Make sure to upload a valid WhatsApp chat export."
        )
    # NOTE it is seen as list of lists in response because JSON does not recognize tuples


    chat = []   # a list of dictionaries
    keys = ["date", "time", "sender", "message"]    # matching the returned patterns
    for index, text in enumerate(text_blocks):
            
        message_details = dict(zip(keys, text))
        message_details["message_id"] = index

        message_details["date_time"] = datetime.strptime(
            f"{message_details["date"]} {message_details["time"]}",
            "%m/%d/%y %I:%M:%S %p"
        )

        chat.append(message_details)

    
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        workspace_session = conn.execute(f"""
        SELECT * FROM workspace
        WHERE session_id = '{session_id}'
        """).fetchall()
        

        if not workspace_session:
            return "Session not found"

        
        cursor = conn.execute("""
                WITH new_document as (
                INSERT INTO chat_documents(session_id, filename)
                VALUES(%s, %s)
                RETURNING id, session_id
                )
                SELECT id, session_id FROM new_document
            """, params = (session_id, file.filename,)).fetchone()
        db_document_id = cursor["id"]
        db_session_id = cursor["session_id"]    # same session_id in cookie. accessed through database instead

        for chat_message in chat:
            conn.execute("""
            INSERT INTO chat_messages(
            document_id, message_id,
            date_time, sender, message)
            VALUES (%s, %s, %s, %s, %s)
            """, params = (
                db_document_id,
                chat_message["message_id"],
                chat_message["date_time"],
                chat_message["sender"],
                chat_message["message"]
            ))



    chunks_to_embed = chunk_chat(
        session_id=db_session_id,
        document_id=db_document_id, 
        chat=chat
        )
    
    embed_chunks(chunks_to_embed)


    return chat




