import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone, date
import os
import anthropic
from dotenv import load_dotenv

import shopify_test as shopify
import google_ads_campaigns as gads

load_dotenv()

REPORT_FILE = "relatorio_smartgr.md"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CACHE_VERSION = "v3"  # bump to bust stale cache after schema changes
PRESETS = [
    "Ontem",
    "Últimos 7 dias",
    "Últimos 14 dias",
    "Último mês",
    "Últimos 30 dias",
    "Últimos 90 dias",
    "Período personalizado",
]

st.set_page_config(
    page_title="Smart GR — Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 13px;
        color: #a6adc8;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #cdd6f4;
        margin-bottom: 4px;
    }
    .delta-pos { color: #a6e3a1; font-size: 13px; font-weight: 600; }
    .delta-neg { color: #f38ba8; font-size: 13px; font-weight: 600; }
    .delta-neu { color: #a6adc8; font-size: 13px; }
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #cdd6f4;
        margin: 24px 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 1px solid #313244;
    }
    .footer {
        text-align: center;
        color: #6c7086;
        font-size: 12px;
        margin-top: 40px;
        padding-top: 16px;
        border-top: 1px solid #313244;
    }
    .stButton > button {
        background-color: #89b4fa;
        color: #1e1e2e;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 6px 20px;
    }
    .stButton > button:hover {
        background-color: #b4befe;
        color: #1e1e2e;
    }
    .big-section {
        font-size: 18px;
        font-weight: 700;
        color: #cdd6f4;
        margin: 40px 0 4px 0;
        padding: 12px 20px;
        background: #181825;
        border-left: 5px solid #89b4fa;
        border-radius: 0 8px 8px 0;
    }
    .big-section-shopify { border-left-color: #a6e3a1; }
</style>
""", unsafe_allow_html=True)


def _to_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _to_dt_end(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)


def _same_last_year(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def compute_date_ranges(preset: str, custom_start=None, custom_end=None):
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    if preset == "Ontem":
        cs, ce = yesterday, yesterday
        ps, pe = _same_last_year(yesterday), _same_last_year(yesterday)

    elif preset == "Últimos 7 dias":
        ce = yesterday
        cs = ce - timedelta(days=6)
        ps, pe = _same_last_year(cs), _same_last_year(ce)

    elif preset == "Últimos 14 dias":
        ce = yesterday
        cs = ce - timedelta(days=13)
        pe = cs - timedelta(days=1)
        ps = pe - timedelta(days=13)

    elif preset == "Último mês":
        first_of_this_month = today.replace(day=1)
        ce = first_of_this_month - timedelta(days=1)
        cs = ce.replace(day=1)
        ps, pe = _same_last_year(cs), _same_last_year(ce)

    elif preset == "Últimos 30 dias":
        ce = yesterday
        cs = ce - timedelta(days=29)
        pe = cs - timedelta(days=1)
        ps = pe - timedelta(days=29)

    elif preset == "Últimos 90 dias":
        ce = yesterday
        cs = ce - timedelta(days=89)
        pe = cs - timedelta(days=1)
        ps = pe - timedelta(days=89)

    else:  # Período personalizado
        cs = custom_start or (today - timedelta(days=30))
        ce = custom_end or yesterday
        n = (ce - cs).days
        pe = cs - timedelta(days=1)
        ps = pe - timedelta(days=n)

    return _to_dt(cs), _to_dt_end(ce), _to_dt(ps), _to_dt_end(pe)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(cur_start_iso: str, cur_end_iso: str, prev_start_iso: str, prev_end_iso: str, cache_version: str = CACHE_VERSION):
    cur_start = datetime.fromisoformat(cur_start_iso)
    cur_end = datetime.fromisoformat(cur_end_iso)
    prev_start = datetime.fromisoformat(prev_start_iso)
    prev_end = datetime.fromisoformat(prev_end_iso)

    shopify_cur = shopify.get_period_data(cur_start, cur_end)
    shopify_prev = shopify.get_period_data(prev_start, prev_end)
    gads_cur = gads.get_period_data(
        cur_start.replace(tzinfo=None), cur_end.replace(tzinfo=None)
    )
    gads_prev = gads.get_period_data(
        prev_start.replace(tzinfo=None), prev_end.replace(tzinfo=None)
    )
    return shopify_cur, shopify_prev, gads_cur, gads_prev


def pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def metric_card(label, value, delta_val, prefix="R$ ", fmt=",.0f", inverse=False):
    if delta_val is None:
        delta_html = '<span class="delta-neu">— sem dados anteriores</span>'
    else:
        sign = "+" if delta_val >= 0 else ""
        css = "delta-pos" if (delta_val >= 0) != inverse else "delta-neg"
        arrow = "▲" if delta_val >= 0 else "▼"
        delta_html = f'<span class="{css}">{arrow} {sign}{delta_val:.1f}% vs período anterior</span>'

    val_str = f"{prefix}{value:{fmt}}"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{val_str}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def campaign_chart(gads_cur, gads_prev):
    active = sorted(
        [c for c in gads_cur["campaigns"] if c["cost"] > 0],
        key=lambda c: c["revenue"], reverse=True
    )
    prev_map = {c["name"]: c for c in gads_prev["campaigns"]}

    names = [c["name"][:35] + "…" if len(c["name"]) > 35 else c["name"] for c in active]
    gastos = [c["cost"] for c in active]
    receitas = [c["revenue"] for c in active]
    roas = [c["roas"] for c in active]
    prev_roas = [prev_map.get(c["name"], {}).get("roas", 0) for c in active]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Gasto (R$)",
        y=names,
        x=gastos,
        orientation="h",
        marker_color="#89b4fa",
        hovertemplate="<b>%{y}</b><br>Gasto: R$ %{x:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Receita atribuída (R$)",
        y=names,
        x=receitas,
        orientation="h",
        marker_color="#a6e3a1",
        hovertemplate="<b>%{y}</b><br>Receita: R$ %{x:,.2f}<br>ROAS: %{customdata:.2f}x<extra></extra>",
        customdata=roas,
    ))

    fig.update_layout(
        barmode="group",
        paper_bgcolor="#1e1e2e",
        plot_bgcolor="#1e1e2e",
        font=dict(color="#cdd6f4", size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            title="R$",
            tickprefix="R$ ",
            gridcolor="#313244",
            tickformat=",.0f",
        ),
        yaxis=dict(autorange="reversed", gridcolor="#313244"),
        height=max(300, len(active) * 52),
        margin=dict(l=10, r=20, t=10, b=40),
    )
    return fig


def products_dataframe(shopify_cur, shopify_prev):
    prev_map = {name: s for name, s in shopify_prev["products"]}
    rows = []
    for i, (name, s) in enumerate(shopify_cur["products"], 1):
        prev = prev_map.get(name, {"quantity": 0, "revenue": 0.0})
        ticket = s["revenue"] / s["quantity"] if s["quantity"] else 0
        var = pct(s["quantity"], prev["quantity"])
        rows.append({
            "#": i,
            "Produto": name,
            "Qtd": s["quantity"],
            "Receita": s["revenue"],
            "Ticket Médio": ticket,
            "Var. Qtd": var,
        })
    return pd.DataFrame(rows)


def generate_claude_analysis(shopify_cur, shopify_prev, gads_cur, gads_prev):
    import analyze
    data_report = analyze.build_report_data(shopify_cur, shopify_prev, gads_cur, gads_prev)
    prompt = analyze.build_prompt(data_report)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    full = ""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": "Você é um especialista em performance de Google Ads e e-commerce para o mercado brasileiro. Produza análises precisas, baseadas em dados, em português.",
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            full += text

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Relatório Smart GR — Gerado em {now_str}\n\n{full}")

    return full, now_str


def render_channel_table(channels_cur, channels_prev):
    if not channels_cur:
        st.info("Nenhum dado de canal disponível para o período.")
        return
    prev_map = {c["canal"]: c for c in (channels_prev or [])}
    rows = []
    for ch in channels_cur:
        prev = prev_map.get(ch["canal"], {})
        var = pct(ch["orders"], prev.get("orders")) if prev else None
        rows.append({
            "Canal": ch["canal"],
            "Tipo": ch["tipo"],
            "Pedidos": ch["orders"],
            "Vendas (R$)": ch["revenue"],
            "AOV": ch["aov"],
            "% das Vendas": ch["pct_revenue"],
            "Novos Clientes": ch["new_customers"],
            "Recorrentes": ch["returning_customers"],
            "_var": var,
        })
    df = pd.DataFrame(rows)
    df["Vendas (R$)"] = df["Vendas (R$)"].apply(lambda v: f"R$ {v:,.2f}")
    df["AOV"] = df["AOV"].apply(lambda v: f"R$ {v:,.2f}")
    df["% das Vendas"] = df["% das Vendas"].apply(lambda v: f"{v:.1f}%")
    df["Var. Pedidos"] = df["_var"].apply(
        lambda v: f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—")
    )
    df.drop(columns=["_var"], inplace=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_geo_tables(shopify_cur, shopify_prev):
    states_cur = shopify_cur.get("geo_states", [])
    states_prev = {s["state_code"]: s for s in shopify_prev.get("geo_states", [])}
    cities_cur = shopify_cur.get("geo_cities", [])
    cities_prev = {(c["city"], c["state_code"]): c for c in shopify_prev.get("geo_cities", [])}

    st.markdown('<div class="section-title">Top 10 Estados — Pedidos Google Ads</div>', unsafe_allow_html=True)
    if states_cur:
        rows = []
        for s in states_cur:
            prev = states_prev.get(s["state_code"], {})
            rows.append({
                "Estado": s["state"],
                "UF": s["state_code"],
                "Pedidos": s["orders"],
                "Receita Google Ads": s["revenue"],
                "Ticket Médio": s["aov"],
                "% do Total": s["pct"],
                "_var": pct(s["orders"], prev.get("orders")) if prev else None,
            })
        df = pd.DataFrame(rows)
        df["Receita Google Ads"] = df["Receita Google Ads"].apply(lambda v: f"R$ {v:,.2f}")
        df["Ticket Médio"] = df["Ticket Médio"].apply(lambda v: f"R$ {v:,.2f}")
        df["% do Total"] = df["% do Total"].apply(lambda v: f"{v:.1f}%")
        df["Var. Pedidos"] = df["_var"].apply(
            lambda v: f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—")
        )
        df.drop(columns=["_var"], inplace=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado geográfico disponível para o período selecionado.")

    st.markdown('<div class="section-title">Top 40 Cidades — Pedidos Google Ads</div>', unsafe_allow_html=True)
    if cities_cur:
        rows = []
        for c in cities_cur:
            prev = cities_prev.get((c["city"], c["state_code"]), {})
            rows.append({
                "Cidade": c["city"],
                "UF": c["state_code"],
                "Pedidos": c["orders"],
                "Receita Google Ads": c["revenue"],
                "Ticket Médio": c["aov"],
                "% do Total": c["pct"],
                "_var": pct(c["orders"], prev.get("orders")) if prev else None,
            })
        df = pd.DataFrame(rows)
        df["Receita Google Ads"] = df["Receita Google Ads"].apply(lambda v: f"R$ {v:,.2f}")
        df["Ticket Médio"] = df["Ticket Médio"].apply(lambda v: f"R$ {v:,.2f}")
        df["% do Total"] = df["% do Total"].apply(lambda v: f"{v:.1f}%")
        df["Var. Pedidos"] = df["_var"].apply(
            lambda v: f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—")
        )
        df.drop(columns=["_var"], inplace=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado geográfico disponível para o período selecionado.")


def check_auth():
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
    <div style="max-width:380px; margin:80px auto 0; text-align:center;">
        <h2 style="color:#cdd6f4; margin-bottom:4px;">📊 Smart GR</h2>
        <p style="color:#a6adc8; margin-bottom:28px;">Performance Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        with st.form("login_form"):
            password = st.text_input("Senha", type="password", placeholder="Digite a senha de acesso")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            expected = st.secrets.get("PASSWORD", "")
            if password == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta.")

    return False


def main():
    if not check_auth():
        st.stop()

    # --- Session state ---
    if "last_updated" not in st.session_state:
        st.session_state.last_updated = datetime.now()
    if "claude_analysis" not in st.session_state:
        if os.path.exists(REPORT_FILE):
            with open(REPORT_FILE, encoding="utf-8") as f:
                cached = f.read()
            first_line = cached.split("\n")[0] if cached else ""
            date_str = first_line.split("— Gerado em")[-1].strip() if "— Gerado em" in first_line else None
            st.session_state.claude_analysis = cached
            st.session_state.claude_analysis_date = date_str
        else:
            st.session_state.claude_analysis = None
            st.session_state.claude_analysis_date = None

    # --- Header ---
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.markdown("## 📊 Smart GR — Performance Dashboard")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar dados"):
            st.cache_data.clear()
            st.session_state.last_updated = datetime.now()
            st.rerun()

    # --- Date filter ---
    today = datetime.now(timezone.utc).date()
    col_preset, col_custom = st.columns([2, 4])
    with col_preset:
        preset = st.selectbox("Período de análise", PRESETS, index=4)

    custom_start = custom_end = None
    if preset == "Período personalizado":
        with col_custom:
            date_range = st.date_input(
                "Selecione o intervalo",
                value=(today - timedelta(days=30), today - timedelta(days=1)),
                max_value=today,
                format="DD/MM/YYYY",
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                custom_start, custom_end = date_range[0], date_range[1]
            elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
                custom_start = custom_end = date_range[0]
            else:
                custom_start = custom_end = date_range

    cur_start, cur_end, prev_start, prev_end = compute_date_ranges(preset, custom_start, custom_end)

    st.markdown(
        f"<span style='color:#cdd6f4;font-weight:600;'>"
        f"{cur_start.strftime('%d/%m/%Y')} – {cur_end.strftime('%d/%m/%Y')}"
        f"</span>"
        f"<span style='color:#6c7086;'>&nbsp;&nbsp;vs&nbsp;&nbsp;</span>"
        f"<span style='color:#a6adc8;'>"
        f"{prev_start.strftime('%d/%m/%Y')} – {prev_end.strftime('%d/%m/%Y')}"
        f"</span>",
        unsafe_allow_html=True,
    )

    # --- Load data ---
    with st.spinner("Carregando dados das APIs…"):
        try:
            shopify_cur, shopify_prev, gads_cur, gads_prev = load_data(
                cur_start.isoformat(),
                cur_end.isoformat(),
                prev_start.isoformat(),
                prev_end.isoformat(),
                CACHE_VERSION,
            )
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            st.stop()

    roas_real_cur = shopify_cur["google_revenue"] / gads_cur["cost"] if gads_cur["cost"] else 0
    roas_real_prev = shopify_prev["google_revenue"] / gads_prev["cost"] if gads_prev["cost"] else 0

    # ── Google Ads — Performance de Mídia ────────────────────────────
    st.markdown('<div class="big-section">📣 Google Ads — Performance de Mídia</div>', unsafe_allow_html=True)

    # --- KPI Cards ---
    st.markdown('<div class="section-title">Métricas Principais — Receita Atribuída (Shopify / Último Clique Não Direto)</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            "Receita Google Ads",
            shopify_cur["google_revenue"],
            pct(shopify_cur["google_revenue"], shopify_prev["google_revenue"]),
        )
    with c2:
        metric_card(
            "ROAS Real (Shopify / GA)",
            roas_real_cur,
            pct(roas_real_cur, roas_real_prev),
            prefix="",
            fmt=".2f",
        )
        st.caption(f"ROAS reportado Google Ads: {gads_cur['roas']:.2f}x")
    with c3:
        metric_card(
            "Pedidos Google Ads",
            shopify_cur["google_orders"],
            pct(shopify_cur["google_orders"], shopify_prev["google_orders"]),
            prefix="",
            fmt=",d",
        )
    with c4:
        metric_card(
            "Ticket Médio",
            shopify_cur["google_ticket"],
            pct(shopify_cur["google_ticket"], shopify_prev["google_ticket"]),
        )

    # --- KPIs secundários ---
    st.markdown('<div class="section-title">Google Ads — Métricas de Mídia</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Gasto Total", gads_cur["cost"], pct(gads_cur["cost"], gads_prev["cost"]))
    with c2:
        metric_card("Cliques", gads_cur["clicks"], pct(gads_cur["clicks"], gads_prev["clicks"]), prefix="", fmt=",d")
    with c3:
        metric_card("CTR", gads_cur["ctr"], pct(gads_cur["ctr"], gads_prev["ctr"]), prefix="", fmt=".2f")
    with c4:
        metric_card("CPC Médio", gads_cur["cpc"], pct(gads_cur["cpc"], gads_prev["cpc"]), inverse=True)
    with c5:
        metric_card("CPA", gads_cur["cpa"], pct(gads_cur["cpa"], gads_prev["cpa"]), inverse=True)

    # --- Gráfico por campanha ---
    st.markdown('<div class="section-title">Gasto vs Receita por Campanha</div>', unsafe_allow_html=True)
    st.plotly_chart(campaign_chart(gads_cur, gads_prev), use_container_width=True)

    # --- Tabela de campanhas ---
    st.markdown('<div class="section-title">Campanhas Ativas — Detalhamento</div>', unsafe_allow_html=True)
    prev_camp_map = {c["name"]: c for c in gads_prev["campaigns"]}
    active = sorted([c for c in gads_cur["campaigns"] if c["cost"] > 0], key=lambda c: c["roas"], reverse=True)
    camp_rows = []
    for c in active:
        prev = prev_camp_map.get(c["name"], {})
        roas_var = pct(c["roas"], prev.get("roas", 0))
        camp_rows.append({
            "Campanha": c["name"],
            "Gasto (R$)": c["cost"],
            "Receita (R$)": c["revenue"],
            "ROAS": c["roas"],
            "Var. ROAS": roas_var,
            "Conversões": c["conversions"],
            "CPA (R$)": c["cpa"] if c["conversions"] > 0 else None,
            "CTR (%)": c["ctr"],
        })

    df_camps = pd.DataFrame(camp_rows)
    df_camps["Gasto (R$)"] = df_camps["Gasto (R$)"].apply(lambda v: f"R$ {v:,.2f}")
    df_camps["Receita (R$)"] = df_camps["Receita (R$)"].apply(lambda v: f"R$ {v:,.2f}")
    df_camps["ROAS"] = df_camps["ROAS"].apply(lambda v: f"{v:.2f}x")
    df_camps["Var. ROAS"] = df_camps["Var. ROAS"].apply(
        lambda v: f"+{v:.1f}%" if v and v >= 0 else (f"{v:.1f}%" if v else "—")
    )
    df_camps["Conversões"] = df_camps["Conversões"].apply(lambda v: f"{v:.1f}")
    df_camps["CPA (R$)"] = df_camps["CPA (R$)"].apply(
        lambda v: f"R$ {v:,.2f}" if v else "—"
    )
    df_camps["CTR (%)"] = df_camps["CTR (%)"].apply(lambda v: f"{v:.2f}%")
    st.dataframe(df_camps, use_container_width=True, hide_index=True)

    # ── Shopify — Performance de E-commerce ──────────────────────────
    st.markdown('<div class="big-section big-section-shopify">🛍️ Shopify — Performance de E-commerce</div>', unsafe_allow_html=True)

    # --- Canais de Vendas ---
    st.markdown('<div class="section-title">Canais de Vendas — Shopify (Todos os Pedidos)</div>', unsafe_allow_html=True)
    st.info(
        "Atribuição baseada em sinais de origem do pedido (referring_site e source_name). "
        "Os números podem divergir do painel de Atribuição da Shopify, que utiliza dados de sessão completos. "
        "Para análise oficial de canais, consulte Shopify → Análises → Atribuição."
    )
    render_channel_table(
        shopify_cur.get("channels", []),
        shopify_prev.get("channels", []),
    )

    # --- Top 20 produtos ---
    st.markdown('<div class="section-title">Top 20 Produtos — Google Ads (Período Atual)</div>', unsafe_allow_html=True)
    df_prod = products_dataframe(shopify_cur, shopify_prev)
    df_prod["Receita"] = df_prod["Receita"].apply(lambda v: f"R$ {v:,.2f}")
    df_prod["Ticket Médio"] = df_prod["Ticket Médio"].apply(lambda v: f"R$ {v:,.2f}")
    df_prod["Var. Qtd"] = df_prod["Var. Qtd"].apply(
        lambda v: f"+{v:.1f}%" if v is not None and v >= 0 else (f"{v:.1f}%" if v is not None else "—")
    )
    st.dataframe(df_prod, use_container_width=True, hide_index=True)

    # --- Dados Geográficos ---
    render_geo_tables(shopify_cur, shopify_prev)

    # --- Análise Claude ---
    st.markdown('<div class="section-title">Análise e Recomendações — Claude AI</div>', unsafe_allow_html=True)

    col_report, col_gen = st.columns([4, 1])
    with col_gen:
        generate = st.button("🤖 Gerar nova análise")

    if generate:
        if not ANTHROPIC_API_KEY:
            st.error("ANTHROPIC_API_KEY não encontrada no .env")
        else:
            with st.spinner("Claude está processando a análise… isso pode levar alguns segundos."):
                content, date_str = generate_claude_analysis(
                    shopify_cur, shopify_prev, gads_cur, gads_prev
                )
            st.session_state.claude_analysis = content
            st.session_state.claude_analysis_date = date_str
            st.success("Análise gerada e salva!")

    if st.session_state.get("claude_analysis_date"):
        st.caption(f"Última análise gerada em: {st.session_state.claude_analysis_date}")

    if st.session_state.get("claude_analysis"):
        with st.expander("Ver relatório completo", expanded=True):
            st.markdown(st.session_state.claude_analysis)
    else:
        st.info("Nenhum relatório gerado ainda. Clique em '🤖 Gerar nova análise'.")

    # --- Footer ---
    last = st.session_state.last_updated.strftime("%d/%m/%Y às %H:%M:%S")
    st.markdown(
        f'<div class="footer">Última atualização: {last} · Smart GR Performance Dashboard</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
