import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import anthropic

import shopify_test as shopify
import google_ads_campaigns as gads

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OUTPUT_FILE = "relatorio_smartgr.md"


def pct(current, previous):
    if not previous:
        return None
    return (current - previous) / previous * 100


def fmt_pct(val, parens=True):
    if val is None:
        return "n/a"
    sign = "+" if val >= 0 else ""
    s = f"{sign}{val:.1f}%"
    return f"({s})" if parens else s


def build_report_data(shopify_cur, shopify_prev, gads_cur, gads_prev):
    roas_real_cur = shopify_cur["google_revenue"] / gads_cur["cost"] if gads_cur["cost"] else 0
    roas_real_prev = shopify_prev["google_revenue"] / gads_prev["cost"] if gads_prev["cost"] else 0

    lines = []
    a = lines.append

    period_cur = f"{shopify_cur['start'].strftime('%d/%m/%Y')} a {shopify_cur['end'].strftime('%d/%m/%Y')}"
    period_prev = f"{shopify_prev['start'].strftime('%d/%m/%Y')} a {shopify_prev['end'].strftime('%d/%m/%Y')}"

    a(f"# Dados de Performance — Smart GR")
    a(f"- Período atual:   {period_cur}")
    a(f"- Período anterior: {period_prev}")
    a("")

    # --- Shopify geral ---
    a("## 1. Shopify — Visão Geral (Todas as Origens)")
    a(f"| Métrica | Atual | Anterior | Variação |")
    a(f"|---|---|---|---|")
    a(f"| Pedidos | {shopify_cur['all_orders']:,} | {shopify_prev['all_orders']:,} | {fmt_pct(pct(shopify_cur['all_orders'], shopify_prev['all_orders']))} |")
    a(f"| Receita | R$ {shopify_cur['all_revenue']:,.2f} | R$ {shopify_prev['all_revenue']:,.2f} | {fmt_pct(pct(shopify_cur['all_revenue'], shopify_prev['all_revenue']))} |")
    a(f"| Ticket médio | R$ {shopify_cur['all_ticket']:,.2f} | R$ {shopify_prev['all_ticket']:,.2f} | {fmt_pct(pct(shopify_cur['all_ticket'], shopify_prev['all_ticket']))} |")
    a("")

    # --- Google Ads Shopify ---
    a("## 2. Shopify — Atribuído ao Google Ads (Último Clique Não Direto)")
    a(f"| Métrica | Atual | Anterior | Variação |")
    a(f"|---|---|---|---|")
    a(f"| Pedidos | {shopify_cur['google_orders']:,} | {shopify_prev['google_orders']:,} | {fmt_pct(pct(shopify_cur['google_orders'], shopify_prev['google_orders']))} |")
    a(f"| Receita | R$ {shopify_cur['google_revenue']:,.2f} | R$ {shopify_prev['google_revenue']:,.2f} | {fmt_pct(pct(shopify_cur['google_revenue'], shopify_prev['google_revenue']))} |")
    a(f"| Ticket médio | R$ {shopify_cur['google_ticket']:,.2f} | R$ {shopify_prev['google_ticket']:,.2f} | {fmt_pct(pct(shopify_cur['google_ticket'], shopify_prev['google_ticket']))} |")
    a(f"| ROAS real (receita Shopify / gasto Google Ads) | {roas_real_cur:.2f}x | {roas_real_prev:.2f}x | {fmt_pct(pct(roas_real_cur, roas_real_prev))} |")
    a("")

    # --- Google Ads totais ---
    a("## 3. Google Ads — Métricas Totais da Conta")
    a(f"| Métrica | Atual | Anterior | Variação |")
    a(f"|---|---|---|---|")
    a(f"| Gasto | R$ {gads_cur['cost']:,.2f} | R$ {gads_prev['cost']:,.2f} | {fmt_pct(pct(gads_cur['cost'], gads_prev['cost']))} |")
    a(f"| Receita atribuída (GA) | R$ {gads_cur['revenue']:,.2f} | R$ {gads_prev['revenue']:,.2f} | {fmt_pct(pct(gads_cur['revenue'], gads_prev['revenue']))} |")
    a(f"| ROAS (GA) | {gads_cur['roas']:.2f}x | {gads_prev['roas']:.2f}x | {fmt_pct(pct(gads_cur['roas'], gads_prev['roas']))} |")
    a(f"| Impressões | {gads_cur['impressions']:,} | {gads_prev['impressions']:,} | {fmt_pct(pct(gads_cur['impressions'], gads_prev['impressions']))} |")
    a(f"| Cliques | {gads_cur['clicks']:,} | {gads_prev['clicks']:,} | {fmt_pct(pct(gads_cur['clicks'], gads_prev['clicks']))} |")
    a(f"| CTR | {gads_cur['ctr']:.2f}% | {gads_prev['ctr']:.2f}% | {fmt_pct(pct(gads_cur['ctr'], gads_prev['ctr']))} |")
    a(f"| CPC médio | R$ {gads_cur['cpc']:.2f} | R$ {gads_prev['cpc']:.2f} | {fmt_pct(pct(gads_cur['cpc'], gads_prev['cpc']))} |")
    a(f"| Conversões | {gads_cur['conversions']:.1f} | {gads_prev['conversions']:.1f} | {fmt_pct(pct(gads_cur['conversions'], gads_prev['conversions']))} |")
    a(f"| CPA | R$ {gads_cur['cpa']:.2f} | R$ {gads_prev['cpa']:.2f} | {fmt_pct(pct(gads_cur['cpa'], gads_prev['cpa']))} |")
    a("")

    # --- Campanhas ---
    a("## 4. Google Ads — Desempenho por Campanha")
    prev_camp_map = {c["name"]: c for c in gads_prev["campaigns"]}
    active = sorted(
        [c for c in gads_cur["campaigns"] if c["cost"] > 0],
        key=lambda c: c["roas"], reverse=True
    )
    a(f"| Campanha | Gasto | Receita (GA) | ROAS | Conv | CPA | CTR | Var ROAS |")
    a(f"|---|---|---|---|---|---|---|---|")
    for c in active:
        prev = prev_camp_map.get(c["name"], {})
        roas_var = fmt_pct(pct(c["roas"], prev.get("roas", 0)))
        cpa_str = f"R$ {c['cpa']:.2f}" if c["conversions"] > 0 else "—"
        a(f"| {c['name']} | R$ {c['cost']:.2f} | R$ {c['revenue']:.2f} | {c['roas']:.2f}x | {c['conversions']:.1f} | {cpa_str} | {c['ctr']:.2f}% | {roas_var} |")

    # campanhas pausadas no período atual mas ativas no anterior
    inactive_prev = [
        p for p in gads_prev["active_campaigns"]
        if p["name"] not in {c["name"] for c in gads_cur["active_campaigns"]}
    ]
    if inactive_prev:
        a("")
        a("### Campanhas ativas no período anterior e sem veiculação no atual:")
        for c in inactive_prev:
            a(f"- {c['name']} (gasto anterior: R$ {c['cost']:.2f}, ROAS: {c['roas']:.2f}x)")
    a("")

    # --- Top 20 produtos ---
    a("## 5. Top 20 Produtos — Google Ads (Período Atual vs Anterior)")
    prev_prod_map = {name: s for name, s in shopify_prev["products"]}
    a(f"| # | Produto | Qtd Atual | Receita Atual | Ticket Atual | Qtd Ant | Var Qtd |")
    a(f"|---|---|---|---|---|---|---|")
    for i, (name, s) in enumerate(shopify_cur["products"], 1):
        prev = prev_prod_map.get(name, {"quantity": 0, "revenue": 0.0})
        ticket = s["revenue"] / s["quantity"] if s["quantity"] else 0
        var_qty = fmt_pct(pct(s["quantity"], prev["quantity"]))
        a(f"| {i} | {name} | {s['quantity']} | R$ {s['revenue']:.2f} | R$ {ticket:.2f} | {prev['quantity']} | {var_qty} |")
    a("")

    return "\n".join(lines)


