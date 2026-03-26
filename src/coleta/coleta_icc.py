"""
Coleta do Índice de Confiança do Consumidor (ICC) e subíndices.

Fontes via SGS/BCB:
  - ICC Fecomércio SP (4393): índice composto mensal
  - ICC Condições Atuais (4394): subíndice de situação atual
  - ICC Expectativas (4395): subíndice de expectativas futuras

Uso:
    python -m src.coleta.coleta_icc
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests

DADOS_BRUTOS = Path("dados/brutos/fgv")
DADOS_PROCESSADOS = Path("dados/processados")

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

DATA_INICIO = "01/01/2012"
DATA_FIM = "31/12/2026"

# Séries do ICC disponíveis no SGS
SERIES_ICC = {
    4393: {
        "nome": "icc_indice",
        "descricao": "Índice de Confiança do Consumidor — Fecomércio SP",
        "unidade": "índice",
    },
    4394: {
        "nome": "icc_condicoes_atuais",
        "descricao": "ICC — Condições Econômicas Atuais",
        "unidade": "índice",
    },
    4395: {
        "nome": "icc_expectativas",
        "descricao": "ICC — Expectativas Futuras",
        "unidade": "índice",
    },
}


def coletar_serie(codigo: int) -> pd.DataFrame:
    """Coleta uma série do SGS/BCB."""
    url = BASE_URL.format(codigo=codigo)
    params = {
        "formato": "json",
        "dataInicial": DATA_INICIO,
        "dataFinal": DATA_FIM,
    }
    headers = {"Accept": "application/json"}

    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()

    dados = response.json()
    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.set_index("data").sort_index()

    return df


def coletar_todas() -> pd.DataFrame:
    """Coleta todas as séries do ICC e consolida em um único DataFrame."""
    DADOS_BRUTOS.mkdir(parents=True, exist_ok=True)
    DADOS_PROCESSADOS.mkdir(parents=True, exist_ok=True)

    series = {}
    total = len(SERIES_ICC)

    for i, (codigo, info) in enumerate(SERIES_ICC.items(), 1):
        nome = info["nome"]
        print(f"[{i}/{total}] Coletando {info['descricao']} (SGS {codigo})...")

        try:
            df = coletar_serie(codigo)
            if not df.empty:
                # Salvar individual em CSV
                caminho_csv = DADOS_BRUTOS / f"{nome}_sgs{codigo}.csv"
                df.to_csv(caminho_csv)

                series[nome] = df["valor"]
                print(f"  OK — {len(df)} observações, {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
            else:
                print("  VAZIO")
        except requests.exceptions.RequestException as e:
            print(f"  ERRO — {e}")

        if i < total:
            time.sleep(1)

    # Consolidar em um DataFrame
    df_consolidado = pd.DataFrame(series)
    df_consolidado = df_consolidado.sort_index()

    # Normalizar para início do mês
    df_consolidado.index = df_consolidado.index.to_period("M").to_timestamp()

    return df_consolidado


def salvar(df: pd.DataFrame) -> None:
    """Salva o DataFrame consolidado."""
    # CSV
    caminho_csv = DADOS_BRUTOS / "icc_consolidado.csv"
    df.to_csv(caminho_csv, float_format="%.2f")
    print(f"\nCSV salvo: {caminho_csv}")

    # Parquet
    caminho_parquet = DADOS_PROCESSADOS / "icc_confianca_consumidor_mensal.parquet"
    df.to_parquet(caminho_parquet)
    print(f"Parquet salvo: {caminho_parquet}")

    # Metadados
    metadados = {
        "icc_confianca_consumidor": {
            "fonte": "Fecomércio SP via BCB/SGS",
            "descricao": "Índice de Confiança do Consumidor e subíndices",
            "arquivo_parquet": "icc_confianca_consumidor_mensal.parquet",
            "frequencia": "mensal",
            "variaveis": {
                info["nome"]: info["descricao"]
                for info in SERIES_ICC.values()
            },
            "nota": "Escala 0-200, acima de 100 indica otimismo, abaixo indica pessimismo",
        }
    }

    caminho_meta = DADOS_PROCESSADOS / "metadados_icc.json"
    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)


def resumo(df: pd.DataFrame) -> None:
    """Imprime resumo."""
    print("\n" + "=" * 60)
    print("RESUMO — ICC (Confiança do Consumidor)")
    print("=" * 60)
    print(f"Período: {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
    print(f"Observações: {len(df)}")
    print(f"\nÚltimos valores ({df.index.max():%Y-%m}):")
    for col in df.columns:
        ultimo = df[col].dropna().iloc[-1]
        print(f"  {col}: {ultimo:.2f}")
    print("\nEstatísticas descritivas:")
    print(df.describe().round(2).to_string())


if __name__ == "__main__":
    print("Iniciando coleta ICC (Confiança do Consumidor)")
    print("-" * 60)
    df = coletar_todas()
    salvar(df)
    resumo(df)
