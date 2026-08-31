import json, urllib.request, urllib.error

# read the key codex actually has in auth.json
with open("/root/.codex/auth.json") as f:
    auth = json.load(f)
key67 = auth.get("OPENAI_API_KEY", "")
print("auth.json key: prefix=%s len=%d" % (key67[:12], len(key67)))

def call(name, url, key, path="/v1/models"):
    h = {"Authorization": "Bearer " + key}
    r = urllib.request.Request(url + path, headers=h, method="GET")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            print("%s [%s key]: HTTP %d" % (name, "auth67" if key == key67 else "env164", resp.status))
            return resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        print("%s [%s key]: HTTP %d %s" % (name, "auth67" if key == key67 else "env164", e.code, e.read().decode()[:150]))
        return None

# read the 164-char key from hermes env
key164 = None
with open("/root/.hermes/profiles/littleapple/.env") as f:
    for line in f:
        s = line.strip()
        if s.startswith("OPENAI_API_KEY="):
            key164 = s.split("=", 1)[1].strip().strip('"').strip("'")
            break
print("hermes env164: prefix=%s len=%d" % (key164[:12], len(key164)))

print("\n--- aigocode provider (config-toml target) ---")
call("aigocode", "https://api.aigocode.com", key67)
call("aigocode", "https://api.aigocode.com", key164)

print("\n--- openai official ---")
call("openai", "https://api.openai.com/v1", key67)
call("openai", "https://api.openai.com/v1", key164)
