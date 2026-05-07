import os
from flask import Flask, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "arddong-default-key")

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.appendonly']

def get_flow():
    redirect_uri = request.url_root.rstrip('/') + '/callback'
    # 로컬 테스트 환경이 아닐 때 https 강제 적용 (Render용)
    if 'onrender.com' in redirect_uri:
        redirect_uri = redirect_uri.replace('http://', 'https://')
        
    return Flow.from_client_config(
        {"web": {
            "client_id": CLIENT_ID, 
            "client_secret": CLIENT_SECRET, 
            "auth_uri": "https://accounts.google.com/o/oauth2/auth", 
            "token_uri": "https://oauth2.googleapis.com/token"
        }},
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

@app.route('/')
def index():
    if 'credentials' not in session:
        return '<h1>PhotoSync ON</h1><p>알똥미디어 서버가 준비되었습니다.</p><a href="/login">🔑 구글 로그인으로 시작하기</a>'
    return '<h1>✅ 인증 성공!</h1><p>이제 구글 포토와 연결되었습니다.</p>'

@app.route('/login')
def login():
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/callback')
def callback():
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url.replace('http://', 'https://'))
    session['credentials'] = flow.credentials.to_json()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
