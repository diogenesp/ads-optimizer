# Relatório Smart GR — Gerado em 24/04/2026 11:52

# Relatório Executivo de Performance — Smart GR
**Período de Análise:** 25/03/2026 a 24/04/2026 vs. 23/02/2026 a 25/03/2026

---

## Avaliação Geral da Conta

### Visão Consolidada

O período atual registra **crescimento sólido no negócio** com sinais mistos dentro da plataforma Google Ads — o que exige leitura cuidadosa antes de qualquer decisão de budget.

**O negócio como um todo (Shopify — todas as origens):**

| Métrica | Atual | Anterior | Variação |
|---|---|---|---|
| Pedidos | 1.855 | 1.609 | **+15,3%** |
| Receita | R$ 1.326.981 | R$ 1.091.654 | **+21,6%** |
| Ticket médio | R$ 715,35 | R$ 678,47 | **+5,4%** |

O crescimento de +21,6% na receita total, combinado com um aumento de ticket médio de +5,4%, indica que a empresa não apenas vendeu mais — vendeu melhor. Esse crescimento simultâneo de volume e valor unitário é um sinal de saúde comercial genuína.

**Google Ads — sinais de eficiência:**

O canal Google Ads gastou praticamente o mesmo valor (R$ 21.100 vs. R$ 21.706, queda de apenas -2,8%) e, ainda assim, gerou **+28,3% mais pedidos atribuídos no Shopify** e **+25,5% mais receita real**. Isso significa que a conta ficou significativamente mais eficiente no período.

Os dados da plataforma, no entanto, mostram aparente contradição:

- **Impressões caíram -14,2%** (521.420 vs. 607.936) — a conta alcançou menos pessoas
- **Cliques subiram +9,2%** (23.025 vs. 21.082) — mas mais pessoas clicaram proporcionalmente
- **CTR saltou de 3,47% para 4,42% (+27,3%)** — o tráfego ficou mais qualificado
- **CPC médio caiu de R$ 1,03 para R$ 0,92 (-11,0%)** — pagando menos por clique mais relevante
- **Conversões reportadas pelo GA caíram -2,4%** (687,8 vs. 704,6) — aparente contradição com os dados Shopify

> **Interpretação-chave:** A conta está atraindo menos tráfego genérico, mais tráfego qualificado, com menor custo por clique e maior taxa de conversão real. A queda nas impressões não é negativa — é provável resultado do algoritmo das campanhas PMax e de Search otimizando para públicos de maior intenção. A divergência entre conversões reportadas no GA (-2,4%) e pedidos Shopify (+28,3%) aponta para um problema de rastreamento que precisa ser investigado (ver seção ROAS Real vs. Reportado).

---

## ROAS Real vs. ROAS Reportado pelo Google Ads

### Entendendo a Divergência

| Métrica | Atual | Anterior | Variação |
|---|---|---|---|
| Gasto Google Ads | R$ 21.100,38 | R$ 21.705,80 | -2,8% |
| Receita Google Ads (GA — conversions_value) | R$ 593.178,53 | R$ 620.849,44 | -4,5% |
| **ROAS reportado (GA)** | **28,11x** | **28,60x** | **-1,7%** |
| Receita Shopify atribuída ao Google (último clique não direto) | R$ 517.778,83 | R$ 412.579,72 | +25,5% |
| **ROAS real (Shopify / gasto GA)** | **24,54x** | **19,01x** | **+29,1%** |

### O que está acontecendo

**O Google Ads reporta R$ 593.178 de receita; o Shopify atribui R$ 517.779.** Há uma diferença de **R$ 75.400 (≈ 12,7%)** que o Google "enxerga" mas o Shopify não confirma pelo modelo de último clique não direto.

Isso é estruturalmente esperado pelas seguintes razões:

1. **Modelo de atribuição diferente:** O Google Ads usa atribuição baseada em dados (data-driven attribution) ou último clique dentro da janela de conversão configurada, enquanto o Shopify usa "último clique não direto" — que ignora tráfego direto subsequente e pode creditar outros canais em compras multicanal.

2. **Janela de conversão:** Se a janela de conversão no Google Ads estiver configurada para 30 ou 90 dias, pedidos de cliques do período anterior estão sendo contabilizados no período atual.

3. **Micro-conversões:** O Google pode estar contando eventos intermediários (add-to-cart, início de checkout) se configurados como conversões — o que inflaria o número reportado.

