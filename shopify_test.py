import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv
import requests

load_dotenv()

SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
STORE_URL = "https://smart-gr-pro.myshopify.com"
API_VERSION = "2024-01"
BASE_URL = f"{STORE_URL}/admin/api/{API_VERSION}"

HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json",
}


def fetch_orders(start_dt, end_dt):
    orders = []
    url = f"{BASE_URL}/orders.json"
    params = {
        "financial_status": "paid",
        "created_at_min": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at_max": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 250,
        "status": "any",
    }

    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        orders.extend(data.get("orders", []))

        link_header = response.headers.get("Link", "")
        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
                break

        url = next_url
        params = {}

    return orders


def is_google_ads(order):
    referring = (order.get("referring_site") or "").lower()
    landing = (order.get("landing_site") or "").lower()
    source = (order.get("source_name") or "").lower()

    if "google" in referring:
        return True
    if any(p in landing for p in ("gclid", "gad_source", "utm_source=google")):
        return True
    if source == "google":
        return True
    if source == "direct" and not referring:
        return False
    return False


def product_stats(orders, top_n=20):
    sales = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    for order in orders:
        for item in order.get("line_items", []):
            title = item.get("title", "Unknown")
            qty = item.get("quantity", 0)
            price = float(item.get("price", 0)) * qty
            sales[title]["quantity"] += qty
            sales[title]["revenue"] += price
    ranked = sorted(sales.items(), key=lambda x: x[1]["quantity"], reverse=True)
    return ranked[:top_n]


def get_period_data(start_dt, end_dt):
    orders = fetch_orders(start_dt, end_dt)
    google_orders = [o for o in orders if is_google_ads(o)]

    all_revenue = sum(float(o["total_price"]) for o in orders)
    g_revenue = sum(float(o["total_price"]) for o in google_orders)

    return {
        "start": start_dt,
        "end": end_dt,
        "all_orders": len(orders),
        "all_revenue": all_revenue,
        "all_ticket": all_revenue / len(orders) if orders else 0,
        "google_orders": len(google_orders),
        "google_revenue": g_revenue,
        "google_ticket": g_revenue / len(google_orders) if google_orders else 0,
        "products": product_stats(google_orders, top_n=20),
    }


def pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def fmt_pct(val):
    if val is None:
        return "  n/a"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def print_comparison(cur, prev):
    label_w = 22

    def row(label, c_val, p_val, fmt=",.2f", prefix="R$ "):
        change = pct(c_val, p_val)
        print(
            f"  {label:<{label_w}} {prefix}{c_val:{fmt}}  |  {prefix}{p_val:{fmt}}  |  {fmt_pct(change)}"
        )

    period_cur = f"{cur['start'].strftime('%d/%m')} – {cur['end'].strftime('%d/%m/%Y')}"
    period_prev = f"{prev['start'].strftime('%d/%m')} – {prev['end'].strftime('%d/%m/%Y')}"
    print(f"\n{'':24} {'Atual':^22}  {'Anterior':^22}  {'Var%':>7}")
    print(f"{'':24} {period_cur:^22}  {period_prev:^22}")
    print("  " + "-" * 72)

    print("  GERAL")
    row("Pedidos", cur["all_orders"], prev["all_orders"], fmt=",d", prefix="")
    row("Receita", cur["all_revenue"], prev["all_revenue"])
    row("Ticket médio", cur["all_ticket"], prev["all_ticket"])

    print("  GOOGLE ADS (último clique não direto)")
    row("Pedidos", cur["google_orders"], prev["google_orders"], fmt=",d", prefix="")
    row("Receita", cur["google_revenue"], prev["google_revenue"])
    row("Ticket médio", cur["google_ticket"], prev["google_ticket"])


def print_products(products, prev_products):
    prev_map = {name: s for name, s in prev_products}
    col = max((len(n) for n, _ in products), default=10)
    col = max(col, 10)

    print(f"\n  {'#':>3}  {'Produto':<{col}}  {'Qtd':>7}  {'Receita':>13}  {'Ticket':>10}  {'Var Qtd':>8}")
    print("  " + "-" * (col + 52))

    for i, (name, s) in enumerate(products, 1):
        prev = prev_map.get(name, {"quantity": 0, "revenue": 0.0})
        change = pct(s["quantity"], prev["quantity"])
        ticket = s["revenue"] / s["quantity"] if s["quantity"] else 0
        print(
            f"  {i:>3}.  {name:<{col}}  "
            f"{s['quantity']:>7,}  "
            f"R$ {s['revenue']:>10,.2f}  "
            f"R$ {ticket:>7,.2f}  "
            f"{fmt_pct(change):>8}"
        )


def main():
    if not SHOPIFY_TOKEN:
        raise ValueError("SHOPIFY_TOKEN não encontrado no .env")

    now = datetime.now(timezone.utc)
    cur_end = now
    cur_start = now - timedelta(days=30)
    prev_end = cur_start
    prev_start = now - timedelta(days=60)

    print("Buscando período atual...")
    current = get_period_data(cur_start, cur_end)
    print("Buscando período anterior...")
    previous = get_period_data(prev_start, prev_end)

    print("\n" + "=" * 76)
    print("SHOPIFY — COMPARATIVO DE PERÍODOS")
    print("=" * 76)
    print_comparison(current, previous)

    print("\n" + "=" * 76)
    print("TOP 20 PRODUTOS — GOOGLE ADS (PERÍODO ATUAL vs ANTERIOR)")
    print("=" * 76)
    print_products(current["products"], previous["products"])


if __name__ == "__main__":
    main()
