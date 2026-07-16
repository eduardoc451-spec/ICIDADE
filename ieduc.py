import re
import streamlit as st
import psycopg2
import json
from io import BytesIO
from datetime import datetime, date

# =============================================================================
# FUNÇÕES DO BANCO NEON (Centralizadas em banco.py)
# =============================================================================
from banco import load_respostas, save_resp, load_todas_respostas


# =============================================================================
# BIBLIOTECAS PARA O PDF (ReportLab)
# =============================================================================
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak
)


# =============================================================================
# BIBLIOTECAS PARA OS GRÁFICOS (Plotly)
# =============================================================================
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# =============================================================================
# CONSTANTES GLOBAIS i-EDUC (ADAPTADAS DO MODELO IGOV TI)
# =============================================================================
CATEGORIAS_MAP = {
    "creche": {
        "label": "1.0 Creche",
        "qids": ["1.1.1", "1.1.2", "1.2.1.1", "1.2.2", "1.3", "1.4", "1.7.1", "1.8", "1.9", "1.10", "1.11", "1.11.1", "1.12", "1.12.1", "1.13", "1.15"]
    },
    "pre_escola": {
        "label": "2.0 Pré-escola",
        "qids": ["2.1.1", "2.1.2", "2.2.1.1", "2.2.2", "2.3", "2.4", "2.7.1", "2.8", "2.9", "2.10", "2.11", "2.11.1", "2.12", "2.12.1", "2.13", "2.15"]
    },
    "anos_iniciais_finais": {
        "label": "3.0 Ensino Fundamental",
        "qids": ["3.1", "3.2", "3.5.1", "3.6", "3.7", "3.8", "3.10", "3.11", "3.12", "3.12.1", "3.13.1", "3.14.1", "3.15.3.1", "3.15.4.1", "3.16", "3.19", "3.20", "3.23"]
    },
    "infra_gestao_merenda": {
        "label": "5.0 a 12.0 Infraestrutura, Gestão e Merenda",
        "qids": ["5.0", "7.0", "8.1", "9.0", "11.1", "12.1"]
    },
    "planos_conselhos_outros": {
        "label": "14.0 a 19.0 Planos, Conselhos e Operação",
        "qids": ["14.3", "14.3.1", "16.1", "16.2", "16.3", "16.5", "17.3.1", "17.4", "17.5", "17.7", "18.1", "18.2", "18.3.1", "19.3"]
    },
    "extras_e1_e2": {
        "label": "Blocos Especiais E1 e E2",
        "qids": ["E1.1", "E1.2", "E1.5", "E1.6", "E1.8", "E1.9", "E2.1", "E2.2", "E2.5", "E2.6", "E2.8", "E2.9"]
    },
    "extras_e3_e13_e5_e7": {
        "label": "Blocos Especiais E3, E5, E6, E7 e E13",
        "qids": ["E3.3", "E3.4", "E3.5", "E3.9", "E3.10", "E13.1", "E.13.2", "E13.3", "E5", "E6", "E7"]
    }
}

