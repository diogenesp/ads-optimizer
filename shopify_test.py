import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv
import requests

load_dotenv()

SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
STORE_URL = "https://smart-gr-pro.myshopify.com"
API_VERSION = "2025-01"
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


def classify_channel(order) -> tuple:
    source = (order.get("source_name") or "").lower().strip()
    referring = (order.get("referring_site") or "").lower()
    landing = (order.get("landing_site") or "").lower()
    has_paid_click = "gclid" in landing or "gad_source" in landing

    # source_name-based signals (non-web channels)
    if source == "tiktok":
        return "TikTok", "Social"
    if source == "pos":
        return "PDV", "PDV"
    if source == "google":
        return "Google Ads", "Pago"
    if source in ("facebook", "instagram"):
        return "Meta Ads", "Social"

    # referring_site-based (web orders)
    if "google" in referring:
        return ("Google Ads", "Pago") if has_paid_click else ("Google Orgânico", "Orgânico")
    if any(d in referring for d in ("instagram.com", "facebook.com", "l.facebook.com", "l.instagram.com")):
        return "Instagram / Facebook", "Social"
    if not referring:
        return "Direto", "Direto"

    return "Outros", "Outros"


def channel_stats(orders: list) -> list:
    channels: dict = {}
    total_revenue = sum(float(o.get("total_price") or 0) for o in orders)

    for order in orders:
        canal, tipo = classify_channel(order)
        price = float(order.get("total_price") or 0)
        if canal not in channels:
            channels[canal] = {
                "canal": canal, "tipo": tipo,
                "revenue": 0.0, "orders": 0,
                "new_customers": 0, "returning_customers": 0,
            }
        channels[canal]["revenue"] += price
        channels[canal]["orders"] += 1
        customer = order.get("customer") or {}
        if (customer.get("orders_count") or 1) <= 1:
            channels[canal]["new_customers"] += 1
        else:
            channels[canal]["returning_customers"] += 1

    result = []
    for data in channels.values():
        result.append({
            **data,
            "aov": data["revenue"] / data["orders"] if data["orders"] else 0,
            "pct_revenue": data["revenue"] / total_revenue * 100 if total_revenue else 0,
        })
    return sorted(result, key=lambda x: x["revenue"], reverse=True)


def geo_stats(google_orders: list, top_n_states: int = 10, top_n_cities: int = 40):
    if not google_orders:
        return [], []

    total_orders = len(google_orders)
    states: dict = {}
    cities: dict = {}

    for order in google_orders:
        addr = order.get("shipping_address") or order.get("billing_address") or {}
        province_code = (addr.get("province_code") or "").strip().upper() or "??"
        province_name = (addr.get("province") or province_code).strip()
        city_name = (addr.get("city") or "Desconhecida").strip()
        price = float(order.get("total_price") or 0)

        if province_code not in states:
            states[province_code] = {"name": province_name, "orders": 0, "revenue": 0.0}
        states[province_code]["orders"] += 1
        states[province_code]["revenue"] += price

        city_key = f"{city_name}||{province_code}"
        if city_key not in cities:
            cities[city_key] = {
                "city": city_name, "state": province_name, "state_code": province_code,
                "orders": 0, "revenue": 0.0,
            }
        cities[city_key]["orders"] += 1
        cities[city_key]["revenue"] += price

    state_list = sorted(
        [
            {
                "state": v["name"], "state_code": k,
                "orders": v["orders"], "revenue": v["revenue"],
                "aov": v["revenue"] / v["orders"] if v["orders"] else 0,
                "pct": v["orders"] / total_orders * 100 if total_orders else 0,
            }
            for k, v in states.items()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:top_n_states]

    city_list = sorted(
        [
            {
                "city": v["city"], "state": v["state"], "state_code": v["state_code"],
                "orders": v["orders"], "revenue": v["revenue"],
                "aov": v["revenue"] / v["orders"] if v["orders"] else 0,
                "pct": v["orders"] / total_orders * 100 if total_orders else 0,
            }
            for v in cities.values()
        ],
        key=lambda x: x["revenue"],
        reverse=True,
    )[:top_n_cities]

    return state_list, city_list


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
    states, cities = geo_stats(google_orders)

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
        "channels": channel_stats(orders),
        "geo_states": states,
        "geo_cities": cities,
    }


