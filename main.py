import re
import asyncio
import os
from aiohttp import web
from telethon import TelegramClient

# ================= CONFIG =================
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")

GROUP_IDS = [
    -1003771161345,
    -1002531902737
]

LIMIT = 100

client = TelegramClient("otp_session", api_id, api_hash)

CACHE = []

# ================= PARSE =================
def clean(text):
    text = re.sub(r'\d{4}-\d{2}-\d{2}', ' ', text)
    text = re.sub(r'\d{2}:\d{2}:\d{2}', ' ', text)
    return text

def extract_numbers(text):
    nums = re.findall(r'\+[\dXx\s]{6,}', text)
    out = []
    for n in nums:
        if len(re.sub(r'\D', '', n)) >= 7:
            out.append(n.strip())
    return out

def extract_otps(text):
    raw = re.findall(r'\b\d{5,7}\b', text)
    return list(dict.fromkeys(raw))

def parse(text):
    text = clean(text)
    numbers = extract_numbers(text)
    otps = extract_otps(text)

    result = []
    for n in numbers:
        for o in otps:
            result.append({
                "number": n,
                "otp": o
            })
    return result

# ================= CACHE =================
async def build_cache():
    global CACHE

    items = []
    seen = set()

    for gid in GROUP_IDS:
        async for msg in client.iter_messages(gid, limit=LIMIT):

            if not msg.message:
                continue

            for item in parse(msg.message):
                key = (item["number"], item["otp"])

                if key in seen:
                    continue

                seen.add(key)
                items.append(item)

    CACHE = items

# ================= API =================
async def data(request):
    return web.json_response({"items": CACHE})

# ================= HTML =================
HTML = """<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>LIVE OTP</title>
<style>
body{margin:0;font-family:sans-serif;background:#0f172a;color:white}
.item{margin:6px;padding:10px;border-radius:10px;border:2px solid red;display:flex;gap:10px}
.num,.otp{flex:1;padding:8px;border-radius:10px;text-align:center;font-weight:bold;cursor:pointer}
.num{background:#3b82f6;color:black}
.otp{background:#4ade80;color:black}
</style>
</head>
<body>
<h2 style="text-align:center;">LIVE OTP SYSTEM</h2>
<div id="data"></div>
<script>
async function load(){
  let r = await fetch("/data");
  let d = await r.json();
  document.getElementById("data").innerHTML =
    d.items.map(i=>`
      <div class="item">
        <div class="num">${i.number}</div>
        <div class="otp">${i.otp}</div>
      </div>
    `).join("");
}
setInterval(load,3000);
load();
</script>
</body>
</html>
"""

# ================= BACKGROUND TASK =================
async def background_task():
    while True:
        try:
            await build_cache()
        except Exception as e:
            print("Error:", e)
        await asyncio.sleep(10)

# ================= START =================
async def main():
    await client.start()
    await build_cache()

    asyncio.create_task(background_task())

    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text=HTML, content_type="text/html"))
    app.router.add_get("/data", data)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Running on port {port}")

    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
