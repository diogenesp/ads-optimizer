import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv()

CUSTOMER_ID = "4686170698"

def get_client():
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": True,
    })


def micros_to_brl(micros):
    return micros / 1_000_000


def fetch_campaigns(start_date, end_date):
    client = get_client()
    service = client.get_service("GoogleAdsService")

    date_range = f"'{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'"
    query = f"""
        SELECT
            campaign.name,
            metrics.cost_micros,
            metrics.impressions,
            metrics.clicks,
            metrics.ctr,
            metrics.average_cpc,
            metrics.conversions,
            metrics.cost_per_conversion,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN {date_range}
          AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
    """

    response = service.search(customer_id=CUSTOMER_ID, query=query)
    campaigns = []
    for row in response:
        m = row.metrics
        cost = micros_to_brl(m.cost_micros)
        revenue = m.conversions_value
        campaigns.append({
            "name": row.campaign.name,
            "cost": cost,
            "revenue": revenue,
            "roas": revenue / cost if cost > 0 else 0,
            "impressions": m.impressions,
            "clicks": m.clicks,
            "ctr": m.ctr * 100,
            "cpc": micros_to_brl(m.average_cpc),
            "conversions": m.conversions,
            "cpa": micros_to_brl(m.cost_per_conversion) if m.conversions > 0 else 0,
        })
    return campaigns


def fetch_product_performance(start_date, end_date):
    """Spend and conversions per Shopping/PMax product, aggregated across campaigns."""
    client = get_client()
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            segments.product_title,
            segments.product_item_id,
            metrics.cost_micros,
            metrics.clicks,
            metrics.conversions,
            metrics.conversions_value
        FROM shopping_performance_view
        WHERE segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
    """
    products: dict = {}
    for row in service.search(customer_id=CUSTOMER_ID, query=query):
        key = row.segments.product_title or row.segments.product_item_id
        p = products.setdefault(key, {"product": key, "cost": 0.0, "clicks": 0,
                                      "conversions": 0.0, "revenue": 0.0})
        p["cost"] += micros_to_brl(row.metrics.cost_micros)
        p["clicks"] += row.metrics.clicks
        p["conversions"] += row.metrics.conversions
        p["revenue"] += row.metrics.conversions_value
    for p in products.values():
        p["roas"] = p["revenue"] / p["cost"] if p["cost"] > 0 else 0
    return sorted(products.values(), key=lambda p: p["cost"], reverse=True)


def product_waste_stats(products: list) -> dict:
    """Products that spent budget without converting (conversions < 0.5)."""
    total_cost = sum(p["cost"] for p in products)
    wasted = [p for p in products if p["cost"] > 0 and p["conversions"] < 0.5]
    winners = sorted([p for p in products if p["conversions"] >= 0.5],
                     key=lambda p: p["revenue"], reverse=True)
    wasted_cost = sum(p["cost"] for p in wasted)
    return {
        "total_cost": total_cost,
        "wasted_cost": wasted_cost,
        "wasted_pct": wasted_cost / total_cost * 100 if total_cost else 0,
        "wasted_count": len(wasted),
        "product_count": len(products),
        "wasted": wasted,
        "winners": winners[:20],
    }


def get_period_data(start_date, end_date):
    campaigns = fetch_campaigns(start_date, end_date)
    active = [c for c in campaigns if c["cost"] > 0]

    total_cost = sum(c["cost"] for c in campaigns)
    total_revenue = sum(c["revenue"] for c in campaigns)
    total_impressions = sum(c["impressions"] for c in campaigns)
    total_clicks = sum(c["clicks"] for c in campaigns)
    total_conversions = sum(c["conversions"] for c in campaigns)

    return {
        "start": start_date,
        "end": end_date,
        "cost": total_cost,
        "revenue": total_revenue,
        "roas": total_revenue / total_cost if total_cost > 0 else 0,
        "impressions": total_impressions,
        "clicks": total_clicks,
        "ctr": total_clicks / total_impressions * 100 if total_impressions else 0,
        "cpc": total_cost / total_clicks if total_clicks else 0,
        "conversions": total_conversions,
        "cpa": total_cost / total_conversions if total_conversions else 0,
        "campaigns": campaigns,
        "active_campaigns": active,
        "product_waste": product_waste_stats(fetch_product_performance(start_date, end_date)),
    }


def get_monthly_data(start_date, end_date):
    """Account-level totals grouped by month, for historical trend charts."""
    client = get_client()
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            segments.month,
            metrics.cost_micros,
            metrics.conversions_value
        FROM campaign
        WHERE segments.date BETWEEN '{start_date.strftime('%Y-%m-%d')}' AND '{end_date.strftime('%Y-%m-%d')}'
          AND campaign.status != 'REMOVED'
        ORDER BY segments.month ASC
    """
    response = service.search(customer_id=CUSTOMER_ID, query=query)
    monthly: dict = {}
    for row in response:
        month = row.segments.month  # "YYYY-MM-DD" (first day of month)
        cost = micros_to_brl(row.metrics.cost_micros)
        revenue = row.metrics.conversions_value
        if month not in monthly:
            monthly[month] = {"cost": 0.0, "revenue": 0.0}
        monthly[month]["cost"] += cost
        monthly[month]["revenue"] += revenue

    result = []
    for month_str, vals in sorted(monthly.items()):
        cost = vals["cost"]
        revenue = vals["revenue"]
        result.append({
            "month": month_str,
            "cost": cost,
            "revenue": revenue,
            "roas": revenue / cost if cost > 0 else 0,
        })
    return result


def pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def fmt_pct(val):
    if val is None:
        return "  n/a"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def print_totals(cur, prev):
    label_w = 20

    def row(label, c_val, p_val, fmt=",.2f", prefix="R$ "):
        change = pct(c_val, p_val)
        print(
            f"  {label:<{label_w}} {prefix}{c_val:{fmt}}  |  {prefix}{p_val:{fmt}}  |  {fmt_pct(change)}"
        )

    period_cur = f"{cur['start'].strftime('%d/%m')} – {cur['end'].strftime('%d/%m/%Y')}"
    period_prev = f"{prev['start'].strftime('%d/%m')} – {prev['end'].strftime('%d/%m/%Y')}"
    print(f"\n{'':22} {'Atual':^22}  {'Anterior':^22}  {'Var%':>7}")
    print(f"{'':22} {period_cur:^22}  {period_prev:^22}")
    print("  " + "-" * 70)

    row("Gasto", cur["cost"], prev["cost"])
    row("Receita atribuída", cur["revenue"], prev["revenue"])
    row("ROAS", cur["roas"], prev["roas"], fmt=".2f", prefix="")
    row("Impressões", cur["impressions"], prev["impressions"], fmt=",d", prefix="")
    row("Cliques", cur["clicks"], prev["clicks"], fmt=",d", prefix="")
    row("CTR", cur["ctr"], prev["ctr"], fmt=".2f", prefix="")
    row("CPC médio", cur["cpc"], prev["cpc"])
    row("Conversões", cur["conversions"], prev["conversions"], fmt=".1f", prefix="")
    row("CPA", cur["cpa"], prev["cpa"])


def print_campaigns(cur_camps, prev_camps):
    prev_map = {c["name"]: c for c in prev_camps}
    active = [c for c in cur_camps if c["cost"] > 0]
    active.sort(key=lambda c: c["roas"], reverse=True)

    col = max((len(c["name"]) for c in active), default=10)

    header = (
        f"  {'Campanha':<{col}}  "
        f"{'Gasto':>11}  {'Receita':>12}  {'ROAS':>7}  "
        f"{'Conv':>6}  {'CPA':>9}  {'CTR':>7}  {'Var ROAS':>9}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for c in active:
        prev = prev_map.get(c["name"], {})
        roas_change = pct(c["roas"], prev.get("roas", 0))
        roas_str = f"{c['roas']:.2f}x"
        cpa_str = f"R${c['cpa']:>8.2f}" if c["conversions"] > 0 else "        —"
        print(
            f"  {c['name']:<{col}}  "
            f"R${c['cost']:>9.2f}  "
            f"R${c['revenue']:>10.2f}  "
            f"{roas_str:>7}  "
            f"{c['conversions']:>6.1f}  "
            f"{cpa_str}  "
            f"{c['ctr']:>6.2f}%  "
            f"{fmt_pct(roas_change):>9}"
        )


def main():
    now = datetime.today()
    cur_end = now
    cur_start = now - timedelta(days=30)
    prev_end = cur_start
    prev_start = now - timedelta(days=60)

    print("Buscando período atual...")
    current = get_period_data(cur_start, cur_end)
    print("Buscando período anterior...")
    previous = get_period_data(prev_start, prev_end)

    print("\n" + "=" * 74)
    print("GOOGLE ADS — COMPARATIVO DE PERÍODOS")
    print("=" * 74)
    print_totals(current, previous)

    print("\n" + "=" * 74)
    print("CAMPANHAS ATIVAS — ORDENADO POR ROAS (PERÍODO ATUAL)")
    print("=" * 74)
    print_campaigns(current["campaigns"], previous["campaigns"])


if __name__ == "__main__":
    main()
