"""
app/routes/documents.py
------------------------
FastAPI router for user PDF document uploads, catalog listing, and deletion.

Prefix: /api/documents
Strictly scoped to the authenticated Clerk user (`current_user["sub"]`).
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.db.mongodb import get_user_doc_collection
from app.rag.user_doc_service import process_user_pdf

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="PDF document to ingest"),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload and ingest an arbitrary user PDF (lecture notes, textbook, question bank).

    Validates:
    - MIME type / file extension is PDF
    - File size is within 25MB limit

    Stores embeddings in `user_documents` partitioned strictly by `user_id`.
    """
    user_id = current_user["sub"]

    # 1. Validate file format
    filename = file.filename or "uploaded_document.pdf"
    content_type = file.content_type or ""
    if content_type and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only application/pdf is supported.",
        )
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents (.pdf) are supported.",
        )

    # 2. Read and validate file size and PDF header
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 25MB (size: {len(file_bytes) / (1024 * 1024):.1f}MB).",
        )

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file: Not a valid PDF document.",
        )

    # 3. Ingest PDF and compute embeddings
    try:
        summary = await process_user_pdf(
            file_bytes=file_bytes,
            filename=filename,
            user_id=user_id,
        )
        return {
            "message": "Document uploaded and indexed successfully.",
            "doc_id": summary["doc_id"],
            "filename": summary["filename"],
            "total_chunks": summary["total_chunks"],
        }
    except ValueError as val_err:
        logger.warning(f"[DocumentsRoute] Validation error for user {user_id}: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"[DocumentsRoute] Document ingestion failed for user {user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {exc}",
        )


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", include_in_schema=False)
async def list_user_documents(
    current_user: dict = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    List all uploaded documents for the authenticated user, grouped by `doc_id`.
    Shows filename, creation timestamp, and chunk count.
    """
    user_id = current_user["sub"]
    collection = get_user_doc_collection()
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection is unavailable.",
        )

    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$doc_id",
                "filename": {"$first": "$filename"},
                "created_at": {"$first": "$created_at"},
                "chunk_count": {"$sum": 1},
            }
        },
        {"$sort": {"created_at": -1}},
    ]

    cursor = collection.aggregate(pipeline)
    raw_docs = await cursor.to_list(length=200)

    documents = []
    for doc in raw_docs:
        created_at = doc.get("created_at")
        created_str = created_at.isoformat() if created_at else None
        documents.append({
            "doc_id": doc["_id"],
            "filename": doc.get("filename", "Untitled"),
            "created_at": created_str,
            "chunk_count": doc.get("chunk_count", 0),
        })

    return documents


@router.delete("/{doc_id}")
async def delete_user_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Delete all chunks associated with `doc_id` belonging strictly to `current_user`.
    Prevents unauthorized deletion of another user's documents.
    """
    user_id = current_user["sub"]
    collection = get_user_doc_collection()
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection is unavailable.",
        )

    result = await collection.delete_many({"user_id": user_id, "doc_id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    logger.info(f"[DocumentsRoute] Deleted {result.deleted_count} chunks for doc_id={doc_id}, user={user_id}")
    return {
        "message": "Document deleted successfully.",
        "doc_id": doc_id,
        "deleted_chunks": result.deleted_count,
    }
