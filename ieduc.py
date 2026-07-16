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
            status = f"{calcular_percentual_checklist(resp, 5):.1f}% Atendido"
        elif qid == "18.3.1":
            metas = "4.0, 16.6"
            status = f"{calcular_percentual_checklist(resp, 9):.1f}% Atendido"
        elif qid == "19.1":
            metas = "4.0"
            status = f"{calcular_percentual_checklist(resp, 4):.1f}% Atendido"
        elif qid == "19.3":
            metas = "4.0"
            status = "Atendido" if "em todas as escolas" in resp_l else "Não Atendido"

        if metas: 
            analise_ods.append({"qid": qid, "status": status, "metas": metas, "resp": resp[:50]})

    if analise_ods:
        data_ods = [["Quesito", "Resposta Informada", "Vínculo Metas ODS", "Status de Cumprimento"]]
        style_td_ods = ParagraphStyle('TdOds', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, alignment=1)
        
        def extrair_chave_hierarquica(x):
            return [float(i) if i.replace('.', '', 1).isdigit() else 999 for i in x['qid'].split('.')]
            
        for item in sorted(analise_ods, key=extrair_chave_hierarquica):
            st_txt = item["status"]
            if "Não Atendido" in st_txt: 
                st_p = Paragraph(f"<font color='#dc3545'><b>{st_txt}</b></font>", style_td_ods)
            elif "Atendido" in st_txt and "%" not in st_txt: 
                st_p = Paragraph(f"<font color='#28a745'><b>{st_txt}</b></font>", style_td_ods)
            else: 
                st_p = Paragraph(f"<font color='#007bff'><b>{st_txt}</b></font>", style_td_ods)
                
            data_ods.append([item["qid"], Paragraph(item["resp"], styles["Normal"]), item["metas"], st_p])
            
        tabela_ods = Table(data_ods, colWidths=[60, 200, 115, 110])
        tabela_ods.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f9d58")), 
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), 
            ("ALIGN", (0, 0), (0, -1), "CENTER"), 
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#0f9d58")), 
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        elements.append(tabela_ods)
        elements.append(Spacer(1, 15))

    # -------------------------------------------------------------------------
    # 📊 5. SÉRIE HISTÓRICA DO I-EDUC (CONSOLIDADO FINAL)
    # -------------------------------------------------------------------------
    elements.append(Spacer(1, 10))

    anos_serie = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
    valores_serie = []
    
    for a in anos_serie:
        if a == ano_atual: 
            # Trava de segurança: garante o uso do parâmetro total oficial repassado
            valores_serie.append(float(total))
        elif a in all_data:
            dados_ano = all_data[a]
            # Coleta de forma estritamente informativa sem forçar recálculos do ano atual
            if isinstance(dados_ano, dict) and "total" in dados_ano:
                valores_serie.append(float(dados_ano["total"]))
            elif isinstance(dados_ano, (int, float)):
                valores_serie.append(float(dados_ano))
            else:
                valores_serie.append(float(sum(info_h.get("pontos", 0) for qid_h, info_h in dados_ano.items() if isinstance(info_h, dict) and not qid_h.startswith("COM_"))))
        else: 
            valores_serie.append(0.0)

    # Configuração do Gráfico ReportLab
    desenho_grafico = Drawing(480, 165)
    bc = VerticalBarChart()
    bc.x = 45; bc.y = 25; bc.height = 110; bc.width = 410
    bc.data = [valores_serie]
    bc.categoryAxis.categoryNames = [str(a) for a in anos_serie]
    bc.categoryAxis.labels.fontSize = 9; bc.categoryAxis.labels.fontName = 'Helvetica-Bold'; bc.categoryAxis.labels.dy = -10
    
    # Voltando para o teto oficial de 1000 pontos do sistema
    bc.valueAxis.valueMin = 0; bc.valueAxis.valueMax = 1000; bc.valueAxis.valueStep = 200; bc.valueAxis.labels.fontSize = 8
    
    # ATIVAÇÃO DOS RÓTULOS (PONTUAÇÃO EM CIMA DA BARRA)
    bc.barLabels.nudge = 8
    bc.barLabels.fontSize = 8
    bc.barLabels.fontName = 'Helvetica-Bold'
    bc.barLabelFormat = '%.1f'  # Formato com uma casa decimal
    
    # Paleta de cores institucional i-EDUC
    bc.bars[0].fillColor = colors.HexColor("#0f9d58")  # Verde ODS/i-EDUC
    bc.bars[0].strokeColor = colors.HexColor("#27ae60")
    bc.bars[0].strokeWidth = 0.5

    # Título do Gráfico atualizado para o contexto educacional
    desenho_grafico.add(String(240, 150, "Série Histórica do i-EDUC", textAnchor='middle', fontName='Helvetica-Bold', fontSize=12, fillColor=colors.HexColor("#2c3e50")))
    desenho_grafico.add(bc)
    
    elements.append(desenho_grafico)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# =============================================================================
# 3. INTERFACE E ABAS
# =============================================================================
from banco import get_connection  # Certificando-se de que a conexão unificada com o banco está importada

