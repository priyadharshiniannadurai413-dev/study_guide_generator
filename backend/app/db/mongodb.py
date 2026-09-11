import logging
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.operations import SearchIndexModel
from app.core.config import settings

# Setup Logger (Critical for Cloud Debugging)
logger = logging.getLogger("uvicorn")


class Database:
    client: AsyncIOMotorClient = None


db_instance = Database()


def get_database_client():
    return db_instance.client


def get_syllabus_collection():
    """Return Motor async collection for global college syllabus vectors (syllabus_vectors)."""
    if db_instance.client is None:
        return None
    db_name = getattr(settings, "DB_NAME", None) or "Chatbot"
    return db_instance.client[db_name]["syllabus_vectors"]


def get_vector_collection():
    """Backward-compatible alias pointing to the global syllabus collection."""
    return get_syllabus_collection()


def get_user_doc_collection():
    """Return Motor async collection for user-uploaded documents (user_documents)."""
    if db_instance.client is None:
        return None
    db_name = getattr(settings, "DB_NAME", None) or "Chatbot"
    return db_instance.client[db_name]["user_documents"]


def get_embedding_dimension() -> int:
    """Resolve embedding dimension dynamically or fall back to 768."""
    dim_env = os.getenv("EMBEDDING_DIMENSION")
    if dim_env and dim_env.isdigit():
        return int(dim_env)
    try:
        from app.rag.embedding import get_embedder
        return len(get_embedder().embed_query("test"))
    except Exception:
        return 768


async def init_db_indexes() -> None:
    """
    Initialize all indexes across the two-tier MongoDB Atlas schema:
    1. syllabus_vectors (Global college syllabus):
       - Text index on 'text' for BM25/keyword search
       - Atlas Vector Search index on 'embedding' (e.g. 768 dimensions, cosine)
    2. user_documents (Strictly tenant-isolated student uploads):
       - Compound index on (user_id, doc_id)
       - Compound sorting index on (user_id, created_at)
       - Text index on 'text'
       - Atlas Vector Search index on 'embedding' with pre-filters on user_id and doc_id
    """
    if db_instance.client is None:
        logger.warning("[MongoDB] Client not connected. Cannot initialize indexes.")
        return

    dim = get_embedding_dimension()

    # -------------------------------------------------------------
    # 1. Tier 1: syllabus_vectors (Global College Syllabus)
    # -------------------------------------------------------------
    try:
        s_coll = get_syllabus_collection()
        if s_coll is not None:
            # Text index for BM25 keyword search
            s_indexes = await s_coll.index_information()
            if "syllabus_text_index" not in s_indexes:
                await s_coll.create_index([("text", "text")], name="syllabus_text_index")
                logger.info("[MongoDB] Created 'syllabus_text_index' on syllabus_vectors.")

            # Atlas Vector Search index on 'embedding'
            try:
                existing_s_search = await s_coll.list_search_indexes().to_list(length=100)
                s_search_names = [idx.get("name") for idx in existing_s_search]
                if "syllabus_vector_index" not in s_search_names:
                    s_definition = {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": dim,
                                "similarity": "cosine",
                            }
                        ]
                    }
                    await s_coll.create_search_index(
                        SearchIndexModel(
                            definition=s_definition,
                            name="syllabus_vector_index",
                            type="vectorSearch",
                        )
                    )
                    logger.info(f"[MongoDB] Created Atlas Vector Search index 'syllabus_vector_index' ({dim} dims).")
            except Exception as s_search_err:
                logger.info(f"[MongoDB] Vector search index notice on syllabus_vectors: {s_search_err}")
    except Exception as exc:
        logger.warning(f"[MongoDB] Could not ensure syllabus_vectors indexes: {exc}")

    # -------------------------------------------------------------
    # 2. Tier 2: user_documents (User-Uploaded Documents)
    # -------------------------------------------------------------
    try:
        u_coll = get_user_doc_collection()
        if u_coll is not None:
            # Compound and sorting indexes
            u_indexes = await u_coll.index_information()
            await u_coll.create_index([("user_id", 1), ("doc_id", 1)])
            await u_coll.create_index([("user_id", 1), ("created_at", -1)])

            # Text index
            if "user_doc_text_index" not in u_indexes:
                await u_coll.create_index([("text", "text")], name="user_doc_text_index")
                logger.info("[MongoDB] Created 'user_doc_text_index' on user_documents.")

            # Atlas Vector Search index with pre-filters for user_id and doc_id
            try:
                existing_u_search = await u_coll.list_search_indexes().to_list(length=100)
                u_search_names = [idx.get("name") for idx in existing_u_search]
                if "user_vector_index" not in u_search_names:
                    u_definition = {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": dim,
                                "similarity": "cosine",
                            },
                            {
                                "type": "filter",
                                "path": "user_id",
                            },
                            {
                                "type": "filter",
                                "path": "doc_id",
                            },
                        ]
                    }
                    await u_coll.create_search_index(
                        SearchIndexModel(
                            definition=u_definition,
                            name="user_vector_index",
                            type="vectorSearch",
                        )
                    )
                    logger.info(f"[MongoDB] Created Atlas Vector Search index 'user_vector_index' ({dim} dims with user_id/doc_id filters).")
            except Exception as u_search_err:
                logger.info(f"[MongoDB] Vector search index notice on user_documents: {u_search_err}")
    except Exception as exc:
        logger.warning(f"[MongoDB] Could not ensure user_documents indexes: {exc}")


async def ensure_user_doc_indexes() -> None:
    """Backward compatibility alias calling init_db_indexes()."""
    await init_db_indexes()


async def connect_to_mongo():
    mongo_url = getattr(settings, "MONGODB_URL", None) or getattr(settings, "MONGODB_URI", None)
    if not mongo_url:
        logger.info("ℹ️ MONGODB_URL is not set. Skipping MongoDB connection.")
        return

    try:
        logger.info("⏳ Connecting to MongoDB...")
        db_instance.client = AsyncIOMotorClient(mongo_url)

        # THE PING TEST (Crucial for Cloud)
        await db_instance.client.admin.command("ping")
        logger.info("✅ MongoDB Connected Successfully!")

        # Ensure all database indexes across both tiers
        await init_db_indexes()
    except Exception as e:
        logger.error(f"❌ MongoDB Connection Failed: {e}")
        raise e


async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("🔒 MongoDB connection closed.")


__all__ = [
    "Database",
    "db_instance",
    "get_database_client",
    "get_syllabus_collection",
    "get_user_doc_collection",
    "get_vector_collection",
    "init_db_indexes",
    "ensure_user_doc_indexes",
    "connect_to_mongo",
    "close_mongo_connection",
]


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    try:
        asyncio.run(connect_to_mongo())
    finally:
        asyncio.run(close_mongo_connection())