4. **Cancelamentos e devoluções:** O Shopify reflete receita líquida confirmada; o Google não desconta cancelamentos automaticamente.

### O que isso significa para a tomada de decisão

> ⚠️ **Use sempre o ROAS real (Shopify) como bússola estratégica.** O ROAS do Google é útil para comparações relativas entre campanhas (qual performa melhor que outra), mas o valor absoluto deve ser validado pelo Shopify.

O dado mais relevante do período: enquanto o ROAS reportado pelo GA *caiu* de 28,60x para 28,11x (-1,7%), sugerindo piora, o ROAS real *subiu* de 19,01x para **24,54x (+29,1%)**, indicando melhora expressiva de eficiência. **Decisões baseadas apenas no painel do Google Ads levariam a conclusões erradas neste caso.**

---

## Análise por Campanha

### Resumo de Recomendações

| Campanha | Gasto | ROAS (GA) | Var. ROAS | Conv | CPA | Recomendação |
|---|---|---|---|---|---|---|
| SRCH — Branding Kw's Exata Brasil | R$ 1.915 | 58,26x | +22,1% | 128,4 | R$ 14,91 | 🟢 **Escalar** |
| PMax — Microagulhamento Smart Pen | R$ 3.018 | 42,20x | +21,6% | 96,6 | R$ 31,25 | 🟢 **Escalar** |
| SRCH — Smart Pen Exata | R$ 1.381 | 45,11x | -20,7% | 51,2 | R$ 27,00 | 🟡 **Otimizar** |
| SRCH — Branding Kw's Exata SP | R$ 1.087 | 38,94x | -9,3% | 51,0 | R$ 21,32 | 🔵 **Manter** |
| PMax — Microagulhamento Smart Pen 2 | R$ 2.760 | 32,65x | -11,7% | 49,8 | R$ 55,46 | 🟡 **Otimizar** |
| PMax — Ativos e Monodoses | R$ 3.293 | 20,56x | -15,9% | 150,3 | R$ 21,91 | 🟡 **Otimizar** |
| SRCH — Branding Produtos Ampla [Lista Marcas] | R$ 2.378 | 15,75x | +1,7% | 52,0 | R$ 45,71 | 🟡 **Otimizar** |
| PMax — Microagulhamento Derma Roller | R$ 927 | 16,18x | -13,5% | 34,6 | R$ 26,84 | 🟡 **Otimizar** |
| PMax — Cartucho Smart Pen | R$ 2.796 | 10,06x | -35,3% | 51,5 | R$ 54,34 | 🔴 **Pausar / Reestruturar** |
| PMax — Smart Micro Cânula | R$ 1.544 | 7,23x | +9,9% | 22,5 | R$ 68,52 | 🟡 **Otimizar** |

---

### Detalhamento por Campanha

**🟢 SRCH — Branding Kw's Exata Brasil — ESCALAR**
- ROAS de **58,26x** com CPA de apenas R$ 14,91 — a campanha mais eficiente da conta por larga margem
- 128,4 conversões com apenas R$ 1.915 de investimento
- CTR de 43,17% confirma tráfego de altíssima intenção (usuários buscando a marca diretamente)
- ROAS cresceu +22,1% no período
- **Ação:** Aumentar budget em 30-50%. Testar expansão para outras regiões além do Brasil geral, monitorando qualidade do tráfego. O risco de canibalização com a campanha de SP é baixo dado o volume.

**🟢 PMax — Microagulhamento Smart Pen — ESCALAR**
- ROAS de **42,20x** com crescimento de +21,6% — a melhor PMax da conta em eficiência
- 96,6 conversões com R$ 3.017 investidos
- Produto âncora (Smart Pen, ticket R$ 1.371) claramente sendo bem servido por esta campanha
- **Ação:** Aumentar budget em 20-30%. Alimentar com novos ativos criativos: vídeos de demonstração, depoimentos de profissionais. Revisar os signal audiences para garantir que está alcançando profissionais de estética médica.

**🟡 SRCH — Smart Pen Exata — OTIMIZAR**
- ROAS ainda alto (45,11x), mas **caiu -20,7%** no período — o maior alerta nas campanhas de Search
- 51,2 conversões com CPA de R$ 27,00
- A queda pode indicar competição crescente nos leilões, deterioração do Quality Score ou mudança de comportamento de busca
- **Ação:** Auditar os termos de busca das últimas 4 semanas. Verificar se há novos concorrentes bidding nas mesmas keywords. Revisar os anúncios e extensões. Não aumentar budget até estabilizar o ROAS.

