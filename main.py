import re
import asyncio
import os
from aiohttp import web
from telethon import TelegramClient

# ================= CONFIG =================
api_id = int(os.getenv("API_ID", "123456"))
api_hash = os.getenv("API_HASH", "your_api_hash")

GROUP_RULES = {
    "-1003771161345": (7, 2),
    "-1002531902737": (4, 4),
    "-1002567258773": (5, 4),
    "-1002652123574": (4, 4),
    "-1003861246919": (3, 4),

    "-1003435291410": (3, 4),
    "-1003775658194": (4, 4),
    "-1002898987582": (2, 4),

    "-1003463811076": (2, 4),
    "-1003357916577": (5, 4),
}

LIMIT = 200

client = TelegramClient("otp_session", api_id, api_hash)

CACHE = {"gid": None, "items": []}
CURRENT_TASK = None

# ================= PARSER =================
def extract_number(text):
    m = re.search(r'Number[:\-]?\s*([+\dXx*\•\s]+)', text)
    if m:
        return m.group(1).strip()

    m = re.search(r'[\+\d][\dXx*\•\s]{6,}', text)
    if m:
        return m.group(0).strip()

    m = re.search(r'(\d{5,}TNE\d{3,})', text)
    if m:
        return m.group(1)

    return None


def extract_otp(text):
    lines = text.splitlines()

    for line in lines:
        # OTP / Code label থাকলে
        m = re.search(r'(OTP|Code)[:\-]?\s*([\d\s]{4,8})', line, re.I)
        if m:
            otp = re.sub(r'\s', '', m.group(2))
            if 5 <= len(otp) <= 7:
                return otp

        # pure number line
        nums = re.findall(r'\b\d{5,7}\b', line)
        if nums:
            return nums[-1]

    return None


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

    async for msg in client.iter_messages(int(gid), limit=500):
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

        if len(items) >= LIMIT:
            break

    CACHE["gid"] = gid
    CACHE["items"] = items


# ================= LIVE REFRESH =================
async def auto_refresh(gid):
    while True:
        try:
            await build_cache(gid)
        except Exception as e:
            print("Refresh error:", e)
        await asyncio.sleep(2)


# ================= API =================
async def data(request):
    global CURRENT_TASK

    gid = request.query.get("gid")

    if CACHE["gid"] != gid:
        if CURRENT_TASK:
            CURRENT_TASK.cancel()

        await build_cache(gid)
        CURRENT_TASK = asyncio.create_task(auto_refresh(gid))

    return web.json_response({"items": CACHE["items"]})


# ================= HTML =================
HTML = """
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>LIVE OTP</title>

<style>
body{margin:0;font-family:sans-serif;background:#0f172a;color:white}
.header{text-align:center;padding:12px;font-weight:bold}
select{width:95%;margin:5px;padding:10px;border-radius:10px}
.searchbox{display:flex;padding:5px}
.searchbox input{flex:1;padding:10px;border-radius:10px;border:none}
.clear{background:red;color:white;padding:10px;border-radius:10px;margin-left:5px}
.item{margin:6px;padding:10px;border-radius:10px;border:2px solid red;display:flex;gap:10px}
.num{flex:1;background:#3b82f6;color:black;padding:10px;border-radius:10px;text-align:center;font-weight:bold}
.otp{flex:1;background:#4ade80;color:black;padding:10px;border-radius:10px;text-align:center;font-weight:bold;cursor:pointer}
</style>
</head>

<body>

<div class="header">TAMIM ANU LIVE OTP SYSTEM</div>

<select id="gid" onchange="changeGroup()"></select>

<div class="searchbox">
<input id="search" placeholder="Paste number & Search..." oninput="filter()">
<button class="clear" onclick="clearSearch()">Clear</button>
</div>

<div id="data"></div>

<script>
let all = [];
let gid = "";
let rules = %RULES%;

function normalize(x){
    return x.replace(/[^0-9]/g,'');
}

function match(num, query){
    let n = normalize(num);
    let q = normalize(query);

    if(!q) return true;

    let rule = rules[gid];
    let f = n.slice(0, rule[0]);
    let l = n.slice(-rule[1]);

    return q.startsWith(f) && q.endsWith(l);
}

function copyOTP(text){
    navigator.clipboard.writeText(text);
}

function render(items){
    document.getElementById("data").innerHTML =
    items.map(i=>`
        <div class="item">
            <div class="num">${i.number}</div>
            <div class="otp" onclick="copyOTP('${i.otp}')">${i.otp}</div>
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
    let groups = Object.keys(rules);

    groups.forEach((g,i)=>{
        let opt = document.createElement("option");
        opt.value = g;
        opt.innerText = "TA Number Range ID ☞ " + (i+1).toString().padStart(2,"0");
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
    print("Telegram Connected ✅")

    app = web.Application()
    html = HTML.replace("%RULES%", str(GROUP_RULES))

    app.router.add_get("/", lambda r: web.Response(text=html, content_type="text/html"))
    app.router.add_get("/data", data)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print("Server Running on", port)

    while True:
        await asyncio.sleep(10)

asyncio.run(main())