PONTUACOES_MAX = {
    # 1.0 Creche
    "1.1.1": 2, "1.1.2": 3, "1.2.1.1": 5, "1.2.2": 5, "1.3": 10, "1.4": 18, "1.7.1": 7, "1.8": 3, 
    "1.9": 2, "1.10": 2, "1.11": 18, "1.11.1": 18, "1.12": 18, "1.12.1": 18, "1.13": 50, "1.15": 10,
    
    # 2.0 Pré-escola
    "2.1.1": 2, "2.1.2": 3, "2.2.1.1": 5, "2.2.2": 5, "2.3": 10, "2.4": 18, "2.7.1": 7, "2.8": 3, 
    "2.9": 2, "2.10": 2, "2.11": 18, "2.11.1": 18, "2.12": 18, "2.12.1": 18, "2.13": 50, "2.15": 10,
    
    # 3.0 Ensino Fundamental
    "3.1": 10, "3.2": 19, "3.5.1": 7, "3.6": 3, "3.7": 2, "3.8": 2, "3.10": 12, "3.11": 2, 
    "3.12": 20, "3.12.1": 20, "3.13.1": 20, "3.14.1": 20, "3.15.3.1": 18, "3.15.4.1": 18, "3.16": 20, 
    "3.19": 10, "3.20": 2.5, "3.23": 25,
    
    # 5.0 a 12.0 Infraestrutura, Gestão e Merenda
    "5.0": 75, "7.0": 5, "8.1": 12, "9.0": 2, "11.1": 2, "12.1": 6,
    
    # 14.0 a 19.0 Planos, Conselhos e Operação
    "14.3": 20, "14.3.1": 30, "16.1": 3, "16.2": 3, "16.3": 6, "16.5": 3, "17.3.1": 2, 
    "17.4": 3, "17.5": 6, "17.7": 3, "18.1": 3, "18.2": 6, "18.3.1": 6, "19.3": 2,
    
    # Bloco Especial E1 e E2
    "E1.1": 2, "E1.2": 4, "E1.5": 6, "E1.6": 2, "E1.8": 12.5, "E1.9": 12.5,
    "E2.1": 2, "E2.2": 4, "E2.5": 6, "E2.6": 2, "E2.8": 12.5, "E2.9": 12.5,
    
    # Bloco Especial E3, E5, E6, E7 e E13
    "E3.3": 6, "E3.4": 12, "E3.5": 2, "E3.9": 12.5, "E3.10": 12.5,
    "E13.1": 18, "E.13.2": 18, "E13.3": 38, "E5": 75, "E6": 5, "E7": 5
}

FAIXA_CORES = {
    "C": "#ef4444",   # Crítico / Vermelho
    "C+": "#f97316",  # Alerta / Laranja
    "B": "#eab308",   # Regular / Amarelo
    "B+": "#22c55e",  # Bom / Verde Claro
    "A": "#16a34a"    # Excelente / Verde Escuro
}

# =============================================================================
# MODAL DE AVISO AUTOMÁTICO (APENAS QUANDO LINKS FOREM DETECTADOS)
# =============================================================================
@st.dialog("⚠️ Atenção! Evidência em Link Externo")
def modal_aviso_link(qid, links_encontrados):
    st.warning(f"Detectamos a inclusão de link(s) no campo de evidências da questão **{qid}**.")
    for lk in links_encontrados:
        st.markdown(f"🔗 **Endereço:** `{lk}`")
    st.markdown("""
    **Por favor, verifique se este link está configurado para acesso público/compartilhado.**
     
    Se as credenciais estiverem privadas ou exigirem login e senha do seu município, as equipes avaliadoras externas **não conseguirão acessar as provas**, invalidando os pontos desse quesito.
    """)
    if st.button("Confirmo que o link está liberado para o público", key=f"btn_conf_{qid}"):
        st.rerun()

# =============================================================================
# 2. GERADOR DO RELATÓRIO PDF
# =============================================================================

