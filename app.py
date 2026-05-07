#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhotoSync — 픽셀폰 중계 통로 버전
디자인 유지 + 로컬 저장 기능 추가
"""

import os, time, json, logging, secrets
from flask import Flask, request, jsonify, render_template_string, redirect, session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("photosync")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

# ── [중요] 사진이 저장될 경로 설정 ──
# Render 환경에서는 /opt/render/project/src/downloads 또는 /tmp 를 사용합니다.
UPLOAD_FOLDER = "downloads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 업로드 허용 확장자
SUPPORTED = {".jpg",".jpeg",".png",".gif",".bmp",".webp",
             ".mp4",".mov",".avi",".mkv",".heic",".heif"}

# ── 클로드가 입혀준 HTML 디자인 (그대로 유지) ──
# (중략된 부분은 기존 HTML과 동일하며, 스크립트의 fetch 경로만 유지됩니다)
HTML = r"""... (클로드가 짜준 기존 HTML 소스 전체를 여기에 넣으세요) ..."""
# ※ 팁: 클로드 코드의 HTML 부분만 변수명에 맞춰 그대로 두시면 디자인이 유지됩니다.

# ── 라우트 (통로 개방) ──

@app.route("/")
def index():
    # 현재는 중계 통로 방식이므로 구글 로그인은 선택사항입니다.
    # 디자인 유지를 위해 무조건 로그인 된 것처럼 처리하거나 자유롭게 두셔도 됩니다.
    return render_template_string(HTML, authed=True)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "파일 없음"})
    
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"ok": False, "error": "파일명 없음"})

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in SUPPORTED:
        return jsonify({"ok": False, "error": f"미지원 형식 {ext}"})

    try:
        # ── 핵심: 구글 포토 API 대신 서버 로컬 폴더에 저장 ──
        # 파일명 중복 방지를 위해 타임스탬프 추가
        save_name = f"{int(time.time())}_{f.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, save_name)
        
        f.save(save_path)
        
        log.info(f"✅ 서버 저장 완료: {save_path}")
        return jsonify({"ok": True, "msg": "서버 전송 완료 (픽셀폰 대기 중)"})
        
    except Exception as e:
        log.error(f"❌ 저장 오류: {str(e)}")
        return jsonify({"ok": False, "error": str(e)})

@app.route("/ping")
def ping():
    return "pong", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
