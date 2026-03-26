"""
Coleta e processamento da PEIC (Pesquisa de Endividamento e Inadimplência do Consumidor).

Fonte: CNC / Fecomércio, disponibilizada pela ABINEE.
URL: https://www.abinee.org.br/arquivos/decon/dados/shpeiccm.xls

Uso:
    python -m src.coleta.coleta_peic
"""

import json
from pathlib import Path

import pandas as pd
import requests

DADOS_BRUTOS = Path("dados/brutos/peic")
DADOS_PROCESSADOS = Path("dados/processados")

URL_PEIC = "https://www.abinee.org.br/arquivos/decon/dados/shpeiccm.xls"

COLUNAS = {
    0: "data",
    1: "pct_familias_endividadas",
    2: "pct_dividas_em_atraso",
    3: "pct_sem_condicoes_pagar",
    4: "pct_renda_comprometida_divida",
}


def baixar_planilha() -> Path:
    """Baixa a planilha XLS da ABINEE."""
    DADOS_BRUTOS.mkdir(parents=True, exist_ok=True)

    print("Baixando planilha PEIC da ABINEE...")
    response = requests.get(URL_PEIC, timeout=30)
    response.raise_for_status()

    caminho = DADOS_BRUTOS / "peic_serie_historica.xls"
    with open(caminho, "wb") as f:
        f.write(response.content)

    print(f"  Salvo: {caminho} ({len(response.content) / 1024:.0f} KB)")
    return caminho


def processar_planilha(caminho: Path) -> pd.DataFrame:
    """Lê e processa a planilha PEIC."""
    print("Processando planilha...")

    df = pd.read_excel(caminho, sheet_name="INEC", header=None)

    # Encontrar onde começam os dados (primeira linha com datetime)
    import datetime
    inicio = None
    for i in range(len(df)):
        val = df.iloc[i, 0]
        if isinstance(val, (datetime.datetime, pd.Timestamp)):
            inicio = i
            break

    if inicio is None:
        raise ValueError("Não foi possível encontrar o início dos dados na planilha")

    # Encontrar onde terminam os dados (primeira linha NaN após os dados)
    fim = inicio
    for i in range(inicio, len(df)):
        if pd.isna(df.iloc[i, 0]):
            fim = i
            break
    else:
        fim = len(df)

    # Extrair dados
    dados = df.iloc[inicio:fim].copy()
    dados.columns = range(len(dados.columns))
    dados = dados.rename(columns=COLUNAS)
    dados = dados[list(COLUNAS.values())]

    # Converter tipos
    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    for col in dados.columns[1:]:
        dados[col] = pd.to_numeric(dados[col], errors="coerce")

    dados = dados.dropna(subset=["data"])
    dados = dados.set_index("data").sort_index()

    # Normalizar para início do mês
    dados.index = dados.index.to_period("M").to_timestamp()

    # Os valores já vêm como proporções (0.61 = 61%), converter para percentual
    for col in dados.columns:
        if dados[col].max() <= 1.0:
            dados[col] = dados[col] * 100

    return dados


def salvar(df: pd.DataFrame) -> None:
    """Salva os dados processados."""
    DADOS_PROCESSADOS.mkdir(parents=True, exist_ok=True)

    # CSV bruto
    caminho_csv = DADOS_BRUTOS / "peic_processada.csv"
    df.to_csv(caminho_csv, float_format="%.2f")
    print(f"  CSV salvo: {caminho_csv}")

    # Parquet
    caminho_parquet = DADOS_PROCESSADOS / "peic_endividamento_mensal.parquet"
    df.to_parquet(caminho_parquet)
    print(f"  Parquet salvo: {caminho_parquet}")

    # Metadados
    metadados = {
        "peic_endividamento": {
            "fonte": "CNC/Fecomércio (via ABINEE)",
            "descricao": "Pesquisa de Endividamento e Inadimplência do Consumidor",
            "arquivo_parquet": "peic_endividamento_mensal.parquet",
            "frequencia": "mensal",
            "variaveis": {
                "pct_familias_endividadas": "Percentual de famílias endividadas (%)",
                "pct_dividas_em_atraso": "Percentual com dívidas em atraso (%)",
                "pct_sem_condicoes_pagar": "Percentual sem condições de pagar (%)",
                "pct_renda_comprometida_divida": "Parcela média da renda comprometida com dívida (%)",
            },
        }
    }

    caminho_meta = DADOS_PROCESSADOS / "metadados_peic.json"
    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)


def resumo(df: pd.DataFrame) -> None:
    """Imprime resumo dos dados."""
    print("\n" + "=" * 60)
    print("RESUMO — PEIC (Endividamento do Consumidor)")
    print("=" * 60)
    print(f"Período: {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
    print(f"Observações: {len(df)}")
    print(f"\nÚltimos valores ({df.index.max():%B %Y}):")
    for col in df.columns:
        print(f"  {col}: {df[col].iloc[-1]:.1f}%")
    nulos = df.isna().sum()
    if nulos.any():
        print(f"\nValores nulos: {nulos[nulos > 0].to_dict()}")


if __name__ == "__main__":
    caminho = baixar_planilha()
    df = processar_planilha(caminho)
    salvar(df)
    resumo(df)
