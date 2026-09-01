let authToken = localStorage.getItem("sih_token");
let currentSessionId = localStorage.getItem("sih_session_id");
let currentDocId = null;
let appMode = "General Chat";
let isBusy = false;

const loginModal = document.getElementById("login-modal");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const userDisplay = document.getElementById("user-display");
const logoutBtn = document.getElementById("logout-btn");

const serverStatusDot = document.getElementById("server-status-dot");
const serverStatusText = document.getElementById("server-status-text");
const modeBadge = document.getElementById("mode-badge");
const currentDocBadge = document.getElementById("current-doc-badge");

const metricPages = document.getElementById("metric-pages");
const metricText = document.getElementById("metric-text");
const metricContext = document.getElementById("metric-context");
const metricMethod = document.getElementById("metric-method");
const metricLlm = document.getElementById("metric-llm");
const metricHost = document.getElementById("metric-host");

const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const clearBtn = document.getElementById("clear-btn");
const pdfFileInput = document.getElementById("pdf-file-input");
const uploadProgress = document.getElementById("upload-progress");
const uploadStatusText = document.getElementById("upload-status-text");
const footerStatus = document.getElementById("footer-status");

document.addEventListener("DOMContentLoaded", () => {
  if (authToken) {
    loginModal.style.display = "none";
    initSession();
  } else {
    loginModal.style.display = "flex";
  }

  checkHealth();
  setInterval(checkHealth, 5000);
});

async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Server error");
    const data = await res.json();
    
    serverStatusDot.className = "status-dot online";
    serverStatusText.textContent = data.ai_service.model_available
      ? `Online (${data.ai_service.model_configured})`
      : "Model missing";

    if (data.metrics) {
      metricHost.textContent = `Host: CPU ${data.metrics.cpu_percent}% | RAM ${data.metrics.memory_percent}%`;
    }
  } catch (err) {
    serverStatusDot.className = "status-dot offline";
    serverStatusText.textContent = "Offline";
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.style.display = "none";
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }

    const data = await res.json();
    authToken = data.token;
    currentSessionId = data.session_id;
    localStorage.setItem("sih_token", authToken);
    localStorage.setItem("sih_session_id", currentSessionId);
    localStorage.setItem("sih_username", data.username);

    loginModal.style.display = "none";
    initSession();
  } catch (err) {
    loginError.textContent = err.message;
    loginError.style.display = "block";
  }
});

