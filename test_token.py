import os
from dotenv import load_dotenv
import requests

load_dotenv()

SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
URL = "https://smart-gr-pro.myshopify.com/admin/api/2024-01/shop.json"

response = requests.get(URL, headers={"X-Shopify-Access-Token": SHOPIFY_TOKEN})

print(f"Status code: {response.status_code}")
print(f"Resposta: {response.json()}")
