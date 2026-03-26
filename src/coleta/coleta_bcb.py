"""
Coleta de séries temporais do Sistema Gerenciador de Séries (SGS) do Banco Central do Brasil.

API docs: https://dadosabertos.bcb.gov.br/dataset/taxas-de-juros
Endpoint: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados

Uso:
    python -m src.coleta.coleta_bcb
"""

import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

# Diretórios
DADOS_BRUTOS = Path("dados/brutos/bcb")
DADOS_PROCESSADOS = Path("dados/processados")

# Séries a coletar — código SGS, nome padronizado, descrição
SERIES = {
    4189: {
        "nome": "selic_meta",
        "descricao": "Taxa Selic — meta definida pelo Copom (% a.a.)",
        "unidade": "% a.a.",
    },
    433: {
        "nome": "ipca_mensal",
        "descricao": "IPCA - variação mensal (%)",
        "unidade": "%",
    },
    20539: {
        "nome": "credito_pf_saldo",
        "descricao": "Saldo de crédito pessoa física (R$ milhões)",
        "unidade": "R$ milhões",
    },
    20631: {
        "nome": "credito_pf_concessoes",
        "descricao": "Concessões de crédito pessoa física (R$ milhões)",
        "unidade": "R$ milhões",
    },
    20783: {
        "nome": "spread_medio_pf",
        "descricao": "Spread bancário médio operações PF (p.p.)",
        "unidade": "p.p.",
    },
    21082: {
        "nome": "inadimplencia_pf",
        "descricao": "Inadimplência da carteira PF (%)",
        "unidade": "%",
    },
    29037: {
        "nome": "endividamento_familias",
        "descricao": "Endividamento das famílias / renda acumulada 12 meses (%)",
        "unidade": "%",
    },
    29038: {
        "nome": "comprometimento_renda",
        "descricao": "Serviço da dívida das famílias / renda acumulada 12 meses (%)",
        "unidade": "%",
    },
}

DATA_INICIO = "01/01/2012"
DATA_FIM = datetime.now().strftime("%d/%m/%Y")

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


def coletar_serie(codigo: int, data_inicio: str = DATA_INICIO, data_fim: str = DATA_FIM) -> pd.DataFrame:
    """Coleta uma série do SGS/BCB e retorna como DataFrame."""
    url = BASE_URL.format(codigo=codigo)
    params = {
        "formato": "json",
        "dataInicial": data_inicio,
        "dataFinal": data_fim,
    }

    headers = {"Accept": "application/json"}
    response = requests.get(url, params=params, headers=headers, timeout=60)
    response.raise_for_status()

    dados = response.json()
    if not dados:
        print(f"  AVISO: série {codigo} retornou vazia")
        return pd.DataFrame()

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.set_index("data").sort_index()
    df.index.name = "data"

    return df


def salvar_serie(df: pd.DataFrame, info: dict, codigo: int) -> None:
    """Salva a série em CSV (bruto) e Parquet (processado)."""
    nome = info["nome"]

    # CSV bruto
    caminho_csv = DADOS_BRUTOS / f"{nome}_sgs{codigo}.csv"
    df.to_csv(caminho_csv)
    print(f"  CSV salvo: {caminho_csv}")

    # Parquet processado
    caminho_parquet = DADOS_PROCESSADOS / f"bcb_{nome}_mensal.parquet"
    df.to_parquet(caminho_parquet)
    print(f"  Parquet salvo: {caminho_parquet}")


def coletar_todas() -> dict[str, pd.DataFrame]:
    """Coleta todas as séries definidas em SERIES."""
    DADOS_BRUTOS.mkdir(parents=True, exist_ok=True)
    DADOS_PROCESSADOS.mkdir(parents=True, exist_ok=True)

    resultados = {}
    total = len(SERIES)

    for i, (codigo, info) in enumerate(SERIES.items(), 1):
        nome = info["nome"]
        print(f"[{i}/{total}] Coletando {nome} (SGS {codigo})...")

        try:
            df = coletar_serie(codigo)
            if not df.empty:
                salvar_serie(df, info, codigo)
                resultados[nome] = df
                print(f"  OK — {len(df)} observações, {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
            else:
                print(f"  VAZIO — nenhum dado retornado")
        except requests.exceptions.RequestException as e:
            print(f"  ERRO — {e}")

        # Pausa entre requisições para não sobrecarregar a API
        if i < total:
            time.sleep(1)

    # Salvar metadados
    metadados = {}
    for codigo, info in SERIES.items():
        metadados[info["nome"]] = {
            "codigo_sgs": codigo,
            "descricao": info["descricao"],
            "unidade": info["unidade"],
            "fonte": "BCB/SGS",
            "arquivo_parquet": f"bcb_{info['nome']}_mensal.parquet",
            "periodo_solicitado": f"{DATA_INICIO} a {DATA_FIM}",
        }

    caminho_meta = DADOS_PROCESSADOS / "metadados_bcb.json"
    with open(caminho_meta, "w", encoding="utf-8") as f:
        json.dump(metadados, f, ensure_ascii=False, indent=2)
    print(f"\nMetadados salvos: {caminho_meta}")

    return resultados


def resumo(resultados: dict[str, pd.DataFrame]) -> None:
    """Imprime resumo da coleta."""
    print("\n" + "=" * 60)
    print("RESUMO DA COLETA — BCB/SGS")
    print("=" * 60)

    for nome, df in resultados.items():
        info = next(v for v in SERIES.values() if v["nome"] == nome)
        print(f"\n{info['descricao']}")
        print(f"  Período: {df.index.min():%Y-%m} a {df.index.max():%Y-%m}")
        print(f"  Observações: {len(df)}")
        print(f"  Último valor: {df['valor'].iloc[-1]:.2f} {info['unidade']}")
        nulos = df["valor"].isna().sum()
        if nulos > 0:
            print(f"  ATENÇÃO: {nulos} valores nulos")


if __name__ == "__main__":
    print(f"Iniciando coleta BCB/SGS — período {DATA_INICIO} a {DATA_FIM}")
    print("-" * 60)
    resultados = coletar_todas()
    resumo(resultados)