logoutBtn.addEventListener("click", async () => {
  if (authToken) {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}` },
      });
    } catch (_) {}
  }
  localStorage.clear();
  authToken = null;
  location.reload();
});

async function initSession() {
  const username = localStorage.getItem("sih_username") || "User";
  userDisplay.textContent = username;

  try {
    const res = await fetch("/api/session", {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (res.status === 401) {
      localStorage.clear();
      loginModal.style.display = "flex";
      return;
    }
    const session = await res.json();
    updateSessionUI(session);
  } catch (err) {
    console.error("Failed to load session:", err);
  }
}

function updateSessionUI(session) {
  appMode = session.mode;
  modeBadge.textContent = appMode;

  if (session.current_document_id && session.uploaded_documents.length > 0) {
    const activeDoc = session.uploaded_documents.find(
      (d) => d.document_id === session.current_document_id
    );
    if (activeDoc) {
      currentDocId = activeDoc.document_id;
      currentDocBadge.textContent = `Document: ${activeDoc.filename}`;
      metricPages.textContent = `Pages: ${activeDoc.page_count}`;
      metricText.textContent = `Text: ${activeDoc.extracted_chars.toLocaleString()} chars`;
      metricMethod.textContent = `Method: ${activeDoc.method_summary}`;

      if (session.current_document_context) {
        const ctx = session.current_document_context;
        metricContext.textContent = `Context: ${ctx.included_pages}/${ctx.total_text_pages} pages`;
      }
    }
  } else {
    currentDocId = null;
    currentDocBadge.textContent = "No document selected";
    resetMetrics();
  }
}

function resetMetrics() {
  metricPages.textContent = "Pages: -";
  metricText.textContent = "Text: -";
  metricContext.textContent = "Context: -";
  metricMethod.textContent = "Method: -";
  metricLlm.textContent = "LLM: -";
}

function appendMessage(role, content) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;

  const header = document.createElement("div");
  header.className = "msg-header";
  header.textContent = role === "user" ? "You" : role === "assistant" ? "Assistant" : "System";

  const body = document.createElement("div");
  body.className = "msg-content";
  body.textContent = content;

  msgDiv.appendChild(header);
  msgDiv.appendChild(body);
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return body;
}

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);

async function sendMessage() {
  if (isBusy) return;
  const prompt = chatInput.value.trim();
  if (!prompt) return;

  chatInput.value = "";
  appendMessage("user", prompt);
  setBusy(true);

  const endpoint =
    appMode === "Document Analysis" && currentDocId
      ? `/api/documents/${currentDocId}/chat`
      : "/api/chat";

  footerStatus.textContent = "Generating response locally...";

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({ message: prompt, stream: true }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Request failed");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let assistantMsgBody = null;
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6));
          if (data.type === "chunk") {
            if (!assistantMsgBody) {
              assistantMsgBody = appendMessage("assistant", "");
            }
            fullText += data.content;
            assistantMsgBody.textContent = fullText;
            chatMessages.scrollTop = chatMessages.scrollHeight;
          } else if (data.type === "done") {
            metricLlm.textContent = `LLM: ${data.latency_seconds}s`;
            footerStatus.textContent = "Ready.";
          } else if (data.type === "error") {
            appendMessage("system", `Inference Error: ${data.error}`);
            footerStatus.textContent = "Error occurred.";
          }
        }
      }
    }
  } catch (err) {
    appendMessage("system", err.message);
    footerStatus.textContent = "Local model request failed.";
  } finally {
    setBusy(false);
  }
}

pdfFileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  uploadProgress.classList.remove("hidden");
  uploadStatusText.textContent = `Extracting & performing OCR on ${file.name}...`;
  footerStatus.textContent = "Validating and extracting PDF on host machine...";
  setBusy(true);

  try {
    const res = await fetch("/api/documents", {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "PDF processing failed");
    }

    const data = await res.json();
    currentDocId = data.document.document_id;
    appMode = data.mode;
    modeBadge.textContent = appMode;
    currentDocBadge.textContent = `Document: ${data.document.filename}`;

    metricPages.textContent = `Pages: ${data.document.page_count}`;
    metricText.textContent = `Text: ${data.document.extracted_chars.toLocaleString()} chars`;
    metricMethod.textContent = `Method: ${data.document.method_summary}`;

    if (data.context) {
      metricContext.textContent = `Context: ${data.context.included_pages}/${data.context.total_text_pages} pages`;
    }

    appendMessage(
      "system",
      `Loaded ${data.document.filename}. ${data.document.page_count} pages, ${data.document.extracted_chars.toLocaleString()} chars, ${data.document.method_summary}. Switched to Document Analysis mode.`
    );
    footerStatus.textContent = "Document ready. Ask a question about it.";
  } catch (err) {
    appendMessage("system", `PDF Upload Error: ${err.message}`);
    footerStatus.textContent = "Failed to load PDF.";
  } finally {
    uploadProgress.classList.add("hidden");
    pdfFileInput.value = "";
    setBusy(false);
  }
});

clearBtn.addEventListener("click", async () => {
  if (isBusy) return;
  try {
    await fetch("/api/chat/clear", {
      method: "POST",
      headers: { Authorization: `Bearer ${authToken}` },
    });
    chatMessages.innerHTML = "";
    appendMessage(
      "system",
      "Cleared. General Chat is active; attach a PDF to start a new document session."
    );
    appMode = "General Chat";
    currentDocId = null;
    modeBadge.textContent = appMode;
    currentDocBadge.textContent = "No document selected";
    resetMetrics();
    footerStatus.textContent = "Ready.";
  } catch (err) {
    console.error("Clear error:", err);
  }
});

function setBusy(busy) {
  isBusy = busy;
  sendBtn.disabled = busy;
  clearBtn.disabled = busy;
  pdfFileInput.disabled = busy;
}
