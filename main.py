from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import datetime
import os
import json
import logging
import sys

# ===================== 第一重保险：提前禁用所有uvicorn日志 =====================
# 必须在uvicorn.run()之前执行
logging.getLogger("uvicorn").disabled = True
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn.error").disabled = True
logging.getLogger("uvicorn.asgi").disabled = True

# 把根日志级别设为最高，只显示致命错误
logging.basicConfig(level=logging.CRITICAL)
# ==================================================================

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "chat_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SETUP_EXE = os.path.join(BASE_DIR, "Ravenchat_Setup.exe")

if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        CHAT_HISTORY = json.load(f)
else:
    CHAT_HISTORY = []


def save_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(CHAT_HISTORY, f, ensure_ascii=False, indent=2)


@app.get("/chat/uploads/{filename}")
async def get_upload(filename: str):
    return FileResponse(os.path.join(UPLOAD_FOLDER, filename))


@app.get("/chat/download/pc")
async def download_pc():
    return FileResponse(SETUP_EXE, filename="Ravenchat_Setup.exe")


@app.get("/chat/manifest.json")
async def manifest():
    return {
        "name": "Raven Chat",
        "short_name": "Raven",
        "start_url": "/chat",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007bff",
        "icons": [
            {
                "src": "/static/raven-icon.png",
                "sizes": "1024x1024",
                "type": "image/png"
            }
        ]
    }


def get_country(ip: str):
    return ""


@app.get("/chat")
async def chat():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link rel="manifest" href="/chat/manifest.json">
<title>Raven Chat</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    background:#fff;
    font-family:Arial,sans-serif;
    height:100vh;
    display:flex;
    flex-direction:column;
    padding:12px;
    font-size:16px;
}

/* 左上角菜单按钮 */
.menu-btn {
    position: fixed;
    top: 10px;
    left: 12px;
    width: 36px;
    height: 36px;
    background: #f0f0f0;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    z-index: 998;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: bold;
    color: #333;
}

/* 下拉菜单 */
.menu-dropdown {
    position: fixed;
    top: 52px;
    left: 12px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
    padding: 8px 16px;
    z-index: 997;
    display: none;
    min-width: 160px;
}
.menu-dropdown a {
    display: block;
    padding: 10px 0;
    text-decoration: none;
    color: #007bff;
    font-weight: 500;
    font-size: 15px;
}
.menu-dropdown.show {
    display: block;
}

/* 点击空白关闭菜单 */
.menu-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 996;
    display: none;
}
.menu-overlay.show {
    display: block;
}

