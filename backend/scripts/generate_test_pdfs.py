"""
scripts/generate_test_pdfs.py
-----------------------------
Generates 3 distinct test PDFs to verify:
1. PDF A (Short, 3 pages, no headers or footers at all)
2. PDF B (Long, 16 pages, with repeated running header & footer with dynamic page numbers)
3. PDF C (Mixed formatting, 4 pages, with tables, rubrics, and credit matrices)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


def create_pdf_a(output_path: str):
    """PDF A: 3-page short PDF on Computer Networks with NO headers or footers."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    story = []

    # Page 1: Physical Layer
    story.append(Paragraph("<b>Chapter 1: Physical Layer Fundamentals</b>", styles["Title"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "The physical layer is responsible for the actual transmission of raw bits over a physical communication channel. "
        "Key transmission media include guided media such as unshielded twisted pair (UTP Cat 6), coaxial cabling, and single-mode optical fiber. "
        "Signal attenuation, dispersion, and thermal noise represent fundamental transmission impairments. "
        "The Nyquist theorem dictates the maximum theoretical data rate for a noiseless channel: C = 2B log2(M), "
        "where B represents channel bandwidth in Hertz and M denotes the number of discrete signal levels. "
        "In the presence of thermal noise, Shannon's capacity formula governs the upper theoretical bound: C = B log2(1 + SNR).",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Modulation techniques convert digital bitstreams into analog carrier signals suitable for propagation. "
        "Standard digital modulation schemes comprise Amplitude Shift Keying (ASK), Frequency Shift Keying (FSK), "
        "and Quadrature Phase Shift Keying (QPSK). Constellation diagrams plot in-phase and quadrature components.",
        styles["Normal"]
    ))
    story.append(PageBreak())

    # Page 2: Data Link Layer
    story.append(Paragraph("<b>Chapter 2: Data Link Layer and Medium Access Control</b>", styles["Title"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "The data link layer transforms an unconditioned transmission facility into a reliable communication link between directly connected nodes. "
        "Core functions include framing (bit-stuffing and byte-stuffing flags), flow control, and error detection. "
        "Cyclic Redundancy Checks (CRC-32) employ polynomial modulo-2 arithmetic to detect burst errors with mathematical certainty. "
        "Medium Access Control (MAC) sublayer arbitrates shared transmission media. In Ethernet networks (IEEE 802.3), "
        "Carrier Sense Multiple Access with Collision Detection (CSMA/CD) ensures exponential backoff upon collision detection.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Switches operate at Layer 2, building dynamic MAC address forwarding tables through backward learning of source MAC addresses. "
        "The Spanning Tree Protocol (IEEE 802.1D STP) prevents broadcast storms by disabling redundant network loops.",
        styles["Normal"]
    ))
    story.append(PageBreak())

    # Page 3: Network Layer & Routing
    story.append(Paragraph("<b>Chapter 3: Network Layer and Packet Routing</b>", styles["Title"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "The network layer facilitates end-to-end packet delivery across heterogeneous internetworks. "
        "The Internet Protocol Version 4 (IPv4) utilizes 32-bit hierarchical addresses, extended by Classless Inter-Domain Routing (CIDR). "
        "IPv6 provides a 128-bit address space, eliminating NAT requirements and integrating IPsec natively. "
        "Intra-domain routing relies on Distance Vector protocols (RIP based on Bellman-Ford) and Link State protocols "
        "(OSPF based on Dijkstra's shortest path first algorithm). Inter-domain routing is orchestrated globally by the Border Gateway Protocol (BGP-4), "
        "a path-vector protocol executing policy-based routing across autonomous systems.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Packet forwarding involves Longest Prefix Match lookups against forwarding information bases (FIB), "
        "supported by hardware TCAMs in enterprise routing architectures.",
        styles["Normal"]
    ))

    doc.build(story)
    print(f"[PDF A] Built 3-page short PDF at {output_path}")


class NumberedCanvas(canvas.Canvas):
    """Canvas that prints running headers and footers with total page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#555555"))
        # Running Header
        self.drawString(54, 750, "Distributed Systems Architecture and Consensus Protocols (CS-804)")
        self.setStrokeColor(colors.HexColor("#cccccc"))
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        # Running Footer with changing page number
        self.line(54, 50, 558, 50)
        footer_text = f"Confidential Academic Draft - Department of Computer Science | Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 38, footer_text)
        self.restoreState()


def create_pdf_b(output_path: str):
    """PDF B: 16-page long PDF with running header and footer on EVERY page."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    topics = [
        ("Module 1: Remote Procedure Calls & Interface Definition", 
         "Remote Procedure Calls (RPC) abstract network communication by allowing a computer program to cause a subroutine to execute in a different address space. "
         "Protocol Buffers and gRPC utilize binary serialization over HTTP/2, providing strong typing through an Interface Definition Language (IDL). "
         "Marshaling serializes in-memory object graphs into contiguous wire byte arrays, while unmarshaling deserializes byte streams upon reception."),
        
        ("Module 2: Logical Time and Vector Clocks", 
         "Physical clocks in distributed systems suffer from relativistic drift and quartz oscillator skew. "
         "Leslie Lamport introduced logical clocks governed by the happened-before relation (a -> b). "
         "Vector clocks extend scalar clocks by maintaining a vector of size N, allowing exact identification of concurrent events and causal dependencies across nodes."),
        
        ("Module 3: Distributed Mutual Exclusion", 
         "Distributed mutual exclusion coordinates access to shared resources without centralized state. "
         "The Ricart-Agrawala algorithm requires 2(N-1) messages per critical section entry by broadcasting timestamped request messages. "
         "Maekawa's algorithm uses voting sets of size O(sqrt(N)), significantly reducing network message overhead but introducing potential deadlock scenarios."),
        
        ("Module 4: Leader Election Algorithms", 
         "Leader election identifies a coordinator among identical participating servers. "
         "The Bully algorithm assumes synchronous crash-stop failure detectors, electing the node with the highest process ID with O(N^2) message complexity. "
         "Ring-based elections pass election tokens along an active unidirectional logical ring until the highest identifier circulates completely."),
        
        ("Module 5: The Paxos Consensus Protocol", 
         "Paxos achieves consensus over an asynchronous network subject to crash-recovery faults. "
         "The protocol separates roles into Proposers, Acceptors, and Learners. "
         "Phase 1 (Prepare/Promise) establishes the highest proposal number n, while Phase 2 (Accept/Accepted) commits the value once a majority quorum responds."),
        
        ("Module 6: Raft Distributed Consensus", 
         "Raft decomposes distributed consensus into understandable subproblems: leader election, log replication, and safety invariants. "
         "Servers exist in one of three states: Follower, Candidate, or Leader. "
         "Heartbeat timeouts trigger randomized election timers, avoiding split-vote ties and guaranteeing that any committed entry exists in future leader logs."),
        
        ("Module 7: Byzantine Fault Tolerance (PBFT)", 
         "Practical Byzantine Fault Tolerance operates under arbitrary malicious failure models where nodes can forge or tamper with messages. "
         "PBFT requires 3f + 1 total nodes to tolerate f Byzantine nodes. "
         "Three phases—Pre-Prepare, Prepare, and Commit—ensure view change consensus using cryptographic digital signatures."),
        
        ("Module 8: Consistency Models in Distributed Systems", 
         "Strong consistency guarantees like Linearizability enforce real-time global ordering where every read returns the most recent write. "
         "Sequential consistency relaxes real-time constraints while preserving program order on each individual thread. "
         "Eventual consistency guarantees that in the absence of new updates, all replicas converge to identical state."),
        
        ("Module 9: Amazon Dynamo Architecture", 
         "Dynamo provides high availability for shopping cart workloads using decentralized peer-to-peer techniques. "
         "Consistent hashing with virtual nodes distributes partitions uniformly across commodity servers. "
         "Sloppy quorums (N, R, W) and hinted handoff ensure write availability even during transient network partitions, with vector clocks reconciling conflicting writes."),
        
        ("Module 10: Google Bigtable Storage Engine", 
         "Bigtable is a distributed, multi-dimensional, sorted map indexed by row key, column key, and timestamp. "
         "Tablet servers manage immutable SSTables stored in Google File System (GFS) and maintain in-memory MemTables. "
         "Writes append to an on-disk Write-Ahead Log (WAL) before updating MemTable, while background compactions merge SSTables and remove tombstones."),
        
        ("Module 11: Google Spanner & The TrueTime API", 
         "Spanner is the first globally distributed database providing external consistency and multi-datacenter ACID transactions. "
         "TrueTime API exposes bounded clock uncertainty [earliest, latest] using GPS receivers and atomic rubidium oscillators. "
         "Two-Phase Commit (2PC) over Paxos groups guarantees serializable snapshot isolation globally without centralized lock managers."),
        
        ("Module 12: The CAP Theorem & PACELC Framework", 
         "Eric Brewer's CAP theorem demonstrates that distributed systems cannot simultaneously achieve Consistency, Availability, and Partition Tolerance. "
         "Daniel Abadi's PACELC framework refines this: if there is a Partition (P), how does the system trade off Availability (A) and Consistency (C); "
         "Else (E), how does the system trade off Latency (L) and Consistency (C)?"),
        
        ("Module 13: Conflict-Free Replicated Data Types (CRDTs)", 
         "CRDTs enable concurrent updates on multiple replicas without centralized synchronization while mathematically guaranteeing conflict-free convergence. "
         "State-based CRDTs (CvRDT) transmit full state and merge using join-semilattice operations (idempotent, commutative, associative). "
         "Operation-based CRDTs (CmRDT) stream commutative operations across a reliable causal broadcast channel."),
        
        ("Module 14: Two-Phase Commit & Distributed Transactions", 
         "Atomic commit across multiple independent resource managers requires coordination protocols. "
         "In Two-Phase Commit (2PC), the coordinator broadcasts Prepare; if all participants vote Commit, Phase 2 issues Global Commit. "
         "The fundamental flaw of 2PC is blocking: if the coordinator crashes during Phase 2, participants remain indefinitely locked holding transaction locks."),
        
        ("Module 15: Distributed Stream Processing & Fault Tolerance", 
         "Stream processing systems process unbounded continuous data streams with sub-second latency. "
         "Apache Kafka provides partitioned, immutable commit logs with persistent consumer offsets. "
         "Apache Flink achieves exactly-once state semantics via asynchronous barrier snapshotting (Chandy-Lamport variant), checkpointing operator state to durable storage."),
        
        ("Module 16: Service Mesh Architecture & Observability", 
         "In microservice topologies, a service mesh decouples networking concerns from business logic. "
         "Sidecar proxies (such as Envoy) intercept inbound and outbound L7 traffic, providing mutual TLS (mTLS) authentication, rate limiting, and circuit breaking. "
         "Distributed tracing propagates W3C TraceContext headers across RPC boundaries, aggregating spans to visualize distributed latency bottlenecks.")
    ]

    for idx, (title, content) in enumerate(topics):
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading1"]))
        story.append(Spacer(1, 14))
        story.append(Paragraph(content, styles["Normal"]))
        story.append(Spacer(1, 14))
        story.append(Paragraph(
            f"<b>Architectural Takeaways ({title.split(':')[0]}):</b> Every design decision in distributed systems represents a trade-off "
            "between latency, durability, availability, and algorithmic complexity. Systems engineers must evaluate network partition probability "
            "and failure modes prior to selecting consensus quorums or replication factors.",
            styles["Normal"]
        ))
        if idx < len(topics) - 1:
            story.append(PageBreak())

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF B] Built 16-page long PDF at {output_path}")


def create_pdf_c(output_path: str):
    """PDF C: 4-page PDF with mixed formatting, course syllabus tables, and credit distributions."""
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    story = []

    # Page 1: Course Specification & Overview
    story.append(Paragraph("<b>Department of Computer Science: Capstone Matrix & Syllabus</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This curriculum document outlines the core course requirements, laboratory modules, and evaluation rubrics "
        "for the Senior Capstone Engineering Sequence (CS-490 / CS-491).",
        styles["Normal"]
    ))
    story.append(Spacer(1, 14))
    
    table_data_1 = [
        ["Course Code", "Course Title", "Lecture (Hrs)", "Lab (Hrs)", "Credits"],
        ["CS-490", "Senior Design Project I", "3", "3", "4"],
        ["CS-491", "Senior Design Project II", "1", "6", "4"],
        ["CS-452", "Cloud Computing & DevOps", "3", "2", "4"],
        ["CS-465", "Distributed Algorithms", "3", "0", "3"],
        ["CS-480", "Engineering Ethics & Law", "2", "0", "2"],
    ]
    t1 = Table(table_data_1, colWidths=[80, 180, 80, 70, 60])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
    ]))
    story.append(t1)
    story.append(PageBreak())

    # Page 2: Project Milestones
    story.append(Paragraph("<b>Capstone Deliverables and Architectural Milestones</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Students must execute projects in four-person agile teams. Deliverables include architectural design specifications, "
        "automated CI/CD pipelines, containerized deployment, and exhaustive integration test suites.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    table_data_2 = [
        ["Milestone", "Deliverable Description", "Weight", "Deadline"],
        ["M1: Inception", "Problem formulation, user stories, and system architecture document", "15%", "Week 4"],
        ["M2: Prototype", "Working MVP with containerized microservices and API documentation", "25%", "Week 8"],
        ["M3: Verification", "End-to-end integration tests, load testing, and security audits", "25%", "Week 12"],
        ["M4: Final Defense", "Live deployment, oral examination, and public code repository", "35%", "Week 16"],
    ]
    t2 = Table(table_data_2, colWidths=[80, 230, 60, 80])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#16A085")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(t2)
    story.append(PageBreak())

    # Page 3: Grading Rubric
    story.append(Paragraph("<b>Evaluation Rubrics and Performance Standards</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Evaluation assesses code quality, architectural robustness, documentation rigor, and peer collaboration. "
        "Plagiarism or fabricated benchmarks results in immediate disqualification.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    table_data_3 = [
        ["Performance Level", "Technical Architecture", "Code Quality & Tests", "Team Collaboration"],
        ["Exemplary (90-100%)", "Fault-tolerant, scalable, clear microservices", ">85% branch test coverage, CI passing", "Equal commit distribution, active reviews"],
        ["Proficient (75-89%)", "Well-structured, minor coupling issues", "60-84% test coverage, passing builds", "Consistent participation across team"],
        ["Developing (60-74%)", "Monolithic tendencies, fragile state handling", "<60% test coverage, manual deployments", "Imbalanced contributions, missed standups"],
        ["Unacceptable (<60%)", "Non-functional architecture, missing specs", "No automated tests, broken code", "Dysfunctional collaboration, missing code"],
    ]
    t3 = Table(table_data_3, colWidths=[100, 130, 120, 120])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8E44AD")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(t3)
    story.append(PageBreak())

    # Page 4: Program Learning Outcomes
    story.append(Paragraph("<b>Program Educational Outcomes & Accreditation Compliance</b>", styles["Heading1"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Upon graduation, students demonstrate capability to design complex engineering systems meeting realistic constraints "
        "including economic, environmental, ethical, health and safety, and sustainability considerations. "
        "All teams must archive project artifacts in institutional institutional repositories.",
        styles["Normal"]
    ))

    doc.build(story)
    print(f"[PDF C] Built 4-page table-rich PDF at {output_path}")


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
    os.makedirs(out_dir, exist_ok=True)
    create_pdf_a(os.path.join(out_dir, "test_pdf_a_short.pdf"))
    create_pdf_b(os.path.join(out_dir, "test_pdf_b_long.pdf"))
    create_pdf_c(os.path.join(out_dir, "test_pdf_c_mixed.pdf"))
