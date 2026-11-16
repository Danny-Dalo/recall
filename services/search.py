
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

from config import settings

database_url = settings.database_url


def semantic_search(embedded_query, document_id) -> list[dict]:
    
    
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        
        register_vector(conn)
        

        # cosine distance range (0 to 2).   cosine similarity range (-1 to 1)
        cursor = conn.execute("""
        WITH similarity_scores AS(
                SELECT document_id, chunk_id, messages, 1 - (%s::vector <=> embeddings) as similarity
                FROM message_chunks
                WHERE document_id = %s
                )
                SELECT * FROM similarity_scores
                ORDER by similarity DESC
                LIMIT 10
            """, params=(embedded_query, document_id)).fetchall()

    
        
    return cursor


def keyword_search(query, document_id) -> list[dict]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        # register_vector(register_vector)

        cursor = conn.execute("""
            SELECT document_id, chunk_id, messages, ts_rank_cd(
                messages_vector, tsquery
            ) AS keyword_score

            FROM message_chunks, websearch_to_tsquery('english', replace(%s, ' ', ' OR ')) AS tsquery

            WHERE document_id = %s
            AND tsquery @@ messages_vector

            ORDER BY keyword_score DESC
            LIMIT 10
            """, params=(query, document_id)).fetchall()


    return cursor




