import re
import asyncio
from aiohttp import web
from telethon import TelegramClient

# ================= CONFIG =================
api_id = 21385262
api_hash = "0b685b2ead34f78600e21e748495682d"

GROUP_ID = -1003771161345
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

    async for msg in client.iter_messages(GROUP_ID, limit=LIMIT):

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
HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>LIVE OTP</title>

<style>
body{
  margin:0;
  font-family:sans-serif;
  background:linear-gradient(135deg,#0f172a,#1e293b);
  color:white;
}

.header{text-align:center;padding:10px;}
.title{background:#1f2937;margin:5px;padding:8px;border-radius:10px;font-weight:bold;}

.search{padding:8px;}
.search input{width:100%;padding:10px;border-radius:10px;border:none;}

.item{
  margin:6px;
  padding:10px;
  border-radius:12px;
  border:2px solid red;
  display:flex;
  gap:10px;
}

.num, .otp{
  flex:1;
  padding:8px;
  border-radius:10px;
  text-align:center;
  font-weight:bold;
  cursor:pointer;
}

.num{
  background:#3b82f6;
  color:black;
}

.otp{
  background:#4ade80;
  color:black;
}
</style>
</head>

<body>

<div class="header">
  <div class="title">LIVE OTP SYSTEM</div>
</div>

<div class="search">
  <input id="search" placeholder="Search..." oninput="filter()">
</div>

<div id="data"></div>

<script>

let all = [];
let searchMode = false;

function normalize(x){
  return x.replace(/[^0-9]/g,'');
}

/*
🔥 STRICT SEARCH:
- first 6 digits
- last 2 digits
*/

function smartMatch(num, q){

  num = normalize(num);
  q = normalize(q);

  if(q.length < 8){
    return num.startsWith(q);
  }

  let qFirst6 = q.substring(0,6);
  let qLast2  = q.slice(-2);

  let nFirst6 = num.substring(0,6);
  let nLast2  = num.slice(-2);

  return (qFirst6 === nFirst6) && (qLast2 === nLast2);
}

// 🔥 COPY FUNCTION
function copyText(t){
  navigator.clipboard.writeText(t);
}

function render(items){
  document.getElementById("data").innerHTML =
    items.map(i=>`
      <div class="item">

        <div class="num" onclick="copyText('${i.number}')">
          ${i.number}
        </div>

        <div class="otp" onclick="copyText('${i.otp}')">
          ${i.otp}
        </div>

      </div>
    `).join("");
}

function filter(){
  let q = document.getElementById("search").value;

  if(!q){
    searchMode = false;
    render(all);
    return;
  }

  searchMode = true;

  let result = all.filter(i => smartMatch(i.number, q));

  render(result);
}

async function load(){
  let r = await fetch("/data");
  let d = await r.json();

  all = d.items;

  if(!searchMode){
    render(all);
  }
}

setInterval(load, 1000);
load();

</script>

</body>
</html>
"""

# ================= START =================
async def main():
    await client.start()
    await build_cache()

    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text=HTML, content_type="text/html"))
    app.router.add_get("/data", data)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    print("LIVE: http://127.0.0.1:8080")

    while True:
        await build_cache()
        await asyncio.sleep(2)

asyncio.run(main())
