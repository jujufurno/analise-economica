"""
Análise exploratória dos dados coletados.

Produz:
  1. Painel de séries temporais (variáveis-chave)
  2. Gráfico de endividamento vs. confiança do consumidor
  3. Matriz de correlação
  4. Cross-correlation (endividamento x ICC)
  5. Testes de estacionariedade (ADF e KPSS)
  6. Estatísticas descritivas

Uso:
    python -m src.analise.exploratoria
"""

from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from statsmodels.tsa.stattools import adfuller, kpss
from scipy import stats

# ============================================================
# Configuração
# ============================================================

DADOS = Path("dados/processados")
GRAFICOS = Path("resultados/graficos")
TABELAS = Path("resultados/tabelas")

GRAFICOS.mkdir(parents=True, exist_ok=True)
TABELAS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 9,
})

# Cores consistentes
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


# ============================================================
# Carregamento dos dados
# ============================================================

def carregar_dados() -> dict[str, pd.DataFrame]:
    """Carrega todos os datasets e retorna em dicionário."""
    dados = {}

    # BCB
    for nome in ["endividamento_familias", "comprometimento_renda", "ipca_mensal",
                  "selic_meta", "spread_medio_pf", "inadimplencia_pf",
                  "credito_pf_saldo", "credito_pf_concessoes"]:
        df = pd.read_parquet(DADOS / f"bcb_{nome}_mensal.parquet")
        dados[nome] = df["valor"]

    # ICC
    icc = pd.read_parquet(DADOS / "icc_confianca_consumidor_mensal.parquet")
    dados["icc_indice"] = icc["icc_indice"]
    dados["icc_condicoes_atuais"] = icc["icc_condicoes_atuais"]
    dados["icc_expectativas"] = icc["icc_expectativas"]

    # PEIC
    peic = pd.read_parquet(DADOS / "peic_endividamento_mensal.parquet")
    for col in peic.columns:
        dados[col] = peic[col]

    # IBGE (trimestral — interpolar para mensal para análises conjuntas)
    for nome, arq in [("desemprego", "ibge_desemprego_trimestral"),
                       ("rendimento_medio", "ibge_rendimento_medio_trimestral")]:
        df = pd.read_parquet(DADOS / f"{arq}.parquet")
        dados[nome] = df["valor"]

    return dados


def construir_painel_mensal(dados: dict) -> pd.DataFrame:
    """Constrói DataFrame consolidado mensal para o período 2012-2025."""
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

    # Adicionar séries trimestrais (interpolar para mensal)
    for nome in ["desemprego", "rendimento_medio"]:
        s = dados[nome].copy()
        s = s.resample("MS").first()  # alinhar ao início do mês
        s = s.reindex(painel.index).interpolate(method="linear")
        painel[nome] = s

    # Filtrar 2012+
    painel = painel[painel.index >= "2012-01-01"]

    return painel


# ============================================================
# 1. Painel de séries temporais
# ============================================================

def grafico_painel_series(painel: pd.DataFrame):
    """Painel com as principais séries temporais."""
    fig, axes = plt.subplots(4, 2, figsize=(14, 16), sharex=True)
    fig.suptitle("Séries Temporais — Variáveis da Pesquisa (2012–2025)", fontsize=14, fontweight="bold", y=0.98)

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

    for ax, (col, titulo, cor, unidade) in zip(axes.flat, configs):
        s = painel[col].dropna()
        ax.plot(s.index, s.values, color=cor, linewidth=1.2)
        ax.fill_between(s.index, s.values, alpha=0.1, color=cor)
        ax.set_title(titulo, fontsize=10, fontweight="bold")
        ax.set_ylabel(unidade, fontsize=8)
        ax.tick_params(labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        # Marcar recessão 2015-16 e pandemia
        for inicio, fim, alpha in [("2014-04", "2016-12", 0.08), ("2020-03", "2020-12", 0.08)]:
            ax.axvspan(pd.Timestamp(inicio), pd.Timestamp(fim), color="gray", alpha=alpha)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    caminho = GRAFICOS / "01_painel_series_temporais.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")