def render_sidebar():
    st.sidebar.title("🎓 Painel i-EDUC")
    anos = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
    ano_sel = st.sidebar.selectbox("Ano de Referência:", anos, key="ano_referencia_global")
    
    if st.session_state.get("limpeza_ativa", False):
        res_data = {}
    else:
        res_data = load_respostas(ano_sel)
        
    total_pts = sum(float(item.get("pontos", 0)) for k, item in res_data.items() if not k.startswith("COM_"))
    total_pts = round(total_pts, 1)
    
    if total_pts <= 500: 
        faixa, cor = "C", "red"
    elif total_pts <= 599: 
        faixa, cor = "C+", "orange"
    elif total_pts <= 749: 
        faixa, cor = "B", "#d4d400"
    elif total_pts <= 899: 
        faixa, cor = "B+", "lightgreen"
    else: 
        faixa, cor = "A", "green"
        
    st.sidebar.metric("Pontuação Total", f"{total_pts:.1f} pts")
    st.sidebar.markdown(f"**Faixa:** <span style='color:{cor}; font-size:20px; font-weight:bold;'>{faixa}</span>", unsafe_allow_html=True)
    
    # 📄 SEÇÃO DE GERAR E BAIXAR RELATÓRIO PDF INTEGRADA
    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Relatórios")
    
    # 🔥 BUSCA HISTÓRICA BLINDADA DIRETO NO BANCO NEON (POSTGRESQL)
    historico_tratado = {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ano, id, pontos FROM respostas")
                for row in cursor.fetchall():
                    try:
                        ano_db = int(str(row[0]).strip()[:4])
                        qid = row[1]
                        pontos_item = float(row[2]) if row[2] is not None else 0.0
                        
                        if ano_db not in historico_tratado:
                            historico_tratado[ano_db] = {}
                        
                        historico_tratado[ano_db][qid] = {"pontos": pontos_item}
                    except:
                        continue
    except Exception as e:
        st.sidebar.error(f"Erro ao processar histórico: {e}")

    st.session_state.all_data = historico_tratado

    pdf_buffer = gerar_relatorio_pdf(res_data, ano_sel, total_pts, faixa, historico_tratado)
    
    st.sidebar.download_button(
        label="📥 Baixar Relatório PDF",
        data=pdf_buffer.getvalue(),
        file_name=f"Relatorio_i-Educ_{ano_sel}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    
    # Botão da Sidebar protegido com a Lógica Inversa
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Zerar Banco de Dados"):
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM respostas WHERE ano = %s", (ano_sel,))
                conn.commit()
            
            for chave in list(st.session_state.keys()):
                if chave.startswith(("q", "res", "com", "val", "data")): 
                    st.session_state.pop(chave, None)
            
            st.session_state["limpeza_ativa"] = True
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erro ao zerar o banco de dados: {e}")
        
    return ano_sel, res_data, total_pts, faixa, cor


def mostrar_formulario_educ():
    # Removido init_db() local redundante (inicialização centralizada no arquivo principal de entrada ou banco.py)
    
    if "limpeza_ativa" in st.session_state:
        st.session_state.pop("limpeza_ativa", None)
        
    ano_sel, res_data, total_pts, faixa, cor = render_sidebar()
    st.markdown("""<style>.quesito-card { background-color: #f9f9f9; padding: 20px; border-left: 6px solid #1e88e5; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e3f2fd; }</style>""", unsafe_allow_html=True)
    
    st.title(f"📚 Auditoria i-EDUC - {ano_sel}")
    
    # 🔴 BOTÃO DE LIMPAR EM BRANCO NA TELA (MÉTODO BLINDADO MANTIDO COM SINTAXE POSTGRESQL)
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        if st.button("🗑️ Limpar Todos os Campos", type="primary", use_container_width=True):
            try:
                with get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("DELETE FROM respostas WHERE ano = %s", (ano_sel,))
                    conn.commit()
                
                # 🔥 Limpa estritamente as chaves de dados das perguntas do questionário
                for chave in list(st.session_state.keys()):
                    if chave.startswith(("q", "res", "com", "val", "data")):
                        st.session_state.pop(chave, None)
                
                st.session_state["limpeza_ativa"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao limpar dados do formulário: {e}")
    
    abas = st.tabs(["📝 Questionário", "📊 Dados Externos", "📈 Gráficos"])
    aba_questionario, aba_dados_externos, aba_graf = abas
    
    opc_sim_nao = ["", "Sim", "Não"]
    
    with aba_questionario:
        st.header("1.0 Diretrizes e Avaliação de Creches")
        import re
import streamlit as st

# Certifique-se de ter importado 're' e definido suas funções globais:
# save_resp, modal_aviso_link, bloco_comentarios e res_data

# =============================================================================
# DENOMINADOR INDEPENDENTE (CENTRALIZADOR)
# =============================================================================
st.number_input(
    "Informe o número TOTAL de creches municipais do município:", 
    min_value=0, 
    step=1, 
    value=st.session_state.get("global_total_creches_ie", 0),
    key="global_total_creches_ie"
)

# Recupera o total global para usar como sugestão/padrão nos quesitos abaixo
v_total_global = st.session_state.get("global_total_creches_ie", 0)

# =============================================================================
# QUESTÃO 1.0 - OFERTA DE CRECHE (IEDUC)
# =============================================================================
st.markdown('<div class="quesito-card">', unsafe_allow_html=True)

with st.container(key=f"container_bloco_ieduc_1_0_{ano_sel}", border=False):
    with st.expander(f"📌 Questão 1.0 • Oferta de Creche ({ano_sel})", expanded=True):
        st.subheader("1.0 • Infraestrutura da Educação Infantil")
        st.write("**1.0 A Prefeitura municipal oferece Creche?**")
        st.caption("ℹ️ *O salvamento é automático. Qualquer alteração grava os dados na hora.*")
        
        opcoes10 = ["Selecione...", "Sim", "Não"]
        d10 = res_data.get("1.0", {"valor": "Selecione...", "points": 0.0, "link": ""})
        val_salvo_10 = d10.get("valor", "Selecione...")
        if val_salvo_10 not in opcoes10:
            val_salvo_10 = "Selecione..."
                
        idx10 = opcoes10.index(val_salvo_10)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            r10 = st.radio("Selecione 1.0:", options=opcoes10, index=idx10, key=f"rb_ieduc_10_{ano_sel}", label_visibility="collapsed")
            pts_10 = 0.0
            
        with col2:
            l10 = st.text_area("Link/Evidência (1.0):", value=d10.get("link", ""), key=f"txt_ieduc_10_{ano_sel}", height=110)
            links_f10 = re.findall(r'(https?://[^\s]+)', l10)
            if links_f10:
                botoes_10 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f10])
                st.markdown(f"**Links Ativos:** {botoes_10}")
                
        score_placeholder_10 = st.empty()
        if r10 == "Selecione...":
            score_placeholder_10.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
        else:
            score_placeholder_10.markdown(f"📊 **Pontuação Aplicada na Questão 1.0:** `{pts_10:.1f} pontos` (Dados Informativos)")
                
        # Persistência reativa sem forçar rerun desnecessário
        if r10 != d10.get("valor", "") or l10 != d10.get("link", ""):
            save_resp("1.0", r10, pts_10, l10)
            res_data["1.0"] = {"valor": r10, "pontos": pts_10, "link": l10}
            if l10 != d10.get("link", "") and links_f10:
                links_10_antigos = re.findall(r'(https?://[^\s]+)', d10.get("link", ""))
                if links_f10 != links_10_antigos:
                    modal_aviso_link("1.0", links_f10)
            st.rerun()
                
        bloco_comentarios("1.0", res_data, ano_sel)
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.1 - BRINQUEDOS NO PÁTIO INFANTIL (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.1 - Brinquedos no Pátio Infantil", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.1")
    st.write("**Algum estabelecimento que oferece Creche possui brinquedos no Pátio Infantil?**")
    st.caption("ℹ️ *O salvamento é automático.*")
    
    opcoes11 = ["Selecione...", "Sim", "Não"]
    d11 = res_data.get("1.1", {"valor": "Selecione...", "pontos": 0.0, "link": ""})
    val_salvo_11 = d11.get("valor", "Selecione...")
    if val_salvo_11 not in opcoes11:
        val_salvo_11 = "Selecione..."
            
    idx11 = opcoes11.index(val_salvo_11)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        r11 = st.radio("Selecione 1.1:", options=opcoes11, index=idx11, key=f"rb_ieduc_11_{ano_sel}", label_visibility="collapsed")
        pts_11 = 0.0 
        
    with col2:
        l11 = st.text_area("Link/Evidência (1.1):", value=d11.get("link", ""), key=f"txt_ieduc_11_{ano_sel}", height=110)
        links_f11 = re.findall(r'(https?://[^\s]+)', l11)
        if links_f11:
            botoes_11 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f11])
            st.markdown(f"**Links Ativos:** {botoes_11}")
            
    score_placeholder_11 = st.empty()
    if r11 == "Selecione...":
        score_placeholder_11.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
    else:
        score_placeholder_11.markdown(f"📊 **Pontuação Aplicada na Questão 1.1:** `{pts_11:.1f} pontos` (Dados Informativos)")
            
    if r11 != d11.get("valor", "") or l11 != d11.get("link", ""):
        save_resp("1.1", r11, pts_11, l11)
        res_data["1.1"] = {"valor": r11, "pontos": pts_11, "link": l11}
        if l11 != d11.get("link", "") and links_f11:
            links_11_antigos = re.findall(r'(https?://[^\s]+)', d11.get("link", ""))
            if links_f11 != links_11_antigos:
                modal_aviso_link("1.1", links_f11)
        st.rerun()
            
    bloco_comentarios("1.1", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.1.1 - DADOS DE BRINQUEDOS NO PÁTIO INFANTIL (BPI)
# =============================================================================
with st.expander("🔍 QUESITO 1.1.1 - Dados de Brinquedos no Pátio Infantil (BPI)", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.1.1")
    st.write("**Informe os dados para o cálculo de brinquedos no Pátio Infantil (BPI):**")
    st.caption("ℹ️ *O salvamento é automático.*")
    
    d111 = res_data.get("1.1.1", {"valor": "BPI:0,TOTAL:0", "pontos": 0.0, "link": ""})
    
    try:
        parts_111 = d111["valor"].split(",")
        v_bpi_input = int(parts_111[0].split(":")[1])
        # INTEGRAÇÃO: Se o valor do banco for 0, usa o total global como sugestão amigável
        v_total_input = int(parts_111[1].split(":")[1])
        if v_total_input == 0 and v_total_global > 0:
            v_total_input = v_total_global
    except:
        v_bpi_input, v_total_input = 0, v_total_global
        
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Nº de creches com brinquedos no pátio infantil:</label>', unsafe_allow_html=True)
        bpi_input = st.number_input(
            "Nº de creches com brinquedos no pátio infantil", 
            min_value=0, 
            step=1, 
            value=v_bpi_input, 
            key=f"q111_bpi_val_{ano_sel}", 
            label_visibility="collapsed"
        )
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Nº TOTAL de creches no município:</label>', unsafe_allow_html=True)
        total_input = st.number_input(
            "Nº TOTAL de creches no município", 
            min_value=0, 
            step=1, 
            value=v_total_input, 
            key=f"q111_total_val_{ano_sel}", 
            label_visibility="collapsed"
        )
        
        pts_111 = 0.0
        if total_input > 0:
            proporcao_p = bpi_input / total_input
            pts_111 = float(min(2.0, proporcao_p * 2.0))
            
    with col2:
        l111 = st.text_area("Link/Evidência (1.1.1):", value=d111.get("link", ""), key=f"txt_ieduc_111_{ano_sel}", height=180)
        links_f111 = re.findall(r'(https?://[^\s]+)', l111)
        if links_f111:
            botoes_111 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f111])
            st.markdown(f"**Links Ativos:** {botoes_111}")
            
    st.markdown(f"📊 **Pontuação Calculada na Questão 1.1.1:** `{pts_111:.2f} pontos` (Máximo: 2.0 pontos)")
        
    str_valor_111 = f"BPI:{bpi_input},TOTAL:{total_input}"
    
    if str_valor_111 != d111.get("valor", "") or l111 != d111.get("link", ""):
        save_resp("1.1.1", str_valor_111, pts_111, l111)
        res_data["1.1.1"] = {"valor": str_valor_111, "pontos": pts_111, "link": l111}
        if l111 != d111.get("link", "") and links_f111:
            links_111_antigos = re.findall(r'(https?://[^\s]+)', d111.get("link", ""))
            if links_f111 != links_111_antigos:
                modal_aviso_link("1.1.1", links_f111)
        st.rerun()
            
    bloco_comentarios("1.1.1", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.1.2 - MANUTENÇÃO DAS CRECHES (IEDUC)
# =============================================================================
with st.expander(f"🔍 QUESITO 1.1.2 - Manutenção das Creches ({ano_sel})", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.1.2")
    st.write("**Informe os dados para o cálculo de manutenção das creches:**")
    st.markdown("""
    *Fórmulas de cálculo:*
    * $P1 = (NMANU / TOTAL) \\times Pmáx1$ *(Pmáx1 = -2 pontos)*
    * $P2 = (NCRON / TOTAL) \\times Pmáx2$ *(Pmáx2 = 1 ponto)*
    * $P3 = (CRON / TOTAL) \\times Pmáx3$ *(Pmáx3 = 3 pontos)*
    * $P = P1 + P2 + P3$
    """)
    st.caption("ℹ *Os cálculos e salvamento ocorrem em tempo real ao alterar os valores.*")
    
    d112 = res_data.get("1.1.2", {"valor": "CRON:0,NCRON:0,SOLIC:0,NMANU:0,TOTAL:0", "pontos": 0.0, "link": ""})
    v_banco_112 = d112.get("valor", "CRON:0,NCRON:0,SOLIC:0,NMANU:0,TOTAL:0")
    v_link_112 = d112.get("link", "")
    v_pontos_112 = float(d112.get("pontos", 0.0))
    
    try:
        parts_m = v_banco_112.split(",")
        v_cron = int(parts_m[0].split(":")[1])
        v_ncron = int(parts_m[1].split(":")[1])
        v_solic = int(parts_m[2].split(":")[1])
        v_nmanu = int(parts_m[3].split(":")[1])
    except:
        v_cron, v_ncron, v_solic, v_nmanu = 0, 0, 0, 0

    k_cron_112 = f"q112_cron_{ano_sel}"
    k_ncron_112 = f"q112_ncron_{ano_sel}"
    k_solic_112 = f"q112_solic_{ano_sel}"
    k_nmanu_112 = f"q112_nmanu_{ano_sel}"
    k_link_112 = f"link_q112_txt_val_{ano_sel}"

    if k_cron_112 not in st.session_state: st.session_state[k_cron_112] = v_cron
    if k_ncron_112 not in st.session_state: st.session_state[k_ncron_112] = v_ncron
    if k_solic_112 not in st.session_state: st.session_state[k_solic_112] = v_solic
    if k_nmanu_112 not in st.session_state: st.session_state[k_nmanu_112] = v_nmanu
    if k_link_112 not in st.session_state: st.session_state[k_link_112] = v_link_112

    def callback_atualiza_q112():
        cron_at = int(st.session_state.get(k_cron_112, 0))
        ncron_at = int(st.session_state.get(k_ncron_112, 0))
        solic_at = int(st.session_state.get(k_solic_112, 0))
        nmanu_at = int(st.session_state.get(k_nmanu_112, 0))
        lk_at = st.session_state.get(k_link_112, "")
        
        total_at = cron_at + ncron_at + solic_at + nmanu_at
        
        pts_112 = 0.0
        if total_at > 0:
            p1 = (nmanu_at / total_at) * (-2.0)
            p2 = (ncron_at / total_at) * 1.0
            p3 = (cron_at / total_at) * 3.0
            pts_112 = float(max(0.0, p1 + p2 + p3))
        
        str_valor_novo = f"CRON:{cron_at},NCRON:{ncron_at},SOLIC:{solic_at},NMANU:{nmanu_at},TOTAL:{total_at}"
        
        if str_valor_novo != str(v_banco_112) or lk_at != v_link_112 or abs(v_pontos_112 - pts_112) > 0.01:
            save_resp("1.1.2", str_valor_novo, pts_112, lk_at)
            res_data["1.1.2"] = {"valor": str_valor_novo, "pontos": pts_112, "link": lk_at}

    def callback_link_q112():
        novo_link = st.session_state.get(k_link_112, "")
        if novo_link != v_link_112:
            callback_atualiza_q112()
            links_f112 = re.findall(r'(https?://[^\s]+)', novo_link)
            links_antigos = re.findall(r'(https?://[^\s]+)', v_link_112)
            if links_f112 and links_f112 != links_antigos:
                st.session_state[f"trigger_modal_112_{ano_sel}"] = True

    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Quantas creches cumpriram o cronograma (CRON):</label>', unsafe_allow_html=True)
        st.number_input("Creches que cumpriram o cronograma (CRON)", min_value=0, step=1, key=k_cron_112, label_visibility="collapsed", on_change=callback_atualiza_q112)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Quantas creches NÃO cumpriram o cronograma (NCRON):</label>', unsafe_allow_html=True)
        st.number_input("Creches que não cumpriram o cronograma (NCRON)", min_value=0, step=1, key=k_ncron_112, label_visibility="collapsed", on_change=callback_atualiza_q112)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Quantas creches têm manutenção SOMENTE por solicitação (SOLIC):</label>', unsafe_allow_html=True)
        st.number_input("Creches com manutenção por solicitação (SOLIC)", min_value=0, step=1, key=k_solic_112, label_visibility="collapsed", on_change=callback_atualiza_q112)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Quantas creches NÃO realizam manutenção (NMANU):</label>', unsafe_allow_html=True)
        st.number_input("Creches que não realizam manutenção (NMANU)", min_value=0, step=1, key=k_nmanu_112, label_visibility="collapsed", on_change=callback_atualiza_q112)
        
        # Somatório automático reativo
        c_cron = int(st.session_state.get(k_cron_112, 0))
        c_ncron = int(st.session_state.get(k_ncron_112, 0))
        c_solic = int(st.session_state.get(k_solic_112, 0))
        c_nmanu = int(st.session_state.get(k_nmanu_112, 0))
        total_atualizado = c_cron + c_ncron + c_solic + c_nmanu
        
        st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Total de Creches (Somatório Automático):</label>', unsafe_allow_html=True)
        st.number_input("", value=int(total_atualizado), disabled=True, key=f"disabled_total_112_{ano_sel}", label_visibility="collapsed")

    with col_m2:
        l112 = st.text_area("Link/Evidência (1.1.2):", key=k_link_112, on_change=callback_link_q112, height=320)
        links_ativos_112 = re.findall(r'(https?://[^\s]+)', l112)
        botoes_112 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_ativos_112]) if links_ativos_112 else "Nenhum link ativo"
        st.markdown(f"**Links Ativos:** {botoes_112}")
            
    if total_atualizado > 0:
        rc_p1 = (c_nmanu / total_atualizado) * (-2.0)
        rc_p2 = (c_ncron / total_atualizado) * 1.0
        rc_p3 = (c_cron / total_atualizado) * 3.0
        pts_exibir = float(max(0.0, rc_p1 + rc_p2 + rc_p3))
        st.code(f"📊 Pontuação Calculada no Quesito 1.1.2: {pts_exibir:.2f} pontos / 3.0 pontos máximos.", language="text")
    else:
        st.code("💡 Insira os quantitativos para realizar o cálculo dinâmico ponderado da nota.", language="text")

    if st.session_state.get(f"trigger_modal_112_{ano_sel}", False):
        st.session_state[f"trigger_modal_112_{ano_sel}"] = False
        modal_aviso_link("1.1.2", re.findall(r'(https?://[^\s]+)', l112))
            
    bloco_comentarios("1.1.2", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.2 - DISPONIBILIZAÇÃO DE BRINQUEDOS/MATERIAIS PEDAGÓGICOS (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.2 - Disponibilização de Brinquedos/Materiais Pedagógicos", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.2")
    st.write("**A Prefeitura disponibiliza brinquedos/materiais pedagógicos para as crianças em todos os estabelecimentos de Creche do município?**")
    st.caption("ℹ️ *O salvamento é automático.*")
    
    opcoes12 = ["Selecione...", "Sim", "Não"]
    d12 = res_data.get("1.2", {"valor": "Selecione...", "pontos": 0.0, "link": ""})
    val_salvo_12 = d12.get("valor", "Selecione...")
    if val_salvo_12 not in opcoes12:
        val_salvo_12 = "Selecione..."
            
    idx12 = opcoes12.index(val_salvo_12)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        r12 = st.radio("Selecione 1.2:", options=opcoes12, index=idx12, key=f"rb_ieduc_12_{ano_sel}", label_visibility="collapsed")
        pts_12 = 0.0  
        
    with col2:
        l12 = st.text_area("Link/Evidência (1.2):", value=d12.get("link", ""), key=f"txt_ieduc_12_{ano_sel}", height=110)
        links_f12 = re.findall(r'(https?://[^\s]+)', l12)
        if links_f12:
            botoes_12 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f12])
            st.markdown(f"**Links Ativos:** {botoes_12}")
            
    score_placeholder_12 = st.empty()
    if r12 == "Selecione...":
        score_placeholder_12.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
    else:
        score_placeholder_12.markdown(f"📊 **Pontuação Aplicada na Questão 1.2:** `{pts_12:.1f} pontos` (Dados Informativos)")
            
    if r12 != d12.get("valor", "") or l12 != d12.get("link", ""):
        save_resp("1.2", r12, pts_12, l12)
        res_data["1.2"] = {"valor": r12, "pontos": pts_12, "link": l12}
        if l12 != d12.get("link", "") and links_f12:
            links_12_antigos = re.findall(r'(https?://[^\s]+)', d12.get("link", ""))
            if links_f12 != links_12_antigos:
                modal_aviso_link("1.2", links_f12)
        st.rerun()
            
    bloco_comentarios("1.2", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)
        import datetime  # Mova todos os imports para o topo do arquivo!
