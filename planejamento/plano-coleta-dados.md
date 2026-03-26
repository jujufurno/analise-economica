# Plano de Coleta de Dados

## Prioridades de Coleta

A coleta segue a ordem de facilidade de acesso e importância para a análise.

---

## Etapa 1 — APIs automatizáveis (prioridade alta)

Dados acessíveis via API pública, que podemos automatizar com scripts Python.

### 1.1 Sistema Gerenciador de Séries (SGS) — Banco Central

Endpoint: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`

| Série | Código SGS | Descrição |
|---|---|---|
| Selic meta | 432 | Taxa Selic meta (% a.a.) |
| Selic efetiva | 11 | Taxa Selic efetiva (% a.a.) |
| IPCA mensal | 433 | Variação mensal do IPCA (%) |
| Crédito PF — saldo total | 20539 | Saldo de crédito pessoa física (R$ milhões) |
| Crédito PF — concessões | 20631 | Concessões de crédito PF (R$ milhões) |
| Spread médio PF | 20783 | Spread bancário médio operações PF (p.p.) |
| Inadimplência PF | 21082 | Inadimplência da carteira PF (%) |
| Endividamento das famílias | 29037 | Endividamento famílias / renda acumulada 12m (%) |
| Comprometimento de renda | 29038 | Serviço da dívida / renda acumulada 12m (%) |

**Script**: `src/coleta/coleta_bcb.py`
**Saída**: `dados/brutos/bcb/`

### 1.2 SIDRA / IBGE

Endpoint: API SIDRA (`https://apisidra.ibge.gov.br/`)

| Tabela | Código | Descrição |
|---|---|---|
| Taxa de desocupação | 6381 | PNAD Contínua trimestral |
| Rendimento médio real | 6387 | PNAD Contínua trimestral |
| PIB trimestral | 1620 | Contas Nacionais Trimestrais |
| IPCA por grupo | 7060 | IPCA - variação por grupo de despesa |

**Script**: `src/coleta/coleta_ibge.py`
**Saída**: `dados/brutos/ibge/`

---

## Etapa 2 — Downloads manuais estruturados (prioridade alta)

Dados disponíveis publicamente mas que requerem download manual ou scraping leve.

### 2.1 PEIC — CNC / Fecomércio

- **Fonte**: https://www.portaldocomercio.org.br (CNC)
- **Dados**: percentual de endividados, inadimplentes, tipo de dívida, comprometimento
- **Formato**: planilhas Excel, releases PDF
- **Ação**: baixar manualmente e padronizar com script de limpeza
- **Script de limpeza**: `src/coleta/limpar_peic.py`
- **Saída**: `dados/brutos/peic/`

### 2.2 ICC — FGV/IBRE

- **Fonte**: Portal IBRE / FGV
- **Dados**: Índice de Confiança do Consumidor e subíndices (situação atual, expectativas)
- **Formato**: Excel / CSV
- **Ação**: download via portal, padronizar
- **Script de limpeza**: `src/coleta/limpar_icc.py`
- **Saída**: `dados/brutos/fgv/`

---

## Etapa 3 — Microdados (prioridade média, maior complexidade)

### 3.1 POF 2017-2018 (IBGE)

- **Fonte**: https://www.ibge.gov.br/estatisticas/sociais/saude/24786-pesquisa-de-orcamentos-familiares-2.html
- **Dados**: microdados completos (múltiplos arquivos .txt com dicionário de variáveis)
- **Tabelas relevantes**:
  - Despesa coletiva (inclui pagamentos de dívida/juros)
  - Rendimento (renda familiar)
  - Condições de vida (percepção subjetiva)
  - Morador (características sociodemográficas)
- **Tamanho**: ~2 GB descompactado
- **Ação**: download + script de importação e vinculação das tabelas
- **Script**: `src/coleta/importar_pof.py`
- **Saída**: `dados/brutos/pof/` (originais) → `dados/processados/pof/` (parquet)

---

## Etapa 4 — Dados complementares (prioridade baixa)

### 4.1 ICE — CNI
- Expectativas do consumidor (complementar ao ICC)

### 4.2 Pesquisas de opinião (Datafolha, IPEC)
- Percepção econômica direta ("economia melhorou/piorou")
- Acesso mais restrito; usar releases quando disponíveis

---

## Padronização dos Dados

Todos os dados coletados devem ser convertidos para formato padronizado:

- **Séries temporais**: DataFrame pandas com índice DatetimeIndex, frequência explícita
- **Formato de armazenamento**: Parquet (dados processados), CSV (dados brutos preservados)
- **Nomenclatura**: `{fonte}_{variavel}_{frequencia}.parquet`
  - Ex: `bcb_endividamento_familias_mensal.parquet`
  - Ex: `ibge_desemprego_trimestral.parquet`
- **Metadados**: cada arquivo processado acompanhado de dicionário em `dados/processados/metadados.json`

---

## Validação

Após coleta, verificar:
- [ ] Séries sem lacunas no período 2012–2025
- [ ] Unidades consistentes (%, R$ milhões, índice)
- [ ] Datas alinhadas (fim de mês para mensais, fim de trimestre para trimestrais)
- [ ] Sem duplicatas
- [ ] Valores extremos investigados (não removidos automaticamente)
