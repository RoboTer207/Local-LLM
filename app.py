import subprocess
import time
import requests
from flask import Flask, request, Response, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- WORKER CONFIG ---
WORKERS = {
    "simple": "http://<A6-IP>:5001",        # SmolLM2-360M
    "medium": "http://<I5-IP>:5002",         # TinyLlama-1.1B
    "complex": "http://127.0.0.1:8080",      # Phi-3-mini 3.8B (local)
}

# --- START LOCAL LLAMA SERVER (Phi-3-mini) ---
llama_command = [
    "./llama.cpp/build/bin/llama-server",
    "-m", "./models/Phi-3-mini-4k-instruct-q4.gguf",
    "--host", "127.0.0.1",
    "--port", "8080",
    "-c", "512",
    "--no-mmap",
    "-t", "8",
    "-np", "2"
]

print("🚀 Starting home llama-server (Phi-3-mini)...")
llama_process = subprocess.Popen(
    llama_command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

for _ in range(60):
    try:
        if requests.get("http://127.0.0.1:8080/health", timeout=1).ok:
            print("✅ llama-server ready!")
            break
    except:
        pass
    time.sleep(1)

# --- QUERY ROUTER ---
def route_query(prompt):
    words = len(prompt.split())
    if words < 15:
        return "simple"
    elif words < 40:
        return "medium"
    else:
        return "complex"

# --- HTML ---
HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Voice Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <style>
        body { font-family: sans-serif; background: #111; color: white; text-align: center; padding: 20px; }
        #chat { width: 100%; max-width: 500px; margin: auto; height: 300px; overflow-y: auto; border: 1px solid #444; padding: 10px; background: #222; border-radius: 10px; text-align: left; }
        .user { color: #00ff00; margin: 10px 0; }
        .bot { color: #00d4ff; margin: 10px 0; }
        .info { color: #888; font-size: 0.8em; margin: 5px 0; }
        input { width: 70%; padding: 10px; border-radius: 5px; border: none; }
        button { padding: 10px; border-radius: 5px; border: none; cursor: pointer; background: #444; color: white; }
        #mic-btn { background: #ff4b2b; }
    </style>
</head>
<body>
    <h2>🧠 AI Voice Chat</h2>
    <div id="chat"></div>
    <br>
    <input id="msg" placeholder="Type or use mic...">
    <button onclick="send()">Send</button>
    <button id="mic-btn" onclick="toggleMic()">🎤</button>

<script>
    let recognition;
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.onresult = (e) => {
            document.getElementById("msg").value = e.results[0][0].transcript;
            send();
        };
    }

    function toggleMic() {
        if (!recognition) return alert("Mic not supported");
        recognition.start();
    }

    async function send() {
        const input = document.getElementById("msg");
        const text = input.value;
        if(!text) return;
        input.blur();
        appendMsg("You: " + text, "user");
        input.value = "";
        const loading = appendMsg("AI: thinking...", "bot");

        try {
            const response = await fetch("/completion", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: "<|system|>\nYou are a helpful assistant.</s>\n<|user|>\n" + text + "</s>\n<|assistant|>\n",
                    n_predict: 150
                })
            });
            const data = await response.json();
            const reply = data.content.trim();
            loading.innerText = "AI: " + reply;
            if (data.worker) {
                appendMsg("(routed to: " + data.worker + ")", "info");
            }

            const utt = new SpeechSynthesisUtterance(reply);
            window.speechSynthesis.speak(utt);
        } catch (e) {
            loading.innerText = "AI: Error connecting to bridge.";
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

# --- ROUTES ---
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/completion", methods=["POST"])
def completion():
    try:
        data = request.json
        prompt = data.get("prompt", "")
        tier = route_query(prompt)
        worker_url = WORKERS[tier]

        print(f"Routing to: {tier} ({worker_url})")
        resp = requests.post(f"{worker_url}/completion", json=data, timeout=120)
        print(f"Bridge response: {resp.status_code}")
        result = resp.json()
        result["worker"] = tier
        return result
    except Exception as e:
        print(f"Bridge error: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000)
    finally:
        print("Stopping AI...")
        llama_process.terminate()