import re
import streamlit as st

# (Certifique-se de que res_data, ano_sel, save_resp, modal_aviso_link e bloco_comentarios estejam definidos)

# =============================================================================
# QUESITO 1.2.1 - HIGIENIZAÇÃO DOS BRINQUEDOS/MATERIAIS PEDAGÓGICOS (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.2.1 - Higienização dos Brinquedos/Materiais", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.2.1")
    st.write("**Realiza higienização dos brinquedos/materiais pedagógicos?**")
    st.caption("ℹ️ *O salvamento é automático. Qualquer alteração nas opções ou no link grava os dados na hora.*")
    
    opcoes121 = ["Selecione...", "Sim", "Não"]
    d121 = res_data.get("1.2.1", {"valor": "Selecione...", "pontos": 0.0, "link": ""})
    val_salvo_121 = d121.get("valor", "Selecione...")
    if val_salvo_121 not in opcoes121:
        val_salvo_121 = "Selecione..."
            
    idx121 = opcoes121.index(val_salvo_121)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        r121 = st.radio("Selecione 1.2.1:", options=opcoes121, index=idx121, key=f"rb_ieduc_121_{ano_sel}", label_visibility="collapsed")
        pts_121 = 0.0  # Configure a pontuação baseada nas regras do IEGM, se aplicável
        
    with col2:
        l121 = st.text_area("Link/Evidência (1.2.1):", value=d121.get("link", ""), key=f"txt_ieduc_121_{ano_sel}", height=110)
        placeholder_links_121 = st.empty()
        links_f121 = re.findall(r'(https?://[^\s]+)', l121)
        if links_f121:
            botoes_121 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f121])
            placeholder_links_121.markdown(f"**Links Ativos:** {botoes_121}")
            
    score_placeholder_121 = st.empty()
    if r121 == "Selecione...":
        score_placeholder_121.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
    else:
        score_placeholder_121.markdown(f"📊 **Pontuação Aplicada na Questão 1.2.1:** `{pts_121:.1f} pontos` (Dados Informativos)")
            
    mudou_opcao_121 = r121 != d121.get("valor", "")
    mudou_link_121 = l121 != d121.get("link", "")
    
    if mudou_opcao_121 or mudou_link_121:
        save_resp("1.2.1", r121, pts_121, l121)
        res_data["1.2.1"] = {"valor": r121, "pontos": pts_121, "link": l121}
        if mudou_link_121 and links_f121:
            links_121_antigos = re.findall(r'(https?://[^\s]+)', d121.get("link", ""))
            if links_f121 != links_121_antigos:
                modal_aviso_link("1.2.1", links_f121)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.2.1", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.2.1.1 - FREQUÊNCIA DE HIGIENIZAÇÃO (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.2.1.1 - Frequência de Higienização", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.2.1.1")
    st.write("**Qual a frequência de higienização aplicada na maior parte dos estabelecimentos que oferecem creche?**")
    st.caption("ℹ️ *O salvamento é automático. Qualquer alteração nas opções ou no link grava os dados na hora.*")
    
    opcoes1211 = [
        "Selecione...", 
        "Diária – 05", 
        "A cada 2 dias – 04", 
        "A cada 3 dias – 03", 
        "Semanal – 02", 
        "Mensal – 01", 
        "> 30 dias – 00"
    ]
    
    d1211 = res_data.get("1.2.1.1", {"valor": "Selecione...", "pontos": 0.0, "link": ""})
    val_salvo_1211 = d1211.get("valor", "Selecione...")
    if val_salvo_1211 not in opcoes1211:
        val_salvo_1211 = "Selecione..."
            
    idx1211 = opcoes1211.index(val_salvo_1211)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        r1211 = st.radio("Selecione 1.2.1.1:", options=opcoes1211, index=idx1211, key=f"rb_ieduc_1211_{ano_sel}", label_visibility="collapsed")
        
        mapa_pontos_1211 = {
            "Diária – 05": 5.0,
            "A cada 2 dias – 04": 4.0,
            "A cada 3 dias – 03": 3.0,
            "Semanal – 02": 2.0,
            "Mensal – 01": 1.0,
            "> 30 dias – 00": 0.0,
            "Selecione...": 0.0
        }
        pts_1211 = float(mapa_pontos_1211.get(r1211, 0.0))
        
    with col2:
        l1211 = st.text_area("Link/Evidência (1.2.1.1):", value=d1211.get("link", ""), key=f"txt_ieduc_1211_{ano_sel}", height=220)
        placeholder_links_1211 = st.empty()
        links_f1211 = re.findall(r'(https?://[^\s]+)', l1211)
        if links_f1211:
            botoes_1211 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f1211])
            placeholder_links_1211.markdown(f"**Links Ativos:** {botoes_1211}")
            
    score_placeholder_1211 = st.empty()
    if r1211 == "Selecione...":
        score_placeholder_1211.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
    else:
        score_placeholder_1211.markdown(f"📊 **Pontuação Aplicada na Questão 1.2.1.1:** `{pts_1211:.1f} pontos` (Máximo: 5.0 pontos)")
            
    mudou_opcao_1211 = r1211 != d1211.get("valor", "")
    mudou_link_1211 = l1211 != d1211.get("link", "")
    
    if mudou_opcao_1211 or mudou_link_1211:
        save_resp("1.2.1.1", r1211, pts_1211, l1211)
        res_data["1.2.1.1"] = {"valor": r1211, "pontos": pts_1211, "link": l1211}
        if mudou_link_1211 and links_f1211:
            links_1211_antigos = re.findall(r'(https?://[^\s]+)', d1211.get("link", ""))
            if links_f1211 != links_1211_antigos:
                modal_aviso_link("1.2.1.1", links_f1211)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.2.1.1", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.2.2 - CRONOGRAMA PARA COMPRA DE BRINQUEDOS (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.2.2 - Cronograma para Compra de Brinquedos", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.2.2")
    st.write("**Possui cronograma para compra de brinquedos/materiais pedagógicos?**")
    st.write("Planejamento de compra de brinquedos/materiais pedagógicos para cada estabelecimento de ensino")
    st.caption("ℹ️ *O salvamento é automático. Qualquer alteração nas opções ou no link grava os dados na hora.*")
    
    opcoes122 = [
        "Selecione...", 
        "Sim – 05", 
        "Não – 00"
    ]
    
    d122 = res_data.get("1.2.2", {"valor": "Selecione...", "pontos": 0.0, "link": ""})
    val_salvo_122 = d122.get("valor", "Selecione...")
    if val_salvo_122 not in opcoes122:
        val_salvo_122 = "Selecione..."
            
    idx122 = opcoes122.index(val_salvo_122)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        r122 = st.radio("Selecione 1.2.2:", options=opcoes122, index=idx122, key=f"rb_ieduc_122_{ano_sel}", label_visibility="collapsed")
        
        mapa_pontos_122 = {
            "Sim – 05": 5.0,
            "Não – 00": 0.0,
            "Selecione...": 0.0
        }
        pts_122 = float(mapa_pontos_122.get(r122, 0.0))
        
    with col2:
        l122 = st.text_area("Link/Evidência (1.2.2):", value=d122.get("link", ""), key=f"txt_ieduc_122_{ano_sel}", height=110)
        placeholder_links_122 = st.empty()
        links_f122 = re.findall(r'(https?://[^\s]+)', l122)
        if links_f122:
            botoes_122 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f122])
            placeholder_links_122.markdown(f"**Links Ativos:** {botoes_122}")
            
    score_placeholder_122 = st.empty()
    if r122 == "Selecione...":
        score_placeholder_122.markdown("⚠️ **Status:** `Aguardando preenchimento` (Selecione uma opção válida)")
    else:
        score_placeholder_122.markdown(f"📊 **Pontuação Aplicada na Questão 1.2.2:** `{pts_122:.1f} pontos` (Máximo: 5.0 pontos)")
            
    mudou_opcao_122 = r122 != d122.get("valor", "")
    mudou_link_122 = l122 != d122.get("link", "")
    
    if mudou_opcao_122 or mudou_link_122:
        save_resp("1.2.2", r122, pts_122, l122)
        res_data["1.2.2"] = {"valor": r122, "pontos": pts_122, "link": l122}
        if mudou_link_122 and links_f122:
            links_122_antigos = re.findall(r'(https?://[^\s]+)', d122.get("link", ""))
            if links_f122 != links_122_antigos:
                modal_aviso_link("1.2.2", links_f122)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.2.2", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.2.3 - DATA DA ÚLTIMA ENTREGA DE BRINQUEDOS (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.2.3 - Data da Última Entrega de Brinquedos", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.2.3")
    st.write("**Informe a data da última entrega de brinquedos/materiais pedagógicos:**")
    st.caption("ℹ️ *O salvamento é automático. Qualquer alteração na data ou no link grava os dados na hora.*")
    
    d123 = res_data.get("1.2.3", {"valor": "", "pontos": 0.0, "link": ""})
    val_salvo_123 = d123.get("valor", "")
    
    # Tratamento seguro da data inicial (datetime importado no topo do arquivo principal)
    try:
        data_inicial = datetime.datetime.strptime(val_salvo_123, "%Y-%m-%d").date() if val_salvo_123 else datetime.date.today()
    except ValueError:
        try:
            # Fallback caso a data salva esteja no formato amigável brasileiro "DD/MM/AAAA"
            data_inicial = datetime.datetime.strptime(val_salvo_123, "%d/%m/%Y").date()
        except ValueError:
            data_inicial = datetime.date.today()
            
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Selecione a Data (DD/MM/AAAA):</label>', unsafe_allow_html=True)
        dt_selecionada = st.date_input(
            "Data da última entrega de brinquedos", 
            value=data_inicial, 
            format="DD/MM/YYYY", 
            key=f"dt_ieduc_123_{ano_sel}", 
            label_visibility="collapsed"
        )
        
        str_data_123 = dt_selecionada.strftime("%d/%m/%Y")
        pts_123 = 0.0
        
    with col2:
        l123 = st.text_area("Link/Evidência (1.2.3):", value=d123.get("link", ""), key=f"txt_ieduc_123_{ano_sel}", height=110)
        placeholder_links_123 = st.empty()
        links_f123 = re.findall(r'(https?://[^\s]+)', l123)
        if links_f123:
            botoes_123 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f123])
            placeholder_links_123.markdown(f"**Links Ativos:** {botoes_123}")
            
    score_placeholder_123 = st.empty()
    score_placeholder_123.markdown(f"📊 **Data Registrada na Questão 1.2.3:** `{str_data_123}` (Dados Informativos)")
            
    mudou_opcao_123 = str_data_123 != d123.get("valor", "")
    mudou_link_123 = l123 != d123.get("link", "")
    
    if mudou_opcao_123 or mudou_link_123:
        save_resp("1.2.3", str_data_123, pts_123, l123)
        res_data["1.2.3"] = {"valor": str_data_123, "pontos": pts_123, "link": l123}
        if mudou_link_123 and links_f123:
            links_123_antigos = re.findall(r'(https?://[^\s]+)', d123.get("link", ""))
            if links_f123 != links_123_antigos:
                modal_aviso_link("1.2.3", links_f123)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.2.3", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.3 - ESPAÇO POR ALUNO EM SALA DE AULA (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.3 - Espaço por Aluno em Sala de Aula", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.3")
    st.write("**Informe a quantidade de turmas de Creche em que o espaço por aluno em sala de aula (área da sala dividido pelo nº de alunos) era:**")
    st.write("*Considerar como sala de aula o local principal ocupado pelos alunos para seu ensino e aprendizagem pelos professores*")
    st.markdown("""
    *Fórmula de cálculo ($P_{máx} = 10$ pontos):*
    * $N_1 = 1.0 \times P_1$ (Superior ou igual a 2,30 m²)
    * $N_2 = 0.5 \times P_2$ (Superior ou igual a 2,00 m² e inferior a 2,30 m²)
    * $N_3 = 0.25 \times P_3$ (Superior ou igual a 1,50 m² e inferior a 2,00 m²)
    * $N_4 = 0.0 \times P_4$ (Inferior a 1,50 m²)
    * $NF = P_{máx} \times (N_1 + N_2 + N_3 + N_4)$ *onde $P_i$ é a proporção de turmas em cada faixa.*
    """)
    st.caption("ℹ️ *O somatório e o cálculo atualizam automaticamente a cada clique ou mudança de foco.*")
    
    d13_dados = res_data.get("1.3", {"valor": "F1:0,F2:0,F3:0,F4:0", "pontos": 0.0, "link": ""})
    v_banco_13 = d13_dados.get("valor", "F1:0,F2:0,F3:0,F4:0")
    v_link_13 = d13_dados.get("link", "")
    v_pontos_13 = float(d13_dados.get("pontos", 0.0))
    
    try:
        parts_13 = v_banco_13.split(",")
        init_f1 = parts_13[0].split(":")[1]
        init_f2 = parts_13[1].split(":")[1]
        init_f3 = parts_13[2].split(":")[1]
        init_f4 = parts_13[3].split(":")[1]
    except Exception:
        init_f1, init_f2, init_f3, init_f4 = "0", "0", "0", "0"
        
    # Inicialização segura dos estados no session_state contra quebras
    key_f1_13 = f"txt_q13_f1_val_{ano_sel}"
    if key_f1_13 not in st.session_state: st.session_state[key_f1_13] = init_f1

    key_f2_13 = f"txt_q13_f2_val_{ano_sel}"
    if key_f2_13 not in st.session_state: st.session_state[key_f2_13] = init_f2

    key_f3_13 = f"txt_q13_f3_val_{ano_sel}"
    if key_f3_13 not in st.session_state: st.session_state[key_q13_f3] = init_f3

    key_f4_13 = f"txt_q13_f4_val_{ano_sel}"
    if key_f4_13 not in st.session_state: st.session_state[key_f4_13] = init_f4

    key_link_13 = f"link_q13_txt_val_{ano_sel}"
    if key_link_13 not in st.session_state: st.session_state[key_link_13] = v_link_13

    # PROCESSAMENTO MATEMÁTICO UNIFICADO COM CALLBACK
    def processar_e_salvar_13():
        # Limpeza robusta das strings de entrada antes de converter
        def extrair_inteiro(valor):
            if not valor:
                return 0
            val_limpo = re.sub(r'\D', '', str(valor).strip())
            return int(val_limpo) if val_limpo else 0

        int_f1 = extrair_inteiro(st.session_state[key_f1_13])
        int_f2 = extrair_inteiro(st.session_state[key_f2_13])
        int_f3 = extrair_inteiro(st.session_state[key_f3_13])
        int_f4 = extrair_inteiro(st.session_state[key_f4_13])
            
        total_turmas = int_f1 + int_f2 + int_f3 + int_f4
        
        if total_turmas > 0:
            p1 = int_f1 / total_turmas
            p2 = int_f2 / total_turmas
            p3 = int_f3 / total_turmas
            pts_calculados = min(10.0, round(10.0 * (p1 + (0.5 * p2) + (0.25 * p3)), 2))
        else:
            pts_calculados = 0.0
            
        str_valor_novo = f"F1:{int_f1},F2:{int_f2},F3:{int_f3},F4:{int_f4}"
        link_atual = st.session_state[key_link_13]
        
        if str_valor_novo != v_banco_13 or link_atual != v_link_13 or v_pontos_13 != pts_calculados:
            if link_atual != v_link_13:
                links_f13 = re.findall(r'(https?://[^\s]+)', link_atual)
                links_13_antigos = re.findall(r'(https?://[^\s]+)', v_link_13)
                if links_f13 and links_f13 != links_13_antigos:
                    st.session_state[f"trigger_modal_13_{ano_sel}"] = True
                    
            save_resp("1.3", str_valor_novo, float(pts_calculados), link_atual)
            res_data["1.3"] = {"valor": str_valor_novo, "pontos": float(pts_calculados), "link": link_atual}

    col_q1, col_q2 = st.columns([1, 1])
    with col_q1:
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Superior ou igual a 2,30 m² por aluno:</label>', unsafe_allow_html=True)
        st.text_input("", key=key_f1_13, placeholder="Quantidade de turmas", on_change=processar_e_salvar_13, label_visibility="collapsed")
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Superior ou igual a 2,00 m² e inferior a 2,30 m² por aluno:</label>', unsafe_allow_html=True)
        st.text_input("", key=key_f2_13, placeholder="Quantidade de turmas", on_change=processar_e_salvar_13, label_visibility="collapsed")
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Superior ou igual a 1,50 m² e inferior a 2,00 m² por aluno:</label>', unsafe_allow_html=True)
        st.text_input("", key=key_f3_13, placeholder="Quantidade de turmas", on_change=processar_e_salvar_13, label_visibility="collapsed")
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Inferior a 1,50 m² por aluno:</label>', unsafe_allow_html=True)
        st.text_input("", key=key_f4_13, placeholder="Quantidade de turmas", on_change=processar_e_salvar_13, label_visibility="collapsed")
        
    with col_q2:
        l13 = st.text_area(f"Link/Evidência (1.3) - {ano_sel}:", key=key_link_13, on_change=processar_e_salvar_13, height=295)
        links_ativos_13 = re.findall(r'(https?://[^\s]+)', l13)
        botoes_13 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_ativos_13]) if links_ativos_13 else "Nenhum link ativo"
        st.markdown(f"**Links Ativos:** {botoes_13}")

    # Geração do feedback visual reativo baseado no session_state de maneira segura
    def extrair_inteiro_visual(valor):
        if not valor:
            return 0
        val_limpo = re.sub(r'\D', '', str(valor).strip())
        return int(val_limpo) if val_limpo else 0

    c_f1 = extrair_inteiro_visual(st.session_state[key_f1_13])
    c_f2 = extrair_inteiro_visual(st.session_state[key_f2_13])
    c_f3 = extrair_inteiro_visual(st.session_state[key_f3_13])
    c_f4 = extrair_inteiro_visual(st.session_state[key_f4_13])
        
    c_total = c_f1 + c_f2 + c_f3 + c_f4
    if c_total > 0:
        cp1 = c_f1 / c_total
        cp2 = c_f2 / c_total
        cp3 = c_f3 / c_total
        c_pts = min(10.0, round(10.0 * (cp1 + (0.5 * cp2) + (0.25 * cp3)), 2))
        st.code(f"📊 Total: {c_total} turmas apuradas ➡️ Nota Ponderada Calculada: {c_pts:.2f} / 10.00 pontos.", language="text")
    else:
        st.code("💡 Insira a quantidade de turmas nas faixas correspondentes para calcular a pontuação ponderada.", language="text")

    # Execução segura do modal automático
    if st.session_state.get(f"trigger_modal_13_{ano_sel}", False):
        st.session_state[f"trigger_modal_13_{ano_sel}"] = False
        modal_aviso_link("1.3", re.findall(r'(https?://[^\s]+)', l13))

    bloco_comentarios("1.3", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# --- QUESITO 1.4 - FORMAÇÃO DOS PROFESSORES DE CRECHE (IEDUC) ---
with st.expander("🔍 QUESITO 1.4 - Formação dos Professores de Creche", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.4")
    st.write("**Informe os dados sobre a formação dos professores regentes de Creche (Efetivos e Temporários - Censo Escolar):**")
    st.markdown("""
    *Regras de Pontuação ($Pmáx = 18$ pontos):*
    * **N1 (Licenciatura - G):** $100\\% = 11$ pts | $90\\%$ a $99.9\\% = 7$ pts | $80\\%$ a $89.9\\% = 3$ pts | $70\\%$ a $79.9\\% = 1$ pt | $< 70\\% = 0$ pts
    * **N2 (Pós-Graduação - P):** $\ge 50\\% = 7$ pts | $40\\%$ a $49.9\\% = 5$ pts | $20\\%$ a $39.9\\% = 3$ pts | $< 20\\% = 0$ pts
    * **Nota Final:** $NF = N1 + N2$
    """)
    st.caption("ℹ️ *Os cálculos e salvamento ocorrem em tempo real ao alterar os valores.*")
    
    d14 = res_data.get("1.4", {"valor": "GRAD:0,PGRAD:0,TOTAL:0", "pontos": 0.0, "link": ""})
    v_banco_14 = d14.get("valor", "GRAD:0,PGRAD:0,TOTAL:0")
    v_link_14 = d14.get("link", "")
    
    # Tratamento seguro de split para ler os dados do banco
    try:
        parts_14 = v_banco_14.split(",")
        v_grad = 0
        v_pgrad = 0
        v_total = 0
        for part in parts_14:
            if "GRAD" in part and "PGRAD" not in part: v_grad = int(part.split(":")[1])
            if "PGRAD" in part: v_pgrad = int(part.split(":")[1])
            if "TOTAL" in part: v_total = int(part.split(":")[1])
    except:
        v_grad, v_pgrad, v_total = 0, 0, 0

    # Definição das chaves do Session State
    k_grad = f"q14_grad_{ano_sel}"
    k_total = f"q14_total_manual_{ano_sel}"
    k_pgrad = f"q14_pgrad_{ano_sel}"
    k_link = f"link_q14_txt_val_{ano_sel}"

    if k_grad not in st.session_state: st.session_state[k_grad] = v_grad
    if k_total not in st.session_state: st.session_state[k_total] = v_total
    if k_pgrad not in st.session_state: st.session_state[k_pgrad] = v_pgrad
    if k_link not in st.session_state: st.session_state[k_link] = v_link_14

    # Função interna para cálculo dinâmico da nota matemática
    def calcular_nota_com_valores(g_val, t_val, p_val):
        if t_val <= 0:
            return 0.0
        
        # N1 (Graduação) - g_perc limitado ao máximo de 1.0 (100%) para evitar distorções
        g_perc = min(1.0, g_val / t_val)
        if g_perc >= 1.0: n1 = 11.0
        elif g_perc >= 0.90: n1 = 7.0
        elif g_perc >= 0.80: n1 = 3.0
        elif g_perc >= 0.70: n1 = 1.0
        else: n1 = 0.0
        
        # N2 (Pós-Graduação)
        p_perc = min(1.0, p_val / t_val)
        if p_perc >= 0.50: n2 = 7.0
        elif p_perc >= 0.40: n2 = 5.0
        elif p_perc >= 0.20: n2 = 3.0
        else: n2 = 0.0
        
        return float(n1 + n2)

    # Callback unificado de salvamento disparado nos Inputs
    def callback_atualiza_q14():
        # 💡 AJUSTADO: Uso consistente do .get() com valores padrões seguros contra KeyError
        g_at = st.session_state.get(k_grad, 0)
        t_at = st.session_state.get(k_total, 0)
        p_at = st.session_state.get(k_pgrad, 0)
        lk_at = st.session_state.get(k_link, "")
        
        str_novo = f"GRAD:{g_at},PGRAD:{p_at},TOTAL:{t_at}"
        pts_novo = calcular_nota_com_valores(g_at, t_at, p_at)
        
        save_resp("1.4", str_novo, pts_novo, lk_at)
        res_data["1.4"] = {"valor": str_novo, "pontos": pts_novo, "link": lk_at}

    # Callback específico do link para disparar o Modal se houver nova URL
    def callback_link_q14():
        novo_link = st.session_state[k_link]
        if novo_link != v_link_14:
            callback_atualiza_q14()
            links_f14 = re.findall(r'(https?://[^\s]+)', novo_link)
            links_antigos = re.findall(r'(https?://[^\s]+)', v_link_14)
            if links_f14 and links_f14 != links_antigos:
                st.session_state[f"trigger_modal_14_{ano_sel}"] = True

    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Total de Professores Regentes de Creche (Censo Escolar):</label>', unsafe_allow_html=True)
        st.number_input("", min_value=0, step=1, key=k_total, label_visibility="collapsed", on_change=callback_atualiza_q14)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Professores que possuem formação superior em LICENCIATURA (GRAD):</label>', unsafe_allow_html=True)
        st.number_input("", min_value=0, step=1, key=k_grad, label_visibility="collapsed", on_change=callback_atualiza_q14)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500; color: #10B981;">Deste total, quantos possuem PÓS-GRADUAÇÃO (PGRAD):</label>', unsafe_allow_html=True)
        st.number_input("", min_value=0, step=1, key=k_pgrad, label_visibility="collapsed", on_change=callback_atualiza_q14)

    with col_m2:
        l14 = st.text_area("Link/Evidência (1.4):", key=k_link, on_change=callback_link_q14, height=210)
        links_ativos_14 = re.findall(r'(https?://[^\s]+)', l14)
        botoes_14 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_ativos_14]) if links_ativos_14 else "Nenhum link ativo"
        st.markdown(f"**Links:** {botoes_14}")
        
    pts_exibir = calcular_nota_com_valores(st.session_state[k_grad], st.session_state[k_total], st.session_state[k_pgrad])
    st.code(f"📊 Pontuação Calculada no Quesito 1.4: {pts_exibir:.2f} pontos / 18.0 pontos máximos.", language="text")

    if st.session_state.get(f"trigger_modal_14_{ano_sel}", False):
        st.session_state[f"trigger_modal_14_{ano_sel}"] = False
        modal_aviso_link("1.4", re.findall(r'(https?://[^\s]+)', l14))
            
    bloco_comentarios("1.4", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.5 - PISO SALARIAL DOS PROFESSORES DE CRECHE (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.5 - Piso Salarial dos Professores de Creche", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### QUESITO 1.5")
    st.write("**Qual o piso salarial mensal dos professores de Creche no município?**")
    st.write("*Considerar o piso base proporcional para uma jornada de 40 horas semanais.*")
    st.markdown("""
    *Regras de Validação ($Pmáx = 0$ pontos - Penalização Crítica):*
    * **Piso < Salário Mínimo:** $-20.0$ pontos (Penalização no bloco)
    * **Piso $\ge$ Salário Mínimo:** $0.0$ pontos (Sem penalização)
    """)
    st.caption("ℹ️ *O salvamento é automático. Qualquer alteração nos valores ou no link grava os dados na hora.*")
    
    # Recupera os dados salvos ou define o padrão em branco ("PISO:;MINIMO:")
    d15 = res_data.get("1.5", {"valor": "PISO:;MINIMO:", "pontos": 0.0, "link": ""})
    
    # Tratamento seguro para extrair os dois valores monetários (aceitando nulos)
    try:
        if ";" in d15["valor"]:
            parts_15 = d15["valor"].split(";")
            piso_str_salvo = parts_15[0].split(":")[1]
            minimo_str_salvo = parts_15[1].split(":")[1]
            
            v_piso = float(piso_str_salvo) if piso_str_salvo != "" else None
            v_minimo = float(minimo_str_salvo) if minimo_str_salvo != "" else None
        else:
            v_piso = float(d15["valor"]) if d15["valor"] != "" else None
            v_minimo = None
    except:
        v_piso = None
        v_minimo = None
        
    # Formatação visual brasileira (R$) ou string vazia para renderizar limpo na tela
    str_inicial_piso = f"R$ {v_piso:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if v_piso is not None else ""
    str_inicial_minimo = f"R$ {v_minimo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if v_minimo is not None else ""
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Valor do Salário Mínimo de Referência (R$):</label>', unsafe_allow_html=True)
        input_minimo_str = st.text_input("", value=str_inicial_minimo, placeholder="Ex: 1.512,00", key=f"txt_ieduc_15_min_{ano_sel}", label_visibility="collapsed")

        st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Valor do Piso Salarial base informado (R$):</label>', unsafe_allow_html=True)
        input_piso_str = st.text_input("", value=str_inicial_piso, placeholder="Ex: 4.580,57", key=f"txt_ieduc_15_piso_{ano_sel}", label_visibility="collapsed")
        
    with col2:
        l15 = st.text_area("Link/Evidência (1.5):", value=d15.get("link", ""), key=f"txt_ieduc_15_{ano_sel}", height=165)
        placeholder_links_15 = st.empty()
        links_f15 = re.findall(r'(https?://[^\s]+)', l15)
        if links_f15:
            botoes_15 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f15])
            placeholder_links_15.markdown(f"**Links Ativos:** {botoes_15}")
            
    # 🧹 Função para converter a string formatada em Float (ou None se vazio)
    def converte_monetario_15(texto):
        if not texto or texto.strip() == "":
            return None
        num_limpo = texto.replace("R$", "").replace(" ", "")
        if "." in num_limpo and "," in num_limpo:
            num_limpo = num_limpo.replace(".", "").replace(",", ".")
        elif "," in num_limpo:
            num_limpo = num_limpo.replace(",", ".")
        try:
            return float(num_limpo)
        except:
            return None

    piso_informado = converte_monetario_15(input_piso_str)
    salario_minimo_ref = converte_monetario_15(input_minimo_str)
    
    # Lógica dinâmica de aplicação da penalidade corrigida para aceitar nulos
    pts_15 = 0.0
    score_placeholder_15 = st.empty()
    
    if piso_informado is None or salario_minimo_ref is None:
        pts_15 = 0.0
        score_placeholder_15.markdown("⚠️ **Status:** `Aguardando preenchimento dos valores` (Insira o Piso e o Salário Mínimo)")
    else:
        if piso_informado < salario_minimo_ref:
            pts_15 = -20.0
            score_placeholder_15.markdown(f"🚨 **Alerta Urgente:** `Piso abaixo do Salário Mínimo` | **Penalização:** `{pts_15:.1f} pontos` (Piso: R$ {piso_informado:,.2f} < Mínimo: R$ {salario_minimo_ref:,.2f})")
        else:
            pts_15 = 0.0
            score_placeholder_15.markdown(f"📊 **Status do Quesito 1.5:** `Piso em conformidade legal` | **Pontuação:** `{pts_15:.1f} pontos` (Piso: R$ {piso_informado:,.2f} $\ge$ Mínimo: R$ {salario_minimo_ref:,.2f})")
        
    # Estrutura a string do banco preservando as lacunas vazias
    piso_banco_str = f"{piso_informado:.2f}" if piso_informado is not None else ""
    minimo_banco_str = f"{salario_minimo_ref:.2f}" if salario_minimo_ref is not None else ""
    str_valor_15 = f"PISO:{piso_banco_str};MINIMO:{minimo_banco_str}"
    
    mudou_opcao_15 = str_valor_15 != d15.get("valor", "")
    mudou_link_15 = l15 != d15.get("link", "")
    
    if mudou_opcao_15 or mudou_link_15:
        save_resp("1.5", str_valor_15, pts_15, l15)
        res_data["1.5"] = {"valor": str_valor_15, "pontos": pts_15, "link": l15}
        if mudou_link_15 and links_f15:
            links_15_antigos = re.findall(r'(https?://[^\s]+)', d15.get("link", ""))
            if links_f15 != links_15_antigos:
                modal_aviso_link("1.5", links_f15)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.5", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# QUESITO 1.6 - QUANTIDADE TOTAL DE AUSÊNCIA DOS PROFESSORES (IEDUC)
