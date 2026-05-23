from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from config import QDRANT_URL
from infrastructure.logger import logger

qdrant = QdrantClient(url=QDRANT_URL)
MEMORY_COLLECTION = "chat_memory"

async def init_qdrant():
    """Ensure the memory collection exists on boot."""
    if not qdrant.collection_exists(MEMORY_COLLECTION):
        logger.info(f"🗄️ Creating Qdrant collection: {MEMORY_COLLECTION}")
        qdrant.create_collection(
            collection_name=MEMORY_COLLECTION,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )

async def get_memory(chat_id: int) -> list:
    """Retrieve user chat history from Qdrant."""
    try:
        # Retrieve by specific ID
        records = qdrant.retrieve(collection_name=MEMORY_COLLECTION, ids=[chat_id])
        if records:
            return records[0].payload.get("history", [])
    except Exception as e:
        logger.error(f"Failed to fetch memory for {chat_id}: {e}")
    return []

async def save_memory(chat_id: int, history: list):
    """Backup user chat history to Qdrant."""
    qdrant.upsert(
        collection_name=MEMORY_COLLECTION,
        points=[
            PointStruct(
                id=chat_id, 
                vector=[1.0], 
                payload={"history": history}
            )
        ]
    )