#mode-select {
    position:fixed; top:0; left:0; width:100%; height:100%;
    background:white; display:flex; align-items:center; justify-content:center;
    z-index:999; flex-direction:column; gap:20px;
}
#mode-select button {
    padding:16px 30px; font-size:18px; border-radius:16px; border:none;
    font-weight:bold; width:80%;
}
.btn-cn { background:#007bff; color:white; }
.btn-foreign { background:#28a745; color:white; }

#chat-container {
    flex:1; overflow-y:auto; padding-bottom:15px; margin-bottom:8px;
    padding-top: 55px;
}
.msg {
    margin:12px 0; padding:14px; border-radius:14px; max-width:80%;
    font-size:16px; line-height:1.3;
}
.me { background:#007bff; color:white; margin-left:auto; text-align:right; }
.other { background:#28a745; color:white; margin-right:auto; }
.time { font-size:14px; color:#fff; margin-top:8px; }
.input-bar { display:flex; flex-direction:column; gap:6px; }
input[type="text"], button, .custom-file-btn {
    width:100%; padding:8px 12px; font-size:16px; border-radius:12px; border:1px solid #ddd;
}
button { background:#007bff; color:white; font-weight:bold; border:none; }
button:disabled { background:#cccccc !important; color:#666666 !important; }
.status { font-size:14px; text-align:center; padding:2px; color:#333; }
.msg img { width:100%; border-radius:10px; margin-bottom:10px; }
#img { opacity:0.01; position:absolute; pointer-events:none; }
.custom-file-btn { background:#f5f5f5; text-align:center; cursor:pointer; }
.file-selected { background:#e3f2fd; color:#007bff; }
</style>
</head>
<body>

<!-- 左上角菜单 -->
<button class="menu-btn" onclick="toggleMenu()">•••</button>
<div class="menu-overlay" id="overlay" onclick="toggleMenu()"></div>
<div class="menu-dropdown" id="menu">
    <a href="/chat/download/pc" target="_blank">Download PC Version</a>
</div>

<div id="mode-select">
    <h3>Choose your identity</h3>
    <button class="btn-cn" onclick="setMode(true)">I am in China</button>
    <button class="btn-foreign" onclick="setMode(false)">I am in Cambodia</button>
</div>

<div id="chat-container"></div>
<div id="status" class="status"></div>

<div class="input-bar">
    <input type="text" id="text" placeholder="Type your message...">
    <button id="sendBtn" onclick="send()" disabled>Send Message</button>
    <div class="custom-file-btn" id="fileLabel" onclick="document.getElementById('img').click()">Select Image</div>
    <input type="file" id="img" accept="image/*">
</div>

<script>
let lastCount = 0;
let sending = false;
let isMeCN = false;

// 菜单开关
function toggleMenu() {
    const menu = document.getElementById('menu');
    const overlay = document.getElementById('overlay');
    menu.classList.toggle('show');
    overlay.classList.toggle('show');
}

function setMode(cn) {
    isMeCN = cn;
    document.getElementById("mode-select").style.display = "none";
    load();
}

document.getElementById('text').addEventListener('input', checkButton);
document.getElementById('img').addEventListener('change', onFileSelect);

function onFileSelect(){
    checkButton();
    const label = document.getElementById('fileLabel');
    if(document.getElementById('img').files.length > 0){
        label.innerText = "Image Selected";
        label.classList.add('file-selected');
    }else{
        label.innerText = "Select Image";
        label.classList.remove('file-selected');
    }
}

function checkButton(){
    let txt = document.getElementById('text').value.trim();
    let img = document.getElementById('img').files.length > 0;
    document.getElementById('sendBtn').disabled = (txt === '' && !img);
}

checkButton();

async function load(){
    let res = await fetch('/chat/history');
    let data = await res.json();
    let box = document.getElementById('chat-container');

    const isAtBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 10;
    const isNewMessage = data.length > lastCount;
    lastCount = data.length;

    box.innerHTML = '';
    data.forEach(m => {
        let div = document.createElement('div');
        div.className = 'msg ' + (m.me ? 'me' : 'other');
        let content = '';
        if (m.image) content += `<img src="/chat/uploads/${m.image}">`;
        div.innerHTML = content + m.content + '<div class="time">'+m.time+'</div>';
        box.appendChild(div);
    });

    if (isAtBottom && isNewMessage) {
        box.scrollTop = box.scrollHeight;
    }
}

async function send(){
    if (sending) return;
    sending = true;

    let btn = document.getElementById('sendBtn');
    let txt = document.getElementById('text');
    let img = document.getElementById('img');
    let status = document.getElementById('status');
    let fileLabel = document.getElementById('fileLabel');

    btn.disabled = true;
    btn.innerText = "Sending...";
    status.innerText = "Sending message...";

    let form = new FormData();
    if (txt.value.trim()) form.append('text', txt.value.trim());
    if (img.files[0]) form.append('image', img.files[0]);
    form.append('is_cn', isMeCN ? '1' : '0');

    try {
        let res = await fetch('/chat/send-combined', { method: 'POST', body: form });
        let data = await res.json();
        if (data.status === "ok") {
            status.innerText = "Sent successfully!";
        } else {
            status.innerText = "Send failed: " + (data.msg || "unknown error");
        }
    } catch (e) {
        status.innerText = "Send failed: " + e;
    }

    setTimeout(() => status.innerText = "", 1500);
    txt.value = "";
    img.value = "";
    btn.innerText = "Send Message";
    fileLabel.innerText = "Select Image";
    fileLabel.classList.remove('file-selected');
    sending = false;
    checkButton();
    load();
}

setInterval(load, 3000);
</script>
</body>
</html>
""")


@app.post("/chat/send-combined")
async def send_combined(request: Request):
    form = await request.form()
    text = form.get("text", "").strip()
    image_file = form.get("image")
    is_cn = form.get("is_cn", "0") == "1"

    if not text and not (image_file and hasattr(image_file, "filename")):
        return {"status": "error", "msg": "empty"}

    now = datetime.datetime.now().strftime("%m-%d %H:%M")

    msg = {
        "time": now,
        "content": text,
        "image": None,
        "me": is_cn
    }

    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.split(".")[-1] if "." in image_file.filename else "jpg"
        fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        path = os.path.join(UPLOAD_FOLDER, fn)
        with open(path, "wb") as f:
            f.write(await image_file.read())
        msg["image"] = fn

    CHAT_HISTORY.append(msg)
    save_history()
    return {"status": "ok"}


@app.get("/chat/history")
async def history():
    return CHAT_HISTORY


if __name__ == "__main__":
    # ===================== 第二重保险：uvicorn启动参数关闭日志 =====================
    # ===================== 第三重保险：使用空的日志配置 =====================
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8901,
        access_log=False,  # 直接关闭访问日志
        log_config={
            "version": 1,
            "disable_existing_loggers": True,
            "handlers": {},
            "loggers": {}
        }
    )