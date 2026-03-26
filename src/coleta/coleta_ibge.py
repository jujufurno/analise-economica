"""
Coleta de dados do IBGE via API SIDRA.

API docs: https://apisidra.ibge.gov.br/
Biblioteca: sidrapy

Uso:
    python -m src.coleta.coleta_ibge
"""

import json
import time
from pathlib import Path

import pandas as pd
import sidrapy

# Diretórios
DADOS_BRUTOS = Path("dados/brutos/ibge")
DADOS_PROCESSADOS = Path("dados/processados")


def _limpar_sidra(df: pd.DataFrame, col_periodo: str = "D2C", col_valor: str = "V") -> pd.DataFrame:
    """Remove cabeçalho do sidrapy e extrai período + valor."""
    df = df.iloc[1:].copy()  # primeira linha é cabeçalho duplicado
    return df


def _parse_periodo_yyyymm(serie: pd.Series) -> pd.Series:
    """Converte '201203' para Timestamp (último dia do mês)."""
    return pd.to_datetime(serie, format="%Y%m", errors="coerce") + pd.offsets.MonthEnd(0)


def _parse_periodo_trimestral(serie: pd.Series) -> pd.Series:
    """
    Converte trimestre móvel SIDRA ('201203') para data.
    O código representa o último mês do trimestre.
    """
    return pd.to_datetime(serie, format="%Y%m", errors="coerce") + pd.offsets.MonthEnd(0)


# ============================================================
# Coleta por tabela
# ============================================================

def coletar_desemprego() -> pd.DataFrame:
    """
    Tabela 6381 — Taxa de desocupação (PNAD Contínua, trimestre móvel).
    Variável 4099 = taxa de desocupação (%).
    """
    print("  Coletando taxa de desocupação (PNAD Contínua)...")

    df = sidrapy.get_table(
        table_code="6381",
        territorial_level="1",
        ibge_territorial_code="all",
        variable="4099",
        period="all",
    )

    df = _limpar_sidra(df)
    resultado = pd.DataFrame({
        "data": _parse_periodo_trimestral(df["D2C"]),
        "valor": pd.to_numeric(df["V"], errors="coerce"),
    })
    resultado = resultado.dropna(subset=["data"]).set_index("data").sort_index()

    # Pegar apenas trimestres fechados (mar, jun, set, dez) para evitar sobreposição
    resultado = resultado[resultado.index.month.isin([3, 6, 9, 12])]

    return resultado


def coletar_rendimento_medio() -> pd.DataFrame:
    """
    Tabela 6387 — Rendimento médio real do trabalho principal (PNAD Contínua).
    Variável 5935 = rendimento médio real efetivo.
    """
    print("  Coletando rendimento médio real (PNAD Contínua)...")

    df = sidrapy.get_table(
        table_code="6387",
        territorial_level="1",
        ibge_territorial_code="all",
        variable="5935",
        period="all",
    )

    df = _limpar_sidra(df)
    resultado = pd.DataFrame({
        "data": _parse_periodo_trimestral(df["D2C"]),
        "valor": pd.to_numeric(df["V"], errors="coerce"),
    })
    resultado = resultado.dropna(subset=["data"]).set_index("data").sort_index()
    resultado = resultado[resultado.index.month.isin([3, 6, 9, 12])]

    return resultado


def coletar_pib_trimestral() -> pd.DataFrame:
    """
    Tabela 1620 — PIB a preços de mercado (Contas Nacionais Trimestrais).
    Variável 583 = PIB (R$ milhões).
    """
    print("  Coletando PIB trimestral...")

    df = sidrapy.get_table(
        table_code="1620",
        territorial_level="1",
        ibge_territorial_code="all",
        variable="583",
        period="all",
    )

    df = _limpar_sidra(df)
    resultado = pd.DataFrame({
        "data": _parse_periodo_yyyymm(df["D2C"]),
        "valor": pd.to_numeric(df["V"], errors="coerce"),
    })
    resultado = resultado.dropna(subset=["data"]).set_index("data").sort_index()

    return resultado


