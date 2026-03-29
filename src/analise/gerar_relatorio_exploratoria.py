"""
Gera relatório HTML interativo da análise exploratória.

Converte os gráficos gerados e os resultados estatísticos em uma página
HTML autocontida com navegação e análise interpretativa.

Uso:
    python -m src.analise.gerar_relatorio_exploratoria
"""

import base64
import webbrowser
from pathlib import Path

import pandas as pd

GRAFICOS = Path("resultados/graficos")
TABELAS = Path("resultados/tabelas")
SAIDA = Path("resultados/relatorio_exploratoria.html")


def img_to_base64(caminho: Path) -> str:
    """Converte imagem para base64 inline."""
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def carregar_tabela_csv(caminho: Path) -> pd.DataFrame:
    """Carrega CSV como DataFrame."""
    return pd.read_csv(caminho, index_col=0 if "descritivas" in str(caminho) else None)


def gerar_html():
    # Carregar tabelas
    df_estac = carregar_tabela_csv(TABELAS / "testes_estacionariedade.csv")
    df_desc = carregar_tabela_csv(TABELAS / "estatisticas_descritivas.csv")

    # Converter imagens
    imgs = {}
    for f in sorted(GRAFICOS.glob("*.png")):
        imgs[f.stem] = img_to_base64(f)

    # Montar tabela de estacionariedade em HTML
    estac_rows = ""
    for _, row in df_estac.iterrows():
        diag = row["Diagnóstico (nível)"]
        if "Estacionária" == diag:
            badge = '<span class="badge badge-ok">Estacionária</span>'
        elif "Não" in str(diag):
            badge = '<span class="badge badge-warn">Não estacionária</span>'
        else:
            badge = '<span class="badge badge-neutral">Inconclusivo</span>'

        id_col = row["I(d)"]
        if id_col == "I(0)":
            id_badge = '<span class="badge badge-ok">I(0)</span>'
        elif id_col == "I(1)":
            id_badge = '<span class="badge badge-warn">I(1)</span>'
        else:
            id_badge = '<span class="badge badge-danger">I(2)?</span>'

        adf_p = float(row["ADF p-valor"])
        kpss_p = float(row["KPSS p-valor"])
        adf_d_p = float(row["ADF 1ª dif. p-valor"])

        estac_rows += f"""
        <tr>
            <td class="var-name">{row["Variável"]}</td>
            <td class="num">{adf_p:.4f}</td>
            <td class="num">{kpss_p:.4f}</td>
            <td>{badge}</td>
            <td class="num">{adf_d_p:.4f}</td>
            <td>{id_badge}</td>
        </tr>"""

    # Tabela descritiva
    desc_rows = ""
    for idx, row in df_desc.iterrows():
        desc_rows += f"""
        <tr>
            <td class="var-name">{idx}</td>
            <td class="num">{row['N']:.0f}</td>
            <td class="num">{row['Média']:.2f}</td>
            <td class="num">{row['Desvio']:.2f}</td>
            <td class="num">{row['Mín']:.2f}</td>
            <td class="num">{row['Mediana']:.2f}</td>
            <td class="num">{row['Máx']:.2f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise Exploratória — Endividamento e Percepção Econômica</title>
    <style>
        :root {{
            --azul: #1a3c78;
            --azul-claro: #2980b9;
            --vermelho: #c0392b;
            --cinza-bg: #f5f7fa;
            --cinza-borda: #e1e5eb;
            --texto: #2c3e50;
            --texto-leve: #5d6d7e;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: var(--texto);
            background: var(--cinza-bg);
            line-height: 1.6;
        }}

        /* NAV */
        nav {{
            position: fixed;
            top: 0;
            width: 100%;
            background: var(--azul);
            color: white;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        nav .nav-inner {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 24px;
            display: flex;
            align-items: center;
            gap: 32px;
            overflow-x: auto;
        }}
        nav .brand {{
            font-weight: 700;
            font-size: 15px;
            white-space: nowrap;
            padding: 14px 0;
        }}
        nav a {{
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            font-size: 13px;
            white-space: nowrap;
            padding: 14px 0;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        nav a:hover {{ color: white; border-bottom-color: rgba(255,255,255,0.5); }}

        /* MAIN */
        main {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 70px 24px 60px;
        }}

        /* HEADER */
        .header {{
            text-align: center;
            padding: 48px 0 36px;
        }}
        .header h1 {{
            font-size: 28px;
            color: var(--azul);
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            font-size: 16px;
            color: var(--texto-leve);
        }}
        .header .meta {{
            margin-top: 12px;
            font-size: 13px;
            color: var(--texto-leve);
        }}

        /* SECTIONS */
        section {{
            background: white;
            border-radius: 10px;
            padding: 32px;
            margin-bottom: 28px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border: 1px solid var(--cinza-borda);
        }}
        section h2 {{
            font-size: 20px;
            color: var(--azul);
            margin-bottom: 6px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--cinza-borda);
        }}
        section h3 {{
            font-size: 15px;
            color: var(--azul-claro);
            margin: 20px 0 8px;
        }}
        section p {{
            margin: 10px 0;
            font-size: 14px;
            color: var(--texto);
        }}
        .insight {{
            background: #eef4fb;
            border-left: 4px solid var(--azul-claro);
            padding: 14px 18px;
            margin: 16px 0;
            border-radius: 0 6px 6px 0;
            font-size: 14px;
        }}
        .insight strong {{ color: var(--azul); }}
        .warning {{
            background: #fdf2e9;
            border-left: 4px solid #e67e22;
            padding: 14px 18px;
            margin: 16px 0;
            border-radius: 0 6px 6px 0;
            font-size: 14px;
        }}
        .key-finding {{
            background: #f9ebea;
            border-left: 4px solid var(--vermelho);
            padding: 14px 18px;
            margin: 16px 0;
            border-radius: 0 6px 6px 0;
            font-size: 14px;
        }}

        /* IMAGES */
        .grafico {{
            text-align: center;
            margin: 20px 0;
        }}
        .grafico img {{
            max-width: 100%;
            border-radius: 6px;
            border: 1px solid var(--cinza-borda);
            cursor: zoom-in;
            transition: transform 0.2s;
        }}
        .grafico img:hover {{ transform: scale(1.01); }}
        .grafico img.zoomed {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) scale(1);
            max-width: 95vw;
            max-height: 95vh;
            z-index: 2000;
            cursor: zoom-out;
            border: 3px solid white;
            box-shadow: 0 0 0 9999px rgba(0,0,0,0.7);
            border-radius: 8px;
        }}
        .grafico .caption {{
            font-size: 12px;
            color: var(--texto-leve);
            margin-top: 8px;
            font-style: italic;
        }}

        /* TABLES */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 13px;
        }}
        thead th {{
            background: var(--azul);
            color: white;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        tbody td {{
            padding: 8px 12px;
            border-bottom: 1px solid var(--cinza-borda);
        }}
        tbody tr:nth-child(even) {{ background: #f8f9fb; }}
        tbody tr:hover {{ background: #eef2f7; }}
        .var-name {{ font-weight: 600; color: var(--azul); }}
        .num {{ font-family: 'Consolas', 'Fira Mono', monospace; text-align: right; }}

        /* BADGES */
        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-ok {{ background: #d5f5e3; color: #1e8449; }}
        .badge-warn {{ background: #fdebd0; color: #b9770e; }}
        .badge-danger {{ background: #fadbd8; color: #922b21; }}
        .badge-neutral {{ background: #eaecee; color: #5d6d7e; }}

        /* CORRELATION HIGHLIGHT */
        .corr-table td.neg-strong {{ background: #f5b7b1; font-weight: 700; }}
        .corr-table td.neg-mod {{ background: #fadbd8; }}
        .corr-table td.pos-strong {{ background: #aed6f1; font-weight: 700; }}
        .corr-table td.pos-mod {{ background: #d6eaf8; }}
        .corr-table td.ns {{ color: #aab7b8; }}

        /* FOOTER */
        footer {{
            text-align: center;
            padding: 24px;
            font-size: 12px;
            color: var(--texto-leve);
        }}
    </style>
</head>
<body>

<nav>
    <div class="nav-inner">
        <span class="brand">Análise Exploratória</span>
        <a href="#series">Séries Temporais</a>
        <a href="#hipotese">Hipótese Central</a>
        <a href="#correlacoes">Correlações</a>
        <a href="#crosscorr">Cross-Correlation</a>
        <a href="#scatter">Dispersão</a>
        <a href="#estacionariedade">Estacionariedade</a>
        <a href="#descritivas">Descritivas</a>
        <a href="#sintese">Síntese</a>
    </div>
</nav>

<main>

<div class="header">
    <h1>Endividamento Familiar e Percepção Econômica no Brasil</h1>
    <div class="subtitle">Análise Exploratória dos Dados — Relatório Completo</div>
    <div class="meta">Juliane Furno &middot; Período: 2012–2025 &middot; 14 variáveis &middot; 171 observações mensais</div>
</div>

<!-- ============================================================ -->
<section id="series">
    <h2>1. Painel de Séries Temporais</h2>
    <p>Visão geral das oito variáveis principais da pesquisa ao longo de 2012–2025. As faixas cinza marcam a recessão de 2014–16 e a pandemia de 2020.</p>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('01_painel_series_temporais', '')}" alt="Painel de séries temporais">
        <div class="caption">Figura 1 — Séries temporais das variáveis-chave (clique para ampliar)</div>
    </div>

    <h3>Observações iniciais</h3>
    <div class="insight">
        <strong>Endividamento em tendência de alta:</strong> tanto o indicador BCB (36% → 50%) quanto a PEIC (56% → 80%) mostram crescimento persistente no período, com aceleração pós-2020. Trata-se de uma tendência estrutural de financeirização do consumo das famílias.
    </div>
    <div class="insight">
        <strong>ICC volátil com ciclos claros:</strong> a confiança do consumidor despencou na recessão 2015–16 (de 170 para 84), recuperou parcialmente, caiu novamente na pandemia, e voltou a subir desde 2022. O subíndice de Condições Atuais (não mostrado aqui) é o mais sensível.
    </div>
    <div class="insight">
        <strong>Desemprego e renda como contexto:</strong> o desemprego subiu de 7% para 14% na recessão e voltou a cair para 5% em 2025. O rendimento médio real mostra recuperação recente (R$ 3.742), mas a pergunta é: quanto dessa renda está comprometida com dívida?
    </div>
</section>

<!-- ============================================================ -->
<section id="hipotese">
    <h2>2. Hipótese Central: Endividamento vs. Confiança</h2>
    <p>Gráfico de dois eixos sobrepondo o percentual de famílias endividadas (PEIC) e o Índice de Confiança do Consumidor (ICC).</p>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('02_endividamento_vs_icc', '')}" alt="Endividamento vs ICC">
        <div class="caption">Figura 2 — PEIC Famílias Endividadas (%, eixo esquerdo) vs. ICC (eixo direito)</div>
    </div>

    <div class="key-finding">
        <strong>Achado central:</strong> visualmente, há uma <strong>relação inversa clara</strong> entre endividamento e confiança — quando o endividamento sobe, o ICC tende a cair, e vice-versa. No entanto, de 2022 em diante, ambos sobem simultaneamente, rompendo esse padrão. Isso sugere que o nível absoluto de endividamento não é o único determinante — o <strong>contexto macroeconômico</strong> (emprego, renda) media essa relação.
    </div>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('03_comprometimento_vs_icc_atuais', '')}" alt="Comprometimento vs ICC Atuais">
        <div class="caption">Figura 3 — Comprometimento de Renda (BCB, %) vs. ICC Condições Atuais</div>
    </div>

    <div class="insight">
        <strong>Comprometimento de renda vs. percepção:</strong> este gráfico revela um padrão interessante. Na recessão 2015–16, o comprometimento de renda caiu (famílias cortaram crédito) enquanto a percepção despencou — ou seja, foi o desemprego, não a dívida, que destruiu a confiança. Pós-2020, ambos sobem juntos, sugerindo que famílias estão se endividando mais num contexto de recuperação (crédito de expansão, não de sobrevivência).
    </div>
</section>

<!-- ============================================================ -->
<section id="correlacoes">
    <h2>3. Matriz de Correlação</h2>
    <p>Correlação de Pearson entre as 14 variáveis do painel, usando observações mensais simultâneas.</p>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('04_matriz_correlacao', '')}" alt="Matriz de correlação">
        <div class="caption">Figura 4 — Matriz de correlação (triângulo inferior). Vermelho = correlação positiva, azul = negativa.</div>
    </div>

    <h3>Correlações-chave para a hipótese</h3>
    <table class="corr-table">
        <thead>
            <tr>
                <th>Variável X</th>
                <th>Variável Y</th>
                <th>r</th>
                <th>Sig.</th>
                <th>Interpretação</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="var-name">Desemprego</td>
                <td>ICC Geral</td>
                <td class="num neg-strong">-0.431</td>
                <td>***</td>
                <td>Maior correlato negativo do ICC — rival à hipótese</td>
            </tr>
            <tr>
                <td class="var-name">PEIC Renda Comprometida</td>
                <td>ICC Geral</td>
                <td class="num neg-strong">-0.383</td>
                <td>***</td>
                <td>Suporte à hipótese: peso da dívida na renda corrói confiança</td>
            </tr>
            <tr>
                <td class="var-name">Comprom. Renda (BCB)</td>
                <td>ICC Geral</td>
                <td class="num pos-mod">+0.328</td>
                <td>***</td>
                <td>Sinal positivo — paradoxal; endividamento de expansão?</td>
            </tr>
            <tr>
                <td class="var-name">Comprom. Renda (BCB)</td>
                <td>ICC Cond. Atuais</td>
                <td class="num pos-mod">+0.310</td>
                <td>***</td>
                <td>Mesmo padrão com subíndice de situação atual</td>
            </tr>
            <tr>
                <td class="var-name">PEIC Endividadas</td>
                <td>ICC Geral</td>
                <td class="num ns">-0.042</td>
                <td>n.s.</td>
                <td>Nível de endividamento não se associa linearmente ao ICC</td>
            </tr>
            <tr>
                <td class="var-name">Endividamento BCB</td>
                <td>ICC Geral</td>
                <td class="num ns">-0.090</td>
                <td>n.s.</td>
                <td>Idem — estoque de dívida sozinho não explica percepção</td>
            </tr>
            <tr>
                <td class="var-name">Selic</td>
                <td>ICC Geral</td>
                <td class="num neg-mod">-0.164</td>
                <td>*</td>
                <td>Juros altos associados a menor confiança</td>
            </tr>
            <tr>
                <td class="var-name">Inadimplência</td>
                <td>ICC Geral</td>
                <td class="num pos-mod">+0.242</td>
                <td>**</td>
                <td>Sinal positivo — ambos sobem na expansão recente</td>
            </tr>
        </tbody>
    </table>

    <h3>Outras correlações relevantes</h3>
    <div class="insight">
        <strong>Endividamento BCB e PEIC são altamente correlacionados</strong> (r = 0.97), confirmando que medem o mesmo fenômeno por fontes diferentes. O <strong>spread bancário correlaciona positivamente com Selic</strong> (r = 0.56), como esperado — juros altos ampliam a margem bancária.
    </div>
    <div class="warning">
        <strong>Atenção ao sinal positivo do comprometimento (BCB) com ICC:</strong> isso não invalida a hipótese, mas indica que a correlação simples é insuficiente. O comprometimento de renda subiu junto com a confiança nos últimos anos porque o emprego melhorou e as famílias voltaram a tomar crédito. É preciso um modelo VAR para separar esses efeitos.
    </div>
</section>

<!-- ============================================================ -->
<section id="crosscorr">
    <h2>4. Cross-Correlation: Quem Precede Quem?</h2>
    <p>Análise de correlação cruzada com defasagens de até 24 meses. Lag positivo = endividamento precede ICC; lag negativo = ICC precede endividamento.</p>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('05_cross_correlation', '')}" alt="Cross-correlation">
        <div class="caption">Figura 5 — Cross-correlation entre medidas de endividamento e ICC. Linhas tracejadas = limites de significância a 5%.</div>
    </div>

    <div class="key-finding">
        <strong>Padrão temporal:</strong> a correlação negativa mais forte ocorre com <strong>lags negativos</strong> (ICC nos meses anteriores). Isso sugere que <strong>a queda de confiança precede o aumento do endividamento</strong> — ou seja, famílias que percebem piora econômica recorrem mais ao crédito. Esse achado é consistente com a ideia de <strong>crédito como mecanismo de sobrevivência</strong> na perspectiva marxista.
    </div>
    <div class="insight">
        <strong>Implicação metodológica:</strong> a causalidade potencialmente bidirecional reforça a necessidade de usar VAR/VECM com testes de causalidade de Granger, em vez de regressões simples. Variáveis instrumentais também serão importantes na análise micro (POF).
    </div>
</section>

<!-- ============================================================ -->
<section id="scatter">
    <h2>5. Gráficos de Dispersão</h2>
    <p>Relação entre medidas de endividamento e confiança do consumidor, com linha de tendência (OLS).</p>

    <div class="grafico">
        <img src="data:image/png;base64,{imgs.get('06_scatter_hipotese', '')}" alt="Scatter plots">
        <div class="caption">Figura 6 — Scatter plots com coeficiente de correlação e p-valor. Linha tracejada = regressão linear simples.</div>
    </div>

    <div class="insight">
        <strong>PEIC Endividadas vs. ICC (r = -0.042):</strong> nuvem dispersa, sem relação linear. O <strong>nível</strong> de endividamento é insuficiente para explicar percepção — o que importa é o <strong>custo</strong> dessa dívida.
    </div>
    <div class="insight">
        <strong>Comprometimento Renda vs. ICC (r = +0.328):</strong> relação positiva, contraintuitiva. Reflete o fato de que o comprometimento sobe tanto em recessão (juros altos + renda caindo) quanto em expansão (mais crédito + consumo). É uma variável ambígua sem controle pelo ciclo.
    </div>
</section>

<!-- ============================================================ -->
<section id="estacionariedade">
    <h2>6. Testes de Estacionariedade</h2>
    <p>Testes ADF (H₀: raiz unitária) e KPSS (H₀: estacionária) para cada variável em nível e em primeira diferença.</p>

    <table>
        <thead>
            <tr>
                <th>Variável</th>
                <th>ADF p-valor</th>
                <th>KPSS p-valor</th>
                <th>Diagnóstico (nível)</th>
                <th>ADF 1ª dif. p-valor</th>
                <th>Ordem</th>
            </tr>
        </thead>
        <tbody>
            {estac_rows}
        </tbody>
    </table>

    <div class="insight">
        <strong>Interpretação conjunta ADF + KPSS:</strong>
        <ul style="margin-top: 8px; padding-left: 20px; font-size: 14px;">
            <li><strong>I(0) — estacionárias em nível:</strong> PEIC Renda Comp., ICC (geral, atuais, expectativas), IPCA, Spread PF</li>
            <li><strong>I(1) — estacionárias em 1ª diferença:</strong> Endividamento BCB, Comprometimento Renda, PEIC Endividadas, PEIC Atraso, Selic, Desemprego</li>
            <li><strong>I(2)? — possível segunda diferença:</strong> Inadimplência, Rendimento Médio (requerem investigação com teste de Zivot-Andrews para quebra estrutural)</li>
        </ul>
    </div>
    <div class="warning">
        <strong>Implicação para modelagem:</strong> com variáveis de ordens mistas (I(0) e I(1)), o VAR padrão em nível não é adequado. As opções são: (a) VAR em primeiras diferenças; (b) teste de cointegração de Johansen e, se confirmada, VECM; (c) modelo ARDL (Bounds Test), que acomoda ordens mistas.
    </div>
</section>

<!-- ============================================================ -->
<section id="descritivas">
    <h2>7. Estatísticas Descritivas</h2>

    <table>
        <thead>
            <tr>
                <th>Variável</th>
                <th>N</th>
                <th>Média</th>
                <th>Desvio</th>
                <th>Mín</th>
                <th>Mediana</th>
                <th>Máx</th>
            </tr>
        </thead>
        <tbody>
            {desc_rows}
        </tbody>
    </table>

    <div class="insight">
        <strong>Destaques:</strong> o PEIC Renda Comprometida tem desvio-padrão baixíssimo (0.56), indicando pouca variação — isso limita seu poder explicativo em modelos de série temporal. Já o ICC Condições Atuais tem o maior desvio (31.13), sendo o mais sensível a choques conjunturais.
    </div>
</section>

<!-- ============================================================ -->
<section id="sintese">
    <h2>8. Síntese e Implicações para o Modelo</h2>

    <h3>O que os dados dizem sobre a hipótese?</h3>

    <div class="key-finding">
        <strong>A hipótese precisa de qualificação.</strong> Os dados sugerem que não é o <em>nível</em> de endividamento que deteriora a percepção, mas o <strong>custo do serviço da dívida</strong> em relação à renda (PEIC Renda Comprometida: r = -0.38 com ICC). Ao mesmo tempo, o <strong>desemprego</strong> aparece como o correlato mais forte (r = -0.43), disputando com o endividamento o papel de "principal fator".
    </div>

    <h3>Achados principais</h3>
    <p><strong>1. Nível de endividamento ≠ percepção</strong><br>
    Estar endividado (PEIC) não correlaciona com percepção negativa. Mas ter renda comprometida com dívida sim. A distinção estoque vs. fluxo é central.</p>

    <p><strong>2. O sinal paradoxal do comprometimento (BCB)</strong><br>
    O comprometimento de renda do BCB sobe em períodos de expansão do crédito (quando a confiança também está alta). Isso reflete a dualidade do crédito: ferramenta de consumo em momentos bons, armadilha em momentos ruins.</p>

    <p><strong>3. Causalidade potencialmente reversa</strong><br>
    A cross-correlation sugere que a queda de confiança <em>precede</em> o aumento do endividamento. Famílias que percebem piora recorrem ao crédito — o endividamento pode ser tanto causa quanto consequência da percepção negativa.</p>

    <p><strong>4. Desemprego é rival forte</strong><br>
    O desemprego tem a maior correlação negativa com o ICC. O modelo VAR precisará arbitrar se o endividamento tem efeito independente do mercado de trabalho.</p>

    <h3>Recomendações para próxima fase</h3>
    <p><strong>Modelo recomendado: ARDL (Bounds Test)</strong><br>
    Dado que as variáveis têm ordens de integração mistas (I(0) e I(1)), o ARDL de Pesaran, Shin & Smith (2001) é mais adequado que o VAR/VECM padrão. Ele permite testar cointegração e estimar efeitos de curto e longo prazo sem exigir que todas as variáveis sejam I(1).</p>

    <p><strong>Variável dependente sugerida:</strong> ICC Condições Atuais (maior variabilidade, mais sensível)<br>
    <strong>Variáveis explicativas:</strong> comprometimento de renda (BCB), desemprego, IPCA, Selic<br>
    <strong>Controles:</strong> rendimento médio real, spread bancário</p>
</section>

</main>

<footer>
    Análise Exploratória — Endividamento Familiar e Percepção Econômica no Brasil<br>
    Juliane Furno &middot; Gerado automaticamente via Python
</footer>

<script>
    // Zoom em imagens
    document.querySelectorAll('.grafico img').forEach(img => {{
        img.addEventListener('click', () => {{
            img.classList.toggle('zoomed');
        }});
    }});
    // ESC para fechar zoom
    document.addEventListener('keydown', e => {{
        if (e.key === 'Escape') {{
            document.querySelectorAll('.grafico img.zoomed').forEach(img => {{
                img.classList.remove('zoomed');
            }});
        }}
    }});
    // Smooth scroll
    document.querySelectorAll('nav a').forEach(a => {{
        a.addEventListener('click', e => {{
            e.preventDefault();
            const target = document.querySelector(a.getAttribute('href'));
            if (target) target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }});
    }});
</script>

</body>
</html>"""

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML gerado: {SAIDA}")
    print(f"Tamanho: {SAIDA.stat().st_size / 1024:.0f} KB")

    # Abrir no navegador
    webbrowser.open(str(SAIDA.resolve()))
    print("Aberto no navegador.")


if __name__ == "__main__":
    gerar_html()
