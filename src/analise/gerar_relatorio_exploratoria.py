"""
Gera relatório HTML interativo da análise exploratória com gráficos Plotly.

Converte os dados em gráficos interativos (hover para ver valores) e inclui
tooltips informativos (ℹ) para cada seção.

Uso:
    python -m src.analise.gerar_relatorio_exploratoria
"""

import json
import webbrowser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss

DADOS = Path("dados/processados")
TABELAS = Path("resultados/tabelas")
SAIDA = Path("resultados/relatorio_exploratoria.html")

CORES = {
    "endividamento": "#c0392b",
    "comprometimento": "#e74c3c",
    "icc": "#2980b9",
    "icc_atuais": "#3498db",
    "icc_expect": "#85c1e9",
    "ipca": "#e67e22",
    "selic": "#8e44ad",
    "desemprego": "#27ae60",
    "renda": "#16a085",
    "spread": "#d35400",
    "inadimplencia": "#c0392b",
    "peic_endiv": "#e74c3c",
    "peic_atraso": "#f39c12",
    "peic_renda": "#d35400",
}

# Tooltips explicativos para cada seção
TOOLTIPS = {
    "series": (
        "Este painel mostra a evolução de 8 variáveis macroeconômicas entre 2012 e 2025. "
        "As áreas cinza marcam a recessão de 2014–16 e a pandemia de 2020. "
        "Passe o mouse sobre as linhas para ver o valor exato em cada mês."
    ),
    "hipotese": (
        "Gráficos de dois eixos sobrepondo medidas de endividamento e confiança do consumidor. "
        "Se a hipótese for verdadeira, esperamos uma relação inversa: quando o endividamento sobe, "
        "a confiança cai. Passe o mouse para comparar os valores mês a mês."
    ),
    "correlacoes": (
        "A matriz de correlação de Pearson mede a associação linear entre pares de variáveis. "
        "Valores próximos de +1 indicam correlação positiva forte; próximos de -1, negativa forte; "
        "próximos de 0, ausência de associação linear. Passe o mouse para ver o valor exato."
    ),
    "crosscorr": (
        "A cross-correlation mostra como a correlação entre duas variáveis muda conforme "
        "deslocamos uma delas no tempo (lags). Lag positivo = endividamento precede ICC; "
        "lag negativo = ICC precede endividamento. Isso ajuda a inferir precedência temporal."
    ),
    "scatter": (
        "Os gráficos de dispersão mostram cada observação mensal como um ponto, permitindo "
        "visualizar o formato da relação entre endividamento e confiança. A linha tracejada "
        "é a regressão linear simples. Passe o mouse para ver a data e os valores de cada ponto."
    ),
    "estacionariedade": (
        "Testes ADF (H₀: raiz unitária) e KPSS (H₀: estacionária) verificam se as séries "
        "têm média constante ao longo do tempo. Séries não estacionárias precisam ser diferenciadas. "
        "I(0) = estacionária em nível; I(1) = estacionária após 1ª diferença."
    ),
    "descritivas": (
        "Estatísticas descritivas resumem a distribuição de cada variável: N (observações), "
        "média, desvio-padrão (dispersão), mínimo, mediana e máximo."
    ),
    "sintese": (
        "Síntese dos achados exploratórios e suas implicações para a modelagem econométrica "
        "na próxima fase da pesquisa."
    ),
}


# ============================================================
# Carregamento dos dados (replicado de exploratoria.py)
# ============================================================

def carregar_dados() -> dict[str, pd.Series]:
    dados = {}
    for nome in ["endividamento_familias", "comprometimento_renda", "ipca_mensal",
                  "selic_meta", "spread_medio_pf", "inadimplencia_pf",
                  "credito_pf_saldo", "credito_pf_concessoes"]:
        df = pd.read_parquet(DADOS / f"bcb_{nome}_mensal.parquet")
        dados[nome] = df["valor"]

    icc = pd.read_parquet(DADOS / "icc_confianca_consumidor_mensal.parquet")
    dados["icc_indice"] = icc["icc_indice"]
    dados["icc_condicoes_atuais"] = icc["icc_condicoes_atuais"]
    dados["icc_expectativas"] = icc["icc_expectativas"]

    peic = pd.read_parquet(DADOS / "peic_endividamento_mensal.parquet")
    for col in peic.columns:
        dados[col] = peic[col]

    for nome, arq in [("desemprego", "ibge_desemprego_trimestral"),
                       ("rendimento_medio", "ibge_rendimento_medio_trimestral")]:
        df = pd.read_parquet(DADOS / f"{arq}.parquet")
        dados[nome] = df["valor"]

    return dados


