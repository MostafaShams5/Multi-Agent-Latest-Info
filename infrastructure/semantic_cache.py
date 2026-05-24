import uuid
from qdrant_client.models import VectorParams, Distance, PointStruct
from fastembed import TextEmbedding
from infrastructure.qdrant_store import qdrant, aqdrant  # Import the async client
from infrastructure.logger import logger

CACHE_COLLECTION = "semantic_cache"

# FastEmbed is lightweight and standard for semantic search
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

async def init_cache():
    if not qdrant.collection_exists(CACHE_COLLECTION):
        logger.info(f"🗄️ Creating Qdrant Semantic Cache: {CACHE_COLLECTION}")
        qdrant.create_collection(
            collection_name=CACHE_COLLECTION,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

async def check_cache(user_query: str, threshold: float = 0.95) -> str | None:
    """Checks if a mathematically similar question was recently answered."""
    # Convert generator to list
    vector = list(embedding_model.embed([user_query]))[0].tolist()
    
    # Use the async client (aqdrant) to prevent event loop blocking
    response = await aqdrant.query_points(
        collection_name=CACHE_COLLECTION,
        query=vector, 
        limit=1,
        score_threshold=threshold
    )
    
    results = response.points
    if results:
        logger.info(f"⚡ Semantic Cache Hit! Score: {results[0].score}")
        return results[0].payload.get("response")
    return None
    
async def save_to_cache(user_query: str, response: str):
    """Saves a successful LLM response to the vector cache."""
    vector = list(embedding_model.embed([user_query]))[0].tolist()
    
    # Use the async client for upserting
    await aqdrant.upsert(
        collection_name=CACHE_COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()), 
            vector=vector, 
            payload={"query": user_query, "response": response}
        )]
    )
