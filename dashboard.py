import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import anthropic
from dotenv import load_dotenv

import shopify_test as shopify
import google_ads_campaigns as gads

load_dotenv()

REPORT_FILE = "relatorio_smartgr.md"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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
</style>
""", unsafe_allow_html=True)


def get_date_ranges():
    now = datetime.now(timezone.utc)
    cur_end = now
    cur_start = now - timedelta(days=30)
    prev_end = cur_start
    prev_start = now - timedelta(days=60)
    return cur_start, cur_end, prev_start, prev_end


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(cache_key: str):
    cur_start, cur_end, prev_start, prev_end = get_date_ranges()
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
    placeholder = st.empty()
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
            placeholder.markdown(full + "▌")

    placeholder.markdown(full)

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Relatório Smart GR — Gerado em {now_str}\n\n{full}")

    return full


def main():
    # --- Session state ---
    if "cache_key" not in st.session_state:
        st.session_state.cache_key = datetime.now().isoformat()
    if "last_updated" not in st.session_state:
        st.session_state.last_updated = datetime.now()

    # --- Header ---
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        cur_start, cur_end, prev_start, prev_end = get_date_ranges()
        st.markdown(f"## 📊 Smart GR — Performance Dashboard")
        st.caption(
            f"Período atual: {cur_start.strftime('%d/%m/%Y')} – {cur_end.strftime('%d/%m/%Y')}  |  "
            f"Anterior: {prev_start.strftime('%d/%m/%Y')} – {prev_end.strftime('%d/%m/%Y')}"
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar dados"):
            st.session_state.cache_key = datetime.now().isoformat()
            st.session_state.last_updated = datetime.now()
            st.cache_data.clear()
            st.rerun()

    # --- Load data ---
    with st.spinner("Carregando dados das APIs…"):
        try:
            shopify_cur, shopify_prev, gads_cur, gads_prev = load_data(
                st.session_state.cache_key
            )
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            st.stop()

    roas_real_cur = shopify_cur["google_revenue"] / gads_cur["cost"] if gads_cur["cost"] else 0
    roas_real_prev = shopify_prev["google_revenue"] / gads_prev["cost"] if gads_prev["cost"] else 0

    # --- KPI Cards ---
    st.markdown('<div class="section-title">Métricas Principais — Google Ads (Último Clique Não Direto)</div>', unsafe_allow_html=True)

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
    st.dataframe(
        df_camps.style.format({
            "Gasto (R$)": "R$ {:,.2f}",
            "Receita (R$)": "R$ {:,.2f}",
            "ROAS": "{:.2f}x",
            "Var. ROAS": lambda v: f"+{v:.1f}%" if v and v >= 0 else (f"{v:.1f}%" if v else "—"),
            "Conversões": "{:.1f}",
            "CPA (R$)": lambda v: f"R$ {v:,.2f}" if v else "—",
            "CTR (%)": "{:.2f}%",
        }).background_gradient(subset=["ROAS"], cmap="RdYlGn"),
        use_container_width=True,
        hide_index=True,
    )

    # --- Top 20 produtos ---
    st.markdown('<div class="section-title">Top 20 Produtos — Google Ads (Período Atual)</div>', unsafe_allow_html=True)
    df_prod = products_dataframe(shopify_cur, shopify_prev)
    st.dataframe(
        df_prod.style.format({
            "Receita": "R$ {:,.2f}",
            "Ticket Médio": "R$ {:,.2f}",
            "Var. Qtd": lambda v: f"+{v:.1f}%" if v and v >= 0 else (f"{v:.1f}%" if v is not None else "—"),
        }).background_gradient(subset=["Var. Qtd"], cmap="RdYlGn"),
        use_container_width=True,
        hide_index=True,
    )

    # --- Análise Claude ---
    st.markdown('<div class="section-title">Análise e Recomendações — Claude AI</div>', unsafe_allow_html=True)

    report_content = ""
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, encoding="utf-8") as f:
            report_content = f.read()

    col_report, col_gen = st.columns([4, 1])
    with col_gen:
        generate = st.button("🤖 Gerar nova análise")

    if generate:
        if not ANTHROPIC_API_KEY:
            st.error("ANTHROPIC_API_KEY não encontrada no .env")
        else:
            with st.spinner("Gerando análise com Claude…"):
                report_content = generate_claude_analysis(
                    shopify_cur, shopify_prev, gads_cur, gads_prev
                )
            st.success("Análise gerada e salva em relatorio_smartgr.md")
            st.rerun()

    if report_content:
        with st.expander("Ver relatório completo", expanded=True):
            st.markdown(report_content)
    else:
        st.info("Nenhum relatório gerado ainda. Clique em 'Gerar nova análise'.")

    # --- Footer ---
    last = st.session_state.last_updated.strftime("%d/%m/%Y às %H:%M:%S")
    st.markdown(
        f'<div class="footer">Última atualização: {last} · Smart GR Performance Dashboard</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
