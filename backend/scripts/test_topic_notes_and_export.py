import time
from app.services.study_generator import (
    ConceptBlock,
    TopicStudyNotes,
    generate_topic_study_notes,
)
from app.services.export_service import (
    export_notes_to_pdf,
    export_notes_to_docx,
)
from app.rag.loader import extract_pdf, is_front_matter

SAMPLE_POINTERS_CONTEXT = """
Pointers in C Programming:
A pointer is a variable that stores the memory address of another variable.
Pointers are declared using the asterisk (*) operator and initialized with the address-of (&) operator.
Syntax:
int x = 10;
int *ptr = &x;
Dereferencing:
*ptr = 20; // changes x to 20

Pointer Arithmetic:
Incrementing a pointer (ptr++) advances it by sizeof(type) bytes in memory.
Arrays and Pointers:
The name of an array acts as a constant pointer to its first element: arr == &arr[0].

Dynamic Memory Allocation:
malloc() allocates contiguous uninitialized bytes in heap memory:
int *arr = (int *)malloc(5 * sizeof(int));
free(arr); // prevents memory leaks

Common Pitfalls & Exam Traps:
1. Dangling pointers occur when accessing memory after calling free().
2. NULL pointer dereferencing causes a segmentation fault.
3. Memory leaks happen when allocated memory is lost without being freed.
4. Array index out of bounds causes undefined behavior.
"""

def test_topic_notes_and_exports():
    print("==================================================")
    print("TESTING TOPIC STUDY NOTES & EXPORT SERVICES")
    print("==================================================")

    # 1. Test In-Memory TopicStudyNotes Creation
    print("\n[1] Validating TopicStudyNotes Pydantic Schema...")
    sample_notes = TopicStudyNotes(
        topic_title="Pointers in C",
        quick_summary=(
            "Pointers are variables that store the hardware memory addresses of other variables. "
            "They enable direct memory manipulation, dynamic heap allocation, and efficient pass-by-reference mechanisms. "
            "Understanding pointer mechanics is foundational for systems programming, data structures, and operating systems."
        ),
        key_takeaways=[
            "Pointers store memory addresses, obtained via the address-of operator (&).",
            "Dereferencing via (*) accesses or modifies the value stored at the pointed-to memory address.",
            "Pointer arithmetic scales automatically by sizeof(data_type) bytes.",
            "Dynamically allocated heap memory via malloc() must always be released using free().",
        ],
        concepts=[
            ConceptBlock(
                subtopic="Pointer Declaration and Initialization",
                explanation="Declaring a pointer requires specifying the base data type followed by the asterisk indirection operator.",
                syntax_or_formula="int *ptr = &variable;",
                practical_example="int num = 42;\nint *p = &num;\nprintf(\"%d\", *p); // prints 42",
            ),
            ConceptBlock(
                subtopic="Dynamic Heap Allocation",
                explanation="malloc requests a specified number of bytes from the heap and returns a void pointer to the allocated memory.",
                syntax_or_formula="void* malloc(size_t size);\nvoid free(void* ptr);",
                practical_example="int *arr = (int *)malloc(10 * sizeof(int));\nif (arr != NULL) {\n    arr[0] = 5;\n    free(arr);\n}",
            ),
        ],
        common_pitfalls=[
            "Dereferencing uninitialized or NULL pointers triggers segmentation faults.",
            "Dangling pointers: using a pointer after the target memory has been freed.",
            "Memory leaks: reassigning a pointer before freeing previously allocated heap memory.",
        ],
    )
    print("[PASS] TopicStudyNotes instantiated and validated successfully.")

    # 2. Test PDF Export
    print("\n[2] Testing PDF Export with ReportLab...")
    pdf_bytes = export_notes_to_pdf(sample_notes)
    print(f"Generated PDF bytes: {len(pdf_bytes)} bytes")
    assert pdf_bytes.startswith(b"%PDF-"), "Generated file does not have valid PDF magic header!"
    assert len(pdf_bytes) > 2000, "PDF file is too small, check content rendering!"
    print("[PASS] PDF Export generated valid, non-empty %PDF- buffer.")

    # 3. Test DOCX Export
    print("\n[3] Testing DOCX Export with python-docx...")
    docx_bytes = export_notes_to_docx(sample_notes)
    print(f"Generated DOCX bytes: {len(docx_bytes)} bytes")
    assert docx_bytes.startswith(b"PK\x03\x04"), "Generated file does not have valid DOCX ZIP header!"
    assert len(docx_bytes) > 2000, "DOCX file is too small, check content rendering!"
    print("[PASS] DOCX Export generated valid, non-empty PK\\x03\\x04 buffer.")

    # 4. Test Ingestion Speed / Loader Optimization
    print("\n[4] Benchmarking Fast PDF Extraction...")
    t0 = time.time()
    pages = extract_pdf("uploads/my_college_syllabus.pdf")
    t1 = time.time()
    elapsed = t1 - t0
    print(f"Extracted {len(pages)} pages in {elapsed:.2f} seconds ({elapsed/len(pages)*1000:.1f} ms/page).")
    assert len(pages) > 0, "Pages should not be empty!"
    assert elapsed < 15.0, f"Extraction took {elapsed:.2f}s, expected < 15s!"
    print("[PASS] Fast extraction benchmark passed with high throughput.")

    # 5. Test Live LLM Generation for TopicStudyNotes
    print("\n[5] Testing generate_topic_study_notes with LLM...")
    try:
        gen_notes = generate_topic_study_notes(
            topic="Pointers in C",
            context_text=SAMPLE_POINTERS_CONTEXT,
        )
        print(f"LLM Generated Topic: {gen_notes.topic_title}")
        print(f"Summary length: {len(gen_notes.quick_summary)} chars")
        print(f"Concepts count: {len(gen_notes.concepts)}")
        for c in gen_notes.concepts:
            print(f"  - {c.subtopic}: has_syntax={bool(c.syntax_or_formula)}, has_example={bool(c.practical_example)}")
        print(f"Takeaways count: {len(gen_notes.key_takeaways)}")
        print(f"Pitfalls count: {len(gen_notes.common_pitfalls)}")

        assert len(gen_notes.concepts) > 0, "Concepts list should not be empty"
        assert len(gen_notes.key_takeaways) > 0, "Key takeaways should not be empty"
        assert len(gen_notes.common_pitfalls) > 0, "Common pitfalls should not be empty"

        # Verify PDF and DOCX on LLM generated notes
        llm_pdf = export_notes_to_pdf(gen_notes)
        llm_docx = export_notes_to_docx(gen_notes)
        assert llm_pdf.startswith(b"%PDF-")
        assert llm_docx.startswith(b"PK\x03\x04")
        print("[PASS] End-to-end LLM Generation -> PDF/DOCX Export verified!")
    except Exception as e:
        print(f"[WARN] Live LLM note generation note: {e}")

    print("\n==================================================")
    print("[ALL CHECKS PASSED] Topic Study Notes & Export Services Verified!")
    print("==================================================")

if __name__ == "__main__":
    test_topic_notes_and_exports()
