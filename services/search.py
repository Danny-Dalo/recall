import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

from services.embed import embed_user_search

from config import settings

database_url = settings.database_url


def semantic_search(embedded_query, document_id) -> list[dict]:
    
    
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        
        register_vector(conn)
        

        # cosine distance range (0 to 2).   cosine similarity range (-1 to 1)
        semantic_search_result = conn.execute("""
        WITH similarity_scores AS(
                SELECT document_id, chunk_id, messages, 1 - (%s::vector <=> embeddings) as similarity
                FROM message_chunks
                WHERE document_id = %s
                )
                SELECT * FROM similarity_scores
                ORDER by similarity DESC
                LIMIT 10
            """, params=(embedded_query, document_id)).fetchall()

    
        
    return semantic_search_result


def keyword_search(query, document_id) -> list[dict]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        # register_vector(register_vector)

        keyword_search_result = conn.execute("""
            SELECT document_id, chunk_id, messages, ts_rank_cd(
                messages_vector, tsquery
            ) AS keyword_score

            FROM message_chunks, websearch_to_tsquery('english', replace(%s, ' ', ' OR ')) AS tsquery

            WHERE document_id = %s
            AND tsquery @@ messages_vector

            ORDER BY keyword_score DESC
            LIMIT 10
            """, params=(query, document_id)).fetchall()


    return keyword_search_result




"""combine keyword and semantic search results using resiprocal rank fusion"""
def hybrid_search(query, document_id, rrf_k = 60):
    rrf_scores = []

    embedded_query = embed_user_search(query)

    semantic_search_results = semantic_search(embedded_query, document_id)
    keyword_search_results = keyword_search(query, document_id)

    for rank, result in enumerate(semantic_search_results, start=1):
        rrf_scores.append({
        #   "document_id" : result["document_id"],
          "chunk_id" : result["chunk_id"],
          "messages" : result["messages"],
          "semantic_score" : result["similarity"],
          "keyword_score" : 0,
          "rrf_score" : 1 / (rank + rrf_k)
        })

    for rank, result in enumerate(keyword_search_results, start=1):
        score = 1 / (rank + rrf_k)

        for index, chunk in enumerate(rrf_scores):
            if chunk["chunk_id"] == result["chunk_id"]:
                rrf_scores[index]["keyword_score"] = result["keyword_score"]
                rrf_scores[index]["rrf_score"] += score
                break

            
    rrf_scores = sorted(rrf_scores, key=lambda item: item["rrf_score"], reverse=True)
    return rrf_scores






