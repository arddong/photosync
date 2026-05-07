#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoSync Server — Render.com 배포용
픽셀폰 ID로 구글 포토 무제한 업로드
"""

import os, time, threading, logging
import requests
from flask import Flask, request, jsonify, render_template_string

try:
    import gpsoauth
except ImportError:
    gpsoauth = None

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photosync")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB

# ──────────────────────────────────────
# 환경변수에서 설정 읽기 (Render 대시보드에서 입력)
# ──────────────────────────────────────
def cfg(key):
    return os.environ.get(key, "").strip()

# ──────────────────────────────────────
# 토큰 캐시 (50분 유효)
# ──────────────────────────────────────
_cache = {"token": None, "exp": 0}
_lock  = threading.Lock()

def get_token():
    with _lock:
        if _cache["token"] and time.time() < _cache["exp"]:
            return _cache["token"]

        if not gpsoauth:
            raise RuntimeError("gpsoauth 미설치")

        email   = cfg("EMAIL")
        passwd  = cfg("APP_PASSWORD")
        android = cfg("ANDROID_ID")

        if not all([email, passwd, android]):
            raise RuntimeError("환경변수 EMAIL / APP_PASSWORD / ANDROID_ID 미설정")

        log.info("🔑 구글 인증 중...")
        master = gpsoauth.perform_master_login(
            email=email,
            password=passwd,
            android_id=android,
            service="ac2dm",
            device_country="kr",
            operator_country="kr",
            lang="ko",
            sdk_version=28
        )
        if "Token" not in master:
            raise RuntimeError(f"마스터 로그인 실패: {master}")

        oauth = gpsoauth.perform_oauth(
            email=email,
            master_token=master["Token"],
            android_id=android,
            service="oauth2:https://www.googleapis.com/auth/photoslibrary",
            app="com.google.android.apps.photos",
            client_sig="38918a453d07199354f8b19af05ec6562ced5788",
            device_country="kr",
            operator_country="kr",
            lang="ko",
            sdk_version=28
        )
        if "Auth" not in oauth:
            raise RuntimeError(f"OAuth 실패: {oauth}")

        _cache["token"] = oauth["Auth"]
        _cache["exp"]   = time.time() + 2900
        log.info("✅ 인증 성공")
        return _cache["token"]

# ──────────────────────────────────────
# 구글 포토 업로드
# ──────────────────────────────────────
SUPPORTED = {".jpg",".jpeg",".png",".gif",".bmp",".webp",
             ".mp4",".mov",".avi",".mkv",".heic",".heif"}

def upload_to_gp(token, data, filename):
    r1 = requests.post(
        "https://photoslibrary.googleapis.com/v1/uploads",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-type": "application/octet-stream",
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-File-Name": filename,
        },
        data=data, timeout=120
    )
    if r1.status_code != 200:
        raise RuntimeError(f"업로드 토큰 오류 {r1.status_code}: {r1.text[:200]}")

    r2 = requests.post(
        "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate",
        headers={"Authorization": f"Bearer {token}"},
        json={"newMediaItems":[{"description":filename,
              "simpleMediaItem":{"uploadToken":r1.text}}]},
        timeout=30
    )
    if r2.status_code != 200:
        raise RuntimeError(f"미디어 등록 오류 {r2.status_code}: {r2.text[:200]}")

# ──────────────────────────────────────
# HTML UI
# ──────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0d0d0d">
<title>PhotoSync</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Mono&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0d0d0d; --card:#161616; --card2:#1f1f1f;
  --border:#2c2c2c; --accent:#4ade80; --blue:#60a5fa;
  --red:#f87171; --yellow:#fbbf24;
  --text:#f0f0f0; --sub:#777; --r:16px;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{
  font-family:'Noto Sans KR',sans-serif;
  background:var(--bg); color:var(--text);
  min-height:100dvh; overscroll-behavior:none;
}
/* 배경 패턴 */
body::before{
  content:''; position:fixed; inset:0; z-index:0; pointer-events:none;
  background:radial-gradient(ellipse 80% 50% at 50% -10%,
    rgba(74,222,128,.08) 0%, transparent 60%);
}

/* 헤더 */
.hdr{
  position:sticky; top:0; z-index:50;
  background:rgba(13,13,13,.9);
  backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px);
  border-bottom:1px solid var(--border);
  padding:12px 18px;
  display:flex; align-items:center; gap:10px;
}
.hdr-logo{
  width:34px; height:34px; border-radius:10px;
  background:var(--accent); display:flex;
  align-items:center; justify-content:center;
  font-size:18px; flex-shrink:0;
}
.hdr-name{font-size:17px; font-weight:700; letter-spacing:-.3px}
.hdr-name span{color:var(--accent)}
.hdr-badge{
  margin-left:auto; display:flex; align-items:center; gap:5px;
  background:var(--card2); border:1px solid var(--border);
  border-radius:99px; padding:5px 11px;
  font-size:11px; color:var(--sub);
}
.dot{width:7px;height:7px;border-radius:50%;background:var(--yellow)}
.dot.ok{background:var(--accent);box-shadow:0 0 8px var(--accent)}
.dot.err{background:var(--red)}

/* 메인 */
main{position:relative;z-index:1;padding:16px;max-width:480px;margin:0 auto}

/* 카드 */
.card{
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--r); margin-bottom:14px; overflow:hidden;
}
.card-hd{
  padding:14px 16px 0; font-size:11px; font-weight:500;
  color:var(--sub); letter-spacing:.08em; text-transform:uppercase;
}

/* 드롭존 */
.drop{
  margin:12px 16px; border:1.5px dashed var(--border);
  border-radius:12px; padding:30px 16px; text-align:center;
  cursor:pointer; transition:all .2s;
}
.drop.over{border-color:var(--accent);background:rgba(74,222,128,.04)}
.drop-ico{font-size:38px;margin-bottom:8px}
.drop-lbl{font-size:14px;color:var(--sub)}
.drop-sub{font-size:12px;color:#484848;margin-top:3px}
input[type=file]{display:none}

/* 썸네일 */
.thumbs{
  display:flex; gap:6px; overflow-x:auto;
  padding:0 16px 14px; scrollbar-width:none;
}
.thumbs::-webkit-scrollbar{display:none}
.th{
  flex-shrink:0; width:72px; height:72px;
  border-radius:9px; overflow:hidden;
  background:var(--card2); position:relative;
}
.th img{width:100%;height:100%;object-fit:cover}
.th .x{
  position:absolute;top:2px;right:2px;
  background:rgba(0,0,0,.65);color:#fff;
  border:none;border-radius:50%;
  width:18px;height:18px;font-size:10px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.th .st{
  position:absolute;inset:0;
  background:rgba(0,0,0,.55);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;
}
.th .vb{
  position:absolute;bottom:2px;left:2px;
  background:rgba(0,0,0,.6);color:#fff;
  font-size:9px;padding:1px 4px;border-radius:3px;
}

/* 프로그레스 */
.prog{padding:10px 16px 4px}
.prog-track{height:3px;background:var(--border);border-radius:99px;overflow:hidden;margin-bottom:7px}
.prog-fill{
  height:100%;border-radius:99px;
  background:linear-gradient(90deg,var(--accent),var(--blue));
  transition:width .35s ease; width:0%
}
.prog-row{display:flex;justify-content:space-between;font-size:11px;color:var(--sub);font-family:'DM Mono',monospace}
.prog-file{font-size:10px;color:#444;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* 버튼 */
.btns{display:flex;gap:8px;padding:0 16px 16px}
.btn{
  flex:1;padding:13px 8px;border:none;border-radius:11px;
  font-size:13px;font-weight:700;
  font-family:'Noto Sans KR',sans-serif;
  cursor:pointer;transition:opacity .15s,transform .1s;
  display:flex;align-items:center;justify-content:center;gap:5px;
}
.btn:active{transform:scale(.96);opacity:.8}
.btn:disabled{opacity:.3;cursor:not-allowed;transform:none}
.btn-g{background:var(--accent);color:#000}
.btn-s{background:var(--card2);color:var(--sub);border:1px solid var(--border)}

/* 통계 */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border)}
.stat{background:var(--card);padding:14px;text-align:center}
.stat-n{font-size:22px;font-weight:700;font-family:'DM Mono',monospace}
.stat-l{font-size:10px;color:var(--sub);margin-top:2px;letter-spacing:.05em;text-transform:uppercase}
.cg{color:var(--accent)} .cb{color:var(--blue)} .cr{color:var(--red)}

/* 로그 */
.log-area{max-height:240px;overflow-y:auto;padding:4px 0}
.log-row{
  display:flex;align-items:flex-start;gap:9px;
  padding:8px 16px;border-bottom:1px solid var(--border);
  animation:fi .25s ease;
}
@keyframes fi{from{opacity:0;transform:translateY(-3px)}}
.log-row:last-child{border:none}
.log-ico{font-size:13px;flex-shrink:0;margin-top:1px}
.log-bd{flex:1;overflow:hidden}
.log-n{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.log-m{font-size:10px;color:var(--sub);margin-top:1px}
.log-t{font-size:9px;color:#3a3a3a;flex-shrink:0;font-family:'DM Mono',monospace;margin-top:2px}

/* 상태 카드 */
.status-card{
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--r); margin-bottom:14px; padding:16px;
  display:flex; align-items:center; gap:12px;
}
.status-ico{font-size:28px}
.status-txt{flex:1}
.status-title{font-size:14px;font-weight:600}
.status-sub{font-size:11px;color:var(--sub);margin-top:2px}
.status-btn{
  background:var(--accent); color:#000;
  border:none; border-radius:9px;
  padding:8px 14px; font-size:12px; font-weight:700;
  cursor:pointer; white-space:nowrap;
  font-family:'Noto Sans KR',sans-serif;
}

.empty{padding:28px 0;text-align:center;font-size:11px;color:#3a3a3a}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-logo">📸</div>
  <div class="hdr-name">Photo<span>Sync</span></div>
  <div class="hdr-badge">
    <div class="dot" id="dot"></div>
    <span id="authLbl">확인 중</span>
  </div>
</header>

<main>

  <!-- 서버 상태 -->
  <div class="status-card" id="statusCard" style="display:none">
    <div class="status-ico" id="statusIco">⚠️</div>
    <div class="status-txt">
      <div class="status-title" id="statusTitle">인증 오류</div>
      <div class="status-sub"  id="statusSub"></div>
    </div>
  </div>

  <!-- 업로드 카드 -->
  <div class="card">
    <div class="card-hd">사진 · 동영상 업로드</div>

    <div class="drop" id="drop"
         onclick="document.getElementById('fi').click()"
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
      <button class="btn btn-g" id="upBtn" onclick="go()" disabled>🚀 업로드</button>
    </div>
  </div>

  <!-- 통계 -->
  <div class="card">
    <div class="stats">
      <div class="stat"><div class="stat-n cb" id="sT">0</div><div class="stat-l">전체</div></div>
      <div class="stat"><div class="stat-n cg" id="sO">0</div><div class="stat-l">성공</div></div>
      <div class="stat"><div class="stat-n cr" id="sF">0</div><div class="stat-l">실패</div></div>
    </div>
  </div>

  <!-- 로그 -->
  <div class="card">
    <div class="card-hd" style="padding:14px 16px 6px;display:flex;justify-content:space-between;align-items:center">
      <span>업로드 로그</span>
      <button onclick="clrLog()" style="background:none;border:none;color:var(--sub);font-size:11px;cursor:pointer">지우기</button>
    </div>
    <div class="log-area" id="logArea">
      <div class="empty">업로드 결과가 여기에 나타납니다</div>
    </div>
  </div>

</main>

<script>
let files=[], st={t:0,o:0,f:0}, authed=false;

// ── 인증 확인 ──
async function chkAuth(){
  try{
    const r=await fetch("/auth_check");
    const d=await r.json();
    const dot=document.getElementById("dot");
    const lbl=document.getElementById("authLbl");
    const card=document.getElementById("statusCard");
    if(d.ok){
      dot.className="dot ok"; lbl.textContent="픽셀 인증됨";
      card.style.display="none"; authed=true;
      if(files.length>0) document.getElementById("upBtn").disabled=false;
    } else {
      dot.className="dot err"; lbl.textContent="인증 오류";
      card.style.display="flex";
      document.getElementById("statusIco").textContent="⚠️";
      document.getElementById("statusTitle").textContent="인증 실패";
      document.getElementById("statusSub").textContent=d.error;
    }
  }catch(e){
    document.getElementById("authLbl").textContent="서버 오류";
  }
}
chkAuth();

// ── 파일 ──
function add(fs){ files=[...files,...Array.from(fs)]; render(); }
function rm(i){ files.splice(i,1); render(); }
function dov(e){ e.preventDefault(); document.getElementById("drop").classList.add("over"); }
function dlv(e){ document.getElementById("drop").classList.remove("over"); }
function ddrop(e){ e.preventDefault(); dlv(e); add(e.dataTransfer.files); }

function render(){
  const el=document.getElementById("thumbs");
  if(!files.length){ el.style.display="none"; return; }
  el.style.display="flex"; el.innerHTML="";
  files.forEach((f,i)=>{
    const d=document.createElement("div"); d.className="th"; d.id="th"+i;
    if(f.type.startsWith("video/")){
      d.innerHTML=`<div style="width:100%;height:100%;background:#111;display:flex;align-items:center;justify-content:center;font-size:22px">🎬</div>
        <span class="vb">영상</span><button class="x" onclick="rm(${i})">✕</button>`;
    } else {
      const u=URL.createObjectURL(f);
      d.innerHTML=`<img src="${u}"><button class="x" onclick="rm(${i})">✕</button>`;
    }
    el.appendChild(d);
  });
  if(authed) document.getElementById("upBtn").disabled=false;
}

// ── 업로드 ──
async function go(){
  if(!files.length||!authed) return;
  document.getElementById("upBtn").disabled=true;
  document.getElementById("progArea").style.display="block";
  const total=files.length;

  for(let i=0;i<files.length;i++){
    const f=files[i];
    const pct=Math.round(i/total*100);
    document.getElementById("pf").style.width=pct+"%";
    document.getElementById("pp").textContent=pct+"%";
    document.getElementById("pl").textContent=`${i+1} / ${total}`;
    document.getElementById("pfile").textContent=f.name;
    const th=document.getElementById("th"+i);
    if(th){ const s=document.createElement("div"); s.className="st"; s.textContent="⏫"; th.appendChild(s); }

    st.t++;
    try{
      const fd=new FormData(); fd.append("file",f);
      const r=await fetch("/upload",{method:"POST",body:fd});
      const d=await r.json();
      if(d.ok){
        st.o++; addLog("✅",f.name,"구글 포토 저장 완료");
        if(th) th.querySelector(".st").textContent="✅";
      } else {
        st.f++; addLog("❌",f.name,d.error||"오류");
        if(th) th.querySelector(".st").textContent="❌";
      }
    }catch(e){
      st.f++; addLog("❌",f.name,"네트워크 오류");
      if(th) th.querySelector(".st").textContent="❌";
    }
    updSt();
  }
  document.getElementById("pf").style.width="100%";
  document.getElementById("pp").textContent="100%";
  document.getElementById("pl").textContent="완료 ✓";
  document.getElementById("pfile").textContent="";
  document.getElementById("upBtn").disabled=false;
  files=[]; render();
}

// ── 로그 ──
function ts(){ return new Date().toLocaleTimeString("ko-KR",{hour:"2-digit",minute:"2-digit",second:"2-digit"}); }
function addLog(ico,name,msg){
  const a=document.getElementById("logArea");
  const e=a.querySelector(".empty"); if(e) e.remove();
  const d=document.createElement("div"); d.className="log-row";
  d.innerHTML=`<span class="log-ico">${ico}</span>
    <div class="log-bd"><div class="log-n">${name}</div><div class="log-m">${msg}</div></div>
    <span class="log-t">${ts()}</span>`;
  a.insertBefore(d,a.firstChild);
}
function clrLog(){ document.getElementById("logArea").innerHTML='<div class="empty">업로드 결과가 여기에 나타납니다</div>'; }
function updSt(){
  document.getElementById("sT").textContent=st.t;
  document.getElementById("sO").textContent=st.o;
  document.getElementById("sF").textContent=st.f;
}
</script>
</body>
</html>
"""

# ──────────────────────────────────────
# 라우트
# ──────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/auth_check")
def auth_check():
    try:
        get_token()
        return jsonify({"ok": True, "email": cfg("EMAIL")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "파일 없음"})
    f   = request.files["file"]
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in SUPPORTED:
        return jsonify({"ok": False, "error": f"미지원 형식 {ext}"})
    try:
        token = get_token()
        upload_to_gp(token, f.read(), f.filename)
        return jsonify({"ok": True})
    except Exception as e:
        log.error(f"Upload error: {e}")
        return jsonify({"ok": False, "error": str(e)})

@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
