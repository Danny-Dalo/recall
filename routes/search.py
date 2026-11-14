from fastapi import APIRouter
from fastapi import Cookie, APIRouter, Form


import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries


from services.embed import embed_user_search
from services.search import semantic_search, keyword_search

from config import settings


database_url = settings.database_url
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



    
    embedded_query = embed_user_search(query)
    

    
    semantic_search_results = semantic_search(embedded_query, document_id)
    keyword_search_results = keyword_search(query=query, document_id=document_id)

    search_details = {
        "query" : query,
        "session_id" : session_id,
        "document_id" : document_id
    }

    search_results = [{**search_details, **result} for result in semantic_search_results]

    return (semantic_search_results,{}, {}, {}, {}, keyword_search_results)









