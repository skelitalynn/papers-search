import json, os, urllib.request, urllib.error

key = None
with open("/root/.hermes/profiles/littleapple/.env") as f:
    for line in f:
        s = line.strip()
        if s.startswith("OPENAI_API_KEY="):
            key = s.split("=", 1)[1].strip().strip('"').strip("'")
            break

print("key prefix: %s len: %d" % (key[:12], len(key)))

def call(method, url, body=None):
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()[:800]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]

print("\n=== Responses API POST (Codex real path) ===")
for model in ["gpt-5.6-sol", "gpt-4o-mini", "gpt-5.5"]:
    print("%s: %s" % (model, call("POST", "https://api.openai.com/v1/responses",
                                  {"model": model, "input": "Hello"})))

print("\n=== chat completions ===")
for model in ["gpt-4o-mini", "gpt-5.5"]:
    print("%s: %s" % (model, call("POST", "https://api.openai.com/v1/chat/completions",
                                  {"model": model, "messages": [{"role": "user", "content": "hi"}]})))
