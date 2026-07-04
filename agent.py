from openai import OpenAI

# --- CONFIG ---
OSAURUS_URL = "http://127.0.0.1:1337/v1"
MODEL = "foundation"

# --- CLIENT ---
client = OpenAI(base_url=OSAURUS_URL, api_key="osaurus")

# --- CONVERSATION HISTORY ---
history = [
    {"role": "system", "content": "You are a helpful, conversational assistant. Keep responses concise."}
]

# --- ASK LLM ---
def ask(prompt):
    history.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=MODEL,
        messages=history,
        max_tokens=300
    )
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("🦕 Agent ready! Ctrl+C to stop.")
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            response = ask(user_input)
            print(f"AI: {response}")
        except KeyboardInterrupt:
            print("\nStopping...")
            break