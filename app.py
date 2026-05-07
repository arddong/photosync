import os
from flask import Flask, redirect, url_for, session, request, render_template_string
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "arddong-special-key")

# 구글 API 설정
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.upload', 'https://www.googleapis.com/auth/photoslibrary.appendonly']

def get_flow():
    return Flow.from_client_config(
        {"web": {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}},
        scopes=SCOPES,
        redirect_uri=request.url_root.rstrip('/') + '/callback'
    )

@app.route('/')
def index():
    if 'credentials' not in session:
        return '<h1>PhotoSync 서버 가동 중</h1><a href="/login">구글 로그인으로 서버 인증하기</a>'
    return '''
        <h1>PhotoSync - 픽셀폰 무제한 업로드</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">업로드</button>
        </form>
    '''

@app.route('/login')
def login():
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/callback')
def callback():
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)
    session['credentials'] = flow.credentials.to_json()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload():
    # 실제 업로드 로직은 성공 시 제가 추가로 보강해 드릴게요! 
    return "인증 성공! 이제 사진을 보낼 준비가 되었습니다."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
