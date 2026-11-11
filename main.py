from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Cookie, Request
from fastapi.responses import HTMLResponse
import re
import os
from pydantic import BaseModel


import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries
from pgvector.psycopg import register_vector

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


client = OpenAI()
database_url = os.getenv("DATABASE_URL")


pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"

app = FastAPI()



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




@app.post("/upload")
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
            "message_id_list": list(range(chunk_slice, chunk_slice + len(chunk)))
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

        



# We'll take in submitted html form data
from fastapi import Form
@app.post("/search")
async def search_message(
        document_id : int,
        query : str | None = Form(media_type="multipart/form-data"),
        session_id : str = Cookie(default=None)):
    # print(document_id, session_id)
    print("session_id")
    print(session_id)

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        # CTEs dont have IDs of their own, we return the referenced table's id for that
        cursor = conn.execute("""
            WITH search_document AS (
            SELECT * FROM chat_documents
            WHERE session_id = %s
            AND id = %s
            )

            SELECT document_id, chunk_id FROM message_chunks
            WHERE document_id IN (SELECT id FROM search_document)
            """, params = (session_id,document_id)).fetchall()

        if not cursor:
            return f"Document does not exist for this session"


        cursor = [{key : value for key, value in result.items() if key!="embeddings"} for result in cursor]
        return cursor
        
        # document_ids = conn.execute("""
        #     SELECT * FROM chat_documents
        #     WHERE session_id = %s
        # """, params=(session_id,)).fetchall()

        # chunk_index_list = conn.execute("SELECT document_id, chunk_id FROM message_chunks WHERE document_id = %s", params=(document_id,)).fetchall()
        # if not chunk_index_list:
        #     return "Not Found"



    # embedded_query = embed_user_search(query)
    # semantic_search(embedded_query, document_id)

    # return {
    #     "query" : query,
    #     "session_id" : session_id,
    #     "chunk_index_list" : [item["chunk_id"] for item in chunk_index_list]
    # }
    
    # return {
    #     "query" : query,
    #     "session_id" : session_id,
    #     # "document_id" : document_ids,
    #     "embedded_query" : embedded_query
    # }




def embed_user_search(query : str):
    query_response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = query
    )

    embedded_query = query_response.data[0].embedding

    return embedded_query



def semantic_search(embedded_query, document_id):
    
    
    with psycopg.connect(database_url) as conn:
        register_vector(conn)

        # cosine distance range (0 to 2)
        # cosine similarity range (-1 to 1)
        results = conn.execute("""
        WITH similarity_scores AS(
                SELECT chunk_id, 1 - (%s::vector <=> embeddings) as similarity
                FROM message_chunks
                WHERE document_id = %s
                )
                SELECT * FROM similarity_scores
                ORDER by similarity DESC
                LIMIT 10
            """, params=(embedded_query, document_id)).fetchall()
        
        print(results)










# USE FRONTEND BOYO, MANUALLY TEST WITH THE ID FIRST ON BACKEND