#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoSync — 구글 드라이브 중계 버전
"""

import os, time, secrets, logging
import requests
from flask import Flask, request, jsonify, render_template_string, redirect, session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photosync")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# 환경 변수에서 구글 인증 정보 가져오기
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "")

# 드라이브 파일 쓰기 권한
SCOPE = "https://www.googleapis.com/auth/drive.file"

# ── 클로드 디자인 유지 (HTML 생략, 위에서 사용한 디자인과 동일) ──
HTML = r"""... (위에서 사용한 클로드 디자인 HTML을 그대로 넣으세요) ..."""

@app.route("/")
def index():
    return render_template_string(HTML, authed="credentials" in session)

@app.route("/login")
def login():
    state = secrets.token_hex(16)
    session["state"] = state
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&scope={SCOPE}&access_type=offline&prompt=consent&state={state}"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"
    })
    if r.status_code == 200:
        session["credentials"] = r.json()
    return redirect("/")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files or "credentials" not in session:
        return jsonify({"ok": False, "error": "인증 필요"})
    
    f = request.files["file"]
    token = session["credentials"]["access_token"]
    
    # 구글 드라이브 업로드 API 호출
    metadata = {"name": f.filename, "parents": ["root"]} # 필요시 특정 폴더 ID 지정 가능
    files = {
        'data': ('metadata', json.dumps(metadata), 'application/json'),
        'file': f.read()
    }
    
    r = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers={"Authorization": f"Bearer {token}"},
        files=files
    )
    
    return jsonify({"ok": r.status_code == 200})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
