import os
import sys
import webbrowser
import argparse
import requests as http_requests
from dotenv import load_dotenv, set_key
from google.ads.googleads.client import GoogleAdsClient

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
LOGIN_CUSTOMER_ID = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

SCOPE = "https://www.googleapis.com/auth/adwords"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    from urllib.parse import urlencode
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code(code):
    resp = http_requests.post(TOKEN_URI, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    data = resp.json()
    if "refresh_token" not in data:
        print("Resposta da API:", data)
        raise ValueError("refresh_token não retornado. Verifique se o app está em modo de teste com seu e-mail adicionado.")
    return data["refresh_token"]


def list_child_accounts(refresh_token):
    client = GoogleAdsClient.load_from_dict({
        "developer_token": DEVELOPER_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "login_customer_id": LOGIN_CUSTOMER_ID,
        "use_proto_plus": True,
    })

    service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            customer_client.descriptive_name,
            customer_client.id,
            customer_client.manager
        FROM customer_client
        WHERE customer_client.level = 1
    """
    response = service.search(customer_id=LOGIN_CUSTOMER_ID, query=query)

    print(f"\nContas filhas da MCC {LOGIN_CUSTOMER_ID}:\n")
    print(f"{'ID':<15} {'Nome'}")
    print("-" * 50)
    for row in response:
        c = row.customer_client
        if not c.manager:
            print(f"{c.id:<15} {c.descriptive_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", help="Código de autorização do Google OAuth2")
    args = parser.parse_args()

    refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")

    if not refresh_token:
        if args.code:
            print("Trocando código por refresh token...")
            refresh_token = exchange_code(args.code)
            set_key(ENV_FILE, "GOOGLE_ADS_REFRESH_TOKEN", refresh_token)
            print("Refresh token salvo no .env com sucesso.\n")
        else:
            auth_url = build_auth_url()
            print("Abrindo navegador para autorização...\n")
            webbrowser.open(auth_url)
            print("Se o navegador não abrir, acesse:\n")
            print(auth_url)
            print("\nDepois rode:")
            print(f'  python google_ads_auth.py --code=SEU_CODIGO\n')
            return
    else:
        print("Refresh token encontrado no .env.\n")

    list_child_accounts(refresh_token)


if __name__ == "__main__":
    main()