_STATIC_INSTRUCTIONS = """Você é um especialista em Google Ads e e-commerce para o mercado brasileiro. Analise os dados de performance da Smart GR (empresa de produtos para estética médica e microagulhamento) fornecidos a seguir e produza um relatório executivo completo em português.

Produza um relatório executivo em markdown com as seguintes seções obrigatórias:

## Avaliação Geral da Conta
Compare os dois períodos. Avalie a saúde geral da conta: crescimento ou queda de receita, eficiência de gasto, tendências de CTR e CPC. Seja específico com números.

## ROAS Real vs ROAS Reportado pelo Google Ads
Explique a diferença entre o ROAS reportado pelo Google Ads (conversions_value/custo) e o ROAS real calculado pela receita do Shopify. Analise o gap e o que ele significa para a tomada de decisão.

## Análise por Campanha
Para cada campanha ativa, indique claramente: **Escalar**, **Manter**, **Otimizar** ou **Pausar**, justificando com os dados. Use tabela se necessário.

## Top 20 Produtos — Insights
Destaque os produtos com melhor e pior desempenho, tendências de crescimento e oportunidades de cross-sell ou upsell com base nos dados.

## Top 3 Oportunidades de Crescimento
Oportunidades concretas identificadas na comparação entre períodos. Cada uma com estimativa de impacto.

## 5 Ações Prioritárias para a Próxima Semana
Lista numerada, cada ação com: o quê fazer, onde (campanha/produto específico), e resultado esperado.

## Alertas de Atenção
Liste métricas com queda significativa (>15%), CPA acima do esperado, CTR baixo, campanhas sem veiculação ou qualquer anomalia relevante.

Seja direto, use dados reais do relatório e evite generalismos.

---

Dados de performance:"""


def build_messages(data_report: str) -> list:
    """Returns a messages list with prompt caching on the static instructions block.

    The static instructions block (~400 tokens) is cached with ephemeral TTL (5 min),
    so repeated calls within that window only bill for the dynamic data tokens.
    """
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": _STATIC_INSTRUCTIONS,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": data_report,
                },
            ],
        }
    ]


def main():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY não encontrado no .env")

    now = datetime.now(timezone.utc)
    cur_end = now
    cur_start = now - timedelta(days=30)
    prev_end = cur_start
    prev_start = now - timedelta(days=60)

    print("Coletando dados do Shopify — período atual...")
    shopify_cur = shopify.get_period_data(cur_start, cur_end)
    print("Coletando dados do Shopify — período anterior...")
    shopify_prev = shopify.get_period_data(prev_start, prev_end)

    print("Coletando dados do Google Ads — período atual...")
    gads_cur = gads.get_period_data(cur_start.replace(tzinfo=None), cur_end.replace(tzinfo=None))
    print("Coletando dados do Google Ads — período anterior...")
    gads_prev = gads.get_period_data(prev_start.replace(tzinfo=None), prev_end.replace(tzinfo=None))

    print("Montando relatório de dados...\n")
    data_report = build_report_data(shopify_cur, shopify_prev, gads_cur, gads_prev)

    print("Enviando para Claude para análise...\n")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    full_response = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": "Você é um especialista em performance de Google Ads e e-commerce para o mercado brasileiro. Produza análises precisas, baseadas em dados, em português.",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=build_messages(data_report),
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_response += text

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    header = f"# Relatório Smart GR — Gerado em {now_str}\n\n"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + full_response)

    print(f"\n\nRelatório salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
