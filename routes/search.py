from fastapi import APIRouter
from fastapi import Cookie, APIRouter, Form
import os




import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries
from pgvector.psycopg import register_vector


from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


database_url = os.getenv("DATABASE_URL")
client = OpenAI()



search_router = APIRouter()



@search_router.post("/search")
async def search_message(
        document_id : int,
        query : str = Form(media_type="multipart/form-data"),
        session_id : str = Cookie(default=None)):

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        # CTEs dont have IDs of their own, we return the referenced table's id for that
        cursor = conn.execute("""
            WITH search_document AS (
            SELECT * FROM chat_documents
            WHERE session_id = %s
            AND id = %s
            )

            SELECT document_id, chunk_id, messages FROM message_chunks
            WHERE document_id IN (SELECT id FROM search_document)
            """, params = (session_id,document_id)).fetchall()

        if not cursor:
            return f"Document does not exist for this session"


        # cursor = [{key : value for key, value in result.items() if key!="embeddings"} for result in cursor]
        # return cursor


    
    embedded_query = embed_user_search(query)
    

    
    semantic_search_results = semantic_search(embedded_query, document_id)
    search_details = {
        "query" : query,
        "session_id" : session_id,
        "document_id" : document_id
    }

    search_results = [{**search_details, **result} for result in semantic_search_results]

    return search_results







def embed_user_search(query : str):
    query_response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = query
    )

    embedded_query = query_response.data[0].embedding

    return embedded_query



def semantic_search(embedded_query, document_id):
    
    
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        
        register_vector(conn)
        

        # cosine distance range (0 to 2).   cosine similarity range (-1 to 1)
        cursor = conn.execute("""
        WITH similarity_scores AS(
                SELECT chunk_id, document_id, messages, 1 - (%s::vector <=> embeddings) as similarity
                FROM message_chunks
                WHERE document_id = %s
                )
                SELECT * FROM similarity_scores
                ORDER by similarity DESC
                LIMIT 10
            """, params=(embedded_query, document_id)).fetchall()

    
        
    return cursor

    