def construir_painel_mensal(dados: dict) -> pd.DataFrame:
    series_mensais = {
        "endividamento_bcb": dados["endividamento_familias"],
        "comprometimento_renda": dados["comprometimento_renda"],
        "icc_indice": dados["icc_indice"],
        "icc_condicoes_atuais": dados["icc_condicoes_atuais"],
        "icc_expectativas": dados["icc_expectativas"],
        "ipca": dados["ipca_mensal"],
        "selic": dados["selic_meta"],
        "spread_pf": dados["spread_medio_pf"],
        "inadimplencia": dados["inadimplencia_pf"],
        "peic_endividadas": dados["pct_familias_endividadas"],
        "peic_atraso": dados["pct_dividas_em_atraso"],
        "peic_renda_comp": dados["pct_renda_comprometida_divida"],
    }
    painel = pd.DataFrame(series_mensais)

    for nome in ["desemprego", "rendimento_medio"]:
        s = dados[nome].copy()
        s = s.resample("MS").first()
        s = s.reindex(painel.index).interpolate(method="linear")
        painel[nome] = s

    painel = painel[painel.index >= "2012-01-01"]
    return painel


# ============================================================
# Gráficos Plotly
# ============================================================

def _recessao_shapes(yref="y"):
    """Retorna shapes para marcar recessão e pandemia."""
    shapes = []
    for inicio, fim in [("2014-04-01", "2016-12-31"), ("2020-03-01", "2020-12-31")]:
        shapes.append(dict(
            type="rect", xref="x", yref="paper",
            x0=inicio, x1=fim, y0=0, y1=1,
            fillcolor="gray", opacity=0.08, line_width=0,
        ))
    return shapes


