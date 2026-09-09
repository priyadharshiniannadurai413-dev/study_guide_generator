import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Setup Logger (Critical for Cloud Debugging)
logger = logging.getLogger("uvicorn")


class Database:
    client: AsyncIOMotorClient = None


db_instance = Database()


def get_database_client():
    return db_instance.client


def get_vector_collection():
    db_name = getattr(settings, "DB_NAME", None) or "Chatbot"
    return db_instance.client[db_name]["vector_documents"]


def get_user_doc_collection():
    """Return Motor async collection for user-uploaded documents (user_documents)."""
    db_name = getattr(settings, "DB_NAME", None) or "Chatbot"
    return db_instance.client[db_name]["user_documents"]


async def ensure_user_doc_indexes() -> None:
    """
    Create compound and sorting indexes on user_documents collection.
    Ensures strict per-user isolation and fast filtering by user_id and doc_id.
    """
    try:
        coll = get_user_doc_collection()
        if coll is not None:
            await coll.create_index([("user_id", 1), ("doc_id", 1)])
            await coll.create_index([("user_id", 1), ("created_at", -1)])
            logger.info("[MongoDB] user_documents compound indexes created/verified.")
    except Exception as exc:
        logger.warning(f"[MongoDB] Could not ensure user_documents indexes: {exc}")


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

        # Ensure user document indexes
        await ensure_user_doc_indexes()
    except Exception as e:
        logger.error(f"❌ MongoDB Connection Failed: {e}")
        raise e


async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logger.info("🔒 MongoDB connection closed.")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    try:
        asyncio.run(connect_to_mongo())
    finally:
        asyncio.run(close_mongo_connection())
