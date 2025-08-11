from flask import Flask, request, jsonify, render_template, url_for, session, redirect
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from functions import validate_user

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'


oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    },
    redirect_uri=os.getenv('GOOGLE_REDIRECT_URI'),
)


@app.route('/')
def home():
    if session.get('user'):
        user = session['user']
        validate_user(user)
        picture = session.get('picture')
        return render_template('home.html')

    return render_template('index.html')


@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    token = google.authorize_access_token()
    user_info = google.get(
        'https://openidconnect.googleapis.com/v1/userinfo').json()
    session['user'] = user_info
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