def fig_painel_series(painel: pd.DataFrame) -> str:
    configs = [
        ("endividamento_bcb", "Endividamento das Famílias (% renda 12m)", CORES["endividamento"], "%"),
        ("comprometimento_renda", "Comprometimento de Renda (% renda 12m)", CORES["comprometimento"], "%"),
        ("icc_indice", "Índice de Confiança do Consumidor", CORES["icc"], "índice"),
        ("peic_endividadas", "Famílias Endividadas — PEIC (%)", CORES["peic_endiv"], "%"),
        ("ipca", "IPCA Mensal (%)", CORES["ipca"], "%"),
        ("selic", "Taxa Selic Meta (% a.a.)", CORES["selic"], "% a.a."),
        ("desemprego", "Taxa de Desemprego (%)", CORES["desemprego"], "%"),
        ("rendimento_medio", "Rendimento Médio Real (R$)", CORES["renda"], "R$"),
    ]

    fig = make_subplots(rows=4, cols=2, subplot_titles=[c[1] for c in configs],
                        vertical_spacing=0.08, horizontal_spacing=0.08)

    for i, (col, titulo, cor, unidade) in enumerate(configs):
        row, colp = divmod(i, 2)
        s = painel[col].dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines",
            line=dict(color=cor, width=1.5),
            fill="tozeroy", fillcolor=cor.replace(")", ",0.08)").replace("rgb", "rgba") if cor.startswith("rgb") else None,
            name=titulo,
            hovertemplate=f"<b>{titulo}</b><br>%{{x|%b %Y}}<br>Valor: %{{y:.2f}} {unidade}<extra></extra>",
            showlegend=False,
        ), row=row + 1, col=colp + 1)

    # Recessão shapes para todos os subplots
    all_shapes = []
    for idx in range(8):
        xref = f"x{idx + 1}" if idx > 0 else "x"
        for inicio, fim in [("2014-04-01", "2016-12-31"), ("2020-03-01", "2020-12-31")]:
            all_shapes.append(dict(
                type="rect", xref=xref, yref="paper",
                x0=inicio, x1=fim, y0=0, y1=1,
                fillcolor="gray", opacity=0.08, line_width=0,
            ))

    fig.update_layout(
        height=900, shapes=all_shapes,
        title=dict(text="Séries Temporais — Variáveis da Pesquisa (2012–2025)", font=dict(size=16)),
        margin=dict(t=80, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(dtick="M12", tickformat="%Y", tickangle=45)

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-series")


def fig_endividamento_vs_icc(painel: pd.DataFrame) -> str:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    s_endiv = painel["peic_endividadas"].dropna()
    s_icc = painel["icc_indice"].dropna()

    fig.add_trace(go.Scatter(
        x=s_endiv.index, y=s_endiv.values, mode="lines",
        line=dict(color=CORES["endividamento"], width=2),
        name="Famílias Endividadas (PEIC, %)",
        hovertemplate="%{x|%b %Y}<br>Endividadas: %{y:.1f}%<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=s_icc.index, y=s_icc.values, mode="lines",
        line=dict(color=CORES["icc"], width=2),
        name="ICC (Fecomércio SP)",
        hovertemplate="%{x|%b %Y}<br>ICC: %{y:.1f}<extra></extra>",
    ), secondary_y=True)

    fig.add_hline(y=100, line_dash="dash", line_color=CORES["icc"], opacity=0.3, secondary_y=True)

    fig.update_layout(
        title="Endividamento das Famílias vs. Confiança do Consumidor (2012–2025)",
        height=420, shapes=_recessao_shapes(),
        legend=dict(x=0, y=1.12, orientation="h"),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Famílias Endividadas (%)", secondary_y=False,
                     title_font_color=CORES["endividamento"])
    fig.update_yaxes(title_text="ICC", secondary_y=True,
                     title_font_color=CORES["icc"])
    fig.update_xaxes(dtick="M12", tickformat="%Y", tickangle=45)

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-hipotese1")


def fig_comprometimento_vs_icc(painel: pd.DataFrame) -> str:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    s_comp = painel["comprometimento_renda"].dropna()
    s_icc = painel["icc_condicoes_atuais"].dropna()

    fig.add_trace(go.Scatter(
        x=s_comp.index, y=s_comp.values, mode="lines",
        line=dict(color=CORES["comprometimento"], width=2),
        name="Comprometimento de Renda (BCB, %)",
        hovertemplate="%{x|%b %Y}<br>Comprom.: %{y:.1f}%<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=s_icc.index, y=s_icc.values, mode="lines",
        line=dict(color=CORES["icc_atuais"], width=2),
        name="ICC — Condições Atuais",
        hovertemplate="%{x|%b %Y}<br>ICC Atuais: %{y:.1f}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        title="Comprometimento de Renda vs. Percepção da Situação Atual (2012–2025)",
        height=420, shapes=_recessao_shapes(),
        legend=dict(x=0, y=1.12, orientation="h"),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Comprometimento de Renda (%)", secondary_y=False,
                     title_font_color=CORES["comprometimento"])
    fig.update_yaxes(title_text="ICC — Condições Atuais", secondary_y=True,
                     title_font_color=CORES["icc_atuais"])
    fig.update_xaxes(dtick="M12", tickformat="%Y", tickangle=45)

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-hipotese2")


def fig_correlacao(painel: pd.DataFrame) -> str:
    colunas = [
        "endividamento_bcb", "comprometimento_renda", "peic_endividadas", "peic_atraso",
        "peic_renda_comp", "icc_indice", "icc_condicoes_atuais", "icc_expectativas",
        "ipca", "selic", "spread_pf", "inadimplencia", "desemprego", "rendimento_medio",
    ]
    nomes = [
        "Endivid. BCB", "Comprom. Renda", "PEIC Endivid.", "PEIC Atraso",
        "PEIC Renda Comp.", "ICC Geral", "ICC Atuais", "ICC Expectat.",
        "IPCA", "Selic", "Spread PF", "Inadimpl.", "Desemprego", "Rend. Médio",
    ]

    df_corr = painel[colunas].dropna()
    corr = df_corr.corr().values

    # Mascarar triângulo superior
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    corr_masked = np.where(mask, np.nan, corr)

    # Texto para hover
    text = []
    for i in range(len(nomes)):
        row_text = []
        for j in range(len(nomes)):
            if mask[i, j]:
                row_text.append("")
            else:
                row_text.append(f"{nomes[i]} × {nomes[j]}<br>r = {corr[i, j]:.3f}")
        text.append(row_text)

    fig = go.Figure(data=go.Heatmap(
        z=corr_masked, x=nomes, y=nomes,
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=text, hovertemplate="%{text}<extra></extra>",
        texttemplate="%{z:.2f}",
        textfont=dict(size=9),
    ))

    fig.update_layout(
        title="Matriz de Correlação — Variáveis da Pesquisa",
        height=650, width=750,
        xaxis=dict(tickangle=45, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=10), autorange="reversed"),
        margin=dict(l=120, b=120),
    )

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-corr")


def fig_cross_correlation(painel: pd.DataFrame) -> str:
    pares = [
        ("peic_endividadas", "icc_indice", "PEIC Endividadas vs. ICC"),
        ("comprometimento_renda", "icc_indice", "Comprom. Renda vs. ICC"),
        ("comprometimento_renda", "icc_condicoes_atuais", "Comprom. Renda vs. ICC Atuais"),
    ]

    fig = make_subplots(rows=1, cols=3, subplot_titles=[p[2] for p in pares],
                        horizontal_spacing=0.08)

    max_lags = 24

    for idx, (col_x, col_y, titulo) in enumerate(pares):
        df_pair = painel[[col_x, col_y]].dropna()
        x = df_pair[col_x].values
        y = df_pair[col_y].values

        x = (x - x.mean()) / x.std()
        y = (y - y.mean()) / y.std()

        correlacoes = []
        lags = list(range(-max_lags, max_lags + 1))
        for lag in lags:
            if lag >= 0:
                corr = np.corrcoef(x[:len(x) - lag], y[lag:])[0, 1]
            else:
                corr = np.corrcoef(x[-lag:], y[:len(y) + lag])[0, 1]
            correlacoes.append(corr)

        cores_barras = [CORES["endividamento"] if c < 0 else CORES["icc"] for c in correlacoes]

        fig.add_trace(go.Bar(
            x=lags, y=correlacoes,
            marker_color=cores_barras,
            hovertemplate="Lag: %{x} meses<br>Correlação: %{y:.3f}<extra></extra>",
            showlegend=False,
        ), row=1, col=idx + 1)

        # Limites de significância
        n = len(df_pair)
        sig = 2 / np.sqrt(n)
        for val in [sig, -sig]:
            fig.add_hline(y=val, line_dash="dash", line_color="gray", opacity=0.5,
                          row=1, col=idx + 1)

        # Anotar pico
        idx_pico = int(np.argmin(correlacoes))
        lag_pico = lags[idx_pico]
        corr_pico = correlacoes[idx_pico]
        fig.add_annotation(
            x=lag_pico, y=corr_pico,
            text=f"lag={lag_pico}<br>r={corr_pico:.2f}",
            showarrow=True, arrowhead=2, font=dict(size=10),
            bgcolor="white", bordercolor="gray",
            row=1, col=idx + 1,
        )

    fig.update_layout(
        height=400,
        title=dict(text="Cross-Correlation: Endividamento → Confiança do Consumidor", font=dict(size=14)),
        margin=dict(t=80, b=60),
    )
    fig.update_xaxes(title_text="Defasagem (meses)")
    fig.update_yaxes(title_text="Correlação", col=1)

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-crosscorr")


def fig_scatter(painel: pd.DataFrame) -> str:
    pares = [
        ("peic_endividadas", "icc_indice", "PEIC Endividadas (%)", "ICC Geral"),
        ("comprometimento_renda", "icc_indice", "Comprometimento Renda (%)", "ICC Geral"),
        ("comprometimento_renda", "icc_condicoes_atuais", "Comprometimento Renda (%)", "ICC Cond. Atuais"),
    ]

    fig = make_subplots(rows=1, cols=3, subplot_titles=[
        f"{lx} vs. {ly}" for _, _, lx, ly in pares
    ], horizontal_spacing=0.08)

    for idx, (col_x, col_y, label_x, label_y) in enumerate(pares):
        df_pair = painel[[col_x, col_y]].dropna()
        x, y = df_pair[col_x], df_pair[col_y]

        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)

        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(color=CORES["endividamento"], size=5, opacity=0.5),
            customdata=df_pair.index.strftime("%b %Y"),
            hovertemplate=f"<b>%{{customdata}}</b><br>{label_x}: %{{x:.2f}}<br>{label_y}: %{{y:.1f}}<extra></extra>",
            showlegend=False,
        ), row=1, col=idx + 1)

        fig.add_trace(go.Scatter(
            x=x_line, y=intercept + slope * x_line, mode="lines",
            line=dict(color=CORES["icc"], width=2, dash="dash"),
            hoverinfo="skip", showlegend=False,
        ), row=1, col=idx + 1)

        # Anotar r e p
        xref = "x domain" if idx == 0 else f"x{idx + 1} domain"
        yref = "y domain" if idx == 0 else f"y{idx + 1} domain"
        fig.add_annotation(
            x=0.5, y=1.0, xref=xref, yref=yref,
            text=f"r = {r_value:.3f} (p = {p_value:.1e})",
            showarrow=False, font=dict(size=11, color=CORES["icc"]),
            bgcolor="white", bordercolor=CORES["icc"], borderpad=3,
        )

        fig.update_xaxes(title_text=label_x, row=1, col=idx + 1)
        fig.update_yaxes(title_text=label_y, row=1, col=idx + 1)

    fig.update_layout(
        height=420,
        title=dict(text="Relação entre Endividamento e Confiança do Consumidor", font=dict(size=14)),
        margin=dict(t=80, b=60),
    )

    return fig.to_html(include_plotlyjs=False, full_html=False, div_id="chart-scatter")