# ============================================================
# 2. Endividamento vs. ICC (gráfico central da hipótese)
# ============================================================

def grafico_endividamento_vs_icc(painel: pd.DataFrame):
    """Gráfico de dois eixos: endividamento e ICC."""
    fig, ax1 = plt.subplots(figsize=(12, 5))

    s_endiv = painel["peic_endividadas"].dropna()
    s_icc = painel["icc_indice"].dropna()

    # Eixo esquerdo — endividamento
    ax1.plot(s_endiv.index, s_endiv.values, color=CORES["endividamento"], linewidth=1.5, label="Famílias Endividadas (PEIC, %)")
    ax1.set_ylabel("Famílias Endividadas (%)", color=CORES["endividamento"], fontsize=10)
    ax1.tick_params(axis="y", labelcolor=CORES["endividamento"])

    # Eixo direito — ICC
    ax2 = ax1.twinx()
    ax2.plot(s_icc.index, s_icc.values, color=CORES["icc"], linewidth=1.5, label="ICC (Fecomércio SP)")
    ax2.set_ylabel("Índice de Confiança do Consumidor", color=CORES["icc"], fontsize=10)
    ax2.tick_params(axis="y", labelcolor=CORES["icc"])
    ax2.axhline(100, color=CORES["icc"], linestyle="--", alpha=0.3, linewidth=0.8)

    # Recessão e pandemia
    for inicio, fim in [("2014-04", "2016-12"), ("2020-03", "2020-12")]:
        ax1.axvspan(pd.Timestamp(inicio), pd.Timestamp(fim), color="gray", alpha=0.08)

    ax1.set_title("Endividamento das Famílias vs. Confiança do Consumidor (2012–2025)",
                   fontsize=12, fontweight="bold")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")

    # Legenda combinada
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.tight_layout()
    caminho = GRAFICOS / "02_endividamento_vs_icc.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")


# ============================================================
# 3. Comprometimento de renda vs. ICC
# ============================================================

def grafico_comprometimento_vs_icc(painel: pd.DataFrame):
    """Comprometimento de renda (BCB) vs. ICC."""
    fig, ax1 = plt.subplots(figsize=(12, 5))

    s_comp = painel["comprometimento_renda"].dropna()
    s_icc = painel["icc_condicoes_atuais"].dropna()

    ax1.plot(s_comp.index, s_comp.values, color=CORES["comprometimento"], linewidth=1.5,
             label="Comprometimento de Renda (BCB, %)")
    ax1.set_ylabel("Comprometimento de Renda (%)", color=CORES["comprometimento"], fontsize=10)
    ax1.tick_params(axis="y", labelcolor=CORES["comprometimento"])

    ax2 = ax1.twinx()
    ax2.plot(s_icc.index, s_icc.values, color=CORES["icc_atuais"], linewidth=1.5,
             label="ICC — Condições Atuais")
    ax2.set_ylabel("ICC — Condições Atuais", color=CORES["icc_atuais"], fontsize=10)
    ax2.tick_params(axis="y", labelcolor=CORES["icc_atuais"])

    for inicio, fim in [("2014-04", "2016-12"), ("2020-03", "2020-12")]:
        ax1.axvspan(pd.Timestamp(inicio), pd.Timestamp(fim), color="gray", alpha=0.08)

    ax1.set_title("Comprometimento de Renda vs. Percepção da Situação Atual (2012–2025)",
                   fontsize=12, fontweight="bold")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.tight_layout()
    caminho = GRAFICOS / "03_comprometimento_vs_icc_atuais.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")


# ============================================================
# 4. Matriz de correlação
# ============================================================

def grafico_correlacao(painel: pd.DataFrame):
    """Matriz de correlação entre as variáveis principais."""
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
    corr = df_corr.corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
        vmin=-1, vmax=1, square=True, linewidths=0.5,
        xticklabels=nomes, yticklabels=nomes,
        annot_kws={"size": 7.5}, ax=ax,
    )
    ax.set_title("Matriz de Correlação — Variáveis da Pesquisa", fontsize=13, fontweight="bold", pad=15)
    ax.tick_params(labelsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    plt.tight_layout()
    caminho = GRAFICOS / "04_matriz_correlacao.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")

    return corr, nomes