**🔵 SRCH — Branding Kw's Exata SP — MANTER**
- ROAS de **38,94x** com leve queda de -9,3% — ainda sólida
- CPA de R$ 21,32 com 51 conversões
- Segmentação geográfica para SP faz sentido estratégico dado o mercado de estética médica concentrado na capital
- **Ação:** Manter budget atual. Monitorar por mais um ciclo antes de qualquer ajuste.

**🟡 PMax — Microagulhamento Smart Pen 2 — OTIMIZAR**
- ROAS de **32,65x** com queda de -11,7% e CPA de R$ 55,46 (o mais alto entre as PMax de microagulhamento)
- Produto de alto ticket (Smart Pen 2, R$ 2.650) justifica CPA mais alto, mas a queda de ROAS merece atenção
- **Ação:** Revisar os asset groups. Separar ativos voltados para Smart Pen 2 vs. outros produtos que possam estar sendo servidos. Adicionar audience signals com listas de compradores da Smart Pen 1 (upsell natural).

**🟡 PMax — Ativos e Monodoses — OTIMIZAR**
- Maior volume de conversões da conta (150,3), mas ROAS de **20,56x caindo -15,9%**
- Inclui produtos como GHK-Cu Exo Skin Pro e PDRN Skin Pro — categoria em expansão no período
- CPA de R$ 21,91 é razoável, mas a queda de eficiência com budget de R$ 3.293 (o maior da conta) é preocupante
- **Ação:** Segmentar por categoria de produto dentro da PMax (asset groups separados por linha de ativo vs. linha de monodoses). Verificar se produtos de baixo ticket (Derma Roller) estão consumindo budget que deveria ir para ativos de maior margem.

**🟡 SRCH — Branding Produtos Ampla [Lista Marcas] — OTIMIZAR**
- ROAS de apenas **15,75x** com CPA de R$ 45,71 — o pior CPA entre as campanhas de Search
- O uso de "Lista de Marcas" indica que esta campanha serve como contenção para buscas de marca ampliadas
- Budget de R$ 2.378 com ROAS 3,7x abaixo da campanha de marca exata aponta ineficiência
- **Ação:** Revisar quais termos estão ativando os anúncios. Negativar termos que são melhor servidos pela campanha de exata. Considerar reduzir budget em 25% e realocar para Branding Exata.

**🟡 PMax — Derma Roller — OTIMIZAR**
- ROAS de **16,18x** com queda de -13,5%
- Produto de baixo ticket (R$ 26,91) — volume alto necessário para justificar o gasto
- 34,6 conversões com R$ 927 de gasto = CPA de R$ 26,84, razoável para o produto
- **Ação:** Avaliar se faz sentido manter como campanha separada ou consolidar no PMax de Ativos e Monodoses. O ROAS ainda está acima do mínimo aceitável, mas a tendência de queda precisa ser monitorada.

**🔴 PMax — Cartucho Smart Pen — PAUSAR / REESTRUTURAR**
- ROAS de **10,06x com queda de -35,3%** — a maior deterioração da conta no período
- CPA de R$ 54,34 para um produto de R$ 251,10 (ticket médio) = margem comprimida
- R$ 2.796 de gasto para apenas 51,5 conversões
- O produto Cartucho em si performa bem organicamente (161 unidades vendidas no top de produtos), sugerindo que a campanha paga está adicionando pouco valor incremental ou está captando conversões que ocorreriam de qualquer forma
- **Ação:** Pausar ou reduzir budget em 60% imediatamente. Investigar sobreposição de audiência com as campanhas de Branding (que podem estar capturando esses clientes mais eficientemente). Considerar estratégia de bundle no produto para aumentar ticket antes de reinvestir.

**🟡 PMax — Smart Micro Cânula — OTIMIZAR**
- ROAS de **7,23x** — o mais baixo da conta, mas com crescimento de +9,9%
- CPA de R$ 68,52 para produto de R$ 163-165 de ticket é alto
- 22,5 conversões com R$ 1.544 de investimento
- A tendência positiva (+9,9%) sugere que o algoritmo ainda está em fase de aprendizado ou que o produto está ganhando tração
-