# ============================================================
# Tabelas (carregadas dos CSVs já gerados)
# ============================================================

def carregar_tabela_csv(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, index_col=0 if "descritivas" in str(caminho) else None)


def tabela_estacionariedade_html(df_estac: pd.DataFrame) -> str:
    rows = ""
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

        rows += f"""
        <tr>
            <td class="var-name">{row["Variável"]}</td>
            <td class="num">{float(row["ADF p-valor"]):.4f}</td>
            <td class="num">{float(row["KPSS p-valor"]):.4f}</td>
            <td>{badge}</td>
            <td class="num">{float(row["ADF 1ª dif. p-valor"]):.4f}</td>
            <td>{id_badge}</td>
        </tr>"""
    return rows


def tabela_descritivas_html(df_desc: pd.DataFrame) -> str:
    rows = ""
    for idx, row in df_desc.iterrows():
        rows += f"""
        <tr>
            <td class="var-name">{idx}</td>
            <td class="num">{row['N']:.0f}</td>
            <td class="num">{row['Média']:.2f}</td>
            <td class="num">{row['Desvio']:.2f}</td>
            <td class="num">{row['Mín']:.2f}</td>
            <td class="num">{row['Mediana']:.2f}</td>
            <td class="num">{row['Máx']:.2f}</td>
        </tr>"""
    return rows


