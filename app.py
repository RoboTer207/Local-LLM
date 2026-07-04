from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
import uvicorn
app = FastAPI()

# --- CONFIG ---
OSAURUS_URL = "http://127.0.0.1:1337/v1"
MODEL = "foundation"

# --- CLIENT ---
client = OpenAI(base_url=OSAURUS_URL, api_key="osaurus")

# --- CONVERSATION HISTORY ---
history = [
    {"role": "system", "content": "You are a helpful, conversational assistant. Keep responses concise."}
]

# --- REQUEST MODEL ---
class Message(BaseModel):
    content: str

# --- ASK LLM ---
def ask_stream(prompt):
    history.append({"role": "user", "content": prompt})
    stream = client.chat.completions.create(
        model=MODEL,
        messages=history,
        max_tokens=300,
        stream=True
    )
    full_reply = ""
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        full_reply += token
        yield token
    history.append({"role": "assistant", "content": full_reply})

# --- HTML ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Chat</title>
    <style>
        body { font-family: sans-serif; background: #111; color: white; text-align: center; padding: 20px; }
        #chat { width: 100%; max-width: 600px; margin: auto; height: 400px; overflow-y: auto; border: 1px solid #444; padding: 10px; background: #222; border-radius: 10px; text-align: left; }
        .user { color: #00ff00; margin: 10px 0; }
        .bot { color: #00d4ff; margin: 10px 0; }
        input { width: 70%; padding: 10px; border-radius: 5px; border: none; background: #333; color: white; }
        button { padding: 10px 20px; border-radius: 5px; border: none; cursor: pointer; background: #444; color: white; }
    </style>
</head>
<body>
    <h2>🦕 AI Chat</h2>
    <div id="chat"></div>
    <br>
    <input id="msg" placeholder="Type a message...">
    <button onclick="send()">Send</button>

<script>
    async function send() {
        const input = document.getElementById("msg");
        const text = input.value.trim();
        if (!text) return;
        appendMsg("You: " + text, "user");
        input.value = "";
        const botMsg = appendMsg("AI: ", "bot");

        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: text })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            botMsg.innerText += decoder.decode(value);
            const c = document.getElementById("chat");
            c.scrollTop = c.scrollHeight;
        }
    }

    function appendMsg(t, cls) {
        const d = document.createElement("div");
        d.className = cls;
        d.innerText = t;
        const c = document.getElementById("chat");
        c.appendChild(d);
        c.scrollTop = c.scrollHeight;
        return d;
    }

    document.getElementById("msg").addEventListener("keydown", function(e) {
        if (e.key === "Enter") send();
    });
</script>
</body>
</html>
"""

#  --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.post("/chat")
def chat(message: Message):
    return StreamingResponse(ask_stream(message.content), media_type="text/plain")

#  --- RUN ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)