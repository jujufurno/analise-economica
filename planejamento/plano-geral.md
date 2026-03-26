# Plano Geral de Pesquisa

## Hipótese Central

O endividamento das famílias brasileiras é o principal fator responsável por:
1. A má percepção das pessoas sobre a situação econômica (dimensão subjetiva)
2. O comprometimento efetivo da renda mensal familiar (dimensão objetiva)

## Abordagem Teórica

Marxista e desenvolvimentista. O crédito no capitalismo periférico brasileiro opera como
mecanismo de transferência de renda da classe trabalhadora para o setor financeiro,
comprimindo a renda disponível e deteriorando a percepção de bem-estar econômico.

---

## Fase 1 — Coleta de Dados

### 1.1 Dados Macroeconômicos (Séries Temporais)

| Variável | Fonte | Periodicidade | Formato | Acesso |
|---|---|---|---|---|
| Endividamento das famílias (% e perfil) | PEIC / CNC-Fecomércio | Mensal | CSV/Excel | Site CNC |
| Comprometimento de renda com dívida | PEIC / CNC-Fecomércio | Mensal | CSV/Excel | Site CNC |
| Inadimplência das famílias | PEIC / CNC-Fecomércio | Mensal | CSV/Excel | Site CNC |
| Confiança do consumidor (ICC) | FGV/IBRE | Mensal | CSV | Portal FGV |
| IPCA (inflação geral e grupos) | IBGE / SGS-BCB | Mensal | JSON/CSV | API SGS (BCB) |
| Taxa Selic (meta e efetiva) | BCB | Diária/Mensal | JSON/CSV | API SGS (BCB) |
| Taxa de desemprego | PNAD Contínua / IBGE | Trimestral | CSV | SIDRA/IBGE |
| Renda média real do trabalho | PNAD Contínua / IBGE | Trimestral | CSV | SIDRA/IBGE |
| Crédito ao consumidor (saldo e concessões) | SGS-BCB | Mensal | JSON/CSV | API SGS (BCB) |
| Spread bancário médio (pessoa física) | SGS-BCB | Mensal | JSON/CSV | API SGS (BCB) |
| PIB trimestral | IBGE | Trimestral | CSV | SIDRA/IBGE |

### 1.2 Microdados (Nível Família/Indivíduo)

| Fonte | Variáveis-chave | Periodicidade | Acesso |
|---|---|---|---|
| POF (IBGE) — 2017-2018 | Despesas com serviço de dívida, renda, composição familiar, percepção de vida | Aperiódica | IBGE (microdados) |
| PNAD Contínua (suplementos) | Renda, emprego, condições de moradia | Trimestral/Anual | IBGE (microdados) |

### 1.3 Dados de Percepção Econômica

| Fonte | O que mede | Acesso |
|---|---|---|
| ICC (FGV) | Confiança atual e expectativas | Portal IBRE/FGV |
| ICE (CNI) | Expectativa do consumidor | Portal CNI |
| Pesquisas Datafolha/IPEC | Percepção sobre economia pessoal e do país | Releases públicos / solicitar |

### Período alvo: 2012–2025
Justificativa: cobre ciclo completo (crescimento, recessão 2015-16, recuperação lenta,
pandemia, recuperação recente), permitindo testar a hipótese em diferentes conjunturas.

---

## Fase 2 — Análise Macro (Séries Temporais)

### 2.1 Análise Exploratória
- Visualização das séries e suas tendências
- Testes de estacionariedade (ADF, KPSS, Zivot-Andrews para quebra estrutural)
- Análise de correlação cruzada (cross-correlation) entre endividamento e ICC

### 2.2 Modelo VAR / VECM
- **Variáveis endógenas**: endividamento, ICC, IPCA, taxa de desemprego, renda real
- **Variáveis exógenas**: Selic (instrumento de política)
- Seleção de defasagens por critérios de informação (AIC, BIC, HQ)
- Teste de cointegração (Johansen) — se houver, usar VECM
- Teste de causalidade de Granger
- Funções impulso-resposta (IRF): choque no endividamento → resposta do ICC
- Decomposição da variância: quanto da variação do ICC é explicado pelo endividamento
  vs. outros fatores

### 2.3 Robustez
- Estimar com janelas móveis para verificar estabilidade
- Testar com diferentes medidas de endividamento (total vs. comprometimento vs. inadimplência)
- Controlar por eventos atípicos (pandemia COVID-19, greve dos caminhoneiros 2018)

---

## Fase 3 — Análise Micro (Dados Familiares — POF)

### 3.1 Construção de Variáveis
- **Comprometimento de renda com dívida**: despesas com juros e amortização / renda total
- **Percepção econômica**: variáveis qualitativas da POF sobre condição de vida
- **Estratificação por classe**: faixas de renda (até 2 SM, 2-5 SM, 5-10 SM, 10+ SM)
- **Tipo de dívida**: crédito de sobrevivência (cartão, cheque especial, crediário) vs.
  crédito patrimonial (imobiliário, veículos)

### 3.2 Modelos Econométricos
- **Probit/Logit ordenado**: percepção econômica (boa/regular/ruim) como variável dependente;
  endividamento, renda, escolaridade, região, composição familiar como independentes
- **Decomposição de dominância (Shapley)**: contribuição relativa de cada preditor
- **Quantile regression**: efeito do endividamento em diferentes pontos da distribuição de renda

### 3.3 Endogeneidade
- Variáveis instrumentais candidatas:
  - Oferta de crédito bancário na microrregião (push de crédito exógeno ao indivíduo)
  - Distância a agências bancárias
  - Selic defasada (afeta custo do crédito, mas não percepção diretamente)
- Testar com 2SLS e verificar validade dos instrumentos (teste de Sargan, primeiro estágio)

---

## Fase 4 — Síntese e Resultados

### 4.1 Confronto macro–micro
- Os resultados macro (VAR) e micro (POF) convergem?
- O endividamento domina em ambas as escalas?

### 4.2 Análise por classe social
- O efeito do endividamento é diferenciado por faixa de renda?
- A dívida de sobrevivência tem impacto maior que a dívida patrimonial?

### 4.3 Interpretação teórica
- Conexão com a financeirização da economia brasileira
- Papel do spread bancário como mecanismo de extração de renda
- Implicações para política econômica (regulação de crédito, teto de juros)

### 4.4 Produtos finais
- Tabelas de resultados econométricos
- Gráficos de séries temporais, IRFs e decomposição de variância
- Relatório analítico com interpretação teórica

---

## Stack Técnica

- **Linguagem**: Python 3.11+
- **Coleta**: requests, python-bcb (API SGS), sidrapy (API SIDRA/IBGE), pandas
- **Análise**: statsmodels (VAR, VECM, probit), linearmodels (IV/2SLS), scikit-learn (Shapley)
- **Visualização**: matplotlib, seaborn, plotly
- **Notebooks**: Jupyter (análise exploratória)
- **Gestão de dados**: pandas, parquet para armazenamento intermediário