def coletar_ipca_grupos() -> pd.DataFrame:
    """
    Tabela 7060 — IPCA por grupo de produtos e serviços.
    Variável 63 = variação mensal (%).
    """
    print("  Coletando IPCA por grupo...")

    # Grupos: 7169=Geral, 7170=Alimentação, 7445=Habitação, 7486=Transportes, 7558=Saúde
    df = sidrapy.get_table(
        table_code="7060",
        territorial_level="1",
        ibge_territorial_code="all",
        variable="63",
        period="all",
        classifications={"315": "7169,7170,7445,7486,7558"},
    )

    df = _limpar_sidra(df)

    resultado = pd.DataFrame({
        "data": _parse_periodo_yyyymm(df["D2C"]),
        "grupo": df["D4N"],
        "valor": pd.to_numeric(df["V"], errors="coerce"),
    })
    resultado = resultado.dropna(subset=["data"])

    # Pivotar: uma coluna por grupo
    df_pivot = resultado.pivot_table(index="data", columns="grupo", values="valor")
    df_pivot = df_pivot.sort_index()

    return df_pivot


# ============================================================
# Orquestração
# ============================================================

TABELAS = {
    "desemprego": {
        "funcao": coletar_desemprego,
        "arquivo": "ibge_desemprego_trimestral",
        "descricao": "Taxa de desocupação — PNAD Contínua (%)",
        "frequencia": "trimestral",
    },
    "rendimento_medio": {
        "funcao": coletar_rendimento_medio,
        "arquivo": "ibge_rendimento_medio_trimestral",
        "descricao": "Rendimento médio real efetivo (R$)",
        "frequencia": "trimestral",
    },
    "pib_trimestral": {
        "funcao": coletar_pib_trimestral,
        "arquivo": "ibge_pib_trimestral",
        "descricao": "PIB a preços de mercado (R$ milhões)",
        "frequencia": "trimestral",
    },
    "ipca_grupos": {
        "funcao": coletar_ipca_grupos,
        "arquivo": "ibge_ipca_grupos_mensal",
        "descricao": "IPCA variação mensal por grupo de despesa (%)",
        "frequencia": "mensal",
    },
}


def coletar_todas() -> dict[str, pd.DataFrame]:
    """Coleta todas as tabelas definidas."""
    DADOS_BRUTOS.mkdir(parents=True, exist_ok=True)
    DADOS_PROCESSADOS.mkdir(parents=True, exist_ok=True)

    resultados = {}
    total = len(TABELAS)

    for i, (nome, config) in enumerate(TABELAS.items(), 1):
        print(f"\n[{i}/{total}] {config['descricao']}")

        try:
            df = config["funcao"]()
            if df.empty:
                print("  VAZIO — nenhum dado retornado")
                continue

            # Filtrar período 2012+
            df = df[df.index >= "2012-01-01"]

            # Salvar CSV bruto
            caminho_csv = DADOS_BRUTOS / f"{config['arquivo']}.csv"
            df.to_csv(caminho_csv)
            print(f"  CSV salvo: {caminho_csv}")

            # Salvar Parquet processado
            caminho_parquet = DADOS_PROCESSADOS / f"{config['arquivo']}.parquet"
            df.to_parquet(caminho_parquet)
            print(f"  Parquet salvo: {caminho_parquet}")

            resultados[nome] = df
            print(f"  OK — {len(df)} observações, {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")

        except Exception as e:
            print(f"  ERRO — {type(e).__name__}: {e}")

        if i < total:
            time.sleep(2)

    # Salvar metadados
    metadados = {}
    for nome, config in TABELAS.items():
        metadados[nome] = {
            "descricao": config["descricao"],
            "frequencia": config["frequencia"],
            "fonte": "IBGE/SIDRA",
            "arquivo_parquet": f"{config['arquivo']}.parquet",
        }

    caminho_meta = DADOS_PROCESSADOS / "metadados_ibge.json"
    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)
    print(f"\nMetadados salvos: {caminho_meta}")

    return resultados


def resumo(resultados: dict[str, pd.DataFrame]) -> None:
    """Imprime resumo da coleta."""
    print("\n" + "=" * 60)
    print("RESUMO DA COLETA — IBGE/SIDRA")
    print("=" * 60)

    for nome, df in resultados.items():
        config = TABELAS[nome]
        print(f"\n{config['descricao']}")
        print(f"  Período: {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
        print(f"  Observações: {len(df)}")


if __name__ == "__main__":
    print("Iniciando coleta IBGE/SIDRA")
    print("-" * 60)
    resultados = coletar_todas()
    resumo(resultados)