# =============================================================================
with st.expander("🔍 QUESITO 1.6 - Quantidade Total de Ausências (QTA)", expanded=True):
    st.markdown("#### QUESITO 1.6")
    st.write("**Informe a quantidade total (em dias) de ausência dos professores por faltas e afastamentos na etapa de Creche:**")
    st.write("*Considerar todos os dias de ausência dos professores regentes no ano base do Censo anterior.*")
    st.caption("ℹ️ *O somatório e o salvamento são automáticos a cada alteração.*")
    
    # Recupera os dados salvos ou define o padrão zerado
    d16 = res_data.get("1.6", {"valor": "INJ:0,JUST:0,MED:0,MAT:0,ABO:0,OUT:0,TOTAL:0", "pontos": 0.0, "link": ""})
    
    # Parse seguro das chaves internas
    try:
        parts_16 = d16["valor"].split(",")
        v_inj = int(parts_16[0].split(":")[1])
        v_just = int(parts_16[1].split(":")[1])
        v_med = int(parts_16[2].split(":")[1])
        v_mat = int(parts_16[3].split(":")[1])
        v_abo = int(parts_16[4].split(":")[1])
        v_out = int(parts_16[5].split(":")[1])
    except:
        v_inj, v_just, v_med, v_mat, v_abo, v_out = 0, 0, 0, 0, 0, 0

    # Chaves para controle do st.session_state
    k_inj = f"q16_inj_{ano_sel}"
    k_just = f"q16_just_{ano_sel}"
    k_med = f"q16_med_{ano_sel}"
    k_mat = f"q16_mat_{ano_sel}"
    k_abo = f"q16_abo_{ano_sel}"
    k_out = f"q16_out_{ano_sel}"
    k_tot_16 = f"q16_total_auto_{ano_sel}"

    # Função de callback para atualização imediata da soma total
    def recalcula_e_soma_16():
        soma = (
            int(st.session_state.get(k_inj, v_inj)) +
            int(st.session_state.get(k_just, v_just)) +
            int(st.session_state.get(k_med, v_med)) +
            int(st.session_state.get(k_mat, v_mat)) +
            int(st.session_state.get(k_abo, v_abo)) +
            int(st.session_state.get(k_out, v_out))
        )
        st.session_state[k_tot_16] = soma

    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Faltas Injustificadas (dias):</label>', unsafe_allow_html=True)
        inj = st.number_input("", min_value=0, step=1, value=v_inj, key=k_inj, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Faltas Justificadas (dias):</label>', unsafe_allow_html=True)
        just = st.number_input("", min_value=0, step=1, value=v_just, key=k_just, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Licença Médica / Tratamento de Saúde (dias):</label>', unsafe_allow_html=True)
        med = st.number_input("", min_value=0, step=1, value=v_med, key=k_med, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Licença Maternidade / Paternidade (dias):</label>', unsafe_allow_html=True)
        mat = st.number_input("", min_value=0, step=1, value=v_mat, key=k_mat, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Abonos / Faltas Abonadas (dias):</label>', unsafe_allow_html=True)
        abo = st.number_input("", min_value=0, step=1, value=v_abo, key=k_abo, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        st.markdown('<label style="font-size: 13px; font-weight: 500;">Outros (ausências pontuais / amparadas por lei em dias):</label>', unsafe_allow_html=True)
        out = st.number_input("", min_value=0, step=1, value=v_out, key=k_out, label_visibility="collapsed", on_change=recalcula_e_soma_16)
        
        # Controle e exibição do somatório automático (QTA)
        tot_ausencias = inj + just + med + mat + abo + out
        if k_tot_16 not in st.session_state:
            st.session_state[k_tot_16] = tot_ausencias
        else:
            tot_ausencias = st.session_state[k_tot_16]
            
        st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Quantidade Total de Ausências - QTA (Somatório):</label>', unsafe_allow_html=True)
        st.number_input("", value=int(tot_ausencias), disabled=True, key=k_tot_16, label_visibility="collapsed")

    with col_m2:
        l16 = st.text_area("Link/Evidência (1.6):", value=d16.get("link", ""), key=f"txt_ieduc_16_{ano_sel}", height=450)
        placeholder_links_16 = st.empty()
        links_f16 = re.findall(r'(https?://[^\s]+)', l16)
        if links_f16:
            botoes_16 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f16])
            placeholder_links_16.markdown(f"**Links Ativos:** {botoes_16}")
    
    # Dados estritamente informativos (Regras de pontuação dependem da matriz geral de servidores)
    pts_16 = 0.0
    score_placeholder_16 = st.empty()
    score_placeholder_16.markdown(f"📊 **Dados Consolidados no Quesito 1.6:** `{tot_ausencias} dias acumulados` (Dados Informativos)")
    
    str_valor_16 = f"INJ:{inj},JUST:{just},MED:{med},MAT:{mat},ABO:{abo},OUT:{out},TOTAL:{tot_ausencias}"
    
    mudou_opcao_16 = str_valor_16 != d16.get("valor", "")
    mudou_link_16 = l16 != d16.get("link", "")
    
    if mudou_opcao_16 or mudou_link_16:
        save_resp("1.6", str_valor_16, pts_16, l16)
        res_data["1.6"] = {"valor": str_valor_16, "pontos": pts_16, "link": l16}
        if mudou_link_16 and links_f16:
            links_16_antigos = re.findall(r'(https?://[^\s]+)', d16.get("link", ""))
            if links_f16 != links_16_antigos:
                modal_aviso_link("1.6", links_f16)
            else:
                st.rerun()
        else:
            st.rerun()
            
    bloco_comentarios("1.6", res_data, ano_sel)

# =============================================================================
# QUESITO 1.7 - CURSOS DE CAPACITAÇÃO DOS PROFISSIONAIS (CRECHE)
# =============================================================================
with st.expander(f"🔍 QUESITO 1.7 - Cursos de Capacitação - Creche ({ano_sel})", expanded=True):
    st.markdown("#### QUESITO 1.7")
    st.write(f"**Os profissionais de Creche da rede municipal participaram de cursos de capacitação durante o ano de {ano_sel}?**")
    st.caption("ℹ️ *O salvamento é automático ao alterar as opções.*")
    
    d17 = res_data.get("1.7", {"valor": "", "pontos": 0, "link": ""})
    opc17 = ["Sim", "Não"]
    idx17 = opc17.index(d17["valor"]) if d17["valor"] in opc17 else None
    
    col_l1, col_l2 = st.columns([1, 2])
    with col_l1:
        r17 = st.radio(f"Selecione 1.7 ({ano_sel}):", opc17, index=idx17, key=f"q17_{ano_sel}")
    
    with col_l2:
        l17 = st.text_area(f"Link/Evidência (1.7) - {ano_sel}:", value=d17.get("link", ""), key=f"l17_txt_{ano_sel}", height=100)
        placeholder_links_17 = st.empty()
        links_f17 = re.findall(r'(https?://[^\s]+)', l17)
        if links_f17:
            botoes_17 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f17])
            placeholder_links_17.markdown(f"**Links Ativos:** {botoes_17}")
            
    # COMPARAÇÃO E SALVAMENTO BLINDADO CONTRA LOOPING
    mudou_opcao_17 = r17 and r17 != d17["valor"]
    mudou_link_17 = l17 != d17["link"]
    
    if mudou_opcao_17 or mudou_link_17:
        pts17 = 0  # Correção: Este quesito não possui pontuação (Sempre salva 0)
        save_resp("1.7", r17, pts17, l17)
        res_data["1.7"] = {"valor": r17, "pontos": pts17, "link": l17}
        
        # Intercepta e dispara o modal se houver alteração real de links válidos
        if mudou_link_17 and links_f17:
            links_17_antigos = re.findall(r'(https?://[^\s]+)', d17.get("link", ""))
            if links_f17 != links_17_antigos:
                modal_aviso_link("1.7", links_f17)
            else:
                st.rerun()
        else:
            st.rerun()
            
    # 💡 AJUSTADO: Passando ano_sel para o bloco_comentarios evitar TypeError
    bloco_comentarios("1.7", res_data, ano_sel)

# =============================================================================
# QUESITO 1.7.1 • Capacitação de Profissionais da Educação Infantil (Creche)
# =============================================================================
with st.expander(f"🔍 QUESITO 1.7.1 - Capacitação de Profissionais da Educação Infantil (Creche)", expanded=True):
    st.markdown('<div class="quesito-card">', unsafe_allow_html=True)
    st.markdown("#### 🎒 QUESITO 1.7.1")
    st.write(f"**Informe a quantidade de profissionais de Creche capacitados em {ano_sel}:**")
    st.caption("⚠️ *Nota: Não contar o mesmo profissional mais de uma vez, mesmo que tenha participado de vários cursos.*")
    
    # 📐 Fórmula de cálculo oficial baseada no i-Educa / IEGM
    st.latex(r"PC = \frac{\text{Prof.Capacitados} + \text{Apoio.Capacitados} + \text{Gestores.Capacitados}}{\text{Total.Prof} + \text{Total.Apoio} + \text{Total.Gestores}}")

    # Recuperação estruturada do banco de dados
    d171 = res_data.get("1.7.1", {"valor": "PCAP:0,ACAP:0,GCAP:0,TGEST:0,TPROF:0,TAPOI:0", "pontos": 0, "link": ""})
    
    try:
        parts_171 = d171["valor"].split(",")
        v_pcap = int(parts_171[0].split(":")[1])
        v_acap = int(parts_171[1].split(":")[1])
        v_gcap = int(parts_171[2].split(":")[1])
        v_tgest = int(parts_171[3].split(":")[1])
        v_tprof = int(parts_171[4].split(":")[1]) if len(parts_171) > 4 else 0
        v_tapoi = int(parts_171[5].split(":")[1]) if len(parts_171) > 5 else 0
    except:
        v_pcap, v_acap, v_gcap, v_tgest, v_tprof, v_tapoi = 0, 0, 0, 0, 0, 0

    # 💡 AJUSTADO: Alinhando o nome da chave para buscar o total correto do quesito 1.4 ("q14_total_manual_...")
    if v_tprof == 0 and f"q14_total_manual_{ano_sel}" in st.session_state:
        v_tprof = st.session_state[f"q14_total_manual_{ano_sel}"]

    col_n1, col_n2 = st.columns([1, 2])
    
    with col_n1:
        st.markdown("##### 📝 Profissionais Capacitados")
        pcap = st.number_input("Professores regentes que participaram de cursos:", min_value=0, step=1, value=v_pcap, key=f"q171_pcap_{ano_sel}")
        acap = st.number_input("Profissionais de apoio/supervisão que participaram de cursos:", min_value=0, step=1, value=v_acap, key=f"q171_acap_{ano_sel}")
        gcap = st.number_input("Gestores escolares que participaram de cursos:", min_value=0, step=1, value=v_gcap, key=f"q171_gcap_{ano_sel}")
        
        st.markdown("##### 📊 Total do Quadro de Funcionários")
        tprof = st.number_input("Total de professores regentes da etapa:", min_value=0, step=1, value=v_tprof, key=f"q171_tprof_{ano_sel}")
        tapoi = st.number_input("Total de profissionais de apoio e supervisão:", min_value=0, step=1, value=v_tapoi, key=f"q171_tapoi_{ano_sel}")
        tgest = st.number_input("Total de gestores escolares de creche:", min_value=0, step=1, value=v_tgest, key=f"q171_tgest_{ano_sel}")

    with col_n2:
        l171 = st.text_area(f"Link/Evidência de comprovação das capacitações (1.7.1) - {ano_sel}:", value=d171.get("link", ""), key=f"l171_txt_{ano_sel}", height=410)
        placeholder_links_171 = st.empty()
        links_f171 = re.findall(r'(https?://[^\s]+)', l171)
        if links_f171:
            botoes_171 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f171])
            placeholder_links_171.markdown(f"**Links Ativos:** {botoes_171}")

    # Volumetria totalizadora das linhas informadas
    total_capacitados = pcap + acap + gcap
    total_geral_quadro = tprof + tapoi + tgest

    pc_pct = 0.0
    pts171 = 0

    if total_geral_quadro > 0:
        calculo_bruto = (total_capacitados / total_geral_quadro) * 100
        pc_pct = min(calculo_bruto, 100.0)
        
        if calculo_bruto >= 100.0:
            pts171 = 7
            status_desc = "🥇 EXCELÊNCIA: Capacitação universal ou acima do quadro permanente"
        elif 70.0 <= pc_pct < 100.0:
            pts171 = 5
            status_desc = "🟢 ALTO ÍNDICE: Ótimo aproveitamento de formação continuada"
        elif 50.0 <= pc_pct < 70.0:
            pts171 = 3
            status_desc = "🟡 REGULAR: Índice intermediário de capacitação pedagógica"
        else:
            pts171 = 0
            status_desc = "❌ CRÍTICO: Baixo envolvimento em programas de formação continuada"
    else:
        status_desc = "⏳ Aguardando a inserção dos dados do quadro de funcionários."

    str_valor_171 = f"PCAP:{pcap},ACAP:{acap},GCAP:{gcap},TGEST:{tgest},TPROF:{tprof},TAPOI:{tapoi}"
    
    # COMPARAÇÃO E SALVAMENTO BLINDADO CONTRA LOOPING
    mudou_opcao_171 = str_valor_171 != d171["valor"]
    mudou_link_171 = l171 != d171["link"]

    if mudou_opcao_171 or mudou_link_171:
        save_resp("1.7.1", str_valor_171, float(pts171), l171)
        res_data["1.7.1"] = {"valor": str_valor_171, "pontos": float(pts171), "link": l171}
        
        if mudou_link_171 and links_f171:
            links_171_antigos = re.findall(r'(https?://[^\s]+)', d171.get("link", ""))
            if links_f171 != links_171_antigos:
                modal_aviso_link("1.7.1", links_f171)
            else:
                st.rerun()
        else:
            st.rerun()

    pct_exibicao = f"{calculo_bruto:.1f}%" if total_geral_quadro > 0 else "0,0%"
    st.info(f"📊 **Métrica Consolidada:** Cobertura de {pct_exibicao} ({total_capacitados} capacitados de {total_geral_quadro} no quadro) | **Status:** {status_desc} | **Pontuação:** {pts171} pontos")
    
    # 💡 AJUSTADO: Passando ano_sel para o bloco_comentarios evitar TypeError
    bloco_comentarios("1.7.1", res_data, ano_sel)
    st.markdown('</div>', unsafe_allow_html=True)

        # =============================================================================
        # QUESITO 1.7.2 - FORMA DE CAPACITAÇÃO (IEDUC)
        # =============================================================================
        with st.expander(f"🔍 QUESITO 1.7.2 - Formas de Capacitação ({ano_sel})", expanded=True):
            st.markdown("#### QUESITO 1.7.2")
            st.write(f"**Assinale as formas de capacitação utilizadas durante o ano de {ano_sel}:**")
            st.write("*Marque todas as alternativas que foram aplicadas no município.*")
            st.caption("ℹ️ *O salvamento das opções marcadas é automático.*")
            
            # Recupera os dados salvos ou define o padrão como tudo falso/desmarcado
            d172 = res_data.get("1.7.2", {"valor": "PRES:0,DIST:0,MULT:0,OUT:0", "pontos": 0.0, "link": ""})
            
            # Parse seguro para ler os booleanos salvos anteriormente (0 para Falso, 1 para Verdadeiro)
            try:
                parts_172 = d172["valor"].split(",")
                v_pres = parts_172[0].split(":")[1] == "1"
                v_dist = parts_172[1].split(":")[1] == "1"
                v_mult = parts_172[2].split(":")[1] == "1"
                v_out  = parts_172[3].split(":")[1] == "1"
            except:
                v_pres, v_dist, v_mult, v_out = False, False, False, False

            col_m1, col_m2 = st.columns([1, 1])
            with col_m1:
                st.markdown(f'<label style="font-size: 13px; font-weight: 500;">Selecione os métodos aplicados em {ano_sel}:</label>', unsafe_allow_html=True)
                
                # Renderização dos Checkboxes com seus respectivos estados recuperados
                check_pres = st.checkbox("Presencialmente", value=v_pres, key=f"chk_q172_pres_{ano_sel}")
                check_dist = st.checkbox("À distância / remotamente", value=v_dist, key=f"chk_q172_dist_{ano_sel}")
                check_mult = st.checkbox("Por meio de multiplicadores", value=v_mult, key=f"chk_q172_mult_{ano_sel}")
                check_out  = st.checkbox("Outros", value=v_out, key=f"chk_q172_out_{ano_sel}")

            with col_m2:
                l172 = st.text_area(f"Link/Evidência (1.7.2 - {ano_sel}):", value=d172.get("link", ""), key=f"txt_ieduc_172_{ano_sel}", height=180)
                placeholder_links_172 = st.empty()
                links_f172 = re.findall(r'(https?://[^\s]+)', l172)
                if links_f172:
                    botoes_172 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f172])
                    placeholder_links_172.markdown(f"**Links Ativos:** {botoes_172}")
            
            # Mapeamento visual das opções escolhidas para a exibição do status
            escolhas = []
            if check_pres: escolhas.append("Presencialmente")
            if check_dist: escolhas.append("À distância")
            if check_mult: escolhas.append("Multiplicadores")
            if check_out:  escolhas.append("Outros")
            
            pts_172 = 0.0
            score_placeholder_172 = st.empty()
            if escolhas:
                score_placeholder_172.markdown(f" 📊 **Formatos Assinalados ({ano_sel}):** {', '.join(escolhas)} (Dados Informativos)")
            else:
                score_placeholder_172.markdown("⚠️ **Status:** `Nenhuma forma de capacitação selecionada`")
                
            # Converte os booleanos em formato string binária estruturada para gravação estável
            str_valor_172 = f"PRES:{1 if check_pres else 0},DIST:{1 if check_dist else 0},MULT:{1 if check_mult else 0},OUT:{1 if check_out else 0}"
            
            mudou_opcao_172 = str_valor_172 != d172.get("valor", "")
            mudou_link_172 = l172 != d172.get("link", "")
            
            if mudou_opcao_172 or mudou_link_172:
                save_resp("1.7.2", str_valor_172, pts_172, l172)
                res_data["1.7.2"] = {"valor": str_valor_172, "pontos": pts_172, "link": l172}
                if mudou_link_172 and links_f172:
                    links_172_antigos = re.findall(r'(https?://[^\s]+)', d172.get("link", ""))
                    if links_f172 != links_172_antigos:
                        modal_aviso_link("1.7.2", links_f172)
                    else:
                        st.rerun()
                else:
                    st.rerun()
                    
            bloco_comentarios("1.7.2", res_data, ano_sel)

        # =============================================================================
        # QUESITO 1.8 - REGULARIDADE E ROTATIVIDADE DO CORPO DOCENTE (IEDUC)
        # =============================================================================
        with st.expander(f"🔍 QUESITO 1.8 - Rotatividade de Professores de Creche ({ano_sel})", expanded=True):
            st.markdown("#### QUESITO 1.8")
            st.write(f"**Informe o número de escolas em cada faixa de rotatividade de professores de Creche em {ano_sel}:**")
            st.markdown("""
            *Regras de Cálculo ($Pmáx = 3$ pontos):*
            * $$NF = Pmáx \\times (N1 + N2 + N3 + N4)$$
            * **N1 (Rotatividade < 20%):** $3 \\times Q1$
            * **N2 (Rotatividade entre 20% e 29.9%):** $2 \\times Q2$
            * **N3 (Rotatividade entre 30% e 39.9%):** $1 \\times Q3$
            * **N4 (Rotatividade $\ge$ 40%):** $0 \\times Q4$
            * *Onde $Qi$ é a proporção (Escolas da Faixa / Total de Escolas).*
            """)
            st.caption("ℹ️ *O cálculo ponderado e o salvamento são automáticos.*")
            
            # Recupera os dados salvos ou define a string padrão estruturada
            d18 = res_data.get("1.8", {"valor": "F1:0,F2:0,F3:0,F4:0,TOTAL:0", "pontos": 0.0, "link": ""})
            
            # Parse seguro das quantidades de escolas em cada uma das 4 faixas
            try:
                parts_18 = d18["valor"].split(",")
                v_f1 = int(parts_18[0].split(":")[1])
                v_f2 = int(parts_18[1].split(":")[1])
                v_f3 = int(parts_18[2].split(":")[1])
                v_f4 = int(parts_18[3].split(":")[1])
            except:
                v_f1, v_f2, v_f3, v_f4 = 0, 0, 0, 0

            # Chaves estáveis do session_state ligadas ao ano selecionado
            k_f1 = f"q18_f1_{ano_sel}"
            k_f2 = f"q18_f2_{ano_sel}"
            k_f3 = f"q18_f3_{ano_sel}"
            k_f4 = f"q18_f4_{ano_sel}"
            k_tot_18 = f"q18_total_auto_{ano_sel}"

            # Função de callback para somar o número total de escolas instantaneamente
            def recalcula_e_soma_18():
                soma = (
                    int(st.session_state.get(k_f1, v_f1)) +
                    int(st.session_state.get(k_f2, v_f2)) +
                    int(st.session_state.get(k_f3, v_f3)) +
                    int(st.session_state.get(k_f4, v_f4))
                )
                st.session_state[k_tot_18] = soma

            col_m1, col_m2 = st.columns([1, 1])
            with col_m1:
                st.markdown('<label style="font-size: 13px; font-weight: 500;">N° de Escolas com rotatividade <b>Menor que 20%</b> (F1):</label>', unsafe_allow_html=True)
                f1 = st.number_input("", min_value=0, step=1, value=v_f1, key=k_f1, label_visibility="collapsed", on_change=recalcula_e_soma_18)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">N° de Escolas com rotatividade <b>$\ge$ 20% e < 30%</b> (F2):</label>', unsafe_allow_html=True)
                f2 = st.number_input("", min_value=0, step=1, value=v_f2, key=k_f2, label_visibility="collapsed", on_change=recalcula_e_soma_18)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">N° de Escolas com rotatividade <b>$\ge$ 30% e < 40%</b> (F3):</label>', unsafe_allow_html=True)
                f3 = st.number_input("", min_value=0, step=1, value=v_f3, key=k_f3, label_visibility="collapsed", on_change=recalcula_e_soma_18)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">N° de Escolas com rotatividade <b>$\ge$ 40%</b> (F4):</label>', unsafe_allow_html=True)
                f4 = st.number_input("", min_value=0, step=1, value=v_f4, key=k_f4, label_visibility="collapsed", on_change=recalcula_e_soma_18)
                
                # Controle e exibição do somatório de escolas
                total_escolas = f1 + f2 + f3 + f4
                if k_tot_18 not in st.session_state:
                    st.session_state[k_tot_18] = total_escolas
                else:
                    total_escolas = st.session_state[k_tot_18]
                    
                st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Total de Escolas Consideradas (Somatório):</label>', unsafe_allow_html=True)
                st.number_input("", value=int(total_escolas), disabled=True, key=k_tot_18, label_visibility="collapsed")

            with col_m2:
                l18 = st.text_area(f"Link/Evidência (1.8 - {ano_sel}):", value=d18.get("link", ""), key=f"txt_ieduc_18_{ano_sel}", height=340)
                placeholder_links_18 = st.empty()
                links_f18 = re.findall(r'(https?://[^\s]+)', l18)
                if links_f18:
                    botoes_18 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f18])
                    placeholder_links_18.markdown(f"**Links Ativos:** {botoes_18}")
            
            # --- LÓGICA DE CÁLCULO PONDERADO ---
            pts_18 = 0.0
            score_placeholder_18 = st.empty()
            
            if total_escolas > 0:
                # Proporções (Qi)
                q1 = f1 / total_escolas
                q2 = f2 / total_escolas
                q3 = f3 / total_escolas
                q4 = f4 / total_escolas
                
                # Notas por faixa (Ni)
                n1 = 3.0 * q1
                n2 = 2.0 * q2
                n3 = 1.0 * q3
                n4 = 0.0 * q4
                
                # Nota Final aplicando o multiplicador Pmáx (3)
                # OBS: Conforme regras do IEDUC para fórmulas baseadas em índices de distribuição (onde a soma dos pesos Ni simula a nota de 0 a 1), 
                # a nota final ponderada resulta diretamente do somatório multiplicado por Pmáx / 3 (normalizador) ou apenas a média direta.
                # Para seguir estritamente o manual: NF = 3 * ((3*q1 + 2*q2 + 1*q3 + 0*q4) / 3) -> simplifica para o próprio somatório de pontos.
                pts_18 = float(n1 + n2 + n3 + n4)
                
                score_placeholder_18.markdown(
                    f"📊 **Proporções Calculadas:** $Q_1$=`{q1*100:.1f}%` | $Q_2$=`{q2*100:.1f}%` | $Q_3$=`{q3*100:.1f}%` | $Q_4$=`{q4*100:.1f}%`<br>"
                    f"✨ **Nota Final do Quesito 1.8:** `{pts_18:.2f} pontos` (Máximo: 3.0 pontos)", 
                    unsafe_allow_html=True
                )
            else:
                score_placeholder_18.markdown("⚠️ **Status:** `Aguardando a inserção do número de escolas para calcular a Nota Final`")
                
            str_valor_18 = f"F1:{f1},F2:{f2},F3:{f3},F4:{f4},TOTAL:{total_escolas}"
            
            mudou_opcao_18 = str_valor_18 != d18.get("valor", "")
            mudou_link_18 = l18 != d18.get("link", "")
            
            if mudou_opcao_18 or mudou_link_18:
                save_resp("1.8", str_valor_18, pts_18, l18)
                res_data["1.8"] = {"valor": str_valor_18, "pontos": pts_18, "link": l18}
                if mudou_link_18 and links_f18:
                    links_18_antigos = re.findall(r'(https?://[^\s]+)', d18.get("link", ""))
                    if links_f18 != links_18_antigos:
                        modal_aviso_link("1.8", links_f18)
                    else:
                        st.rerun()
                else:
                    st.rerun()
                    
            bloco_comentarios("1.8", res_data, ano_sel)

        # =============================================================================
        # QUESITO 1.9 - REGULARIDADE DE GESTORES (IEDUC)
        # =============================================================================
        with st.expander(f"🔍 QUESITO 1.9 - Regularidade de Gestores ({ano_sel})", expanded=True):
            st.markdown("#### 1.9")
            st.write(f"**Quanto a regularidade de gestores, indique a quantidade de escolas municipais cujo diretor/gestor de Creche, ao final de {ano_sel}, permanecia à frente da mesma unidade por:**")
            st.markdown("""
            *Fórmula de cálculo:*
            * $$NF = (N1 + N2 + N3 + N4 + N5 + N6)$$
            * **N1 = 0 x Q1** (Menor que 1 ano)
            * **N2 = 0,5 x Q2** (Maior ou igual a 1 ano e menor que 3 anos)
            * **N3 = 1 x Q3** (Maior ou igual a 3 anos e menor que 5 anos)
            * **N4 = 1,5 x Q4** (Maior ou igual a 5 anos e menor que 10 anos)
            * **N5 = 1,75 x Q5** (Maior ou igual a 10 anos e menor que 15 anos)
            * **N6 = 2 x Q6** (Maior ou igual a 15 anos)
            
            *Legenda: Ni = Nota obtida por cada faixa de porcentagem | Qi = Proporção de escolas em cada faixa | NF = Nota final do quesito*
            * $Pmáx = 2$ pontos
            """)
            st.caption("ℹ️ *O cálculo ponderado e o salvamento são automáticos a cada alteração.*")
            
            # Recupera os dados salvos ou define o padrão zerado com as 6 faixas
            d19 = res_data.get("1.9", {"valor": "F1:0,F2:0,F3:0,F4:0,F5:0,F6:0,TOTAL:0", "pontos": 0.0, "link": ""})
            
            # Parse seguro das quantidades de escolas em cada uma das 6 faixas
            try:
                parts_19 = d19["valor"].split(",")
                v_f1 = int(parts_19[0].split(":")[1])
                v_f2 = int(parts_19[1].split(":")[1])
                v_f3 = int(parts_19[2].split(":")[1])
                v_f4 = int(parts_19[3].split(":")[1])
                v_f5 = int(parts_19[4].split(":")[1])
                v_f6 = int(parts_19[5].split(":")[1])
            except:
                v_f1, v_f2, v_f3, v_f4, v_f5, v_f6 = 0, 0, 0, 0, 0, 0

            # CHAVES EXCLUSIVAS PARA O QUESITO 1.9 (Evita colisão com o 1.8)
            k_q19_faixa1 = f"key_q19_fx1_{ano_sel}"
            k_q19_faixa2 = f"key_q19_fx2_{ano_sel}"
            k_q19_faixa3 = f"key_q19_fx3_{ano_sel}"
            k_q19_faixa4 = f"key_q19_fx4_{ano_sel}"
            k_q19_faixa5 = f"key_q19_fx5_{ano_sel}"
            k_q19_faixa6 = f"key_q19_fx6_{ano_sel}"
            k_q19_total  = f"key_q19_total_auto_{ano_sel}"

            # Função de callback customizada e isolada para o 1.9
            def recalcula_e_soma_q19():
                soma = (
                    int(st.session_state.get(k_q19_faixa1, v_f1)) +
                    int(st.session_state.get(k_q19_faixa2, v_f2)) +
                    int(st.session_state.get(k_q19_faixa3, v_f3)) +
                    int(st.session_state.get(k_q19_faixa4, v_f4)) +
                    int(st.session_state.get(k_q19_faixa5, v_f5)) +
                    int(st.session_state.get(k_q19_faixa6, v_f6))
                )
                st.session_state[k_q19_total] = soma

            col_m1, col_m2 = st.columns([1, 1])
            with col_m1:
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Menor que 1 ano:</label>', unsafe_allow_html=True)
                f1 = st.number_input("", min_value=0, step=1, value=v_f1, key=k_q19_faixa1, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Maior ou igual a 1 ano e menor que 3 anos:</label>', unsafe_allow_html=True)
                f2 = st.number_input("", min_value=0, step=1, value=v_f2, key=k_q19_faixa2, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Maior ou igual a 3 anos e menor que 5 anos:</label>', unsafe_allow_html=True)
                f3 = st.number_input("", min_value=0, step=1, value=v_f3, key=k_q19_faixa3, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Maior ou igual a 5 anos e menor que 10 anos:</label>', unsafe_allow_html=True)
                f4 = st.number_input("", min_value=0, step=1, value=v_f4, key=k_q19_faixa4, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Maior ou igual a 10 anos e menor que 15 anos:</label>', unsafe_allow_html=True)
                f5 = st.number_input("", min_value=0, step=1, value=v_f5, key=k_q19_faixa5, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                st.markdown('<label style="font-size: 13px; font-weight: 500;">Maior ou igual a 15 anos:</label>', unsafe_allow_html=True)
                f6 = st.number_input("", min_value=0, step=1, value=v_f6, key=k_q19_faixa6, label_visibility="collapsed", on_change=recalcula_e_soma_q19)
                
                # Controle e exibição do somatório de escolas gestoras
                total_escolas = f1 + f2 + f3 + f4 + f5 + f6
                if k_q19_total not in st.session_state:
                    st.session_state[k_q19_total] = total_escolas
                else:
                    total_escolas = st.session_state[k_q19_total]
                    
                st.markdown('<label style="font-size: 13px; font-weight: 600; color: #1E3A8A;">Total de Escolas com Gestores Avaliados:</label>', unsafe_allow_html=True)
                st.number_input("", value=int(total_escolas), disabled=True, key=k_q19_total, label_visibility="collapsed")

            with col_m2:
                l19 = st.text_area(f"Link/Evidência (1.9 - {ano_sel}):", value=d19.get("link", ""), key=f"txt_ieduc_19_{ano_sel}", height=450)
                placeholder_links_19 = st.empty()
                links_f19 = re.findall(r'(https?://[^\s]+)', l19)
                if links_f19:
                    botoes_19 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f19])
                    placeholder_links_19.markdown(f"**Links Ativos:** {botoes_19}")
            
            # --- LÓGICA DE CÁLCULO DA NOTA PONDERADA ---
            pts_19 = 0.0
            score_placeholder_19 = st.empty()
            
            if total_escolas > 0:
                # Proporções (Qi)
                q1 = f1 / total_escolas
                q2 = f2 / total_escolas
                q3 = f3 / total_escolas
                q4 = f4 / total_escolas
                q5 = f5 / total_escolas
                q6 = f6 / total_escolas
                
                # Notas parciais ponderadas (Ni)
                n1 = 0.0 * q1
                n2 = 0.5 * q2
                n3 = 1.0 * q3
                n4 = 1.5 * q4
                n5 = 1.75 * q5
                n6 = 2.0 * q6
                
                # Nota Final do Quesito (Soma das frações, teto máximo de Pmáx = 2.0)
                pts_19 = min(2.0, float(n1 + n2 + n3 + n4 + n5 + n6))
                
                score_placeholder_19.markdown(
                    f"📊 **Proporções Calculadas (Q1 a Q6):**<br>"
                    f"▫️ <1a: `{q1*100:.1f}%` | ▫️ 1-3a: `{q2*100:.1f}%` | ▫️ 3-5a: `{q3*100:.1f}%`<br>"
                    f"▫️ 5-10a: `{q4*100:.1f}%` | ▫️ 10-15a: `{q5*100:.1f}%` | ▫️ $\ge$15a: `{q6*100:.1f}%`<br>"
                    f"✨ **Nota Final do Quesito 1.9:** `{pts_19:.2f} pontos` (Máximo: 2.0 pontos)", 
                    unsafe_allow_html=True
                )
            else:
                score_placeholder_19.markdown("⚠️ **Status:** `Aguardando a inserção dos dados populacionais para computar a Nota Final`")
                
            str_valor_19 = f"F1:{f1},F2:{f2},F3:{f3},F4:{f4},F5:{f5},F6:{f6},TOTAL:{total_escolas}"
            
            mudou_opcao_19 = str_valor_19 != d19.get("valor", "")
            mudou_link_19 = l19 != d19.get("link", "")
            
            if mudou_opcao_19 or mudou_link_19:
                save_resp("1.9", str_valor_19, pts_19, l19)
                res_data["1.9"] = {"valor": str_valor_19, "pontos": pts_19, "link": l19}
                if mudou_link_19 and links_f19:
                    links_19_antigos = re.findall(r'(https?://[^\s]+)', d19.get("link", ""))
                    if links_f19 != links_19_antigos:
                        modal_aviso_link("1.9", links_f19)
                    else:
                        st.rerun()
                else:
                    st.rerun()
                    
            bloco_comentarios("1.9", res_data, ano_sel)

# =============================================================================
        # QUESITO 1.10 - REUNIÕES PERIÓDICAS COM OS PAIS (IEDUC)
        # =============================================================================
        with st.expander(f"🔍 QUESITO 1.10 - Reuniões com os Pais ({ano_sel})", expanded=True):
            st.markdown("#### 1.10")
            st.write(f"**Os professores realizam reuniões periódicas com os pais dos alunos de Creche sobre planejamento/projeto escolar e desempenho/desenvolvimento da criança?**")
            st.caption("ℹ️ *O salvamento é automático ao alterar a opção ou o link.*")
            
            # Recupera os dados salvos ou define o padrão vazio
            d110 = res_data.get("1.10", {"valor": "", "pontos": 0.0, "link": ""})
            v_110 = d110["valor"]
            
            # Mapeamento estável de opções com as pontuações na íntegra ao lado do texto
            opcoes_110 = [
                "Selecione...",
                "Sobre planejamento e desempenho da criança – 02",
                "Apenas sobre o projeto político-pedagógico – 1,5",
                "Apenas sobre o desempenho da criança – 01",
                "Não realiza reuniões periódicas – 00"
            ]
            
            # Define o índice do rádio de forma segura contra loops de inicialização
            if v_110 in opcoes_110:
                idx_110 = opcoes_110.index(v_110)
            else:
                idx_110 = 0
                
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f'<label style="font-size: 13px; font-weight: 500;">Selecione a alternativa correspondente para {ano_sel}:</label>', unsafe_allow_html=True)
                op_escolhida_110 = st.radio(
                    "",
                    opcoes_110,
                    index=idx_110,
                    key=f"rad_ieduc_110_{ano_sel}",
                    label_visibility="collapsed"
                )
                
                # Normaliza o valor para salvar apenas se houver uma interação real
                op_110 = op_escolhida_110 if op_escolhida_110 != "Selecione..." else ""
                
            with col2:
                l110 = st.text_area(f"Link/Evidência (1.10 - {ano_sel}):", value=d110.get("link", ""), key=f"txt_ieduc_110_{ano_sel}", height=140)
                placeholder_links_110 = st.empty()
                links_f110 = re.findall(r'(https?://[^\s]+)', l110)
                if links_f110:
                    botoes_110 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f110])
                    placeholder_links_110.markdown(f"**Links Ativos:** {botoes_110}")
            
            # --- LÓGICA DE ATRIBUIÇÃO DE PONTOS ---
            pts_110 = 0.0
            score_placeholder_110 = st.empty()
            
            if op_110:
                if op_110 == "Sobre planejamento e desempenho da criança – 02":
                    pts_110 = 2.0
                elif op_110 == "Apenas sobre o projeto político-pedagógico – 1,5":
                    pts_110 = 1.5
                elif op_110 == "Apenas sobre o desempenho da criança – 01":
                    pts_110 = 1.0
                elif op_110 == "Não realiza reuniões periódicas – 00":
                    pts_110 = 0.0
                    
                score_placeholder_110.markdown(f"📊 **Pontuação Obtida:** `{pts_110:.1f} pontos` | Opção: `{op_110}`")
            else:
                score_placeholder_110.markdown("⚠️ **Status:** `Aguardando seleção da resposta`")
                
            # Controle de mutação de estado e gravação estável
            mudou_opcao_110 = op_110 != v_110
            mudou_link_110 = l110 != d110.get("link", "")
            
            if mudou_opcao_110 or mudou_link_110:
                save_resp("1.10", op_110, pts_110, l110)
                res_data["1.10"] = {"valor": op_110, "pontos": pts_110, "link": l110}
                if mudou_link_110 and links_f110:
                    links_110_antigos = re.findall(r'(https?://[^\s]+)', d110.get("link", ""))
                    if links_f110 != links_110_antigos:
                        modal_aviso_link("1.10", links_f110)
                    else:
                        st.rerun()
                else:
                    st.rerun()
                    
            bloco_comentarios("1.10", res_data, ano_sel)

        # =============================================================================
        # QUESITO 1.10.1 - PERIODICIDADE DAS REUNIÕES (IEDUC)
        # =============================================================================
        with st.expander(f"🔍 QUESITO 1.10.1 - Periodicidade das Reuniões ({ano_sel})", expanded=True):
            st.markdown("#### 1.10.1")
            st.write("**Qual a periodicidade das reuniões?**")
            st.caption("ℹ️ *O salvamento é automático ao alterar a opção ou o link.*")
            
            # Recupera os dados salvos ou define o padrão vazio
            d1101 = res_data.get("1.10.1", {"valor": "", "pontos": 0.0, "link": ""})
            v_1101 = d1101["valor"]
            
            # Mapeamento estável de opções conforme o enunciado
            opcoes_1101 = [
                "Selecione...",
                "Mensal",
                "Bimestral",
                "Trimestral",
                "Quadrimestral",
                "Semestral",
                "Anual"
            ]
            
            # Define o índice do rádio de forma segura contra loops de inicialização
            if v_1101 in opcoes_1101:
                idx_1101 = opcoes_1101.index(v_1101)
            else:
                idx_1101 = 0
                
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f'<label style="font-size: 13px; font-weight: 500;">Selecione a periodicidade para {ano_sel}:</label>', unsafe_allow_html=True)
                op_escolhida_1101 = st.radio(
                    "",
                    opcoes_1101,
                    index=idx_1101,
                    key=f"rad_ieduc_1101_{ano_sel}",
                    label_visibility="collapsed"
                )
                
                # Normaliza o valor para salvar apenas se houver uma interação real
                op_1101 = op_escolhida_1101 if op_escolhida_1101 != "Selecione..." else ""
                
            with col2:
                l1101 = st.text_area(f"Link/Evidência (1.10.1 - {ano_sel}):", value=d1101.get("link", ""), key=f"txt_ieduc_1101_{ano_sel}", height=140)
                placeholder_links_1101 = st.empty()
                links_f1101 = re.findall(r'(https?://[^\s]+)', l1101)
                if links_f1101:
                    botoes_1101 = " | ".join([f"🔗 [{lk}]({lk})" for lk in links_f1101])
                    placeholder_links_1101.markdown(f"**Links Ativos:** {botoes_1101}")
            
            # Dados estritamente informativos (atrelados ao detalhamento do quesito 1.10)
            pts_1101 = 0.0
            score_placeholder_1101 = st.empty()
            if op_1101:
                score_placeholder_1101.markdown(f"📊 **Periodicidade Selecionada ({ano_sel}):** `{op_1101}` (Dados Informativos)")
            else:
                score_placeholder_1101.markdown("⚠️ **Status:** `Aguardando seleção da resposta`")
                
            # Controle de mutação de estado e gravação estável
            mudou_opcao_1101 = op_1101 != v_1101
            mudou_link_1101 = l1101 != d1101.get("link", "")
            
            if mudou_opcao_1101 or mudou_link_1101:
                save_resp("1.10.1", op_1101, pts_1101, l1101)
                res_data["1.10.1"] = {"valor": op_1101, "pontos": pts_1101, "link": l1101}
                if mudou_link_1101 and links_f1101:
                    links_1101_antigos = re.findall(r'(https?://[^\s]+)', d1101.get("link", ""))
                    if links_f1101 != links_1101_antigos:
                        modal_aviso_link("1.10.1", links_f1101)
                    else:
                        st.rerun()
                else:
                    st.rerun()
                    
            bloco_comentarios("1.10.1", res_data, ano_sel)

