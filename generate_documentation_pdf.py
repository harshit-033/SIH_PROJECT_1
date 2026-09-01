import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PDF = PROJECT_ROOT / "SIH_Local_AI_Workbench_Comprehensive_Documentation.pdf"


class NumberedCanvas(canvas.Canvas):
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
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6b7280"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "SIH Local AI Workbench - Comprehensive Architecture & Technical Specification")
            self.setStrokeColor(colors.HexColor("#e5e7eb"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)

        # Footer (all pages)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 30, page_str)
        self.drawString(54, 30, "CONFIDENTIAL & PROPRIETARY - SIH 2026 LOCAL AI WORKBENCH")
        self.setStrokeColor(colors.HexColor("#e5e7eb"))
        self.setLineWidth(0.5)
        self.line(54, 42, letter[0] - 54, 42)
        
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1e3a8a")  # Dark Blue
    secondary_color = colors.HexColor("#0f766e")  # Teal
    accent_color = colors.HexColor("#7c3aed")  # Purple
    dark_neutral = colors.HexColor("#111827")
    body_color = colors.HexColor("#374151")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=body_color,
        spaceAfter=5,
    )

    body_bold = ParagraphStyle(
        "DocBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=dark_neutral,
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2.5,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.5,
        textColor=dark_neutral,
    )

    table_cell_code = ParagraphStyle(
        "TableCellCode",
        parent=table_cell_style,
        fontName="Courier",
        fontSize=7.2,
        leading=9.5,
    )

    story = []

    # -------------------------------------------------------------
    # Cover / Header Section
    # -------------------------------------------------------------
    story.append(Paragraph("SIH Local AI Workbench", title_style))
    story.append(Paragraph("Comprehensive Technical Documentation, System Architecture, Algorithms & API Specification", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8))

    # Meta table
    meta_data = [
        [
            Paragraph("<b>Project Version:</b> 2.1.0", table_cell_style),
            Paragraph("<b>Deployment Mode:</b> 100% Offline / Local LAN", table_cell_style),
            Paragraph("<b>Target LLM:</b> Ollama llama3.2:latest", table_cell_style),
        ],
        [
            Paragraph("<b>OCR Engine:</b> Tesseract OCR (Local)", table_cell_style),
            Paragraph("<b>Document Engine:</b> PyMuPDF + PIL", table_cell_style),
            Paragraph("<b>Security Model:</b> Multi-Tenant RBAC + Single Admin Session", table_cell_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[170, 170, 164])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 1: Executive Summary (WHAT, WHERE, HOW)
    # -------------------------------------------------------------
    story.append(Paragraph("1. Executive Summary & Core Purpose (What, Where & How)", h1_style))
    story.append(Paragraph(
        "<b>What is the system?</b> The SIH Local AI Workbench is a high-performance, air-gapped, privacy-first local AI platform designed for multi-client document intelligence, optical character recognition (OCR), and conversational AI. It allows connected client devices on a Local Area Network (LAN) or local machine to perform interactive LLM chat and inspect complex native and scanned PDF reports without external internet access or cloud dependencies.",
        body_style
    ))
    story.append(Paragraph(
        "<b>What problem does it solve?</b> Standard enterprise AI tools expose sensitive inspection documents to cloud APIs, incur recurring token fees, and require active internet connectivity. The SIH Local AI Workbench hosts the entire pipeline - from PDF parsing and OCR rasterization to LLM inference and role-based user management - completely on the local host machine.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Where and how does it execute?</b>",
        body_style
    ))
    story.append(Paragraph("- <b>Host Server Tier:</b> Runs on Windows 10/11 with Python 3.10+, Ollama service hosting <code>llama3.2:latest</code>, and Tesseract OCR installed locally. The FastAPI server listens on port 8000.", bullet_style))
    story.append(Paragraph("- <b>Client Tier:</b> Multiple client laptops connect over standard LAN WiFi/Ethernet using any web browser pointing to <code>http://&lt;SERVER-LAN-IP&gt;:8000</code>. No GPUs or AI binaries are needed on client devices.", bullet_style))
    story.append(Paragraph("- <b>Standalone Desktop Mode:</b> Includes a standalone Tkinter desktop GUI (<code>app.py</code>) running directly on the workstation.", bullet_style))
    story.append(Spacer(1, 6))

    # -------------------------------------------------------------
    # Section 2: High-Level Architecture
    # -------------------------------------------------------------
    story.append(Paragraph("2. System Architecture & Multi-Tenant Model", h1_style))
    story.append(Paragraph(
        "The architecture is organized into three decoupled layers: <b>Client Presentation Layer</b>, <b>Server Orchestration & Security Layer</b>, and the <b>Compute & Storage Engine</b>.",
        body_style
    ))

    arch_table_data = [
        [Paragraph("<b>Layer</b>", table_header_style), Paragraph("<b>Components & Technologies</b>", table_header_style), Paragraph("<b>Responsibilities & Isolation Boundary</b>", table_header_style)],
        [
            Paragraph("<b>1. Client Layer</b>", table_cell_style),
            Paragraph("- Browser SPA (Vanilla JS + CSS)<br/>- Tkinter Desktop Client (app.py)", table_cell_style),
            Paragraph("Renders chat messages, SSE stream consumer, Admin user/profile management, PDF upload controls. Zero local AI processing.", table_cell_style),
        ],
        [
            Paragraph("<b>2. Server Layer</b>", table_cell_style),
            Paragraph("- FastAPI & Uvicorn<br/>- AuthService & UserStore<br/>- SessionManager & FileHandler<br/>- RequestQueue (Semaphore)", table_cell_style),
            Paragraph("Enforces RBAC (admin vs user), validates session bearer tokens, isolates multi-client session files, serializes LLM inference, and tracks hardware metrics.", table_cell_style),
        ],
        [
            Paragraph("<b>3. Engine Layer</b>", table_cell_style),
            Paragraph("- Ollama (llama3.2:latest)<br/>- PyMuPDF (fitz)<br/>- Tesseract OCR (--psm 6)<br/>- data/users.json & uploads/", table_cell_style),
            Paragraph("Executes offline LLM text generation, parses PDF streams, rasterizes scanned pages to 220 DPI for OCR, and persists encrypted user databases.", table_cell_style),
        ],
    ]
    arch_table = Table(arch_table_data, colWidths=[80, 170, 254])
    arch_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 3.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3.5),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 3: Directory Layout & File Responsibilities
    # -------------------------------------------------------------
    story.append(Paragraph("3. Codebase File Structure & Module Responsibilities", h1_style))
    
    file_map_data = [
        [Paragraph("<b>Directory / File</b>", table_header_style), Paragraph("<b>Module Role</b>", table_header_style), Paragraph("<b>Key Functions & Architectural Role</b>", table_header_style)],
        [
            Paragraph("<b>core/models.py</b>", table_cell_code),
            Paragraph("Data Contracts", table_cell_style),
            Paragraph("Defines <code>UserRole</code>, <code>UserModel</code>, <code>SessionData</code>, <code>DocumentMetadata</code>, <code>AuthToken</code>, and <code>SystemMetrics</code>.", table_cell_style),
        ],
        [
            Paragraph("<b>core/user_store.py</b>", table_cell_code),
            Paragraph("Persistent Database", table_cell_style),
            Paragraph("Thread-safe JSON repository. Handles user CRUD, <code>update_username</code>, <code>update_password_hash</code>, atomic file replace via <code>.tmp</code>.", table_cell_style),
        ],
        [
            Paragraph("<b>core/auth.py</b>", table_cell_code),
            Paragraph("Security & Cryptography", table_cell_style),
            Paragraph("Salted PBKDF2-HMAC-SHA256 (100k rounds), token validation, and single active admin session enforcement.", table_cell_style),
        ],
        [
            Paragraph("<b>core/session_manager.py</b>", table_cell_code),
            Paragraph("Session Store", table_cell_style),
            Paragraph("In-memory multi-tenant state store. Maintains per-session chat history, document bindings, and thread-safe locks.", table_cell_style),
        ],
        [
            Paragraph("<b>core/request_queue.py</b>", table_cell_code),
            Paragraph("Inference Gate", table_cell_style),
            Paragraph("<code>asyncio.Semaphore(1)</code> throttle serializing simultaneous LLM requests to prevent local GPU/CPU thrashing.", table_cell_style),
        ],
        [
            Paragraph("<b>core/file_handler.py</b>", table_cell_code),
            Paragraph("File Security", table_cell_style),
            Paragraph("Sanitizes upload filenames, prevents path traversal (<code>../</code>), isolates uploads in <code>uploads/&lt;session_id&gt;/</code>.", table_cell_style),
        ],
        [
            Paragraph("<b>core/document_service.py</b>", table_cell_code),
            Paragraph("Document Adapter", table_cell_style),
            Paragraph("Connects extraction pipeline to context budgeter and prompts.", table_cell_style),
        ],
        [
            Paragraph("<b>core/monitoring.py</b>", table_cell_code),
            Paragraph("Telemetry", table_cell_style),
            Paragraph("Uses <code>psutil</code> to track CPU percentage, RAM MB, and queue depth.", table_cell_style),
        ],
        [
            Paragraph("<b>core/ai_service.py</b>", table_cell_code),
            Paragraph("Ollama Client", table_cell_style),
            Paragraph("Ollama API client wrapper; checks model health and streams tokens.", table_cell_style),
        ],
        [
            Paragraph("<b>document/extractor.py</b>", table_cell_code),
            Paragraph("Hybrid Extraction Router", table_cell_style),
            Paragraph("Routes pages between native PyMuPDF extraction and Tesseract OCR via text usability heuristics (<code>is_usable_text</code>).", table_cell_style),
        ],
        [
            Paragraph("<b>document/loader.py</b>", table_cell_code),
            Paragraph("Loader & Budgeter", table_cell_style),
            Paragraph("Enforces 25MB / 80-page limits. Implements greedy 14k-char context budgeting and defensive prompt wrapping.", table_cell_style),
        ],
        [
            Paragraph("<b>document/ocr.py</b>", table_cell_code),
            Paragraph("OCR Engine Interface", table_cell_style),
            Paragraph("Auto-discovers Tesseract binary, renders 220 DPI RGB pixmaps, applies <code>--psm 6</code>, and normalizes OCR artifacts.", table_cell_style),
        ],
        [
            Paragraph("<b>server/main.py</b>", table_cell_code),
            Paragraph("REST & SSE API Server", table_cell_style),
            Paragraph("FastAPI endpoints, RBAC dependencies (<code>require_admin</code>), SSE streaming chat, admin profile and user management.", table_cell_style),
        ],
        [
            Paragraph("<b>static/ (html, css, js)</b>", table_cell_code),
            Paragraph("Web UI Client", table_cell_style),
            Paragraph("SPA frontend with dark mode, live telemetry, SSE token rendering, Admin Dashboard, and My Account profile forms.", table_cell_style),
        ],
        [
            Paragraph("<b>app.py</b>", table_cell_code),
            Paragraph("Desktop Workstation", table_cell_style),
            Paragraph("Standalone Tkinter desktop GUI with threaded background Ollama inference.", table_cell_style),
        ],
        [
            Paragraph("<b>run_server.py</b>", table_cell_code),
            Paragraph("Server Launcher", table_cell_style),
            Paragraph("Auto-detects host LAN IP socket and binds Uvicorn to <code>0.0.0.0:8000</code>.", table_cell_style),
        ],
    ]
    file_map_table = Table(file_map_data, colWidths=[120, 105, 279])
    file_map_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(file_map_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 4: Detailed Execution Flows
    # -------------------------------------------------------------
    story.append(Paragraph("4. End-to-End Execution Flows", h1_style))
    
    story.append(Paragraph("Flow 1: Authentication & Single Active Admin Session Envariant", h2_style))
    story.append(Paragraph(
        "1. <b>Login Request:</b> Client submits credentials to <code>POST /api/auth/login</code>.<br/>"
        "2. <b>Verification:</b> <code>AuthService.authenticate()</code> verifies password hash against <code>data/users.json</code>.<br/>"
        "3. <b>Single Admin Session Check:</b> For <code>role=admin</code>, checks <code>user.active_session_token</code>. If a valid unexpired session exists, returns <code>ADMIN_ALREADY_ACTIVE</code> and responds with <code>HTTP 409 Conflict: 'Admin account is already logged in on another system.'</code><br/>"
        "4. <b>Token Generation:</b> If clean, generates 32-byte URL-safe Bearer token, stores active token on admin record, and initializes isolated <code>SessionData</code>.<br/>"
        "5. <b>Logout Invalidation:</b> On <code>POST /api/auth/logout</code>, token is revoked, admin active session is cleared, and session upload directory is deleted.",
        body_style
    ))

    story.append(Paragraph("Flow 2: Admin Profile Self-Management ('My Account')", h2_style))
    story.append(Paragraph(
        "- <b>Username Change (<code>PATCH /api/admin/me</code>):</b> Guarded by <code>require_admin</code>. Validates format (1-50 chars), checks uniqueness across all accounts, updates user record atomically, and syncs active session labels.<br/>"
        "- <b>Password Change (<code>POST /api/admin/me/change-password</code>):</b> Guarded by <code>require_admin</code>. Verifies current password against stored hash, validates confirmation match (min 4 chars), generates new random 16-byte salt + PBKDF2 hash, and invalidates old password immediately for future logins.",
        body_style
    ))

    story.append(Paragraph("Flow 3: PDF Upload, Hybrid Extraction & Local OCR Pipeline", h2_style))
    story.append(Paragraph(
        "1. <b>Validation:</b> Checks file existence, <code>.pdf</code> extension, size &le; 25 MB, pages &le; 80.<br/>"
        "2. <b>Page-by-Page Extraction:</b> For each page, runs <code>extract_page_text()</code>.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;a. Extracts native text with PyMuPDF. Cleans whitespace.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;b. Runs <code>is_usable_text()</code> heuristic. If text &ge; 30 chars and &ge; 12 alphanumeric, creates <code>PageBlock(method='native')</code>.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;c. If below threshold, rasterizes page to 220 DPI RGB pixmap, runs Tesseract OCR (<code>--psm 6</code>), cleans glyph errors, and creates <code>PageBlock(method='ocr')</code>.<br/>"
        "3. <b>Context Budgeting:</b> <code>build_document_context()</code> packs complete page blocks greedily into a 14,000 character budget.<br/>"
        "4. <b>Session Binding:</b> Attaches document extraction and context to client session.",
        body_style
    ))

    story.append(Paragraph("Flow 4: Document Q&A with Request Queue & SSE Streaming", h2_style))
    story.append(Paragraph(
        "1. <b>Prompt Synthesis:</b> Formats prompt injecting strict defensive system directives treating document text as untrusted reference.<br/>"
        "2. <b>Concurrency Throttling:</b> Task is created in <code>RequestQueue</code>. Awaits <code>asyncio.Semaphore(1)</code> to ensure single-worker local GPU/CPU execution.<br/>"
        "3. <b>Token Streaming:</b> <code>AIService.generate_chat_stream()</code> streams tokens from Ollama to FastAPI's <code>StreamingResponse</code> as Server-Sent Events (<code>data: {'token': '...'}</code>).<br/>"
        "4. <b>Completion & Release:</b> Appends final exchange to session history and releases semaphore slot for waiting client requests.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 5: Algorithms & Cryptographic Specifications
    # -------------------------------------------------------------
    story.append(Paragraph("5. Algorithms, Cryptography & Core Heuristics", h1_style))

    algo_data = [
        [Paragraph("<b>Algorithm / Heuristic</b>", table_header_style), Paragraph("<b>Mathematical / Technical Definition</b>", table_header_style), Paragraph("<b>Purpose & Invariant</b>", table_header_style)],
        [
            Paragraph("<b>PBKDF2-HMAC-SHA256</b>", table_cell_style),
            Paragraph("<code>hashlib.pbkdf2_hmac('sha256', pw, salt_16b, 100000)</code><br/>Verification: <code>hmac.compare_digest(k1, k2)</code>", table_cell_code),
            Paragraph("Secure password storage with 100k derivation iterations. Constant-time digest comparison prevents timing attacks.", table_cell_style),
        ],
        [
            Paragraph("<b>Hybrid OCR Router<br/>(is_usable_text)</b>", table_cell_style),
            Paragraph("<code>len(clean) &gt;= 30 and sum(c.isalnum() for c in clean) &gt;= 12</code>", table_cell_code),
            Paragraph("Distinguishes real native text from empty/scanned PDFs to trigger OCR automatically only when necessary.", table_cell_style),
        ],
        [
            Paragraph("<b>OCR Error Normalizer</b>", table_cell_style),
            Paragraph("Regex: <code>(?&lt;=\\d)[O@](?=\\d) -&gt; 0</code><br/>Strips <code>\\ufffd</code> replacement characters.", table_cell_code),
            Paragraph("Eliminates OCR character misclassifications in serial numbers, timestamps, and inspection metrics.", table_cell_style),
        ],
        [
            Paragraph("<b>Context Budgeting</b>", table_cell_style),
            Paragraph("Greedy packing: Limit &le; 14,000 chars (~3,500 tokens). Pack whole page blocks sequentially.", table_cell_style),
            Paragraph("Guarantees complete page context without mid-sentence truncation; prevents LLM context overflow.", table_cell_style),
        ],
        [
            Paragraph("<b>Inference Semaphore</b>", table_cell_style),
            Paragraph("<code>asyncio.Semaphore(max_concurrent=1)</code>", table_cell_code),
            Paragraph("Serializes concurrent client inference to prevent local GPU/CPU thrashing under multi-client load.", table_cell_style),
        ],
        [
            Paragraph("<b>Atomic File Replace</b>", table_cell_style),
            Paragraph("Write to <code>users.json.tmp</code> &rarr; <code>temp_path.replace(target)</code>", table_cell_code),
            Paragraph("Guarantees zero database corruption across server crashes or sudden power loss.", table_cell_style),
        ],
        [
            Paragraph("<b>Single Admin Lock</b>", table_cell_style),
            Paragraph("Reentrant <code>threading.RLock()</code> check-and-set", table_cell_code),
            Paragraph("Enforces <code>valid_active_admin_sessions &le; 1</code> across concurrent login attempts.", table_cell_style),
        ],
    ]
    algo_table = Table(algo_data, colWidths=[110, 180, 214])
    algo_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(algo_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 6: Complete API Specification
    # -------------------------------------------------------------
    story.append(Paragraph("6. Complete REST & Streaming API Specification", h1_style))

    api_data = [
        [Paragraph("<b>Method & Route</b>", table_header_style), Paragraph("<b>Auth Level</b>", table_header_style), Paragraph("<b>Request Body</b>", table_header_style), Paragraph("<b>Response / Status Codes</b>", table_header_style)],
        [Paragraph("<code>GET /health</code>", table_cell_code), Paragraph("Public", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: Status, Ollama & OCR health, metrics", table_cell_style)],
        [Paragraph("<code>GET /api/metrics</code>", table_cell_code), Paragraph("Public", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: CPU %, RAM MB, queue load", table_cell_style)],
        [Paragraph("<code>POST /api/auth/login</code>", table_cell_code), Paragraph("Public", table_cell_style), Paragraph("<code>{username, password}</code>", table_cell_code), Paragraph("<code>200 OK</code> (token, role), <code>401</code>, <code>409</code> (Admin active)", table_cell_style)],
        [Paragraph("<code>POST /api/auth/logout</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: Session revoked & temp files wiped", table_cell_style)],
        [Paragraph("<code>GET /api/auth/me</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: User profile (id, username, role)", table_cell_style)],
        [Paragraph("<code>PATCH /api/admin/me</code>", table_cell_code), Paragraph("Admin Only", table_cell_style), Paragraph("<code>{username}</code>", table_cell_code), Paragraph("<code>200 OK</code>, <code>400</code>, <code>403</code>, <code>409</code> (Duplicate)", table_cell_style)],
        [Paragraph("<code>POST /api/admin/me/change-password</code>", table_cell_code), Paragraph("Admin Only", table_cell_style), Paragraph("<code>{current_pw, new_pw, confirm_pw}</code>", table_cell_code), Paragraph("<code>200 OK</code>, <code>400</code> (Wrong old/mismatch), <code>403</code>", table_cell_style)],
        [Paragraph("<code>GET /api/admin/users</code>", table_cell_code), Paragraph("Admin Only", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: List of users & summary counts, <code>403</code>", table_cell_style)],
        [Paragraph("<code>POST /api/admin/users</code>", table_cell_code), Paragraph("Admin Only", table_cell_style), Paragraph("<code>{username, password}</code>", table_cell_code), Paragraph("<code>200 OK</code>, <code>400</code>, <code>403</code>, <code>409</code> (Conflict)", table_cell_style)],
        [Paragraph("<code>DELETE /api/admin/users/{id}</code>", table_cell_code), Paragraph("Admin Only", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>, <code>400</code> (Self/last-admin guard), <code>403</code>", table_cell_style)],
        [Paragraph("<code>GET /api/session</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: Session mode, messages, active docs", table_cell_style)],
        [Paragraph("<code>POST /api/chat</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("<code>{message, stream: true}</code>", table_cell_code), Paragraph("<code>200 OK</code>: SSE streaming event stream", table_cell_style)],
        [Paragraph("<code>POST /api/documents</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("Multipart: <code>file</code> (.pdf)", table_cell_code), Paragraph("<code>200 OK</code>: Metadata, extraction summary, <code>400</code>", table_cell_style)],
        [Paragraph("<code>GET /api/documents</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: List of uploaded docs in session", table_cell_style)],
        [Paragraph("<code>POST /api/documents/{id}/select</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: Switches active doc, <code>404</code>", table_cell_style)],
        [Paragraph("<code>POST /api/documents/{id}/chat</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("<code>{message, stream: true}</code>", table_cell_code), Paragraph("<code>200 OK</code>: SSE streaming document Q&A", table_cell_style)],
        [Paragraph("<code>POST /api/chat/clear</code>", table_cell_code), Paragraph("Authenticated", table_cell_style), Paragraph("None", table_cell_style), Paragraph("<code>200 OK</code>: Clears chat history", table_cell_style)],
    ]
    api_table = Table(api_data, colWidths=[150, 65, 125, 164])
    api_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(api_table)
    story.append(Spacer(1, 8))

    # -------------------------------------------------------------
    # Section 7: Default Credentials & Test Verification Matrix
    # -------------------------------------------------------------
    story.append(Paragraph("7. Default Credentials & Automated Verification Matrix", h1_style))

    cred_data = [
        [Paragraph("<b>Username</b>", table_header_style), Paragraph("<b>Password</b>", table_header_style), Paragraph("<b>Role</b>", table_header_style), Paragraph("<b>Granted Permissions & Capabilities</b>", table_header_style)],
        [Paragraph("<code>admin</code>", table_cell_code), Paragraph("<code>admin123</code>", table_cell_code), Paragraph("ADMIN", table_cell_style), Paragraph("Admin Dashboard, User CRUD, My Account profile/pw editing, AI Chat & Doc Analysis (Single Active Session).", table_cell_style)],
        [Paragraph("<code>user1</code>", table_cell_code), Paragraph("<code>pass123</code>", table_cell_code), Paragraph("USER", table_cell_style), Paragraph("General AI chat, PDF document analysis, isolated session storage (Multi-client concurrent login enabled).", table_cell_style)],
        [Paragraph("<code>user2</code>", table_cell_code), Paragraph("<code>pass123</code>", table_cell_code), Paragraph("USER", table_cell_style), Paragraph("General AI chat, PDF document analysis, isolated session storage (Multi-client concurrent login enabled).", table_cell_style)],
        [Paragraph("<code>inspector</code>", table_cell_code), Paragraph("<code>sih2026</code>", table_cell_code), Paragraph("USER", table_cell_style), Paragraph("General AI chat, PDF document analysis, isolated session storage (Multi-client concurrent login enabled).", table_cell_style)],
    ]
    cred_table = Table(cred_data, colWidths=[70, 70, 60, 304])
    cred_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), secondary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(cred_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Automated Verification Test Suite Status:</b>", body_bold))
    test_status_data = [
        [Paragraph("<b>Test Suite File</b>", table_header_style), Paragraph("<b>Scope Verified</b>", table_header_style), Paragraph("<b>Status</b>", table_header_style)],
        [Paragraph("<code>tests/test_rbac_auth.py</code>", table_cell_code), Paragraph("19 RBAC tests: bootstrap, login, user creation, deletion, self-guard, last-admin guard", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_admin_profile.py</code>", table_cell_code), Paragraph("10 profile & single-session tests: username/pw change, 409 rejection, concurrent race conditions", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_api_server.py</code>", table_cell_code), Paragraph("API server endpoints, health checks, document selection, clear chat", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_session_isolation.py</code>", table_cell_code), Paragraph("Multi-client data isolation, document privacy, cross-session prevention", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_security_file_handling.py</code>", table_cell_code), Paragraph("Path traversal escapes, corrupted PDF handling, session directory bounds", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_document_workflow.py</code>", table_cell_code), Paragraph("PyMuPDF native extraction, Tesseract OCR rendering, context budgeting", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_concurrency_queue.py</code>", table_cell_code), Paragraph("Inference worker serialization, queue stats, active request limits", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_lan_server_e2e.py</code>", table_cell_code), Paragraph("3 full simulated multi-client LAN E2E interaction cycles", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_demo_runs.py</code>", table_cell_code), Paragraph("3 full demo-equivalent document workflow cycles", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
        [Paragraph("<code>tests/test_app_state.py</code>", table_cell_code), Paragraph("Tkinter desktop client state transitions, queue processing", table_cell_style), Paragraph("<b>100% PASS</b>", table_cell_style)],
    ]
    test_table = Table(test_status_data, colWidths=[160, 260, 84])
    test_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), primary_color),
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 10))

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Documentation PDF successfully generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
