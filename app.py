from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from enum import Enum
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import ollama

from document import (
    DIRECT_ANALYSIS_CHAR_BUDGET,
    ESTIMATED_CHARS_PER_TOKEN,
    MAX_PDF_PAGES,
    MAX_PDF_SIZE_MB,
    DocumentContext,
    DocumentExtraction,
    PageBlock,
    build_document_context,
    build_document_prompt,
    extract_pdf,
    extract_pdf_text,
    validate_pdf_path,
)


MODEL_NAME = "llama3.2:latest"


class AppMode(str, Enum):
    GENERAL_CHAT = "General Chat"
    DOCUMENT_ANALYSIS = "Document Analysis"


class LocalLLMChatApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("SIH Local AI Workbench")
        self.geometry("1040x720")
        self.minsize(820, 560)

        self.system_message = {
            "role": "system",
            "content": (
                "You are a helpful offline AI assistant running locally. "
                "Answer clearly and do not claim to use online services."
            ),
        }
        self.general_messages: list[dict[str, str]] = [self.system_message]
        self.document_messages: list[dict[str, str]] = [self.system_message]
        self.response_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.mode = AppMode.GENERAL_CHAT
        self.is_generating = False
        self.current_answer_parts: list[str] = []
        self.pending_user_prompt = ""
        self.pending_mode = AppMode.GENERAL_CHAT
        self.current_document: DocumentExtraction | None = None
        self.current_document_context: DocumentContext | None = None
        self.last_llm_latency_seconds = 0.0
        self.queue_after_id: str | None = None

        self._build_styles()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_queue_processing(100)

    def _build_styles(self) -> None:
        self.configure(bg="#0d1117")
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("App.TFrame", background="#0d1117")
        style.configure("Header.TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#161b22", relief=tk.FLAT)
        style.configure("Toolbar.TFrame", background="#161b22")
        style.configure(
            "Title.TLabel",
            background="#111827",
            foreground="#ffffff",
            font=("Segoe UI", 19, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#111827",
            foreground="#9fb3c8",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Mode.TLabel",
            background="#2563eb",
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 5),
        )
        style.configure(
            "Metric.TLabel",
            background="#212936",
            foreground="#dbeafe",
            font=("Segoe UI", 9),
            padding=(8, 5),
        )
        style.configure(
            "Status.TLabel",
            background="#0d1117",
            foreground="#9ca3af",
            font=("Segoe UI", 9),
        )
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1, minsize=360)
        self.grid_columnconfigure(0, weight=1, minsize=760)

        header = ttk.Frame(self, style="Header.TFrame", padding=(24, 18))
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="SIH Local AI Workbench", style="Title.TLabel").pack(
            anchor=tk.W
        )
        ttk.Label(
            header,
            text=f"Offline document analysis - {MODEL_NAME} through local Ollama",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        main = ttk.Frame(self, style="App.TFrame", padding=(18, 14))
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(2, weight=1, minsize=180)
        main.grid_columnconfigure(0, weight=1)

        toolbar = ttk.Frame(main, style="Toolbar.TFrame", padding=(12, 10))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(2, weight=1)

        self.attach_button = tk.Button(
            toolbar,
            text="Attach PDF",
            command=self.attach_pdf,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            disabledforeground="#cbd5e1",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.attach_button.grid(row=0, column=0, sticky="w")

        self.clear_button = tk.Button(
            toolbar,
            text="Clear",
            command=self.clear_chat,
            bg="#30363d",
            fg="#f3f4f6",
            activebackground="#374151",
            activeforeground="#ffffff",
            disabledforeground="#94a3b8",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.clear_button.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.document_label = ttk.Label(
            toolbar,
            text="No document selected",
            style="Metric.TLabel",
        )
        self.document_label.grid(row=0, column=2, sticky="w", padx=(12, 0))

        self.mode_label = ttk.Label(toolbar, text="General Chat", style="Mode.TLabel")
        self.mode_label.grid(row=0, column=3, sticky="e")

        metrics = ttk.Frame(main, style="Toolbar.TFrame", padding=(12, 8))
        metrics.grid(row=1, column=0, sticky="ew", pady=(1, 10))

        self.page_metric = ttk.Label(metrics, text="Pages: -", style="Metric.TLabel")
        self.page_metric.pack(side=tk.LEFT)
        self.char_metric = ttk.Label(metrics, text="Text: -", style="Metric.TLabel")
        self.char_metric.pack(side=tk.LEFT, padx=(8, 0))
        self.context_metric = ttk.Label(metrics, text="Context: -", style="Metric.TLabel")
        self.context_metric.pack(side=tk.LEFT, padx=(8, 0))
        self.method_metric = ttk.Label(metrics, text="Method: -", style="Metric.TLabel")
        self.method_metric.pack(side=tk.LEFT, padx=(8, 0))
        self.latency_metric = ttk.Label(metrics, text="LLM: -", style="Metric.TLabel")
        self.latency_metric.pack(side=tk.LEFT, padx=(8, 0))

        self.chat_display = scrolledtext.ScrolledText(
            main,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            padx=18,
            pady=16,
            relief=tk.FLAT,
            borderwidth=0,
        )
        self.chat_display.tag_configure(
            "user", foreground="#0f766e", font=("Segoe UI", 11, "bold")
        )
        self.chat_display.tag_configure(
            "assistant", foreground="#1d4ed8", font=("Segoe UI", 11, "bold")
        )
        self.chat_display.tag_configure(
            "system", foreground="#b45309", font=("Segoe UI", 10, "italic")
        )
        self.chat_display.tag_configure("body", foreground="#111827", lmargin2=12)
        self.chat_display.configure(
            bg="#f8fafc",
            fg="#111827",
            selectbackground="#bfdbfe",
            selectforeground="#111827",
        )
        self.chat_display.grid(row=2, column=0, sticky="nsew")

        input_frame = ttk.Frame(main, style="Panel.TFrame", padding=(12, 12))
        input_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        input_frame.grid_columnconfigure(0, weight=1, minsize=420)

        self.prompt_input = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#0f172a",
            insertbackground="#2563eb",
            selectbackground="#bfdbfe",
            selectforeground="#0f172a",
            padx=14,
            pady=12,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=2,
            highlightbackground="#334155",
            highlightcolor="#2563eb",
        )
        self.prompt_input.grid(row=0, column=0, sticky="ew")
        self.prompt_input.bind("<Return>", self._send_with_enter)
        self.prompt_input.bind("<Shift-Return>", self._insert_newline)

        self.send_button = tk.Button(
            input_frame,
            text="Send",
            command=self.send_prompt,
            bg="#16a34a",
            fg="#ffffff",
            activebackground="#15803d",
            activeforeground="#ffffff",
            disabledforeground="#dcfce7",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            padx=22,
            pady=12,
            width=10,
            cursor="hand2",
        )
        self.send_button.grid(row=0, column=1, sticky="ns", padx=(12, 0))

        footer = ttk.Frame(main, style="App.TFrame")
        footer.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.status_label = ttk.Label(
            footer,
            text="Ready. Ask normally, or attach a local PDF for document analysis.",
            style="Status.TLabel",
        )
        self.status_label.pack(side=tk.LEFT)

        self._append_message(
            "system",
            "General Chat is active. Attach a local PDF to switch into Document Analysis.",
        )

    def _send_with_enter(self, event: tk.Event) -> str:
        self.send_prompt()
        return "break"

    def _insert_newline(self, event: tk.Event) -> None:
        self.prompt_input.insert(tk.INSERT, "\n")

    def send_prompt(self) -> None:
        if self.is_generating:
            return

        prompt = self.prompt_input.get("1.0", tk.END).strip()
        if not prompt:
            return

        if self.mode == AppMode.DOCUMENT_ANALYSIS and not self.current_document_context:
            self._append_message(
                "system",
                "No readable document text is available. Attach a digital PDF with selectable text, or use General Chat.",
            )
            return

        self.prompt_input.delete("1.0", tk.END)
        self.pending_user_prompt = prompt
        self.pending_mode = self.mode
        self._append_message("user", prompt)
        self._set_busy(True)
        self.current_answer_parts = []
        self.status_label.configure(
            text=(
                "Analyzing local document..."
                if self.mode == AppMode.DOCUMENT_ANALYSIS
                else "Starting local response..."
            )
        )

        worker = threading.Thread(target=self._ask_llm, args=(prompt, self.mode), daemon=True)
        worker.start()

    def attach_pdf(self) -> None:
        if self.is_generating:
            return

        pdf_path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not pdf_path:
            return

        self._set_busy(True)
        self.document_label.configure(text=f"Loading {Path(pdf_path).name}")
        self.status_label.configure(text="Validating and extracting local PDF...")
        worker = threading.Thread(target=self._load_pdf, args=(pdf_path,), daemon=True)
        worker.start()

    def _load_pdf(self, pdf_path: str) -> None:
        try:
            extraction = extract_pdf(
                pdf_path,
                progress_callback=lambda message: self.response_queue.put(
                    ("document_progress", message)
                ),
            )
            self.response_queue.put(("document_loaded", extraction))
        except ValueError as exc:
            self.response_queue.put(("document_error", str(exc)))
        except Exception:
            self.response_queue.put(("document_error", "The selected PDF could not be read."))

    def _ask_llm(self, prompt: str, mode: AppMode) -> None:
        started_at = time.perf_counter()
        try:
            if mode == AppMode.DOCUMENT_ANALYSIS and self.current_document_context:
                messages = self.document_messages.copy()
                content = build_document_prompt(prompt, self.current_document_context.text)
            else:
                messages = self.general_messages.copy()
                content = prompt

            messages.append({"role": "user", "content": content})
            self.response_queue.put(("start", ""))
            stream = ollama.chat(model=MODEL_NAME, messages=messages, stream=True)

            for chunk in stream:
                content_piece = chunk.get("message", {}).get("content", "")
                if content_piece:
                    self.response_queue.put(("chunk", content_piece))

            elapsed = time.perf_counter() - started_at
            self.response_queue.put(("done", elapsed))
        except Exception:
            self.response_queue.put(
                (
                    "error",
                    "Local model is unavailable. Check Ollama and the configured model.",
                )
            )

    def _process_response_queue(self) -> None:
        self.queue_after_id = None
        processed_event = False

        try:
            while True:
                event_type, payload = self.response_queue.get_nowait()
                processed_event = True

                if event_type == "start":
                    self._start_streamed_message("assistant")
                    self.status_label.configure(text="Generating response locally...")
                elif event_type == "chunk":
                    self.current_answer_parts.append(str(payload))
                    self._append_streamed_text(str(payload))
                elif event_type == "done":
                    self._handle_generation_done(float(payload))
                elif event_type == "error":
                    self._handle_generation_error(str(payload))
                elif event_type == "document_loaded":
                    self._handle_document_loaded(payload)
                elif event_type == "document_error":
                    self._handle_document_error(str(payload))
                elif event_type == "document_progress":
                    self.status_label.configure(text=str(payload))
        except queue.Empty:
            pass

        self._schedule_queue_processing(20 if processed_event else 100)

    def _handle_generation_done(self, elapsed_seconds: float) -> None:
        answer = "".join(self.current_answer_parts).strip()
        if answer:
            target_history = (
                self.document_messages
                if self.pending_mode == AppMode.DOCUMENT_ANALYSIS
                else self.general_messages
            )
            target_history.append({"role": "user", "content": self.pending_user_prompt})
            target_history.append({"role": "assistant", "content": answer})

        self.pending_user_prompt = ""
        self.last_llm_latency_seconds = elapsed_seconds
        self.latency_metric.configure(text=f"LLM: {elapsed_seconds:.2f}s")
        self._finish_streamed_message()
        self.status_label.configure(text="Ready.")
        self._set_busy(False)

    def _handle_generation_error(self, message: str) -> None:
        self.pending_user_prompt = ""
        self._append_message("system", message)
        self.status_label.configure(text="Local model failed.")
        self._set_busy(False)

    def _handle_document_loaded(self, payload: object) -> None:
        if not isinstance(payload, DocumentExtraction):
            self._handle_document_error("The selected PDF could not be read.")
            return

        self.current_document = payload
        self.current_document_context = build_document_context(payload.pages)
        self.document_messages = [self.system_message]
        self.mode = AppMode.DOCUMENT_ANALYSIS if payload.pages else AppMode.GENERAL_CHAT
        self._refresh_mode_ui()

        self.page_metric.configure(text=f"Pages: {payload.page_count}")
        self.char_metric.configure(text=f"Text: {payload.extracted_chars:,} chars")
        self.method_metric.configure(text=f"Method: {payload.method_summary}")

        if payload.pages and self.current_document_context:
            context = self.current_document_context
            self.context_metric.configure(
                text=f"Context: {context.included_pages}/{context.total_text_pages} pages"
            )
            warning = ""
            if context.truncated:
                warning = (
                    f" Only pages 1-{context.included_pages} fit the current direct-analysis limit."
                )

            self._append_message(
                "system",
                (
                    f"Document Mode: {payload.filename}. "
                    f"{payload.page_count} pages, {payload.extracted_chars:,} extracted characters, "
                    f"{payload.method_summary}, "
                    f"about {context.estimated_tokens:,} prompt tokens, "
                    f"{payload.extraction_seconds:.2f}s extraction time.{warning}"
                ),
            )
            self.status_label.configure(text="Document ready. Ask a question about it.")
        else:
            self.current_document_context = None
            self.context_metric.configure(text="Context: no text")
            self._append_message(
                "system",
                (
                    f"Loaded {payload.filename}, but no readable text was found. "
                    "OCR was attempted where needed, but no useful text was recovered."
                ),
            )
            self.status_label.configure(text="No readable text found after extraction/OCR.")

        self._set_busy(False)

    def _handle_document_error(self, message: str) -> None:
        self.current_document = None
        self.current_document_context = None
        self.document_messages = [self.system_message]
        self.mode = AppMode.GENERAL_CHAT
        self._refresh_mode_ui()
        self._reset_metrics()
        self._append_message("system", message)
        self.status_label.configure(text="PDF validation or extraction failed.")
        self._set_busy(False)

    def _append_message(self, role: str, content: str) -> None:
        label = {
            "user": "You",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role.title())

        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{label}\n", role)
        self.chat_display.insert(tk.END, f"{content}\n\n", "body")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _start_streamed_message(self, role: str) -> None:
        label = {
            "user": "You",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role.title())

        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{label}\n", role)
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _append_streamed_text(self, content: str) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, content, "body")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _finish_streamed_message(self) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n\n", "body")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _set_busy(self, busy: bool) -> None:
        self.is_generating = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.send_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.attach_button.configure(state=state)

    def _refresh_mode_ui(self) -> None:
        if self.mode == AppMode.DOCUMENT_ANALYSIS and self.current_document:
            self.mode_label.configure(text="Document Analysis")
            self.document_label.configure(text=f"Document Mode: {self.current_document.filename}")
        else:
            self.mode_label.configure(text="General Chat")
            self.document_label.configure(text="No document selected")

    def _reset_metrics(self) -> None:
        self.page_metric.configure(text="Pages: -")
        self.char_metric.configure(text="Text: -")
        self.context_metric.configure(text="Context: -")
        self.method_metric.configure(text="Method: -")
        self.latency_metric.configure(text="LLM: -")

    def clear_chat(self) -> None:
        if self.is_generating:
            return

        self.general_messages = [self.system_message]
        self.document_messages = [self.system_message]
        self.pending_user_prompt = ""
        self.pending_mode = AppMode.GENERAL_CHAT
        self.current_document = None
        self.current_document_context = None
        self.mode = AppMode.GENERAL_CHAT
        self.last_llm_latency_seconds = 0.0
        self._refresh_mode_ui()
        self._reset_metrics()
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state=tk.DISABLED)
        self._append_message(
            "system",
            "Cleared. General Chat is active; attach a PDF to start a new document session.",
        )
        self.status_label.configure(text="Ready.")

    def _schedule_queue_processing(self, delay_ms: int) -> None:
        if self.winfo_exists():
            self.queue_after_id = self.after(delay_ms, self._process_response_queue)

    def _cancel_queue_processing(self) -> None:
        if self.queue_after_id:
            try:
                self.after_cancel(self.queue_after_id)
            except tk.TclError:
                pass
            self.queue_after_id = None

    def _on_close(self) -> None:
        self._cancel_queue_processing()
        self.destroy()

    def destroy(self) -> None:
        self._cancel_queue_processing()
        super().destroy()


def main() -> None:
    try:
        app = LocalLLMChatApp()
        app.mainloop()
    except tk.TclError as exc:
        messagebox.showerror("SIH Local AI Workbench", str(exc))


if __name__ == "__main__":
    main()
