from typing import Annotated
from fastapi import UploadFile, File, Cookie, APIRouter
import re
import os




import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries
from pgvector.psycopg import register_vector


from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


database_url = os.getenv("DATABASE_URL")
client = OpenAI()


pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"


upload_router = APIRouter()


@upload_router.post("/upload")
async def upload_file(
    file : Annotated[UploadFile, File()] = None,
    session_id : str = Cookie(default=None)):

    if not file:
        return {"message" : "no file has been uploaded", "session_id" : session_id}
    if not file.filename.endswith(".txt"):
        return {
            "error" : "Invalid file type",
            "message" : "only .txt files accepted"
        }

    try:
        read_file = await file.read()
        chat_string = read_file.decode("utf-8") # decode bytes to regular string
    except UnicodeDecodeError:
        return {
            "error" : "Couldn't read file",
            "message" : "The uploaded document does not appear to be a valid WhatsApp chat export."
        }
    
    
        
    # Returns a list of tuples that match the regex pattern
    text_blocks = re.findall(pattern, chat_string, re.DOTALL)
    if not text_blocks:
        return {
            "error" : "Invalid File",
            "message": "The uploaded document does not appear to be a valid WhatsApp chat export."
        }
    # NOTE it is seen as list of lists in response because JSON does not recognize tuples


    chat = []   # a list of dictionaries
    keys = ["date", "time", "sender", "message"]    # matching the returned patterns
    for index, text in enumerate(text_blocks):
            
        message_details = dict(zip(keys, text))
        message_details["message_id"] = index

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



    chunks_to_embed = chunk_chat(
        session_id=db_session_id,
        document_id=db_document_id, 
        chat=chat
        )
    
    embed_chunks(chunks_to_embed)


    return chunks_to_embed
















def chunk_chat(session_id : str, 
               document_id : int | None = None, 
               chat : list[tuple] = None) -> list[dict]:

    messages = [f"{data["sender"]}: {data["message"]}" for data in chat]
    chunks_to_embed = []

    chunk_overlap = 2
    chunk_size = 5
    step_size = chunk_size - chunk_overlap

    # overlap of 2 for each chunk of 5
    for index, chunk_slice in enumerate(range(0, len(messages), step_size)):
        chunk = messages[chunk_slice: chunk_slice + chunk_size]

        chunks_to_embed.append({
            "session_id" : session_id,
            "document_id" : document_id,
            "chunk_id": index,
            "messages": chunk,
            # "message_id_list": list(range(chunk_slice, chunk_slice + len(chunk)))
        })


    return chunks_to_embed



"""Takes is document id and chunks to be embedded from the upload endpoint"""
def embed_chunks(chunks_to_embed : list[dict]):
    if not chunks_to_embed:
        return []

    message_chunks = ["\n".join(data["messages"]) for data in chunks_to_embed]

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input = message_chunks
    )

    # a list of sorted Embeddings() onbjects
    embeddings = sorted(response.data, key=lambda item : item.index)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        register_vector(conn)

        for chunk, embedding in zip(chunks_to_embed, embeddings):
            
            conn.execute("""
            INSERT INTO message_chunks(document_id, chunk_id, embeddings, messages)
            VALUES (%s, %s, %s, %s)
        """, params=(chunk["document_id"], chunk["chunk_id"], embedding.embedding, chunk["messages"]))

        
