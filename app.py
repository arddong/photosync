#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoSync — 픽셀폰 중계 통로 버전 (디자인 유지 + 로컬 저장)
"""

import os, time, json, logging, secrets
from flask import Flask, request, jsonify, render_template_string, redirect, session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photosync")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# ── [중요] 사진이 저장될 경로 ──
UPLOAD_FOLDER = "downloads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

SUPPORTED = {".jpg",".jpeg",".png",".gif",".bmp",".webp",
             ".mp4",".mov",".avi",".mkv",".heic",".heif"}

# ── 클로드가 준 디자인 그대로 유지 ──
HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
main{position:relative;z-index:1;padding:16px;max-width:480px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);margin-bottom:14px;overflow:hidden}
.card-hd{padding:14px 16px 0;font-size:11px;font-weight:500;color:var(--sub);letter-spacing:.08em;text-transform:uppercase}
.drop{margin:12px 16px;border:1.5px dashed var(--border);border-radius:12px;
  padding:30px 16px;text-align:center;cursor:pointer;transition:all .2s}
.drop.over{border-color:var(--accent);background:rgba(74,222,128,.04)}
.drop-ico{font-size:38px;margin-bottom:8px}
.drop-lbl{font-size:14px;color:var(--sub)}
input[type=file]{display:none}
.thumbs{display:flex;gap:6px;overflow-x:auto;padding:0 16px 14px;scrollbar-width:none}
.th{flex-shrink:0;width:72px;height:72px;border-radius:9px;overflow:hidden;background:var(--card2);position:relative}
.th img{width:100%;height:100%;object-fit:cover}
.th .x{position:absolute;top:2px;right:2px;background:rgba(0,0,0,.65);color:#fff;border:none;border-radius:50%;width:18px;height:18px;font-size:10px;cursor:pointer;display:flex;align-items:center;justify-content:center}
.th .st{position:absolute;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;font-size:20px}
.prog{padding:10px 16px 4px}
.prog-track{height:3px;background:var(--border);border-radius:99px;overflow:hidden;margin-bottom:7px}
.prog-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--blue));transition:width .35s ease;width:0%}
.prog-row{display:flex;justify-content:space-between;font-size:11px;color:var(--sub);font-family:'DM Mono',monospace}
.btns{display:flex;gap:8px;padding:0 16px 16px}
.btn{flex:1;padding:13px 8px;border:none;border-radius:11px;font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:5px}
.btn-g{background:var(--accent);color:#000}
.btn-s{background:var(--card2);color:var(--sub);border:1px solid var(--border)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border)}
.stat{background:var(--card);padding:14px;text-align:center}
.stat-n{font-size:22px;font-weight:700;font-family:'DM Mono',monospace}
.stat-l{font-size:10px;color:var(--sub)}
.cg{color:var(--accent)}.cb{color:var(--blue)}.cr{color:var(--red)}
.log-area{max-height:240px;overflow-y:auto;padding:4px 0}
.log-row{display:flex;align-items:flex-start;gap:9px;padding:8px 16px;border-bottom:1px solid var(--border)}
.log-ico{font-size:13px;flex-shrink:0}
.log-bd{flex:1;overflow:hidden}
.log-n{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.log-m{font-size:10px;color:var(--sub)}
.empty{padding:28px 0;text-align:center;font-size:11px;color:#3a3a3a}
</style>
</head>
<body>
<header class="hdr">
  <div class="hdr-logo">📸</div>
  <div class="hdr-name">Photo<span>Sync</span></div>
  <div class="hdr-badge"><div class="dot ok"></div><span>중계 서버 가동 중</span></div>
</header>
<main>
<div class="card">
  <div class="card-hd">픽셀폰으로 전송</div>
  <div class="drop" id="drop" onclick="document.getElementById('fi').click()"
       ondragover="dov(event)" ondrop="ddrop(event)" ondragleave="dlv(event)">
    <div class="drop-ico">☁️</div>
    <div class="drop-lbl">탭하여 선택 또는 드래그</div>
  </div>
  <input type="file" id="fi" multiple accept="image/*,video/*" onchange="add(this.files)">
  <div class="thumbs" id="thumbs" style="display:none"></div>
  <div class="prog" id="progArea" style="display:none">
    <div class="prog-track"><div class="prog-fill" id="pf"></div></div>
    <div class="prog-row"><span id="pl">대기</span><span id="pp">0%</span></div>
  </div>
  <div class="btns">
    <button class="btn btn-s" onclick="location.reload()">🔄 새로고침</button>
    <button class="btn btn-g" id="upBtn" onclick="go()">🚀 서버로 전송</button>
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
  <div class="card-hd" style="padding:14px 16px 6px">실시간 전송 로그</div>
  <div class="log-area" id="logArea"><div class="empty">전송 결과가 여기에 나타납니다</div></div>
</div>
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
    d.innerHTML=`<img src="${URL.createObjectURL(f)}"><button class="x" onclick="rm(${i})">✕</button>`;
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
    document.getElementById("pf").style.width=Math.round((i+1)/total*100)+"%";
    document.getElementById("pp").textContent=Math.round((i+1)/total*100)+"%";
    document.getElementById("pl").textContent=`${i+1} / ${total}`;
    const th=document.getElementById("th"+i);
    if(th){const s=document.createElement("div");s.className="st";s.textContent="⏫";th.appendChild(s);}
    st.t++;
    try{
      const fd=new FormData();fd.append("file",f);
      const r=await fetch("/upload",{method:"POST",body:fd});
      const d=await r.json();
      if(d.ok){st.o++;addLog("✅",f.name,"서버 저장 완료");if(th)th.querySelector(".st").textContent="✅";}
      else{st.f++;addLog("❌",f.name,d.error||"오류");}
    }catch(e){st.f++;addLog("❌",f.name,"오류");}
    updSt();
  }
  document.getElementById("upBtn").disabled=false;
  files=[];render();
}
function addLog(ico,name,msg){
  const a=document.getElementById("logArea");
  const e=a.querySelector(".empty");if(e)e.remove();
  const d=document.createElement("div");d.className="log-row";
  d.innerHTML=`<span class="log-ico">${ico}</span><div class="log-bd"><div class="log-n">${name}</div><div class="log-m">${msg}</div></div>`;
  a.insertBefore(d,a.firstChild);
}
function updSt(){document.getElementById("sT").textContent=st.t;document.getElementById("sO").textContent=st.o;document.getElementById("sF").textContent=st.f;}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "파일 없음"})
    f = request.files["file"]
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in SUPPORTED:
        return jsonify({"ok": False, "error": f"미지원 형식 {ext}"})
    try:
        # 파일명 중복 방지를 위해 타임스탬프 결합
        save_name = f"{int(time.time())}_{f.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, save_name)
        f.save(save_path)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
