import subprocess
import time
import requests
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Start llama-server in background
llama_command = [
    "/home/omkar/anish/coding/llama.cpp/build/bin/llama-server",
    "-m", "/home/omkar/anish/coding/llama.cpp/models/models/SmolLM2-360M-Instruct-Q4_K_M.gguf",
    "--host", "127.0.0.1",
    "--port", "8081",
    "-c", "512",
    "--no-mmap",
    "-t", "2"
]

print("🚀 Starting worker llama-server...")
llama_process = subprocess.Popen(llama_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait for llama-server to be ready
for _ in range(30):
    try:
        if requests.get("http://127.0.0.1:8081/health", timeout=1).ok:
            print("✅ llama-server ready!")
            break
    except:
        pass
    time.sleep(1)

@app.route("/completion", methods=["POST"])
def completion():
    try:
        resp = requests.post("http://127.0.0.1:8081/completion", json=request.json, timeout=60)
        return Response(resp.content, status=resp.status_code, mimetype="application/json")
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/health", methods=["GET"])
def health():
    try:
        r = requests.get("http://127.0.0.1:8081/health", timeout=2)
        return {"status": "ok"}, 200
    except:
        return {"status": "unavailable"}, 503

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5001)
    finally:
        print("Stopping worker...")
        llama_process.terminate()