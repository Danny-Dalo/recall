import psycopg
from psycopg.rows import dict_row   # tells database to return queries as dictionaries
from pgvector.psycopg import register_vector


from openai import OpenAI
from config import settings

client = OpenAI()
database_url = settings.database_url


pattern = r"\[(\d+/\d+/\d+), (\d+:\d+:\d+ [AP]M)\] (.*?): (.*?)(?=\n\[|\Z)"





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

        




def embed_user_search(query : str):
    query_response = client.embeddings.create(
        model = "text-embedding-3-small",
        input = query
    )

    embedded_query = query_response.data[0].embedding

    return embedded_query
