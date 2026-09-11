import asyncio
from app.db.mongodb import connect_to_mongo, close_mongo_connection, get_syllabus_collection, get_user_doc_collection

async def test_indexes():
    await connect_to_mongo()
    try:
        s_coll = get_syllabus_collection()
        u_coll = get_user_doc_collection()

        s_info = await s_coll.index_information()
        u_info = await u_coll.index_information()

        print("=== SYLLABUS_VECTORS INDEXES ===")
        for name, meta in s_info.items():
            print(f" - {name}: {meta.get('key')}")

        print("\n=== USER_DOCUMENTS INDEXES ===")
        for name, meta in u_info.items():
            print(f" - {name}: {meta.get('key')}")

        try:
            s_search = await s_coll.list_search_indexes().to_list(length=100)
            print("\n=== SYLLABUS_VECTORS SEARCH INDEXES ===")
            for s in s_search:
                print(f" - {s.get('name')}: {s.get('type')}")
        except Exception as e:
            print(f"Syllabus search indexes info: {e}")

        try:
            u_search = await u_coll.list_search_indexes().to_list(length=100)
            print("\n=== USER_DOCUMENTS SEARCH INDEXES ===")
            for u in u_search:
                print(f" - {u.get('name')}: {u.get('type')}")
        except Exception as e:
            print(f"User docs search indexes info: {e}")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_indexes())