def gerar_relatorio_pdf(dados, ano, total, faixa, all_data=None):
    # Inicializa o buffer na memória e vincula ao SimpleDocTemplate
    buffer = BytesIO()
     
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()

    style_titulo_capa = ParagraphStyle('TituloCapa', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=colors.HexColor("#1b4f72"), alignment=1)

    # -------------------------------------------------------------------------
    # FOLHA 1: CAPA
    # -------------------------------------------------------------------------
    elements.append(Spacer(1, 100))
     
    elements.append(Paragraph("RELATÓRIO I-EDUC", styles["Title"]))
         
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("Relatório i-Educ (Validação Municipal)", style_titulo_capa))
    elements.append(Spacer(1, 15))
     
    style_ano_capa = ParagraphStyle('AnoCapa', parent=styles['Normal'], fontName='Helvetica', fontSize=16, textColor=colors.HexColor("#7f8c8d"), alignment=1)
    elements.append(Paragraph(f"Exercício: {ano}", style_ano_capa))
    elements.append(PageBreak())

    # -------------------------------------------------------------------------
    # FOLHA 2: SUMÁRIO (ADAPTADO i-EDUC)
    # -------------------------------------------------------------------------
    elements.append(Paragraph("<b>SUMÁRIO</b>", styles["h1"]))
    elements.append(Spacer(1, 30))

    style_item_esquerda = ParagraphStyle('ItemEsq', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#2c3e50"))
    style_pag_direita = ParagraphStyle('PagDir', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#1b4f72"), alignment=2)

    dados_sumario = [
        [Paragraph("1. Resumo Executivo (Análise Comparativa de Gestão Educacional)", style_item_esquerda), Paragraph("Pág. 3", style_pag_direita)],
        [Paragraph("2. Análise de Desempenho e Conformidade por Quesito", style_item_esquerda), Paragraph("Pág. 3", style_pag_direita)],
        [Paragraph("3. Análise de Impacto e Penalidades (Eficiência Preventiva)", style_item_esquerda), Paragraph("Pág. 4", style_pag_direita)],
        [Paragraph("4. Alinhamento com a Agenda 2030 (ODS)", style_item_esquerda), Paragraph("Pág. 4", style_pag_direita)],
        [Paragraph("5. Série Histórica do Desempenho i-EDUC", style_item_esquerda), Paragraph("Pág. 5", style_pag_direita)],
    ]
     
    tabela_sumario = Table(dados_sumario, colWidths=[400, 90])
    tabela_sumario.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7"), 1, (2, 4)), 
    ]))
    elements.append(tabela_sumario)
    elements.append(PageBreak())

    # -------------------------------------------------------------------------
    # FOLHA 3+: CONTEÚDO
    # -------------------------------------------------------------------------
    elements.append(Paragraph(f"RELATÓRIO DE VALIDAÇÃO E AUDITORIA i-EDUC - {ano}", styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<b>1. RESUMO EXECUTIVO (ANÁLISE COMPARATIVA)</b>", styles["h2"]))
    elements.append(Spacer(1, 8))

    nota_atual = float(total)
    ano_atual = int(str(ano).strip()[:4])
    ano_ant = ano_atual - 1

    # Regra de faixas fixas mantendo o teto real de 1000 pontos do sistema
    def converter_pontos_em_faixa_iegm(pontos):
        pts = float(pontos)
        if pts <= 500:       return "C"
        elif pts <= 599:     return "C+"
        elif pts <= 749:     return "B"
        elif pts <= 899:     return "B+"
        else:                return "A"

    if all_data is None:
        all_data = {}

    dados_ano_anterior = all_data.get(ano_ant, {})
    nota_anterior = 0.0
     
    # Varredura blindada: aceita tanto dicionários estruturados quanto valores diretos
    if dados_ano_anterior and isinstance(dados_ano_anterior, dict):
        if "total" in dados_ano_anterior:
            nota_anterior = float(dados_ano_anterior["total"])
        else:
            for qid_ant, info_ant in dados_ano_anterior.items():
                if qid_ant.startswith("COM_"): 
                    continue
                try:
                    if isinstance(info_ant, dict):
                        nota_anterior += float(info_ant.get("pontos", 0))
                    else:
                        nota_anterior += float(info_ant)
                except (ValueError, TypeError):
                    continue
    elif isinstance(dados_ano_anterior, (int, float)):
        nota_anterior = float(dados_ano_anterior)

    faixa_anterior = converter_pontos_em_faixa_iegm(nota_anterior)
    faixa_real_atual = faixa if faixa else converter_pontos_em_faixa_iegm(nota_atual)

    # CORREÇÃO DA TRAVA MATEMÁTICA DA BASE ZERO
    variacao_pontos = nota_atual - nota_anterior
    if nota_anterior > 0:
        variacao_percentual = (variacao_pontos / nota_anterior) * 100
        texto_percentual = f"{variacao_percentual:+.2f}%"
    elif nota_anterior == 0 and nota_atual > 0:
        # Crescimento partindo do zero calculado sobre a escala global (teto de 1000 pts)
        variacao_percentual = (nota_atual / 1000) * 100
        texto_percentual = f"{variacao_percentual:+.2f}%"
    else:
        texto_percentual = "0.00%"

    if variacao_pontos > 0:
        cor_variacao = colors.HexColor("#28a745")
        seta_tendencia = "▲"
    elif variacao_pontos < 0:
        cor_variacao = colors.HexColor("#dc3545")
        seta_tendencia = "▼"
    else:
        cor_variacao = colors.HexColor("#6c757d")
        seta_tendencia = "■"

    style_th = ParagraphStyle('Th', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.whitesmoke, alignment=1)
    style_td_ano = ParagraphStyle('TdAno', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#2c3e50"), alignment=1)
    style_td_pts = ParagraphStyle('TdPts', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, alignment=1)
    style_td_faixa = ParagraphStyle('TdFaixa', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor("#1b4f72"), alignment=1)
    style_td_var = ParagraphStyle('TdVar', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, textColor=cor_variacao, alignment=1)

    dados_comparativos = [
        [Paragraph("Exercício", style_th), Paragraph("Pontuação Obtida (i-Educ)", style_th), Paragraph("Faixa / Conceito", style_th), Paragraph("Variação Nominal", style_th), Paragraph("Variação Percentual", style_th)],
        [Paragraph(str(ano_ant), style_td_ano), Paragraph(f"{nota_anterior:.1f} pts", style_td_pts), Paragraph(str(faixa_anterior), style_td_faixa), Paragraph("-", style_td_var), Paragraph("-", style_td_var)],
        [Paragraph(str(ano_atual), style_td_ano), Paragraph(f"{nota_atual:.1f} pts", style_td_pts), Paragraph(str(faixa_real_atual), style_td_faixa), Paragraph(f"{seta_tendencia} {variacao_pontos:+.1f} pts", style_td_var), Paragraph(f"{seta_tendencia} {texto_percentual}", style_td_var)]
    ]

    tabela_comp = Table(dados_comparativos, colWidths=[80, 115, 90, 105, 100])
    tabela_comp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")), 
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8f9fa")), ("BACKGROUND", (0, 2), (-1, 2), colors.whitesmoke),                    
    ]))
    elements.append(tabela_comp)
    elements.append(Spacer(1, 12))

    style_analise = ParagraphStyle('Analise', parent=styles['Normal'], fontSize=10, leading=14)
    if nota_anterior == 0:
        texto_analise = f"<b>Análise de Tendência Educacional:</b> Não foram localizados dados consolidados do exercício de {ano_ant} no banco de dados local para gerar a análise comparativa de evolução."
    elif variacao_pontos > 0:
        texto_analise = f"<b>Análise de Tendência Educacional:</b> O município registrou evolução de desempenho na infraestrutura e pedagógico com incremento de <b>{texto_percentual}</b> na sua pontuação global frente aos indicadores do i-Educ do exercício de {ano_ant}."
    elif variacao_pontos < 0:
        texto_analise = f"<b>Análise de Tendência Educacional:</b> <font color='#dc3545'><b>Alerta de Retrocesso:</b></font> Foi identificada uma redução de <b>{texto_percentual}</b> na eficiência e conformidade dos índices educacionais e administrativos em relação a {ano_ant}."
    else:
        texto_analise = f"<b>Análise de Tendência Educacional:</b> O município manteve estabilidade absoluta (0.00%) em suas métricas de validação educacional."

    elements.append(Paragraph(texto_analise, style_analise))
    elements.append(Spacer(1, 15))

    # 2. ANÁLISE DE DESEMPENHO POR QUESITO
    elements.append(Paragraph("<b>2. ANÁLISE DE DESEMPENHO E CONFORMIDADE POR QUESITO</b>", styles["h2"]))
    elements.append(Spacer(1, 6))

    lista_pontos_fortes = []
    lista_pontos_fracos = []

    for qid, info in dados.items():
        if qid.startswith("COM_") or not isinstance(info, dict): 
            continue
        pts_obtidos = float(info.get("pontos", 0))
        valor_resposta = info.get("valor", "")
        link_evidencia = info.get("link", "")
         
        pts_maximo = float(PONTUACOES_MAX.get(qid, 0)) if 'PONTUACOES_MAX' in globals() else 10.0
         
        if pts_maximo > 0:
            eficiencia = (pts_obtidos / pts_maximo) * 100
            item_data = {
                "qid": qid, 
                "pts_obtidos": pts_obtidos, 
                "pts_maximo": pts_maximo, 
                "eficiencia": eficiencia, 
                "valor": valor_resposta, 
                "link": link_evidencia
            }
             
            # NOVA REGRA: >= 70% é Ponto Forte, < 70% é Oportunidade de Melhoria
            if eficiencia >= 70.0: 
                lista_pontos_fortes.append(item_data)
            else:
                lista_pontos_fracos.append(item_data)

    if lista_pontos_fortes:
        elements.append(Paragraph("<b>✅ Indicadores em Conformidade Alta ou Máxima (≥ 70%):</b>", styles["h3"]))
        data_fortes = [["Quesito", "Nota / Teto", "Eficiência", "Resposta / Link de Evidência"]]
        for item in sorted(lista_pontos_fortes, key=lambda x: x["eficiencia"], reverse=True):
            evidencia = f"<b>{item['valor']}</b><br/>{item['link']}"
            data_fortes.append([item['qid'], f"{item['pts_obtidos']:.1f} / {item['pts_maximo']:.1f}", f"{item['eficiencia']:.1f}%", Paragraph(evidencia, styles["Normal"])])
        tabela_fortes = Table(data_fortes, colWidths=[65, 75, 65, 285])
        tabela_fortes.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#28a745")), 
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), 
            ("ALIGN", (0, 0), (2, -1), "CENTER"), 
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#28a745")), 
            ("FONTSIZE", (0, 0), (-1, -1), 9), 
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        elements.append(tabela_fortes)
        elements.append(Spacer(1, 12))

    if lista_pontos_fracos:
        elements.append(Paragraph("<b>⚠️ Oportunidades de Melhoria e Inconformidades (< 70%):</b>", styles["h3"]))
        data_fracos = [["Quesito", "Nota / Teto", "Eficiência", "Resposta / Link de Evidência"]]
        for item in sorted(lista_pontos_fracos, key=lambda x: x["eficiencia"]):
            evidencia = f"<b>{item['valor']}</b><br/>{item['link']}"
            data_fracos.append([item['qid'], f"{item['pts_obtidos']:.1f} / {item['pts_maximo']:.1f}", f"{item['eficiencia']:.1f}%", Paragraph(evidencia, styles["Normal"])])
        tabela_fracos = Table(data_fracos, colWidths=[65, 75, 65, 285])
        tabela_fracos.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e67e22")), 
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), 
            ("ALIGN", (0, 0), (2, -1), "CENTER"), 
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e67e22")), 
            ("FONTSIZE", (0, 0), (-1, -1), 9), 
            ("VALIGN", (0, 0), (-1, -1), "TOP")
        ]))
        elements.append(tabela_fracos)
        elements.append(Spacer(1, 15))

    # =========================================================================
    # 3. ANÁLISE DE IMPACTO E PENALIDADES (EFICIÊNCIA PREVENTIVA)
    # =========================================================================
    elements.append(Paragraph("<b>3. ANÁLISE DE IMPACTO E PENALIDADES (EFICIÊNCIA PREVENTIVA)</b>", styles["h2"]))
    elements.append(Spacer(1, 6))

    # Mapeamento oficial de penalidades máximas i-Educ fornecido
    PENALIDADES_MAX = {
        "1.5": -20.0, "1.14": -50.0, "2.5": -20.0, "2.14": -50.0, 
        "3.3": -20.0, "3.9": -50.0, "3.17": -20.0, "3.22.2": -10.0, 
        "3.22.2.1": -10.0, "6.0": -10.0, "13.1.1": -5.0, "13.1.2": -5.0, 
        "13.1.3": -5.0, "13.1.4": -5.0, "13.1.5": -3.0, "13.1.6": -3.0, 
        "14.0": -50.0, "15.3": -5.0, "15.3.1": -10.0, "15.3.2": -5.0, 
        "16.4": -50.0, "17.6": -50.0, "E1.10.1": -10.0, "E2.10.1": -10.0, 
        "E3.8": -10.0, "E3.12.1": -10.0, "E.8": -10.0
    }

    lista_penalidades = []
     
    # Fazemos apenas LEITURA direta no dicionário original, sem clonar ou modificar chaves
    for qid, pen_max in PENALIDADES_MAX.items():
        info = dados.get(qid, None)
         
        # Se o quesito existe no banco, extrai a nota real de forma segura
        if info is not None:
            if isinstance(info, dict):
                nota_real = float(info.get("pontos", 0.0))
            else:
                nota_real = float(info)
        else:
            # Caso não esteja preenchido no banco, assumimos 0.0 estritamente para o relatório
            nota_real = 0.0
         
        # Computa o risco: se for negativo, registra. Se for positivo ou zero, risco é zero.
        nota_risco = nota_real if nota_real <= 0.0 else 0.0
         
        if pen_max != 0:
            eficiencia_preventiva = (1.0 - (nota_risco / pen_max)) * 100.0
        else:
            eficiencia_preventiva = 100.0
             
        eficiencia_preventiva = max(0.0, min(eficiencia_preventiva, 100.0))

        lista_penalidades.append({
            "qid": qid, 
            "nota_real": nota_real, 
            "pen_max": pen_max, 
            "eficiencia": eficiencia_preventiva
        })

    if lista_penalidades:
        style_tabela_centro = ParagraphStyle('TabCentro', parent=styles['Normal'], fontSize=9, alignment=1)
        style_tabela_padrao = ParagraphStyle('TabPadrao', parent=styles['Normal'], fontSize=9, alignment=0)

        data_penalidades = [[
            Paragraph("Quesito", style_th), 
            Paragraph("Penalidade Aplicada", style_th), 
            Paragraph("Pior Cenário", style_th), 
            Paragraph("Eficiência Preventiva", style_th), 
            Paragraph("Status de Risco", style_th)
        ]]
         
        # Algoritmo de ordenação alfanumérico inteligente protegido contra tipos
        def ordenar_quesitos(x):
            limpo = ''.join(c for c in str(x["qid"]).split('_')[0] if c.isdigit() or c == '.')
            partes = [int(i) for i in limpo.split('.') if i.isdigit()]
            prefixo = ''.join(c for c in str(x["qid"]) if c.isalpha())
            return (prefixo, partes if partes else [999])

        for item in sorted(lista_penalidades, key=ordenar_quesitos):
            nota_txt = f"{item['nota_real']:.1f} pts"
            teto_txt = f"{item['pen_max']:.1f} pts"
            ef_txt = f"{item['eficiencia']:.1f}%"
             
            if item['eficiencia'] >= 100.0: 
                status = "<font color='#2e7d32'><b>Risco Mitigado</b></font>"
            elif item['eficiencia'] <= 0.0: 
                status = "<font color='#c0392b'><b>Impacto Máximo</b></font>"
            else: 
                status = "<font color='#d35400'><b>Impacto Parcial</b></font>"
                 
            data_penalidades.append([
                Paragraph(item['qid'], style_tabela_centro), 
                Paragraph(nota_txt, style_tabela_centro), 
                Paragraph(teto_txt, style_tabela_centro), 
                Paragraph(ef_txt, style_tabela_centro), 
                Paragraph(status, style_tabela_padrao)
            ])
             
        tabela_pen = Table(data_penalidades, colWidths=[70, 110, 80, 115, 125])
        tabela_pen.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4f72")), 
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1b4f72")), 
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(tabela_pen)
        elements.append(Spacer(1, 15))

    # -------------------------------------------------------------------------
    # 4. ALINHAMENTO COM A AGENDA 2030 (METAS ODS / ONU)
    # -------------------------------------------------------------------------
    elements.append(Paragraph("<b>4. ALINHAMENTO COM A AGENDA 2030 (METAS ODS / ONU)</b>", styles["h2"]))
    elements.append(Spacer(1, 6))
     
    def calcular_percentual_checklist(resposta_bruta, total_itens):
        if not resposta_bruta: return 0.0
        itens = [i.strip().lower() for i in str(resposta_bruta).split(",") if i.strip()]
        itens_validos = [i for i in itens if "outros" not in i]
        return min((len(itens_validos) / total_itens) * 100.0, 100.0) if total_itens > 0 else 0.0

    analise_ods = []
    for qid, info in dados.items():
        if qid.startswith("COM_") or not isinstance(info, dict): 
            continue
        resp = str(info.get("valor", "")).strip()
        resp_l = resp.lower()
        metas = ""
        status = ""
         
        # --- BLOCO EIXO 1 (Mapeamento ODS 4.2 e variações) ---
        if qid in ["1.0", "1.1", "1.2", "1.2.1", "1.2.2", "1.7", "1.11", "1.12", "1.13"]:
            metas = "4.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "1.2.1.1":
            metas = "4.2, 4A"
            status = "Atendido" if "diária – 05" in resp_l or "diaria" in resp_l else "Não Atendido"
        elif qid == "1.7.2":
            metas = "4C, 4.2"
            status = "Atendido" if any(x in resp_l for x in ["presencialmente", "distância", "distancia", "remotamente", "multiplicadores"]) else "Não Atendido"
        elif qid == "1.10":
            metas = "4.2"
            status = "Atendido" if "planejamento e desempenho da criança – 02" in resp_l or "planejamento" in resp_l else "Não Atendido"
        elif qid == "1.10.1":
            metas = "4.2"
            status = "Atendido" if any(x in resp_l for x in ["mensal", "bimestral", "trimestral", "quadrimestral", "semestral", "anual"]) else "Não Atendido"
             
        # --- BLOCO EIXO 2 (Mapeamento ODS 4.2 e variações) ---
        elif qid in ["2.0", "2.1", "2.2", "2.2.1", "2.2.2", "2.7", "2.11", "2.12", "2.13"]:
            metas = "4.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "2.2.1.1":
            metas = "4.2, 4A"
            status = "Atendido" if "diária – 05" in resp_l or "diaria" in resp_l else "Não Atendido"
        elif qid == "2.7.2":
            metas = "4C, 4.2"
            status = "Atendido" if any(x in resp_l for x in ["presencialmente", "distância", "distancia", "remotamente", "multiplicadores"]) else "Não Atendido"
        elif qid == "2.10":
            metas = "4.2"
            status = "Atendido" if "planejamento e desempenho da criança – 02" in resp_l or "planejamento" in resp_l else "Não Atendido"
        elif qid == "2.10.1":
            metas = "4.2"
            status = "Atendido" if any(x in resp_l for x in ["mensal", "bimestral", "trimestral", "quadrimestral", "semestral", "anual"]) else "Não Atendido"

        # --- BLOCO EIXO 3 (Mapeamento ODS 4.1, 4C, 5.1, etc) ---
        elif qid in ["3.0", "3.5", "3.10", "3.12", "3.13", "3.14", "3.15", "3.15.2", "3.15.4", "3.16", "3.22", "3.22.2", "3.23"]:
            metas = "4.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "3.5.2":
            metas = "4.1, 4C"
            status = "Atendido" if any(x in resp_l for x in ["presencialmente", "distância", "distancia", "remotamente", "multiplicadores"]) else "Não Atendido"
        elif qid == "3.8":
            metas = "4.1"
            status = "Atendido" if (any(x in resp_l for x in ["mensal", "bimestral", "trimestral", "quadrimestral", "semestral", "anual"]) or "planejamento" in resp_l) else "Não Atendido"
        elif qid == "3.11":
            metas = "4.7, 5.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "3.15.3":
            metas = "4.6, 4.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "3.20":
            metas = "4.1"
            status = "Atendido" if "metodologia desenvolvida exclusivamente pelos profissionais" in resp_l or "exclusivamente" in resp_l else "Não Atendido"
        elif qid == "3.22.2.1":
            metas = "4.1"
            status = "Atendido" if "todas as metas foram atingidas" in resp_l else "Não Atendido"
        elif qid == "3.23.1":
            metas = "4.1"
            status = f"{calcular_percentual_checklist(resp, 8):.1f}% Atendido"

        # --- BLOCO DEMAIS EIXOS (4.0, 4C, 2.1, 11.2, 16.6) ---
        elif qid == "4.0":
            metas = "4.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "6.0":
            metas = "4C"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "6.2":
            metas = "4C"
            status = f"{calcular_percentual_checklist(resp, 5):.1f}% Atendido"
        elif qid == "7.0":
            metas = "4C"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "8.0":
            metas = "2.1, 4.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "8.2":
            metas = "2.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "9.0":
            metas = "2.1, 4.2"
            status = "Atendido" if "secretaria de educação e em todas as escolas" in resp_l else "Não Atendido"
        elif qid == "10.0":
            metas = "2.1, 4.2"
            status = "Atendido" if "em todas as escolas" in resp_l else "Não Atendido"
        elif qid == "11.0":
            metas = "2.1, 4.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "11.1":
            metas = "2.1, 4.2"
            status = f"{calcular_percentual_checklist(resp, 8):.1f}% Atendido"
        elif qid == "12.0":
            metas = "2.1"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "12.1":
            metas = "2.1, 4A"
            status = f"{calcular_percentual_checklist(resp, 17):.1f}% Atendido"
        elif qid == "13.0":
            metas = "4.0"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "13.1":
            metas = "11.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid in ["13.1.2", "13.1.5"]:
            metas = "11.2"
            status = "Atendido" if "não" in resp_l else "Não Atendido"
        elif qid in ["13.1.3", "13.1.4", "13.1.6"]:
            metas = "11.2"
            status = "Atendido" if "todos os veículos" in resp_l or "todos os condutores" in resp_l or "00" in resp_l else "Não Atendido"
        elif qid in ["14.0", "14.3"]:
            metas = "4.0"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "14.3.1":
            metas = "4.0"
            status = "Atendido" if "todas as metas foram atingidas dentro do prazo" in resp_l else "Não Atendido"
        elif qid in ["15.0", "15.3", "15.3.1", "15.3.2"]:
            metas = "4.2"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "16.0":
            metas = "16.6"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "16.1":
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 5):.1f}% Atendido"
        elif qid == "16.2":
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 6):.1f}% Atendido"
        elif qid == "16.3":
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 11):.1f}% Atendido"
        elif qid == "17.0":
            metas = "4.0, 16.6"
            status = "Atendido" if "estrutura independente" in resp_l else "Não Atendido"
        elif qid in ["17.3.1", "17.4"]:
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 5):.1f}% Atendido"
        elif qid == "17.5":
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 8):.1f}% Atendido"
        elif qid == "17.6":
            metas = "4.0, 16.6"
            status = "Atendido" if "aprovado sem ressalva" in resp_l or "00" in resp_l else "Não Atendido"
        elif qid in ["18.0", "18.2", "19.0", "19.1"]:
            metas = "4.0, 16.6" if "18" in qid else "4.0"
            status = "Atendido" if "sim" in resp_l else "Não Atendido"
        elif qid == "18.1":
            metas = "2.1, 4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 10):.1f}% Atendido" # <-- Exemplo de fechamento para a linha cortada




           