# ============================================================
# Montagem do HTML
# ============================================================

def _tooltip_html(key: str) -> str:
    text = TOOLTIPS.get(key, "")
    return f'<span class="info-tooltip">ℹ<span class="info-tooltip-text">{text}</span></span>'


def gerar_html():
    print("Carregando dados...")
    dados = carregar_dados()
    painel = construir_painel_mensal(dados)
    print(f"  Painel: {painel.shape[0]} meses x {painel.shape[1]} variáveis")

    # Tabelas
    df_estac = carregar_tabela_csv(TABELAS / "testes_estacionariedade.csv")
    df_desc = carregar_tabela_csv(TABELAS / "estatisticas_descritivas.csv")
    estac_rows = tabela_estacionariedade_html(df_estac)
    desc_rows = tabela_descritivas_html(df_desc)

    # Gráficos Plotly
    print("Gerando gráficos interativos...")
    chart_series = fig_painel_series(painel)
    chart_hipotese1 = fig_endividamento_vs_icc(painel)
    chart_hipotese2 = fig_comprometimento_vs_icc(painel)
    chart_corr = fig_correlacao(painel)
    chart_crosscorr = fig_cross_correlation(painel)
    chart_scatter = fig_scatter(painel)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise Exploratória — Endividamento e Percepção Econômica</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
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

        main {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 70px 24px 60px;
        }}

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
            display: flex;
            align-items: center;
            gap: 10px;
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

        .chart-container {{
            margin: 20px 0;
        }}

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

        .corr-table td.neg-strong {{ background: #f5b7b1; font-weight: 700; }}
        .corr-table td.neg-mod {{ background: #fadbd8; }}
        .corr-table td.pos-strong {{ background: #aed6f1; font-weight: 700; }}
        .corr-table td.pos-mod {{ background: #d6eaf8; }}
        .corr-table td.ns {{ color: #aab7b8; }}

        /* Info tooltip */
        .info-tooltip {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: var(--azul-claro);
            color: white;
            font-size: 13px;
            font-weight: 700;
            font-style: italic;
            cursor: help;
            position: relative;
            flex-shrink: 0;
        }}
        .info-tooltip .info-tooltip-text {{
            visibility: hidden;
            opacity: 0;
            position: absolute;
            top: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: #2c3e50;
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 400;
            font-style: normal;
            line-height: 1.5;
            width: 340px;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: opacity 0.2s;
            pointer-events: none;
        }}
        .info-tooltip .info-tooltip-text::before {{
            content: "";
            position: absolute;
            bottom: 100%;
            left: 50%;
            margin-left: -6px;
            border-width: 6px;
            border-style: solid;
            border-color: transparent transparent #2c3e50 transparent;
        }}
        .info-tooltip:hover .info-tooltip-text {{
            visibility: visible;
            opacity: 1;
        }}

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
    <div class="subtitle">Análise Exploratória dos Dados — Relatório Interativo</div>
    <div class="meta">Juliane Furno &middot; Período: 2012–2025 &middot; 14 variáveis &middot; {len(painel)} observações mensais</div>
</div>

<!-- ============================================================ -->
<section id="series">
    <h2>1. Painel de Séries Temporais {_tooltip_html("series")}</h2>
    <p>Visão geral das oito variáveis principais da pesquisa ao longo de 2012–2025. As faixas cinza marcam a recessão de 2014–16 e a pandemia de 2020.</p>

    <div class="chart-container">{chart_series}</div>

    <h3>Observações iniciais</h3>
    <div class="insight">
        <strong>Endividamento em tendência de alta:</strong> tanto o indicador BCB (36% → 50%) quanto a PEIC (56% → 80%) mostram crescimento persistente no período, com aceleração pós-2020. Trata-se de uma tendência estrutural de financeirização do consumo das famílias.
    </div>
    <div class="insight">
        <strong>ICC volátil com ciclos claros:</strong> a confiança do consumidor despencou na recessão 2015–16 (de 170 para 84), recuperou parcialmente, caiu novamente na pandemia, e voltou a subir desde 2022. O subíndice de Condições Atuais é o mais sensível.
    </div>
    <div class="insight">
        <strong>Desemprego e renda como contexto:</strong> o desemprego subiu de 7% para 14% na recessão e voltou a cair para 5% em 2025. O rendimento médio real mostra recuperação recente (R$ 3.742), mas a pergunta é: quanto dessa renda está comprometida com dívida?
    </div>
</section>

<!-- ============================================================ -->
<section id="hipotese">
    <h2>2. Hipótese Central: Endividamento vs. Confiança {_tooltip_html("hipotese")}</h2>
    <p>Gráfico de dois eixos sobrepondo o percentual de famílias endividadas (PEIC) e o Índice de Confiança do Consumidor (ICC).</p>

    <div class="chart-container">{chart_hipotese1}</div>

    <div class="key-finding">
        <strong>Achado central:</strong> visualmente, há uma <strong>relação inversa clara</strong> entre endividamento e confiança — quando o endividamento sobe, o ICC tende a cair, e vice-versa. No entanto, de 2022 em diante, ambos sobem simultaneamente, rompendo esse padrão. Isso sugere que o nível absoluto de endividamento não é o único determinante — o <strong>contexto macroeconômico</strong> (emprego, renda) media essa relação.
    </div>

    <div class="chart-container">{chart_hipotese2}</div>

    <div class="insight">
        <strong>Comprometimento de renda vs. percepção:</strong> este gráfico revela um padrão interessante. Na recessão 2015–16, o comprometimento de renda caiu (famílias cortaram crédito) enquanto a percepção despencou — ou seja, foi o desemprego, não a dívida, que destruiu a confiança. Pós-2020, ambos sobem juntos, sugerindo que famílias estão se endividando mais num contexto de recuperação (crédito de expansão, não de sobrevivência).
    </div>
</section>

<!-- ============================================================ -->
<section id="correlacoes">
    <h2>3. Matriz de Correlação {_tooltip_html("correlacoes")}</h2>
    <p>Correlação de Pearson entre as 14 variáveis do painel, usando observações mensais simultâneas.</p>

    <div class="chart-container">{chart_corr}</div>

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
    <h2>4. Cross-Correlation: Quem Precede Quem? {_tooltip_html("crosscorr")}</h2>
    <p>Análise de correlação cruzada com defasagens de até 24 meses. Lag positivo = endividamento precede ICC; lag negativo = ICC precede endividamento.</p>

    <div class="chart-container">{chart_crosscorr}</div>

    <div class="key-finding">
        <strong>Padrão temporal:</strong> a correlação negativa mais forte ocorre com <strong>lags negativos</strong> (ICC nos meses anteriores). Isso sugere que <strong>a queda de confiança precede o aumento do endividamento</strong> — ou seja, famílias que percebem piora econômica recorrem mais ao crédito. Esse achado é consistente com a ideia de <strong>crédito como mecanismo de sobrevivência</strong> na perspectiva marxista.
    </div>
    <div class="insight">
        <strong>Implicação metodológica:</strong> a causalidade potencialmente bidirecional reforça a necessidade de usar VAR/VECM com testes de causalidade de Granger, em vez de regressões simples. Variáveis instrumentais também serão importantes na análise micro (POF).
    </div>
</section>

<!-- ============================================================ -->
<section id="scatter">
    <h2>5. Gráficos de Dispersão {_tooltip_html("scatter")}</h2>
    <p>Relação entre medidas de endividamento e confiança do consumidor, com linha de tendência (OLS).</p>

    <div class="chart-container">{chart_scatter}</div>

    <div class="insight">
        <strong>PEIC Endividadas vs. ICC (r = -0.042):</strong> nuvem dispersa, sem relação linear. O <strong>nível</strong> de endividamento é insuficiente para explicar percepção — o que importa é o <strong>custo</strong> dessa dívida.
    </div>
    <div class="insight">
        <strong>Comprometimento Renda vs. ICC (r = +0.328):</strong> relação positiva, contraintuitiva. Reflete o fato de que o comprometimento sobe tanto em recessão (juros altos + renda caindo) quanto em expansão (mais crédito + consumo). É uma variável ambígua sem controle pelo ciclo.
    </div>
</section>

<!-- ============================================================ -->
<section id="estacionariedade">
    <h2>6. Testes de Estacionariedade {_tooltip_html("estacionariedade")}</h2>
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
    <h2>7. Estatísticas Descritivas {_tooltip_html("descritivas")}</h2>

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
    <h2>8. Síntese e Implicações para o Modelo {_tooltip_html("sintese")}</h2>

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
    Juliane Furno &middot; Gerado automaticamente via Python (gráficos interativos Plotly)
</footer>

<script>
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

    webbrowser.open(str(SAIDA.resolve()))
    print("Aberto no navegador.")


if __name__ == "__main__":
    gerar_html()
