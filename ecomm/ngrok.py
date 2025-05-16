from django.conf import settings
from pyngrok import ngrok
import os
from dotenv import load_dotenv

load_dotenv()

def start_ngrok():
    # Lấy NGROK_AUTH_TOKEN từ biến môi trường
    auth_token = os.getenv('NGROK_AUTH_TOKEN')
    if auth_token:
        ngrok.set_auth_token(auth_token)

    # Khởi động tunnel
    tunnel = ngrok.connect(8000)
    public_url = tunnel.public_url
    print(f'ngrok tunnel "{public_url}" -> "http://127.0.0.1:8000"')

    # Cập nhật ALLOWED_HOSTS
    settings.ALLOWED_HOSTS.append(public_url.replace('https://', '').replace('http://', ''))

    return public_url 