# ==========================================
# QUESITO 1.11
# ==========================================
with st.expander("Quesito 1.11 - [Insira o Título do Quesito Aqui]", expanded=False):
    # 1. Recuperação do estado atual do banco/sessão
    d111 = res_data.get("1.11", {})
    v_111 = d111.get("valor", "")
    
    # Defina aqui as opções reais do seu quesito
    opcoes_111 = ["Selecione...", "Opção A", "Opção B", "Opção C", "Não se aplica"]
    
    # Determinação do índice inicial para evitar resets visuais indesejados
    idx_init_111 = 0
    if v_111 in opcoes_111:
        idx_init_111 = opcoes_111.index(v_111)
        
    # 2. Renderização dos inputs do usuário
    op_111 = st.selectbox(
        "Selecione a resposta para o Quesito 1.11:",
        opcoes_111,
        index=idx_init_111,
        key="sb_111"
    )
    
    l111 = st.text_input(
        "Insira o link para a documentação comprobatória:",
        value=d111.get("link", ""),
        key="link_111"
    )
    
    # 3. Processamento de dados e cálculo de pontos
    links_f111 = re.findall(r'(https?://[^\s]+)', l111)
    
    # Regra de pontuação (ajuste os valores conforme as regras reais do quesito)
    pts_111 = 0.0
    if op_111 == "Opção A":
        pts_111 = 10.0
    elif op_111 == "Opção B":
        pts_111 = 5.0
    elif op_111 == "Opção C":
        pts_111 = 2.0

    # 4. Painel de status visual
    if op_111 != "Selecione...":
        texto_painel = f"📊 **Pontuação Obtida:** `{pts_111:.1f} pontos` | Opção: `{op_111}`"
    else:
        texto_painel = "⚠️ **Status:** `Aguardando seleção da resposta`"
    
    st.markdown(texto_painel)
    
    # 5. Lógica de detecção de mudanças e salvamento reativo
    op_salvar_111 = op_111 if op_111 != "Selecione..." else ""
    
    mudou_opcao_111 = op_salvar_111 != v_111
    mudou_link_111 = l111 != d111.get("link", "")
    
    if mudou_opcao_111 or mudou_link_111:
        # Salva no banco de dados / estado global
        save_resp("1.11", op_salvar_111, pts_111, l111)
        res_data["1.11"] = {"valor": op_salvar_111, "pontos": pts_111, "link": l111}
        
        if mudou_link_111 and links_f111:
            links_111_antigos = re.findall(r'(https?://[^\s]+)', d111.get("link", ""))
            if links_f111 != links_111_antigos:
                modal_aviso_link("1.11", links_f111)
            else:
                st.rerun()
        else:
            st.rerun()
            
    # 6. Bloco de comentários adicionais
    bloco_comentarios("1.11", res_data, ano_sel)
       