def fetch_orders_any_status(start_dt, end_dt):
    """Fetch all orders regardless of financial or fulfillment status."""
    orders = []
    url = f"{BASE_URL}/orders.json"
    params = {
        "status": "any",
        "created_at_min": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at_max": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 250,
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


def _is_new_in_period(order, period_start):
    """True if the customer's Shopify profile was created within/after period_start."""
    customer = order.get("customer") or {}
    cust_created = customer.get("created_at")
    if not cust_created:
        return True  # guest checkout — treat as new
    try:
        cust_dt = datetime.fromisoformat(cust_created.replace("Z", "+00:00"))
        if cust_dt.tzinfo is None:
            cust_dt = cust_dt.replace(tzinfo=timezone.utc)
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        return cust_dt >= period_start
    except (ValueError, TypeError):
        return True


def customer_stats_full(orders, period_start):
    """
    Returns new/returning breakdown, repurchase rate, avg LTV, and top-100 customer list.
    New = customer.created_at >= period_start (first-ever order proxy).
    """
    if not orders:
        return {
            "new_count": 0, "returning_count": 0,
            "new_pct": 0.0, "returning_pct": 0.0,
            "repurchase_rate": 0.0, "avg_ltv": 0.0,
            "top_100": [],
        }

    customer_map = {}

    for order in orders:
        customer = order.get("customer") or {}
        email = (
            customer.get("email")
            or order.get("email")
            or "desconhecido"
        ).lower().strip()
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Desconhecido"
        price = float(order.get("total_price") or 0)
        created_at = order.get("created_at", "")
        ltv = float(customer.get("total_spent") or 0)
        is_new = _is_new_in_period(order, period_start)

        if email not in customer_map:
            customer_map[email] = {
                "name": name, "email": email,
                "total_revenue": 0.0, "order_count": 0,
                "last_order": created_at, "ltv": ltv,
                "is_new": is_new,
            }
        customer_map[email]["total_revenue"] += price
        customer_map[email]["order_count"] += 1
        if created_at > customer_map[email]["last_order"]:
            customer_map[email]["last_order"] = created_at

    all_customers = list(customer_map.values())
    total = len(all_customers)
    new_count = sum(1 for c in all_customers if c["is_new"])
    returning_count = total - new_count
    repurchase_count = sum(1 for c in all_customers if c["order_count"] > 1)

    return {
        "new_count": new_count,
        "returning_count": returning_count,
        "new_pct": new_count / total * 100 if total else 0.0,
        "returning_pct": returning_count / total * 100 if total else 0.0,
        "repurchase_rate": repurchase_count / total * 100 if total else 0.0,
        "avg_ltv": sum(c["ltv"] for c in all_customers) / total if total else 0.0,
        "top_100": sorted(all_customers, key=lambda c: c["total_revenue"], reverse=True)[:100],
    }


def coupon_stats(orders):
    """Discount-code analysis for a set of orders."""
    coupons = {}
    total_revenue = sum(float(o.get("total_price") or 0) for o in orders)

    for order in orders:
        price = float(order.get("total_price") or 0)
        for dc in order.get("discount_codes", []):
            code = (dc.get("code") or "").upper().strip()
            if not code:
                continue
            discount = float(dc.get("amount") or 0)
            if code not in coupons:
                coupons[code] = {"uses": 0, "total_discount": 0.0, "total_revenue": 0.0}
            coupons[code]["uses"] += 1
            coupons[code]["total_discount"] += discount
            coupons[code]["total_revenue"] += price

    result = []
    for code, data in coupons.items():
        result.append({
            "coupon": code,
            "uses": data["uses"],
            "total_discount": data["total_discount"],
            "total_revenue": data["total_revenue"],
            "avg_ticket": data["total_revenue"] / data["uses"] if data["uses"] else 0.0,
            "pct_revenue": data["total_revenue"] / total_revenue * 100 if total_revenue else 0.0,
        })
    return sorted(result, key=lambda x: x["total_revenue"], reverse=True)


def time_stats(orders):
    """Revenue by day-of-week and hour (Brasilia UTC-3)."""
    WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    by_weekday = {d: 0.0 for d in WEEKDAYS}
    by_hour = {h: 0.0 for h in range(24)}

    for order in orders:
        price = float(order.get("total_price") or 0)
        created_at = order.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            dt_local = dt - timedelta(hours=3)  # UTC-3 Brasilia
            by_weekday[WEEKDAYS[dt_local.weekday()]] += price
            by_hour[dt_local.hour] += price
        except (ValueError, TypeError):
            pass

    return by_weekday, by_hour


def all_product_stats(orders, top_n=50):
    """Top-N products by revenue across all provided orders, with pct_revenue included."""
    sales = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    total_revenue = sum(float(o.get("total_price") or 0) for o in orders)

    for order in orders:
        for item in order.get("line_items", []):
            title = item.get("title", "Unknown")
            qty = item.get("quantity", 0)
            price = float(item.get("price", 0)) * qty
            sales[title]["quantity"] += qty
            sales[title]["revenue"] += price

    ranked = sorted(sales.items(), key=lambda x: x[1]["revenue"], reverse=True)[:top_n]
    return [
        {
            "product": name,
            "quantity": s["quantity"],
            "revenue": s["revenue"],
            "aov": s["revenue"] / s["quantity"] if s["quantity"] else 0.0,
            "pct_revenue": s["revenue"] / total_revenue * 100 if total_revenue else 0.0,
        }
        for name, s in ranked
    ]


def get_full_period_data(start_dt, end_dt):
    """Comprehensive Shopify data for the 'Visão Completa' section."""
    all_orders = fetch_orders_any_status(start_dt, end_dt)

    cancelled_orders = [o for o in all_orders if o.get("cancelled_at")]
    paid_fs = ("paid", "partially_refunded", "partially_paid")
    paid_orders = [
        o for o in all_orders
        if not o.get("cancelled_at") and o.get("financial_status") in paid_fs
    ]
    refunded_orders = [
        o for o in all_orders
        if o.get("financial_status") in ("refunded", "partially_refunded")
    ]

    gross_revenue = sum(float(o.get("total_price") or 0) for o in paid_orders)

    refund_total = 0.0
    for order in all_orders:
        for refund in order.get("refunds", []):
            for txn in refund.get("transactions", []):
                if txn.get("kind") == "refund":
                    refund_total += float(txn.get("amount") or 0)

    cancelled_revenue = sum(float(o.get("total_price") or 0) for o in cancelled_orders)
    net_revenue = gross_revenue - refund_total

    avg_ticket = gross_revenue / len(paid_orders) if paid_orders else 0.0

    new_orders = [o for o in paid_orders if _is_new_in_period(o, start_dt)]
    ret_orders = [o for o in paid_orders if not _is_new_in_period(o, start_dt)]
    new_revenue = sum(float(o.get("total_price") or 0) for o in new_orders)
    ret_revenue = sum(float(o.get("total_price") or 0) for o in ret_orders)
    new_ticket = new_revenue / len(new_orders) if new_orders else 0.0
    ret_ticket = ret_revenue / len(ret_orders) if ret_orders else 0.0

    states, cities = geo_stats(paid_orders, top_n_states=20, top_n_cities=100)
    by_weekday, by_hour = time_stats(paid_orders)

    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "total_orders": len(paid_orders),
        "cancelled_count": len(cancelled_orders),
        "cancelled_revenue": cancelled_revenue,
        "refund_count": len(refunded_orders),
        "refund_total": refund_total,
        "avg_ticket": avg_ticket,
        "new_ticket": new_ticket,
        "ret_ticket": ret_ticket,
        "customer_data": customer_stats_full(paid_orders, start_dt),
        "products_all": all_product_stats(paid_orders, top_n=50),
        "geo_states_all": states,
        "geo_cities_all": cities,
        "coupons": coupon_stats(paid_orders),
        "by_weekday": by_weekday,
        "by_hour": by_hour,
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
