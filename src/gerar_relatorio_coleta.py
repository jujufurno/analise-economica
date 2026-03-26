"""
Gera relatório PDF com sumário da pesquisa e inventário dos dados coletados.

Uso:
    python -m src.gerar_relatorio_coleta
"""

from pathlib import Path
from datetime import datetime

import pandas as pd
from fpdf import FPDF


DADOS_PROCESSADOS = Path("dados/processados")
SAIDA = Path("resultados/relatorio_coleta_dados.pdf")


FONTS_DIR = "C:/Windows/Fonts"


class RelatorioPDF(FPDF):
    """PDF personalizado com cabeçalho e rodapé."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_font("Arial", "", f"{FONTS_DIR}/arial.ttf")
        self.add_font("Arial", "B", f"{FONTS_DIR}/arialbd.ttf")
        self.add_font("Arial", "I", f"{FONTS_DIR}/ariali.ttf")
        self.add_font("Arial", "BI", f"{FONTS_DIR}/arialbi.ttf")

    def header(self):
        self.set_font("Arial", "B", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Pesquisa: Endividamento Familiar e Percepção Econômica no Brasil", align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")

    def titulo_secao(self, texto: str):
        self.set_font("Arial", "B", 16)
        self.set_text_color(20, 60, 120)
        self.ln(4)
        self.cell(0, 10, texto, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 60, 120)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def subtitulo(self, texto: str):
        self.set_font("Arial", "B", 12)
        self.set_text_color(40, 40, 40)
        self.ln(2)
        self.cell(0, 8, texto, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def corpo(self, texto: str):
        self.set_font("Arial", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, texto)
        self.ln(1)

    def item_lista(self, texto: str):
        self.set_font("Arial", "", 10)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.cell(6, 5.5, chr(8226))  # bullet
        self.multi_cell(0, 5.5, texto)
        self.ln(0.5)

    def tabela(self, cabecalho: list[str], linhas: list[list[str]], larguras: list[int]):
        # Cabeçalho
        self.set_font("Arial", "B", 8.5)
        self.set_fill_color(20, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, (cab, larg) in enumerate(zip(cabecalho, larguras)):
            self.cell(larg, 7, cab, border=1, fill=True, align="C")
        self.ln()

        # Linhas
        self.set_font("Arial", "", 8)
        self.set_text_color(30, 30, 30)
        for j, linha in enumerate(linhas):
            if j % 2 == 0:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            for i, (cel, larg) in enumerate(zip(linha, larguras)):
                align = "L" if i == 0 else "C"
                self.cell(larg, 6, cel, border=1, fill=True, align=align)
            self.ln()
        self.ln(3)


def carregar_inventario() -> list[dict]:
    """Carrega informações de todos os parquets coletados."""
    inventario = []
    for f in sorted(DADOS_PROCESSADOS.glob("*.parquet")):
        df = pd.read_parquet(f)
        info = {
            "arquivo": f.name,
            "periodo_inicio": df.index.min(),
            "periodo_fim": df.index.max(),
            "observacoes": len(df),
            "colunas": list(df.columns),
            "n_colunas": len(df.columns),
        }
        # Último valor por coluna
        ultimos = {}
        for col in df.columns:
            s = df[col].dropna()
            if not s.empty:
                ultimos[col] = s.iloc[-1]
        info["ultimos_valores"] = ultimos
        inventario.append(info)
    return inventario


def gerar_pdf():
    pdf = RelatorioPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ================================================================
    # CAPA
    # ================================================================
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(20, 60, 120)
    pdf.multi_cell(0, 12, "Endividamento Familiar e\nPercepção Econômica no Brasil", align="C")
    pdf.ln(8)
    pdf.set_font("Arial", "", 14)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "Relatório de Coleta de Dados", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, "Juliane Furno", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Abordagem marxista e desenvolvimentista", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, f"Gerado em {datetime.now():%d/%m/%Y às %H:%M}", align="C", new_x="LMARGIN", new_y="NEXT")

    # ================================================================
    # SUMÁRIO
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("Sumário")
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(30, 30, 30)
    sumario = [
        ("1. Hipótese Central e Plano Geral da Pesquisa", 3),
        ("2. Plano de Coleta de Dados", 4),
        ("3. Inventário dos Dados Coletados", 6),
        ("   3.1  Banco Central do Brasil (BCB/SGS)", 6),
        ("   3.2  PEIC — Endividamento do Consumidor (CNC)", 7),
        ("   3.3  ICC — Confiança do Consumidor (Fecomércio SP)", 7),
        ("   3.4  IBGE/SIDRA", 8),
        ("4. Descrição Detalhada das Séries e Índices", 9),
        ("5. Próximos Passos", 10),
    ]
    for titulo, _pag in sumario:
        pdf.cell(0, 7, titulo, new_x="LMARGIN", new_y="NEXT")

    # ================================================================
    # 1. HIPÓTESE E PLANO GERAL
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("1. Hipótese Central e Plano Geral")

    pdf.subtitulo("Hipótese")
    pdf.corpo(
        "O endividamento das famílias brasileiras é o principal fator responsável por: "
        "(a) a má percepção das pessoas sobre a situação econômica (dimensão subjetiva); "
        "(b) o comprometimento efetivo da renda mensal familiar (dimensão objetiva)."
    )

    pdf.subtitulo("Enquadramento teórico")
    pdf.corpo(
        "Perspectiva marxista e desenvolvimentista. O crédito no capitalismo periférico brasileiro "
        "opera como mecanismo de transferência de renda da classe trabalhadora para o setor "
        "financeiro, comprimindo a renda disponível e deteriorando a percepção de bem-estar "
        "econômico. O spread bancário brasileiro — entre os mais altos do mundo — amplifica "
        "esse efeito estrutural."
    )

    pdf.subtitulo("Fases da pesquisa")
    fases = [
        "Fase 1 — Coleta de dados: séries macroeconômicas (BCB, IBGE) e dados de endividamento/percepção (PEIC, ICC). Microdados da POF para análise no nível familiar.",
        "Fase 2 — Análise macro (séries temporais): modelo VAR/VECM com endividamento, ICC, IPCA, desemprego e renda real. Testes de causalidade de Granger, funções impulso-resposta e decomposição da variância.",
        "Fase 3 — Análise micro (POF): modelos probit/logit ordenados para percepção econômica; decomposição de Shapley para contribuição relativa de cada fator; regressão quantílica; variáveis instrumentais (2SLS) para endogeneidade.",
        "Fase 4 — Síntese: confronto macro-micro, análise diferenciada por classe de renda, interpretação à luz da financeirização da economia brasileira.",
    ]
    for fase in fases:
        pdf.item_lista(fase)

    pdf.subtitulo("Variáveis endógenas do modelo VAR")
    pdf.corpo(
        "Endividamento das famílias (ou comprometimento de renda), Índice de Confiança "
        "do Consumidor (ICC), IPCA, taxa de desemprego, rendimento médio real."
    )
    pdf.subtitulo("Variável exógena")
    pdf.corpo("Taxa Selic (instrumento de política monetária).")

    pdf.subtitulo("Período de análise")
    pdf.corpo(
        "2012 a 2025, cobrindo ciclo completo: crescimento (2012-13), recessão (2015-16), "
        "recuperação lenta (2017-19), pandemia (2020-21) e recuperação recente (2022-25)."
    )

    # ================================================================
    # 2. PLANO DE COLETA
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("2. Plano de Coleta de Dados")

    pdf.subtitulo("Etapa 1 — APIs automatizáveis (concluída)")
    pdf.corpo(
        "Dados coletados automaticamente via scripts Python acessando as APIs públicas do "
        "Banco Central (SGS) e do IBGE (SIDRA). Incluem séries de juros, inflação, crédito, "
        "endividamento, desemprego, renda e PIB."
    )

    pdf.subtitulo("Etapa 2 — Downloads estruturados (concluída)")
    pdf.corpo(
        "PEIC (CNC/Fecomércio): planilha Excel com série histórica mensal desde 2010, "
        "disponibilizada pela ABINEE. Contém percentual de famílias endividadas, inadimplentes "
        "e comprometimento de renda.\n\n"
        "ICC (Fecomércio SP): séries do Índice de Confiança do Consumidor e subíndices "
        "(condições atuais e expectativas), coletadas via SGS/BCB."
    )

    pdf.subtitulo("Etapa 3 — Microdados (pendente)")
    pdf.corpo(
        "POF 2017-2018 (IBGE): microdados de orçamento familiar com despesas de serviço "
        "de dívida, renda e percepção subjetiva de condições de vida. Download manual "
        "do site do IBGE (~2 GB)."
    )

    pdf.subtitulo("Etapa 4 — Dados complementares (pendente)")
    pdf.corpo(
        "ICE (CNI), pesquisas Datafolha/IPEC sobre percepção econômica. Acesso mais restrito; "
        "a ser utilizado conforme disponibilidade."
    )

    pdf.subtitulo("Padronização")
    pdf.corpo(
        "Todos os dados foram convertidos para formato Parquet com índice DatetimeIndex. "
        "Séries mensais e trimestrais mantêm frequência explícita. Metadados salvos em "
        "arquivos JSON por fonte."
    )

    # ================================================================
    # 3. INVENTÁRIO DOS DADOS COLETADOS
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("3. Inventário dos Dados Coletados")

    inventario = carregar_inventario()

    # --- 3.1 BCB ---
    pdf.subtitulo("3.1  Banco Central do Brasil (BCB/SGS)")
    pdf.corpo("Séries mensais coletadas via API SGS. Período geral: jan/2012 a início de 2026.")

    bcb_series = [
        ("Selic meta (% a.a.)", "bcb_selic_meta_mensal.parquet", "Taxa básica de juros definida pelo Copom"),
        ("IPCA mensal (%)", "bcb_ipca_mensal_mensal.parquet", "Variação mensal do índice de preços ao consumidor"),
        ("Crédito PF — saldo (R$ mi)", "bcb_credito_pf_saldo_mensal.parquet", "Saldo total de crédito para pessoa física"),
        ("Crédito PF — concessões (R$ mi)", "bcb_credito_pf_concessoes_mensal.parquet", "Novas concessões mensais de crédito PF"),
        ("Spread bancário PF (p.p.)", "bcb_spread_medio_pf_mensal.parquet", "Diferença entre taxa de captação e de empréstimo PF"),
        ("Inadimplência PF (%)", "bcb_inadimplencia_pf_mensal.parquet", "Percentual da carteira PF com atraso > 90 dias"),
        ("Endividamento famílias (%)", "bcb_endividamento_familias_mensal.parquet", "Dívida das famílias / renda acumulada 12 meses"),
        ("Comprometimento de renda (%)", "bcb_comprometimento_renda_mensal.parquet", "Serviço da dívida / renda acumulada 12 meses"),
    ]

    cabecalho = ["Série", "Período", "Obs", "Último"]
    larguras = [70, 40, 18, 30]
    linhas = []
    for nome, arq, _desc in bcb_series:
        info = next((x for x in inventario if x["arquivo"] == arq), None)
        if info:
            periodo = f"{info['periodo_inicio']:%Y-%m} a {info['periodo_fim']:%Y-%m}"
            ultimo_val = list(info["ultimos_valores"].values())[0] if info["ultimos_valores"] else "—"
            ultimo_str = f"{ultimo_val:,.2f}" if isinstance(ultimo_val, (int, float)) else str(ultimo_val)
            linhas.append([nome, periodo, str(info["observacoes"]), ultimo_str])
        else:
            linhas.append([nome, "—", "—", "—"])
    pdf.tabela(cabecalho, linhas, larguras)

    # --- 3.2 PEIC ---
    pdf.subtitulo("3.2  PEIC — Endividamento do Consumidor (CNC/Fecomércio)")
    pdf.corpo(
        "Pesquisa mensal da CNC que entrevista ~18.000 consumidores em todas as capitais. "
        "Dados desde jan/2010, coletados via planilha ABINEE."
    )

    peic_info = next((x for x in inventario if x["arquivo"] == "peic_endividamento_mensal.parquet"), None)
    if peic_info:
        cabecalho = ["Variável", "Período", "Obs", "Último (%)"]
        larguras = [70, 40, 18, 30]
        nomes_peic = {
            "pct_familias_endividadas": "Famílias endividadas",
            "pct_dividas_em_atraso": "Dívidas em atraso",
            "pct_sem_condicoes_pagar": "Sem condições de pagar",
            "pct_renda_comprometida_divida": "Renda comprometida com dívida",
        }
        linhas = []
        periodo = f"{peic_info['periodo_inicio']:%Y-%m} a {peic_info['periodo_fim']:%Y-%m}"
        for col in peic_info["colunas"]:
            nome = nomes_peic.get(col, col)
            val = peic_info["ultimos_valores"].get(col, 0)
            linhas.append([nome, periodo, str(peic_info["observacoes"]), f"{val:.1f}"])
        pdf.tabela(cabecalho, linhas, larguras)

    # --- 3.3 ICC ---
    pdf.subtitulo("3.3  ICC — Confiança do Consumidor (Fecomércio SP)")
    pdf.corpo(
        "Índice de Confiança do Consumidor da Fecomércio SP, coletado via SGS/BCB. "
        "Escala de 0 a 200: acima de 100 indica otimismo, abaixo indica pessimismo. "
        "Inclui subíndices de condições atuais e expectativas futuras."
    )

    icc_info = next((x for x in inventario if x["arquivo"] == "icc_confianca_consumidor_mensal.parquet"), None)
    if icc_info:
        cabecalho = ["Subíndice", "Período", "Obs", "Último"]
        larguras = [70, 40, 18, 30]
        nomes_icc = {
            "icc_indice": "ICC — Índice geral",
            "icc_condicoes_atuais": "ICC — Condições Atuais",
            "icc_expectativas": "ICC — Expectativas Futuras",
        }
        linhas = []
        periodo = f"{icc_info['periodo_inicio']:%Y-%m} a {icc_info['periodo_fim']:%Y-%m}"
        for col in icc_info["colunas"]:
            nome = nomes_icc.get(col, col)
            val = icc_info["ultimos_valores"].get(col, 0)
            linhas.append([nome, periodo, str(icc_info["observacoes"]), f"{val:.2f}"])
        pdf.tabela(cabecalho, linhas, larguras)

    # --- 3.4 IBGE ---
    pdf.add_page()
    pdf.subtitulo("3.4  IBGE/SIDRA")
    pdf.corpo(
        "Dados trimestrais da PNAD Contínua (desemprego e rendimento) e Contas Nacionais (PIB), "
        "além do IPCA por grupo de despesa (mensal). Coletados via API SIDRA."
    )

    ibge_series = [
        ("Taxa de desocupação (%)", "ibge_desemprego_trimestral.parquet", "PNAD Contínua — trimestral"),
        ("Rendimento médio real (R$)", "ibge_rendimento_medio_trimestral.parquet", "PNAD Contínua — trimestral"),
        ("PIB a preços de mercado (R$ mi)", "ibge_pib_trimestral.parquet", "Contas Nacionais — trimestral"),
        ("IPCA por grupo de despesa (%)", "ibge_ipca_grupos_mensal.parquet", "IPCA desagregado — mensal"),
    ]

    cabecalho = ["Série", "Período", "Obs", "Freq."]
    larguras = [70, 40, 18, 30]
    linhas = []
    for nome, arq, freq in ibge_series:
        info = next((x for x in inventario if x["arquivo"] == arq), None)
        if info:
            periodo = f"{info['periodo_inicio']:%Y-%m} a {info['periodo_fim']:%Y-%m}"
            linhas.append([nome, periodo, str(info["observacoes"]), freq.split("—")[-1].strip()])
        else:
            linhas.append([nome, "—", "—", "—"])
    pdf.tabela(cabecalho, linhas, larguras)

    # ================================================================
    # 4. DESCRIÇÃO DETALHADA DAS SÉRIES
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("4. Descrição Detalhada das Séries e Índices")

    descricoes = [
        ("Endividamento das famílias (BCB, série 29037)",
         "Razão entre a dívida total das famílias e a renda acumulada nos últimos 12 meses. "
         "Mede o estoque de dívida relativo à capacidade de pagamento. Série calculada pelo "
         "Banco Central com base nos dados do Sistema de Informações de Crédito (SCR). "
         "É a variável central da hipótese — captura o nível estrutural de endividamento."),

        ("Comprometimento de renda com dívida (BCB, série 29038)",
         "Razão entre o serviço da dívida (juros + amortização) e a renda acumulada em 12 meses. "
         "Diferente do endividamento, mede o fluxo mensal que sai da renda para pagar dívidas. "
         "É o indicador mais relevante para o impacto direto na renda disponível."),

        ("PEIC — Famílias endividadas (CNC)",
         "Percentual de famílias que declararam possuir qualquer tipo de dívida (cartão de crédito, "
         "cheque especial, crediário, empréstimo pessoal, prestação de carro ou imóvel). "
         "Pesquisa amostral mensal com ~18.000 consumidores em todas as capitais brasileiras. "
         "Inclui estratificação por faixa de renda (até 10 SM e acima de 10 SM)."),

        ("PEIC — Dívidas em atraso (CNC)",
         "Percentual de famílias endividadas que possuem dívidas ou contas em atraso. "
         "Indica a transição do endividamento para a inadimplência efetiva."),

        ("PEIC — Renda comprometida com dívida (CNC)",
         "Parcela média da renda familiar que está comprometida com pagamento de dívidas, "
         "declarada pelas próprias famílias. Difere da série BCB por ser autodeclarada e "
         "incluir compromissos informais."),

        ("ICC — Índice de Confiança do Consumidor (Fecomércio SP)",
         "Indicador sintético de percepção econômica, calculado pela Fecomércio SP com base "
         "em pesquisa mensal com consumidores da Região Metropolitana de São Paulo. "
         "Escala de 0 a 200, onde 100 é o ponto neutro. Composto por dois subíndices: "
         "Condições Econômicas Atuais (CEA) e Expectativas do Consumidor (EC). "
         "É a principal proxy para a dimensão subjetiva da hipótese."),

        ("ICC — Condições Econômicas Atuais",
         "Subíndice que mede como o consumidor avalia a situação econômica presente: "
         "emprego, renda e capacidade de consumo no momento da pesquisa. "
         "Tende a ser mais sensível a choques de curto prazo."),

        ("ICC — Expectativas Futuras",
         "Subíndice que mede o que o consumidor espera para os próximos meses em termos "
         "de emprego, renda e situação econômica. Tipicamente mais estável e mais influenciado "
         "por narrativas macroeconômicas e políticas."),

        ("Taxa Selic (BCB, série 4189)",
         "Taxa básica de juros da economia brasileira, definida pelo Copom a cada 45 dias. "
         "No modelo VAR, entra como variável exógena (instrumento de política). "
         "Impacta o custo do crédito e, portanto, o endividamento — mas não é determinada "
         "diretamente pela percepção do consumidor."),

        ("IPCA (BCB, série 433)",
         "Índice Nacional de Preços ao Consumidor Amplo, calculado pelo IBGE. "
         "Principal indicador de inflação no Brasil e meta do regime de metas. "
         "Controla-se por inflação no modelo para isolar o efeito do endividamento."),

        ("Spread bancário PF (BCB, série 20783)",
         "Diferença entre a taxa de captação dos bancos e a taxa cobrada nos empréstimos "
         "a pessoas físicas. O spread brasileiro é um dos maiores do mundo e funciona "
         "como mecanismo de extração de renda — ponto central na análise marxista."),

        ("Taxa de desocupação (IBGE/PNAD Contínua)",
         "Percentual da população economicamente ativa que está desempregada. "
         "Variável de controle essencial: o desemprego afeta tanto a percepção econômica "
         "quanto o endividamento (pessoas desempregadas recorrem ao crédito)."),

        ("Rendimento médio real (IBGE/PNAD Contínua)",
         "Rendimento médio real efetivamente recebido no trabalho principal. "
         "Deflacionado pelo IPCA. Essencial para contextualizar o endividamento: "
         "dívida alta com renda crescente é diferente de dívida alta com renda estagnada."),
    ]

    for titulo, desc in descricoes:
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(20, 60, 120)
        pdf.cell(0, 6, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(3)

    # ================================================================
    # 5. PRÓXIMOS PASSOS
    # ================================================================
    pdf.add_page()
    pdf.titulo_secao("5. Próximos Passos")

    proximos = [
        "Análise exploratória: visualização das séries temporais, testes de estacionariedade (ADF, KPSS) e correlação cruzada entre endividamento e ICC.",
        "Modelo VAR/VECM: estimação com séries mensais (endividamento, ICC, IPCA, desemprego, renda); testes de cointegração de Johansen; causalidade de Granger; funções impulso-resposta; decomposição da variância.",
        "Download e processamento dos microdados da POF 2017-2018 para análise no nível familiar.",
        "Análise micro com POF: probit/logit ordenado para percepção econômica, decomposição de dominância (Shapley), regressão quantílica e variáveis instrumentais.",
        "Estratificação por classe de renda: testar se o efeito do endividamento é diferenciado para famílias de baixa renda (crédito de sobrevivência) versus renda média-alta (crédito patrimonial).",
        "Robustez: janelas móveis, diferentes medidas de endividamento, controle por eventos atípicos (pandemia, greve dos caminhoneiros).",
        "Relatório final com interpretação teórica à luz da financeirização e implicações de política econômica.",
    ]
    for item in proximos:
        pdf.item_lista(item)

    # ================================================================
    # SALVAR
    # ================================================================
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(SAIDA))
    print(f"PDF gerado: {SAIDA}")
    print(f"Tamanho: {SAIDA.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    gerar_pdf()
