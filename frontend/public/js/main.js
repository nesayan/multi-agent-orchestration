let BACKEND_URL = "";

const form = document.getElementById("chat-form");
const input = document.getElementById("query");
const messages = document.getElementById("messages");

// Generate a unique thread_id per session
const threadId = crypto.randomUUID();

// Fetch backend URL from server config on page load
async function loadConfig() {
  try {
    const res = await fetch("/config");
    const config = await res.json();
    BACKEND_URL = config.backendUrl;
  } catch (err) {
    console.error("Failed to load config, using default", err);
    BACKEND_URL = "http://localhost:80";
  }
}
loadConfig();

// Append a message to the chatbox
function appendMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${role}`;

  const icon = document.createElement("i");
  icon.className = role === "user" ? "bi bi-person-fill msg-icon" : "bi bi-robot msg-icon";

  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = text;

  wrapper.appendChild(icon);
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// Event listener: Runs when the user submits a query
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  appendMessage("user", query);
  input.value = "";

  const botWrapper = document.createElement("div");
  botWrapper.className = "message-wrapper bot";

  const botIcon = document.createElement("i");
  botIcon.className = "bi bi-robot msg-icon";

  const botDiv = document.createElement("div");
  botDiv.className = "message bot";
  const spinner = document.createElement("div");
  spinner.className = "spinner";
  botDiv.appendChild(spinner);

  botWrapper.appendChild(botIcon);
  botWrapper.appendChild(botDiv);
  messages.appendChild(botWrapper);
  messages.scrollTop = messages.scrollHeight;

  try {
    const res = await fetch(`${BACKEND_URL}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, thread_id: threadId }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let botText = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]") break;
        if (spinner.parentNode) spinner.remove();
        botText += data;
        botDiv.textContent = botText;
        messages.scrollTop = messages.scrollHeight;
      }
    }
  } catch (err) {
    spinner.remove();
    botDiv.textContent = "Error: " + err.message;
  }
});
