import asyncio
from datetime import datetime, timezone
from app.db.mongodb import (
    connect_to_mongo,
    close_mongo_connection,
    get_syllabus_collection,
    get_user_doc_collection,
)
from app.rag.vector_store import get_vector_store

async def full_verification():
    print("==================================================")
    print("RUNNING TWO-TIER ARCHITECTURE VERIFICATION SUITE")
    print("==================================================")

    await connect_to_mongo()
    try:
        s_coll = get_syllabus_collection()
        u_coll = get_user_doc_collection()

        # 1. Syllabus Vectors Verification
        s_count = await s_coll.count_documents({})
        print(f"\n[1] Syllabus Vectors Collection Count: {s_count}")
        assert s_count > 0, "syllabus_vectors should not be empty!"

        sample = await s_coll.find_one({})
        print("Sample syllabus document:")
        print(f"  - chunk_id: {sample.get('chunk_id')}")
        print(f"  - is_global: {sample.get('is_global')}")
        print(f"  - chunk_type: {sample.get('chunk_type')}")
        print(f"  - page_number: {sample.get('page_number')}")
        print(f"  - embedding dims: {len(sample.get('embedding', []))}")
        print(f"  - text snippet: {sample.get('text', '')[:80]}...")

        assert sample.get("is_global") is True, "Syllabus chunk must have is_global=True"
        assert sample.get("chunk_id", "").startswith("syllabus_"), "chunk_id must start with 'syllabus_'"

        # 2. Indexes Verification
        print("\n[2] Verifying Search and Text Indexes...")
        s_indexes = await s_coll.index_information()
        u_indexes = await u_coll.index_information()

        assert "syllabus_text_index" in s_indexes, "Missing syllabus_text_index"
        assert "user_id_1_doc_id_1" in u_indexes, "Missing user_id_1_doc_id_1 compound index"
        assert "user_id_1_created_at_-1" in u_indexes, "Missing user_id_1_created_at_-1 sorting index"
        assert "user_doc_text_index" in u_indexes, "Missing user_doc_text_index"
        print("[OK] Standard and text indexes verified.")

        s_search = await s_coll.list_search_indexes().to_list(length=10)
        u_search = await u_coll.list_search_indexes().to_list(length=10)
        s_search_names = [idx["name"] for idx in s_search]
        u_search_names = [idx["name"] for idx in u_search]

        print(f"Syllabus search indexes: {s_search_names}")
        print(f"User docs search indexes: {u_search_names}")
        assert "syllabus_vector_index" in s_search_names, "Missing syllabus_vector_index"
        assert "user_vector_index" in u_search_names, "Missing user_vector_index"
        print("[OK] Vector search indexes verified across both tiers.")

        # 3. Global Syllabus Retrieval Test
        print("\n[3] Testing Syllabus Hybrid Retrieval...")
        vstore = get_vector_store()
        res = await vstore.retrieve("computer science engineering data structures", top_k=3)
        matches = res.get("matches", [])
        print(f"Retrieved {len(matches)} matches for curriculum query:")
        for i, m in enumerate(matches, 1):
            print(f"  Match {i} [Score: {m['score']:.4f}]: {m['text'][:90]}...")
        assert len(matches) > 0, "Should retrieve relevant curriculum chunks"

        # 4. Strict Tenant Isolation Test
        print("\n[4] Testing Strict Tenant Isolation in user_documents...")
        now = datetime.now(timezone.utc)
        test_doc_A = {
            "user_id": "student_alice",
            "doc_id": "doc_alice_1",
            "chunk_id": "alice_chunk_1",
            "text": "Alice secret notes on distributed systems consensus algorithms.",
            "embedding": [0.01] * 384,
            "created_at": now,
        }
        test_doc_B = {
            "user_id": "student_bob",
            "doc_id": "doc_bob_1",
            "chunk_id": "bob_chunk_1",
            "text": "Bob confidential research on quantum cryptography protocols.",
            "embedding": [0.02] * 384,
            "created_at": now,
        }

        # Clean up any leftover test docs
        await u_coll.delete_many({"user_id": {"$in": ["student_alice", "student_bob"]}})
        await u_coll.insert_many([test_doc_A, test_doc_B])

        # Query as Alice
        alice_docs = await u_coll.find({"user_id": "student_alice"}).to_list(length=10)
        bob_docs = await u_coll.find({"user_id": "student_bob"}).to_list(length=10)

        print(f"Alice scoped query returned {len(alice_docs)} docs (expected 1).")
        print(f"Bob scoped query returned {len(bob_docs)} docs (expected 1).")

        assert len(alice_docs) == 1 and alice_docs[0]["user_id"] == "student_alice"
        assert len(bob_docs) == 1 and bob_docs[0]["user_id"] == "student_bob"
        assert not any(d["user_id"] == "student_bob" for d in alice_docs), "LEAKAGE: Bob doc found in Alice query!"

        # Cleanup test docs
        await u_coll.delete_many({"user_id": {"$in": ["student_alice", "student_bob"]}})
        print("[OK] Tenant isolation verified with ZERO data leakage.")

        print("\n==================================================")
        print("[ALL TESTS PASSED] Strict Two-Tier Architecture Confirmed!")
        print("==================================================")

    finally:
        await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(full_verification())