# ============================================================
# 5. Cross-correlation (endividamento x ICC)
# ============================================================

def grafico_cross_correlation(painel: pd.DataFrame):
    """Cross-correlation entre endividamento e ICC em diferentes defasagens."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    pares = [
        ("peic_endividadas", "icc_indice", "PEIC Endividadas vs. ICC"),
        ("comprometimento_renda", "icc_indice", "Comprom. Renda vs. ICC"),
        ("comprometimento_renda", "icc_condicoes_atuais", "Comprom. Renda vs. ICC Atuais"),
    ]

    max_lags = 24

    for ax, (col_x, col_y, titulo) in zip(axes, pares):
        df_pair = painel[[col_x, col_y]].dropna()
        x = df_pair[col_x].values
        y = df_pair[col_y].values

        # Normalizar
        x = (x - x.mean()) / x.std()
        y = (y - y.mean()) / y.std()

        correlacoes = []
        lags = range(-max_lags, max_lags + 1)
        for lag in lags:
            if lag >= 0:
                corr = np.corrcoef(x[:len(x) - lag], y[lag:])[0, 1]
            else:
                corr = np.corrcoef(x[-lag:], y[:len(y) + lag])[0, 1]
            correlacoes.append(corr)

        cores_barras = [CORES["endividamento"] if c < 0 else CORES["icc"] for c in correlacoes]
        ax.bar(list(lags), correlacoes, color=cores_barras, alpha=0.7, width=0.8)
        ax.axhline(0, color="black", linewidth=0.5)

        # Limites de significância (2/sqrt(N))
        n = len(df_pair)
        sig = 2 / np.sqrt(n)
        ax.axhline(sig, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)
        ax.axhline(-sig, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)

        ax.set_title(titulo, fontsize=10, fontweight="bold")
        ax.set_xlabel("Defasagem (meses)", fontsize=9)
        ax.set_ylabel("Correlação", fontsize=9)
        ax.set_xlim(-max_lags - 0.5, max_lags + 0.5)
        ax.tick_params(labelsize=8)

        # Anotar pico
        idx_pico = np.argmin(correlacoes)  # esperamos correlação negativa
        lag_pico = list(lags)[idx_pico]
        corr_pico = correlacoes[idx_pico]
        ax.annotate(f"lag={lag_pico}\nr={corr_pico:.2f}",
                    xy=(lag_pico, corr_pico), fontsize=7.5,
                    ha="center", va="top" if corr_pico < 0 else "bottom",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    fig.suptitle("Cross-Correlation: Endividamento → Confiança do Consumidor",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.text(0.5, -0.02, "Lag positivo = endividamento precede ICC | Lag negativo = ICC precede endividamento",
             ha="center", fontsize=9, style="italic", color="gray")

    plt.tight_layout()
    caminho = GRAFICOS / "05_cross_correlation.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")


# ============================================================
# 6. Testes de estacionariedade
# ============================================================

def testes_estacionariedade(painel: pd.DataFrame) -> pd.DataFrame:
    """Executa ADF e KPSS para cada série."""
    colunas = [
        "endividamento_bcb", "comprometimento_renda", "peic_endividadas",
        "peic_atraso", "peic_renda_comp",
        "icc_indice", "icc_condicoes_atuais", "icc_expectativas",
        "ipca", "selic", "spread_pf", "inadimplencia",
        "desemprego", "rendimento_medio",
    ]

    nomes_display = {
        "endividamento_bcb": "Endividamento BCB",
        "comprometimento_renda": "Comprometimento Renda",
        "peic_endividadas": "PEIC Endividadas",
        "peic_atraso": "PEIC Atraso",
        "peic_renda_comp": "PEIC Renda Comp.",
        "icc_indice": "ICC Geral",
        "icc_condicoes_atuais": "ICC Atuais",
        "icc_expectativas": "ICC Expectativas",
        "ipca": "IPCA",
        "selic": "Selic",
        "spread_pf": "Spread PF",
        "inadimplencia": "Inadimplência",
        "desemprego": "Desemprego",
        "rendimento_medio": "Rendimento Médio",
    }

    resultados = []

    for col in colunas:
        s = painel[col].dropna()
        if len(s) < 20:
            continue

        nome = nomes_display.get(col, col)

        # ADF (H0: tem raiz unitária, ou seja, não estacionária)
        try:
            adf_stat, adf_p, adf_lags, _, _, _ = adfuller(s, autolag="AIC")
        except Exception:
            adf_stat, adf_p, adf_lags = np.nan, np.nan, np.nan

        # KPSS (H0: estacionária)
        try:
            kpss_stat, kpss_p, kpss_lags, _ = kpss(s, regression="c", nlags="auto")
        except Exception:
            kpss_stat, kpss_p, kpss_lags = np.nan, np.nan, np.nan

        # Diagnóstico combinado
        if adf_p < 0.05 and kpss_p >= 0.05:
            diag = "Estacionária"
        elif adf_p >= 0.05 and kpss_p < 0.05:
            diag = "Não estacionária"
        elif adf_p < 0.05 and kpss_p < 0.05:
            diag = "Inconclusivo (tendência?)"
        else:
            diag = "Inconclusivo"

        # ADF na primeira diferença
        s_diff = s.diff().dropna()
        try:
            adf_d_stat, adf_d_p, _, _, _, _ = adfuller(s_diff, autolag="AIC")
        except Exception:
            adf_d_stat, adf_d_p = np.nan, np.nan

        resultados.append({
            "Variável": nome,
            "ADF Stat": adf_stat,
            "ADF p-valor": adf_p,
            "KPSS Stat": kpss_stat,
            "KPSS p-valor": kpss_p,
            "Diagnóstico (nível)": diag,
            "ADF 1ª dif. p-valor": adf_d_p,
            "I(d)": "I(0)" if diag == "Estacionária" else ("I(1)" if adf_d_p < 0.05 else "I(2)?"),
        })

    df_result = pd.DataFrame(resultados)
    return df_result


# ============================================================
# 7. Estatísticas descritivas
# ============================================================

def estatisticas_descritivas(painel: pd.DataFrame) -> pd.DataFrame:
    """Tabela de estatísticas descritivas das variáveis principais."""
    colunas = [
        "endividamento_bcb", "comprometimento_renda", "peic_endividadas",
        "peic_renda_comp", "icc_indice", "icc_condicoes_atuais",
        "ipca", "selic", "spread_pf", "inadimplencia",
        "desemprego", "rendimento_medio",
    ]
    nomes = {
        "endividamento_bcb": "Endivid. BCB (%)",
        "comprometimento_renda": "Comprom. Renda (%)",
        "peic_endividadas": "PEIC Endivid. (%)",
        "peic_renda_comp": "PEIC Renda Comp. (%)",
        "icc_indice": "ICC Geral",
        "icc_condicoes_atuais": "ICC Atuais",
        "ipca": "IPCA (%)",
        "selic": "Selic (% a.a.)",
        "spread_pf": "Spread PF (p.p.)",
        "inadimplencia": "Inadimpl. (%)",
        "desemprego": "Desemprego (%)",
        "rendimento_medio": "Rend. Médio (R$)",
    }

    desc = painel[colunas].describe().T
    desc.index = [nomes.get(c, c) for c in desc.index]
    desc = desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max"]]
    desc.columns = ["N", "Média", "Desvio", "Mín", "Q1", "Mediana", "Q3", "Máx"]

    return desc.round(2)


# ============================================================
# 8. Scatter plots: endividamento vs ICC
# ============================================================

def grafico_scatter_hipotese(painel: pd.DataFrame):
    """Scatter plots para visualizar a relação endividamento-percepção."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    pares = [
        ("peic_endividadas", "icc_indice", "PEIC Endividadas (%)", "ICC Geral"),
        ("comprometimento_renda", "icc_indice", "Comprometimento Renda (%)", "ICC Geral"),
        ("comprometimento_renda", "icc_condicoes_atuais", "Comprometimento Renda (%)", "ICC Cond. Atuais"),
    ]

    for ax, (col_x, col_y, label_x, label_y) in zip(axes, pares):
        df_pair = painel[[col_x, col_y]].dropna()
        x, y = df_pair[col_x], df_pair[col_y]

        ax.scatter(x, y, alpha=0.4, s=20, color=CORES["endividamento"], edgecolors="none")

        # Linha de tendência
        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, intercept + slope * x_line, color=CORES["icc"], linewidth=1.5, linestyle="--")

        ax.set_xlabel(label_x, fontsize=9)
        ax.set_ylabel(label_y, fontsize=9)
        ax.set_title(f"r = {r_value:.3f} (p = {p_value:.1e})", fontsize=10, fontweight="bold")
        ax.tick_params(labelsize=8)

    fig.suptitle("Relação entre Endividamento e Confiança do Consumidor",
                 fontsize=12, fontweight="bold", y=1.02)

    plt.tight_layout()
    caminho = GRAFICOS / "06_scatter_hipotese.png"
    fig.savefig(caminho, bbox_inches="tight")
    plt.close()
    print(f"  Salvo: {caminho}")


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 60)
    print("ANÁLISE EXPLORATÓRIA")
    print("=" * 60)

    print("\nCarregando dados...")
    dados = carregar_dados()
    painel = construir_painel_mensal(dados)
    print(f"  Painel: {painel.shape[0]} meses x {painel.shape[1]} variáveis")
    print(f"  Período: {painel.index.min():%Y-%m} a {painel.index.max():%Y-%m}")
    print(f"  Nulos por coluna:\n{painel.isna().sum().to_string()}")

    # Gráficos
    print("\n--- Gerando gráficos ---")
    grafico_painel_series(painel)
    grafico_endividamento_vs_icc(painel)
    grafico_comprometimento_vs_icc(painel)
    grafico_correlacao(painel)
    grafico_cross_correlation(painel)
    grafico_scatter_hipotese(painel)

    # Testes de estacionariedade
    print("\n--- Testes de estacionariedade ---")
    df_estac = testes_estacionariedade(painel)
    caminho_estac = TABELAS / "testes_estacionariedade.csv"
    df_estac.to_csv(caminho_estac, index=False, float_format="%.4f")
    print(f"  Salvo: {caminho_estac}")
    print()
    print(df_estac[["Variável", "ADF p-valor", "KPSS p-valor", "Diagnóstico (nível)", "I(d)"]].to_string(index=False))

    # Estatísticas descritivas
    print("\n--- Estatísticas descritivas ---")
    df_desc = estatisticas_descritivas(painel)
    caminho_desc = TABELAS / "estatisticas_descritivas.csv"
    df_desc.to_csv(caminho_desc, float_format="%.2f")
    print(f"  Salvo: {caminho_desc}")
    print()
    print(df_desc.to_string())

    # Correlações-chave
    print("\n--- Correlações-chave para a hipótese ---")
    pares_chave = [
        ("peic_endividadas", "icc_indice"),
        ("comprometimento_renda", "icc_indice"),
        ("comprometimento_renda", "icc_condicoes_atuais"),
        ("peic_renda_comp", "icc_indice"),
        ("endividamento_bcb", "icc_indice"),
        ("inadimplencia", "icc_indice"),
        ("desemprego", "icc_indice"),
        ("selic", "icc_indice"),
    ]
    for col_x, col_y in pares_chave:
        df_p = painel[[col_x, col_y]].dropna()
        r, p = stats.pearsonr(df_p[col_x], df_p[col_y])
        sinal = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
        print(f"  {col_x:30s} x {col_y:20s}:  r = {r:+.3f} {sinal}")

    print("\n" + "=" * 60)
    print("Análise exploratória concluída.")
    print(f"Gráficos em: {GRAFICOS}/")
    print(f"Tabelas em: {TABELAS}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
