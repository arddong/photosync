#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoSync — 공식 Google OAuth 2.0 버전
한글 파일명 지원
"""

import os, time, json, logging, secrets
from urllib.parse import quote
import requests
from flask import Flask, request, jsonify, render_template_string, redirect, session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photosync")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI  = os.environ.get("REDIRECT_URI", "")

SCOPE      = "https://www.googleapis.com/auth/photoslibrary.appendonly"
TOKEN_FILE = "/tmp/tokens.json"

# ── 토큰 관리 ──
def save_tokens(data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f)

def load_tokens():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                return json.load(f)
    except:
        pass
    return None

def get_access_token():
    tokens = load_tokens()
    if not tokens:
        return None
    if tokens.get("expires_at", 0) > time.time() + 60:
        return tokens["access_token"]
    refresh = tokens.get("refresh_token")
    if not refresh:
        return None
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh,
        "grant_type": "refresh_token"
    })
    if r.status_code == 200:
        d = r.json()
        tokens["access_token"] = d["access_token"]
        tokens["expires_at"]   = time.time() + d.get("expires_in", 3600)
        save_tokens(tokens)
        return tokens["access_token"]
    return None

# ── 구글 포토 업로드 (한글 파일명 지원) ──
SUPPORTED = {".jpg",".jpeg",".png",".gif",".bmp",".webp",
             ".mp4",".mov",".avi",".mkv",".heic",".heif"}

def upload_to_gp(token, data, filename):
    # 한글 등 특수문자 파일명 인코딩
    safe_name = quote(filename.encode('utf-8'))

    r1 = requests.post(
        "https://photoslibrary.googleapis.com/v1/uploads",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-type": "application/octet-stream",
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-File-Name": safe_name,
        },
        data=data, timeout=120
    )
    if r1.status_code != 200:
        raise RuntimeError(f"업로드 오류 {r1.status_code}")

    r2 = requests.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate",
        headers={"Authorization": f"Bearer {token}"},
        json={"newMediaItems":[{"description":filename,
              "simpleMediaItem":{"uploadToken":r1.text}}]},
        timeout=30
    )
    if r2.status_code != 200:
        raise RuntimeError(f"등록 오류 {r2.status_code}")

# ── HTML ──
HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0d0d0d">
<title>PhotoSync</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=DM+Mono&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d0d0d;--card:#161616;--card2:#1f1f1f;--border:#2c2c2c;
  --accent:#4ade80;--blue:#60a5fa;--red:#f87171;--text:#f0f0f0;--sub:#777;--r:16px}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:'Noto Sans KR',sans-serif;background:var(--bg);color:var(--text);min-height:100dvh}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:radial-gradient(ellipse 80% 50% at 50% -10%,rgba(74,222,128,.08) 0%,transparent 60%)}
.hdr{position:sticky;top:0;z-index:50;background:rgba(13,13,13,.9);
  backdrop-filter:blur(24px);border-bottom:1px solid var(--border);
  padding:12px 18px;display:flex;align-items:center;gap:10px}
.hdr-logo{width:34px;height:34px;border-radius:10px;background:var(--accent);
  display:flex;align-items:center;justify-content:center;font-size:18px}
.hdr-name{font-size:17px;font-weight:700}
.hdr-name span{color:var(--accent)}
.hdr-badge{margin-left:auto;display:flex;align-items:center;gap:5px;
  background:var(--card2);border:1px solid var(--border);
  border-radius:99px;padding:5px 11px;font-size:11px;color:var(--sub)}
.dot{width:7px;height:7px;border-radius:50%;background:#fbbf24}
.dot.ok{background:var(--accent);box-shadow:0 0 8px var(--accent)}
.dot.err{background:var(--red)}
main{position:relative;z-index:1;padding:16px;max-width:480px;margin:0 auto}
.login-card{background:var(--card);border:1px solid var(--border);
  border-radius:var(--r);margin-bottom:14px;padding:36px 24px;text-align:center}
.login-ico{font-size:56px;margin-bottom:16px}
.login-title{font-size:20px;font-weight:700;margin-bottom:10px}
.login-sub{font-size:13px;color:var(--sub);margin-bottom:28px;line-height:1.7}
.login-btn{display:flex;align-items:center;justify-content:center;gap:10px;
  background:white;color:#333;border:none;border-radius:12px;
  padding:15px 24px;font-size:15px;font-weight:600;cursor:pointer;
  text-decoration:none;width:100%;transition:opacity .15s}
.login-btn:active{opacity:.8}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);margin-bottom:14px;overflow:hidden}
.card-hd{padding:14px 16px 0;font-size:11px;font-weight:500;color:var(--sub);letter-spacing:.08em;text-transform:uppercase}
.drop{margin:12px 16px;border:1.5px dashed var(--border);border-radius:12px;
  padding:30px 16px;text-align:center;cursor:pointer;transition:all .2s}
.drop.over{border-color:var(--accent);background:rgba(74,222,128,.04)}
.drop-ico{font-size:38px;margin-bottom:8px}
.drop-lbl{font-size:14px;color:var(--sub)}
.drop-sub{font-size:12px;color:#484848;margin-top:3px}
input[type=file]{display:none}
.thumbs{display:flex;gap:6px;overflow-x:auto;padding:0 16px 14px;scrollbar-width:none}
.thumbs::-webkit-scrollbar{display:none}
.th{flex-shrink:0;width:72px;height:72px;border-radius:9px;overflow:hidden;background:var(--card2);position:relative}
.th img{width:100%;height:100%;object-fit:cover}
.th .x{position:absolute;top:2px;right:2px;background:rgba(0,0,0,.65);color:#fff;
  border:none;border-radius:50%;width:18px;height:18px;font-size:10px;cursor:pointer;
  display:flex;align-items:center;justify-content:center}
.th .st{position:absolute;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;font-size:20px}
.th .vb{position:absolute;bottom:2px;left:2px;background:rgba(0,0,0,.6);color:#fff;font-size:9px;padding:1px 4px;border-radius:3px}
.prog{padding:10px 16px 4px}
.prog-track{height:3px;background:var(--border);border-radius:99px;overflow:hidden;margin-bottom:7px}
.prog-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--blue));transition:width .35s ease;width:0%}
.prog-row{display:flex;justify-content:space-between;font-size:11px;color:var(--sub);font-family:'DM Mono',monospace}
.prog-file{font-size:10px;color:#444;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.btns{display:flex;gap:8px;padding:0 16px 16px}
.btn{flex:1;padding:13px 8px;border:none;border-radius:11px;font-size:13px;font-weight:700;
  font-family:'Noto Sans KR',sans-serif;cursor:pointer;transition:opacity .15s,transform .1s;
  display:flex;align-items:center;justify-content:center;gap:5px}
.btn:active{transform:scale(.96);opacity:.8}
.btn:disabled{opacity:.3;cursor:not-allowed;transform:none}
.btn-g{background:var(--accent);color:#000}
.btn-s{background:var(--card2);color:var(--sub);border:1px solid var(--border)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border)}
.stat{background:var(--card);padding:14px;text-align:center}
.stat-n{font-size:22px;font-weight:700;font-family:'DM Mono',monospace}
.stat-l{font-size:10px;color:var(--sub);margin-top:2px;letter-spacing:.05em;text-transform:uppercase}
.cg{color:var(--accent)}.cb{color:var(--blue)}.cr{color:var(--red)}
.log-area{max-height:240px;overflow-y:auto;padding:4px 0}
.log-row{display:flex;align-items:flex-start;gap:9px;padding:8px 16px;border-bottom:1px solid var(--border);animation:fi .25s ease}
@keyframes fi{from{opacity:0;transform:translateY(-3px)}}
.log-row:last-child{border:none}
.log-ico{font-size:13px;flex-shrink:0;margin-top:1px}
.log-bd{flex:1;overflow:hidden}
.log-n{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.log-m{font-size:10px;color:var(--sub);margin-top:1px}
.log-t{font-size:9px;color:#3a3a3a;flex-shrink:0;font-family:'DM Mono',monospace;margin-top:2px}
.empty{padding:28px 0;text-align:center;font-size:11px;color:#3a3a3a}
</style>
</head>
<body>
<header class="hdr">
  <div class="hdr-logo">📸</div>
  <div class="hdr-name">Photo<span>Sync</span></div>
  <div class="hdr-badge">
    <div class="dot {{ 'ok' if authed else 'err' }}"></div>
    <span>{{ '구글 연결됨' if authed else '로그인 필요' }}</span>
  </div>
</header>
<main>
{% if not authed %}
<div class="login-card">
  <div class="login-ico">📸</div>
  <div class="login-title">PhotoSync</div>
  <div class="login-sub">구글 계정으로 로그인하면<br>사진이 바로 구글 포토에 업로드됩니다<br><br>최초 1회만 로그인하면 됩니다</div>
  <a href="/login" class="login-btn">
    <svg width="20" height="20" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
    Google로 로그인
  </a>
</div>
{% else %}
<div class="card">
  <div class="card-hd">사진 · 동영상 업로드</div>
  <div class="drop" id="drop" onclick="document.getElementById('fi').click()"
       ondragover="dov(event)" ondrop="ddrop(event)" ondragleave="dlv(event)">
    <div class="drop-ico">☁️</div>
    <div class="drop-lbl">탭하여 선택 또는 드래그</div>
    <div class="drop-sub">JPG · PNG · HEIC · MP4 · MOV 지원</div>
  </div>
  <input type="file" id="fi" multiple accept="image/*,video/*" onchange="add(this.files)">
  <input type="file" id="ci" accept="image/*" capture="environment" onchange="add(this.files)">
  <div class="thumbs" id="thumbs" style="display:none"></div>
  <div class="prog" id="progArea" style="display:none">
    <div class="prog-track"><div class="prog-fill" id="pf"></div></div>
    <div class="prog-row"><span id="pl">대기</span><span id="pp">0%</span></div>
    <div class="prog-file" id="pfile"></div>
  </div>
  <div class="btns">
    <button class="btn btn-s" onclick="document.getElementById('ci').click()">📷 촬영</button>
    <button class="btn btn-g" id="upBtn" onclick="go()">🚀 업로드</button>
  </div>
</div>
<div class="card">
  <div class="stats">
    <div class="stat"><div class="stat-n cb" id="sT">0</div><div class="stat-l">전체</div></div>
    <div class="stat"><div class="stat-n cg" id="sO">0</div><div class="stat-l">성공</div></div>
    <div class="stat"><div class="stat-n cr" id="sF">0</div><div class="stat-l">실패</div></div>
  </div>
</div>
<div class="card">
  <div class="card-hd" style="padding:14px 16px 6px;display:flex;justify-content:space-between;align-items:center">
    <span>업로드 로그</span>
    <button onclick="clrLog()" style="background:none;border:none;color:var(--sub);font-size:11px;cursor:pointer">지우기</button>
  </div>
  <div class="log-area" id="logArea"><div class="empty">업로드 결과가 여기에 나타납니다</div></div>
</div>
{% endif %}
</main>
<script>
let files=[],st={t:0,o:0,f:0};
function add(fs){files=[...files,...Array.from(fs)];render();}
function rm(i){files.splice(i,1);render();}
function dov(e){e.preventDefault();document.getElementById("drop").classList.add("over");}
function dlv(e){document.getElementById("drop").classList.remove("over");}
function ddrop(e){e.preventDefault();dlv(e);add(e.dataTransfer.files);}
function render(){
  const el=document.getElementById("thumbs");
  if(!files.length){el.style.display="none";return;}
  el.style.display="flex";el.innerHTML="";
  files.forEach((f,i)=>{
    const d=document.createElement("div");d.className="th";d.id="th"+i;
    if(f.type.startsWith("video/")){
      d.innerHTML=`<div style="width:100%;height:100%;background:#111;display:flex;align-items:center;justify-content:center;font-size:22px">🎬</div><span class="vb">영상</span><button class="x" onclick="rm(${i})">✕</button>`;
    }else{
      d.innerHTML=`<img src="${URL.createObjectURL(f)}"><button class="x" onclick="rm(${i})">✕</button>`;
    }
    el.appendChild(d);
  });
}
async function go(){
  if(!files.length)return;
  document.getElementById("upBtn").disabled=true;
  document.getElementById("progArea").style.display="block";
  const total=files.length;
  for(let i=0;i<files.length;i++){
    const f=files[i];
    document.getElementById("pf").style.width=Math.round(i/total*100)+"%";
    document.getElementById("pp").textContent=Math.round(i/total*100)+"%";
    document.getElementById("pl").textContent=`${i+1} / ${total}`;
    document.getElementById("pfile").textContent=f.name;
    const th=document.getElementById("th"+i);
    if(th){const s=document.createElement("div");s.className="st";s.textContent="⏫";th.appendChild(s);}
    st.t++;
    try{
      const fd=new FormData();fd.append("file",f);
      const r=await fetch("/upload",{method:"POST",body:fd});
      const d=await r.json();
      if(d.ok){st.o++;addLog("✅",f.name,"구글 포토 저장 완료");if(th)th.querySelector(".st").textContent="✅";}
      else{st.f++;addLog("❌",f.name,d.error||"오류");if(th)th.querySelector(".st").textContent="❌";}
    }catch(e){st.f++;addLog("❌",f.name,"오류");if(th)th.querySelector(".st").textContent="❌";}
    updSt();
  }
  document.getElementById("pf").style.width="100%";
  document.getElementById("pp").textContent="100%";
  document.getElementById("pl").textContent="완료 ✓";
  document.getElementById("pfile").textContent="";
  document.getElementById("upBtn").disabled=false;
  files=[];render();
}
function ts(){return new Date().toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit",second:"2-digit"});}
function addLog(ico,name,msg){
  const a=document.getElementById("logArea");
  const e=a.querySelector(".empty");if(e)e.remove();
  const d=document.createElement("div");d.className="log-row";
  d.innerHTML=`<span class="log-ico">${ico}</span><div class="log-bd"><div class="log-n">${name}</div><div class="log-m">${msg}</div></div><span class="log-t">${ts()}</span>`;
  a.insertBefore(d,a.firstChild);
}
function clrLog(){document.getElementById("logArea").innerHTML='<div class="empty">업로드 결과가 여기에 나타납니다</div>';}
function updSt(){document.getElementById("sT").textContent=st.t;document.getElementById("sO").textContent=st.o;document.getElementById("sF").textContent=st.f;}
</script>
</body>
</html>"""

# ── 라우트 ──
@app.route("/")
def index():
    return render_template_string(HTML, authed=get_access_token() is not None)

@app.route("/login")
def login():
    state = secrets.token_hex(16)
    session["state"] = state
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    })
    if r.status_code == 200:
        d = r.json()
        save_tokens({
            "access_token":  d["access_token"],
            "refresh_token": d.get("refresh_token"),
            "expires_at":    time.time() + d.get("expires_in", 3600)
        })
        log.info("✅ 로그인 성공!")
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "파일 없음"})
    f   = request.files["file"]
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in SUPPORTED:
        return jsonify({"ok": False, "error": f"미지원 형식 {ext}"})
    token = get_access_token()
    if not token:
        return jsonify({"ok": False, "error": "로그인 필요"})
    try:
        upload_to_gp(token, f.read(), f.filename)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
