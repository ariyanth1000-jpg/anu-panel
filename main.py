import re
import asyncio
import os
from aiohttp import web
from telethon import TelegramClient

# ================= CONFIG =================
api_id = int(os.getenv("API_ID", "123456"))
api_hash = os.getenv("API_HASH", "your_api_hash")

GROUP_IDS = [
    "-1003771161345",
    "-1002531902737",
    "-1002567258773",
    "-1002652123574",
    "-1003861246919",
    "-1003435291410",
    "-1003775658194",
    "-1002898987582",
    "-1003463811076",
    "-1003357916577",
]

LIMIT = 200

client = TelegramClient("otp_session", api_id, api_hash)

CACHE = {gid: [] for gid in GROUP_IDS}

# ================= PARSER =================
def extract_number(text):
    m = re.search(r'[\+\d][\dXx*\s]{6,}', text)
    return m.group(0).strip() if m else None

def extract_otp(text):
    text = text.replace(" ", "")
    m = re.findall(r'\b\d{5,6}\b', text)
    return m[-1] if m else None

def parse(text):
    n = extract_number(text)
    o = extract_otp(text)
    if n and o:
        return {"number": n, "otp": o}
    return None

# ================= CACHE =================
async def build_cache(gid):
    items = []
    seen = set()

    async for msg in client.iter_messages(int(gid), limit=LIMIT):
        if not msg.message:
            continue

        item = parse(msg.message)
        if not item:
            continue

        key = (item["number"], item["otp"])
        if key in seen:
            continue

        seen.add(key)
        items.append(item)

    CACHE[gid] = items

async def background_refresh():
    while True:
        await asyncio.gather(*[build_cache(g) for g in GROUP_IDS])
        await asyncio.sleep(2)

# ================= API =================
async def data(request):
    gid = request.query.get("gid")
    return web.json_response({"items": CACHE.get(gid, [])})

# ================= HTML =================
HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>LIVE OTP</title>

<style>
body{margin:0;background:#0f172a;color:white;font-family:sans-serif}
.header{text-align:center;padding:12px;font-weight:bold}
select{width:95%;margin:5px;padding:10px;border-radius:10px}

.searchbox{display:flex;padding:5px}
.searchbox input{flex:1;padding:10px;border-radius:10px;border:none}
.clear{background:red;color:white;padding:10px;border-radius:10px;margin-left:5px}

.item{margin:6px;padding:10px;border-radius:10px;border:2px solid red;display:flex;gap:10px}
.num{flex:1;background:#3b82f6;color:black;padding:10px;border-radius:10px;text-align:center;font-weight:bold}
.otp{flex:1;background:#4ade80;color:black;padding:10px;border-radius:10px;text-align:center;font-weight:bold;cursor:pointer}

.toast{
position:fixed;
bottom:20px;
left:50%;
transform:translateX(-50%);
background:#22c55e;
color:black;
padding:10px 20px;
border-radius:10px;
display:none;
font-weight:bold;
}
</style>
</head>

<body>

<div class="header">TAMIM ANU LIVE OTP SYSTEM</div>

<select id="gid" onchange="changeGroup()"></select>

<div class="searchbox">
<input id="search" placeholder="Paste number & Search..." oninput="filter()">
<button class="clear" onclick="clearSearch()">Clear Number</button>
</div>

<div id="data"></div>

<div id="toast" class="toast">Copied ✅</div>

<script>

let all = [];
let gid = "";

function normalize(x){
    return (x || "").replace(/[^0-9]/g,'');
}

// 🔥 FILTER
function match(num, query){
    let n = normalize(num);
    let q = normalize(query);

    if(!q) return true;

    if(q.length < 5){
        return n.includes(q);
    }

    return n.startsWith(q.slice(0,3)) && n.endsWith(q.slice(-2));
}

// 🔥 COPY FIX (WORKS EVERYWHERE)
function copyText(text){

    if(navigator.clipboard){
        navigator.clipboard.writeText(text);
    }else{
        let textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
    }

    showToast();
}

function showToast(){
    let t = document.getElementById("toast");
    t.style.display = "block";
    setTimeout(()=>{ t.style.display = "none"; },1000);
}

function render(items){
    document.getElementById("data").innerHTML =
    items.map(i=>`
        <div class="item">
            <div class="num">${i.number}</div>
            <div class="otp" onclick="copyText('${i.otp}')">${i.otp}</div>
        </div>
    `).join("");
}

function filter(){
    let q = document.getElementById("search").value;

    localStorage.setItem("searchValue", q);

    if(!q){
        render(all);
        return;
    }

    let res = all.filter(i=>match(i.number,q));

    if(res.length === 0){
        document.getElementById("data").innerHTML = "<center>No Result</center>";
        return;
    }

    render(res);
}

function clearSearch(){
    document.getElementById("search").value="";
    localStorage.removeItem("searchValue");
    render(all);
}

async function load(){
    let r = await fetch("/data?gid="+gid);
    let d = await r.json();
    all = d.items;
    filter();
}

function changeGroup(){
    gid = document.getElementById("gid").value;
    localStorage.setItem("selectedGroup", gid);
    load();
}

function init(){
    let select = document.getElementById("gid");
    let groups = %GROUPS%;

    groups.forEach((g,i)=>{
        let opt = document.createElement("option");
        opt.value = g;
        opt.innerText = "TA Range ☞ " + (i+1).toString().padStart(2,"0");
        select.appendChild(opt);
    });

    let saved = localStorage.getItem("selectedGroup");
    gid = saved && groups.includes(saved) ? saved : groups[0];
    select.value = gid;

    let s = localStorage.getItem("searchValue");
    if(s){
        document.getElementById("search").value = s;
    }

    load();
    setInterval(load,2000);
}

init();

</script>

</body>
</html>
"""

# ================= START =================
async def main():
    await client.start()

    app = web.Application()
    html = HTML.replace("%GROUPS%", str(GROUP_IDS))

    app.router.add_get("/", lambda r: web.Response(text=html, content_type="text/html"))
    app.router.add_get("/data", data)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    asyncio.create_task(background_refresh())

    print("Running on", port)

    while True:
        await asyncio.sleep(10)

asyncio.run(main())
