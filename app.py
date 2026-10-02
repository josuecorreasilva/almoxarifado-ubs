import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import re
import textwrap
import unicodedata
from datetime import datetime, date
from contextlib import nullcontext
from zoneinfo import ZoneInfo
from supabase import create_client, Client

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_DISPONIVEL = True
except ImportError:
    FPDF_DISPONIVEL = False
    FPDF = object
    XPos = YPos = None

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
# POR QUE: Define como a página vai aparecer na aba do navegador e usa a tela toda (layout wide)
st.set_page_config(page_title="SisPAC — SMS Pelotas", page_icon="🏥", layout="wide")

st.markdown("""
    <style>
    @media print {
        @page { size: A4; margin: 10mm 10mm 16mm 10mm; }
        html, body {
            background: white !important;
            height: auto !important;
            margin: 0 !important;
        }
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-baseweb="tab-list"],
        [role="tablist"],
        header,
        .sispac-header,
        .nao-imprimir,
        [data-testid="stImage"],
        [data-testid="stForm"],
        [data-testid="stRadio"],
        [data-testid="stSelectbox"],
        [data-testid="stButton"],
        [data-testid="stDownloadButton"],
        [data-testid="stCheckbox"],
        [data-testid="stTextInput"],
        [data-testid="stNumberInput"],
        [data-testid="stCaption"],
        footer,
        [data-testid="stStatusWidget"],
        .stAppDeployButton,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }
        *:has(.area-impressao) {
            display: block !important;
            visibility: visible !important;
            height: auto !important;
            overflow: visible !important;
            position: static !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        *:has(.area-impressao) > *:not(:has(.area-impressao)):not(.area-impressao) {
            display: none !important;
        }
        .area-impressao, .area-impressao * {
            visibility: visible !important;
            color: #000 !important;
        }
        .area-impressao {
            display: block !important;
            width: 100% !important;
            background: white !important;
        }
        .area-impressao table { display: table !important; width: 100% !important; }
        .area-impressao thead { display: table-header-group !important; }
        .area-impressao tbody { display: table-row-group !important; }
        .area-impressao tr { display: table-row !important; }
        .area-impressao th, .area-impressao td { display: table-cell !important; }
        .bloco-assinaturas { display: flex !important; }
        .campo-assinatura, .campo-assinatura .linha { display: block !important; }
        .rodape-impressao {
            display: block !important;
            position: fixed !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            visibility: visible !important;
            font-size: 10px !important;
            color: #222 !important;
            text-align: left !important;
            padding: 0 10mm 4mm 10mm !important;
            background: transparent !important;
        }
    }
    .rodape-impressao { display: none; }
    .area-impressao table {
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0 16px 0;
        font-size: 13px;
    }
    .area-impressao th, .area-impressao td {
        border: 1px solid #999;
        padding: 6px 8px;
        text-align: left;
    }
    .area-impressao th { background: #f2f2f2; }
    .bloco-assinaturas {
        display: flex;
        gap: 36px;
        margin-top: 48px;
        page-break-inside: avoid;
    }
    .campo-assinatura {
        flex: 1;
        text-align: center;
    }
    .campo-assinatura .linha {
        border-top: 1px solid #333;
        margin: 42px 12px 8px 12px;
    }
    .campo-assinatura p {
        margin: 0;
        font-size: 12px;
        color: #222;
    }
    .campo-assinatura span {
        display: block;
        margin-top: 2px;
        font-size: 11px;
        color: #666;
    }
    .block-container { padding-top: 0.7rem; padding-bottom: 1.1rem; max-width: 1400px; }
    [data-testid="stSidebar"] { background: #f4f7f8; }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavSeparator"] {
        display: none !important;
    }
    footer,
    [data-testid="stStatusWidget"],
    .stAppDeployButton,
    [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }
    [data-testid="stHeaderActionElements"],
    [data-testid="stHeadingWithActionElements"] a,
    .stMarkdown a[href^="#"] {
        display: none !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
        gap: 0.42rem !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    [data-testid="stElementContainer"] {
        margin-bottom: 0 !important;
    }
    [data-testid="stWidgetLabel"] {
        margin-bottom: 0.15rem !important;
        font-size: 0.86rem !important;
    }
    [data-testid="stMarkdown"] h1,
    [data-testid="stMarkdown"] h2,
    [data-testid="stMarkdown"] h3,
    [data-testid="stMarkdown"] h4,
    [data-testid="stMarkdown"] h5 {
        margin: 0.15rem 0 0.3rem 0 !important;
        line-height: 1.25 !important;
    }
    [data-testid="stMarkdownContainer"] p {
        margin: 0.15rem 0 0.35rem 0 !important;
    }
    [data-testid="stCaptionContainer"] {
        margin-top: -0.15rem !important;
        margin-bottom: 0.2rem !important;
    }
    div.stButton > button {
        padding: 0.22rem 0.65rem !important;
        min-height: 1.85rem !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] {
        min-height: 1.85rem !important;
        font-size: 0.88rem !important;
    }
    [data-testid="stTextArea"] textarea {
        font-size: 0.88rem !important;
    }
    [data-testid="stForm"] {
        padding: 0.55rem 0.7rem !important;
        border-width: 1px !important;
    }
    hr {
        margin: 0.35rem 0 !important;
    }
    .sispac-header {
        background: linear-gradient(90deg, #0e4d56 0%, #1a6b75 100%);
        color: #fff;
        border-radius: 8px;
        padding: 8px 16px;
        margin-bottom: 4px;
    }
    .sispac-header h1 { font-size: 1.2rem; margin: 0; font-weight: 650; color: #fff; }
    .sispac-header p { margin: 2px 0 0 0; font-size: 0.82rem; opacity: 0.9; }
    .sispac-card {
        background: #f8fbfb;
        border: 1px solid #d5e4e6;
        border-radius: 10px;
        padding: 8px 4px 4px 4px;
        margin-bottom: 8px;
    }
    div.stButton > button[kind="primary"] {
        background: #0e4d56;
        border: 0;
    }
    .st-key-catalogo_marcacao p,
    .st-key-catalogo_marcacao [data-testid="stMarkdownContainer"],
    .st-key-catalogo_marcacao [data-testid="stWidgetLabel"],
    .st-key-catalogo_marcacao label {
        font-size: 0.82rem !important;
        line-height: 1.3 !important;
    }
    .st-key-catalogo_marcacao [data-testid="stVerticalBlock"] {
        gap: 0.28rem !important;
    }
    .st-key-catalogo_marcacao [data-testid="stForm"] [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"]) {
        background: #f7fafb;
        border: 1px solid #e2ecee;
        border-radius: 8px;
        padding: 4px 10px 2px 8px;
        margin-bottom: 4px;
        align-items: center;
    }
    .st-key-catalogo_marcacao [data-testid="stNumberInput"] {
        max-width: 92px;
    }
    .st-key-catalogo_marcacao [data-testid="stNumberInput"] input {
        font-size: 0.85rem !important;
        font-weight: 600;
        text-align: center;
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .st-key-catalogo_marcacao [data-testid="stCheckbox"] {
        min-height: 1.3rem !important;
    }
    .st-key-lista_pedidos [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    .st-key-lista_pedidos [data-testid="stHorizontalBlock"] {
        gap: 0.35rem !important;
        align-items: center !important;
        min-height: 28px !important;
        margin: 0 !important;
    }
    .st-key-lista_pedidos p {
        text-align: left !important;
        margin: 0 !important;
        line-height: 1.25 !important;
    }
    .st-key-lista_pedidos [data-testid="stColumn"],
    .st-key-lista_pedidos [data-testid="column"] {
        align-items: center !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 0 !important;
    }
    .st-key-lista_pedidos [data-testid="stColumn"] > div,
    .st-key-lista_pedidos [data-testid="column"] > div {
        width: 100% !important;
        align-items: stretch !important;
        text-align: left !important;
        gap: 0 !important;
    }
    .st-key-lista_pedidos [data-testid="stMarkdown"],
    .st-key-lista_pedidos [data-testid="stMarkdownContainer"],
    .st-key-lista_pedidos [data-testid="stElementContainer"] {
        width: 100% !important;
        text-align: left !important;
        display: block !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    .st-key-lista_pedidos [data-testid="stHorizontalBlock"] > div:first-child {
        position: relative !important;
        text-align: left !important;
    }
    .st-key-lista_pedidos div.stButton > button {
        font-size: 0.78rem !important;
        padding: 0.1rem 0.4rem !important;
        min-height: 26px !important;
        height: 26px !important;
        line-height: 1.2 !important;
    }
    .st-key-lista_pedidos [class*="st-key-hit_"] {
        position: absolute !important;
        left: 0 !important;
        right: 0 !important;
        top: 0 !important;
        height: 28px !important;
        z-index: 6 !important;
    }
    .st-key-lista_pedidos [class*="st-key-hit_"] div.stButton > button {
        width: 100% !important;
        height: 28px !important;
        min-height: 28px !important;
        opacity: 0 !important;
        cursor: pointer !important;
        border: none !important;
        background: transparent !important;
    }
    .linha-pedido {
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        width: 100% !important;
        max-width: 100% !important;
        text-align: left !important;
        gap: 10px;
        padding: 3px 8px !important;
        min-height: 26px;
        border-bottom: 1px solid #d5d8dc;
        box-sizing: border-box;
        font-size: 0.84rem;
        line-height: 1.25;
        color: #1c2833;
    }
    .linha-pedido-cab {
        font-weight: 700;
        color: #2c3e50;
        background: #f4f6f7;
        border-bottom: 1px solid #bdc3c7;
    }
    .linha-pedido .ped-num {
        flex: 0 0 210px;
        font-weight: 700;
        text-align: left !important;
    }
    .linha-pedido .ped-ubs {
        flex: 0 0 170px;
        text-align: left !important;
    }
    .linha-pedido .ped-meta {
        flex: 1 1 auto;
        color: #5d6d6e;
        text-align: left !important;
    }
    .area-impressao s {
        text-decoration: line-through;
        color: #7b241c;
    }
    .linha-pedido.linha-sel,
    .linha-empenho.linha-sel {
        background: #e8f4f5;
    }
    .st-key-lista_empenhos,
    .st-key-lista_notas_emp {
        width: 100% !important;
    }
    .st-key-lista_empenhos p,
    .st-key-lista_notas_emp p {
        text-align: left !important;
        margin: 0 !important;
    }
    .st-key-lista_empenhos [class*="st-key-emp_row_"],
    .st-key-lista_notas_emp [class*="st-key-nf_row_"] {
        position: relative !important;
        width: 100% !important;
    }
    .st-key-lista_empenhos [class*="st-key-emp_row_"] [data-testid="stVerticalBlock"],
    .st-key-lista_notas_emp [class*="st-key-nf_row_"] [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    .st-key-lista_empenhos [class*="st-key-hit_emp_"],
    .st-key-lista_notas_emp [class*="st-key-hit_nf_"] {
        position: absolute !important;
        left: 0 !important;
        right: 92px !important;
        top: 0 !important;
        height: 100% !important;
        z-index: 6 !important;
    }
    .st-key-lista_empenhos [class*="st-key-hit_emp_"] div.stButton > button,
    .st-key-lista_notas_emp [class*="st-key-hit_nf_"] div.stButton > button,
    .st-key-lista_empenhos [class*="st-key-hit_emp_"] button,
    .st-key-lista_notas_emp [class*="st-key-hit_nf_"] button {
        width: 100% !important;
        height: 100% !important;
        min-height: 36px !important;
        opacity: 0 !important;
        cursor: pointer !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        color: transparent !important;
    }
    .st-key-lista_empenhos [class*="st-key-open_emp_"],
    .st-key-lista_notas_emp [class*="st-key-open_nf_"] {
        position: absolute !important;
        right: 4px !important;
        top: 50% !important;
        transform: translateY(-50%);
        width: 84px !important;
        z-index: 8 !important;
    }
    .st-key-lista_empenhos [class*="st-key-open_emp_"] div.stButton > button,
    .st-key-lista_notas_emp [class*="st-key-open_nf_"] div.stButton > button {
        font-size: 0.8rem !important;
        padding: 0.2rem 0.4rem !important;
        min-height: 0 !important;
        height: 32px !important;
        width: 100% !important;
    }
    .linha-empenho {
        display: grid !important;
        grid-template-columns: 1.3fr 2.2fr 1fr 0.7fr 0.85fr 0.95fr 88px;
        align-items: center;
        width: 100% !important;
        max-width: 100% !important;
        gap: 10px 16px;
        padding: 10px 8px !important;
        border-bottom: 1px solid #d5d8dc;
        box-sizing: border-box;
        font-size: 0.92rem;
        line-height: 1.35;
        color: #1c2833;
        cursor: pointer;
    }
    .linha-nota {
        grid-template-columns: 1.5fr 1.2fr 1.1fr 0.9fr 88px;
    }
    .linha-empenho-cab {
        font-weight: 700;
        color: #2c3e50;
        background: #f4f6f7;
        border-bottom: 1px solid #bdc3c7;
        cursor: default;
    }
    .linha-empenho > span {
        min-width: 0;
        display: block;
        overflow-wrap: anywhere;
        text-align: left !important;
    }
    .linha-empenho .emp-num { font-weight: 700; }
    .linha-empenho .emp-meta { color: #5d6d6e; }
    .st-key-catalogo_marcacao [data-testid="stCheckbox"] label {
        cursor: pointer !important;
        font-weight: 500 !important;
    }
    .st-key-catalogo_lista {
        border: 1px solid #d5d8dc;
        border-radius: 6px;
        padding: 0;
        background: #fff;
    }
    .st-key-catalogo_lista [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    .st-key-catalogo_lista [data-testid="stHorizontalBlock"] {
        gap: 0.35rem !important;
        align-items: center !important;
        min-height: 28px !important;
        margin: 0 !important;
        padding: 0 6px !important;
        border-bottom: 1px solid #d5d8dc !important;
        width: 100% !important;
    }
    .st-key-catalogo_lista [data-testid="stColumn"],
    .st-key-catalogo_lista [data-testid="column"] {
        align-items: center !important;
        padding: 0 !important;
    }
    .st-key-catalogo_lista p {
        margin: 0 !important;
        font-size: 0.84rem !important;
        line-height: 1.25 !important;
    }
    .st-key-catalogo_lista [data-testid="stMarkdown"],
    .st-key-catalogo_lista [data-testid="stMarkdownContainer"],
    .st-key-catalogo_lista [data-testid="stElementContainer"] {
        width: 100% !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    .linha-catalogo {
        display: flex;
        align-items: center;
        min-height: 26px;
        padding: 3px 4px;
        font-size: 0.84rem;
        line-height: 1.25;
        color: #1c2833;
    }
    .linha-catalogo-cab {
        font-weight: 700;
        color: #2c3e50;
        background: #f4f6f7;
    }
    .st-key-catalogo_lista [data-testid="stNumberInput"] {
        max-width: 78px;
    }
    .st-key-catalogo_lista [data-testid="stNumberInput"] input {
        font-size: 0.82rem !important;
        font-weight: 600;
        text-align: center;
        min-height: 26px !important;
        height: 26px !important;
        padding-top: 0.08rem !important;
        padding-bottom: 0.08rem !important;
    }
    .st-key-catalogo_lista div.stButton > button {
        padding: 0.1rem 0.4rem !important;
        min-height: 26px !important;
        height: 26px !important;
        font-size: 0.78rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# POR QUE: Conecta o seu aplicativo ao banco de dados na nuvem (Supabase)
supabase_url = "https://dglgicnsdelxvhkxwfzd.supabase.co"
supabase_key = "sb_publishable_D6M75JYkHMrtR40Caw1Ruw_RYO3qWbF" 
supabase = create_client(supabase_url, supabase_key)

# ==========================================
# 2. VARIÁVEIS FUNDAMENTAIS (DADOS BASE)
# ==========================================
# POR QUE: Sem esta lista, o sistema não sabe quais UBSs existem para montar os filtros do formulário.
distritos_ubs = {
    "Centro/Porto": ["Balsa", "Bom Jesus", "Simões Lopes"],
    "Areal": ["Areal Leste", "Areal Fundão"],
    "Três Vendas": ["Fernando Osório", "Lindoia"],
    "Fragata": ["Guabiroba", "Simões Lopes"],
    "Rural": ["Coronel Maciel", "Gruppelli"]
}

# POR QUE: Link para puxar a lista de materiais ao vivo do seu Google Sheets. 
url_google_sheets_materiais = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pub?output=csv"

MATERIAIS_INVALIDOS = {
    "Erro", "Selecione Categoria", "Selecione a categoria", "Selecione o material",
    "Nenhuma", "Sem itens", "",
}
LIMIAR_ESTOQUE_BAIXO = 50


def normalizar_texto(texto):
    texto = str(texto).lower().strip()
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.replace(" ", "").replace("_", "").replace(".", "").replace("-", "")


def identificar_ubs_por_email(email):
    local = normalizar_texto(str(email).split("@")[0])
    candidatos = []
    for distrito, unidades in distritos_ubs.items():
        for unidade in unidades:
            nome_norm = normalizar_texto(unidade)
            if nome_norm and nome_norm in local:
                candidatos.append((len(nome_norm), distrito, unidade))
    if candidatos:
        candidatos.sort(reverse=True)
        return candidatos[0][1], candidatos[0][2]
    return "Não Encontrado", None


def achar_coluna(df, aliases):
    mapa = {str(c).strip().lower(): c for c in df.columns}
    for alias in aliases:
        chave = alias.strip().lower()
        if chave in mapa:
            return mapa[chave]
    return None


FUSO_SISPAC = ZoneInfo("America/Sao_Paulo")


def agora_sispac():
    return datetime.now(FUSO_SISPAC)


def texto_agora_sispac():
    return agora_sispac().strftime("%Y-%m-%d %H:%M:%S%z")


def formatar_datahora_br(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nat", "nan", "none"}:
        return ""
    try:
        ts = pd.to_datetime(valor, utc=False)
        if getattr(ts, "tzinfo", None) is None:
            ts = ts.tz_localize("UTC")
        ts = ts.tz_convert(FUSO_SISPAC)
        return ts.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return texto[:16]


def parse_numero(valor, inteiro=False):
    padrao = 0 if inteiro else 0.0
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return padrao
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        numero = float(valor)
        return int(numero) if inteiro else numero

    texto = str(valor).strip().replace("R$", "").replace("\xa0", "").replace(" ", "")
    if texto == "" or texto.lower() in {"nan", "none", "-"}:
        return padrao
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        numero = float(texto)
        return int(numero) if inteiro else numero
    except ValueError:
        return padrao


def filtrar_pedidos_por_numero(df, termo):
    if df is None or df.empty or not str(termo or "").strip():
        return df
    termo = str(termo).strip()
    nums = df["numero_pedido"].astype(str)
    return df[nums.str.contains(re.escape(termo), case=False, regex=True, na=False)]


STATUS_PEDIDO_ENVIADO = "Pedido enviado"
STATUS_SEPARADO = "Separado"
STATUS_TRANSITO = "Em trânsito"
STATUS_ATENDIDO_PARCIAL = "Atendido Parcialmente"
STATUS_ATENDIDO_INTEGRAL = "Atendido Integralmente"
STATUS_SAIU_CENTRAL = {STATUS_TRANSITO, STATUS_ATENDIDO_PARCIAL, STATUS_ATENDIDO_INTEGRAL}


def pedido_concluido(status):
    return str(status or "") in {STATUS_ATENDIDO_PARCIAL, STATUS_ATENDIDO_INTEGRAL}


def pedido_separado(status):
    return str(status or "") == STATUS_SEPARADO


def pedido_em_transito(status):
    return str(status or "") == STATUS_TRANSITO


def status_pedido_unico(pedidos_unicos, numero):
    m = pedidos_unicos[pedidos_unicos["numero_pedido"].astype(str) == str(numero)]
    if m.empty:
        return ""
    return m["status"].iloc[0]


def resolver_pedido_aberto(pedidos_unicos, tipo_lista, perfil):
    pedido = st.session_state.get("pedido_aberto") or "Selecione..."
    if pedido == "Selecione..." or pedidos_unicos is None or pedidos_unicos.empty:
        return "Selecione..."
    if pedido not in set(pedidos_unicos["numero_pedido"].astype(str)):
        return "Selecione..."
    status = status_pedido_unico(pedidos_unicos, pedido)
    if not pedido_pertence_lista(status, tipo_lista, perfil):
        return "Selecione..."
    return pedido


def tipo_lista_pedidos(rotulo, perfil):
    texto = str(rotulo or "")
    if texto.startswith("Despacho"):
        return "despacho"
    if texto.startswith("Conclu"):
        return "concluidos"
    return "pendentes"


def rotulo_lista_por_status(status, perfil, opcoes):
    if perfil == "GESTAO":
        if pedido_concluido(status):
            tipo = "concluidos"
        elif pedido_separado(status) or pedido_em_transito(status):
            tipo = "despacho"
        else:
            tipo = "pendentes"
    else:
        tipo = "concluidos" if pedido_concluido(status) else "pendentes"
    for opcao in opcoes:
        if tipo_lista_pedidos(opcao, perfil) == tipo:
            return opcao
    return opcoes[0] if opcoes else "Pendentes (conferência)"


def pedido_pertence_lista(status, tipo_lista, perfil="GESTAO"):
    status = str(status or STATUS_PEDIDO_ENVIADO)
    if tipo_lista == "concluidos":
        return pedido_concluido(status)
    if tipo_lista == "despacho":
        return pedido_separado(status) or pedido_em_transito(status)
    if perfil == "UBS":
        return not pedido_concluido(status)
    return status in {STATUS_PEDIDO_ENVIADO, ""}


def abrir_pedido_lista(numero, modo, imprimir=False):
    st.session_state.pedido_aberto = numero
    st.session_state.modo_abertura = modo
    if imprimir:
        pedir_impressao()
    st.rerun()


def pedir_impressao():
    st.session_state["_print_token"] = str(time.time_ns())


def render_iframe_impressao():
    token = str(st.session_state.get("_print_token") or "")
    if not token:
        return
    components.html(
        f"""
<!DOCTYPE html>
<html><body>
<script>
(function() {{
  var token = {token!r};
  var alvo = null;
  try {{ alvo = window.parent; }} catch (e1) {{ alvo = null; }}
  if (!alvo) {{
    try {{ alvo = window.top; }} catch (e2) {{ alvo = window; }}
  }}
  try {{
    alvo.__sispacPrinted = alvo.__sispacPrinted || {{}};
    if (alvo.__sispacPrinted[token]) return;
    alvo.__sispacPrinted[token] = 1;
  }} catch (e3) {{}}
  setTimeout(function() {{
    try {{
      var oldTitle = alvo.document.title;
      alvo.document.title = "SisPAC";
      try {{
        if (alvo.history && alvo.history.replaceState) {{
          alvo.history.replaceState(null, "", alvo.location.pathname + alvo.location.search);
        }}
      }} catch (eHash) {{}}
      var restaurar = function() {{
        try {{ alvo.document.title = oldTitle; }} catch (eT) {{}}
        try {{ alvo.removeEventListener("afterprint", restaurar); }} catch (eL) {{}}
      }};
      try {{ alvo.addEventListener("afterprint", restaurar); }} catch (eA) {{}}
      alvo.focus();
      alvo.print();
    }} catch (e4) {{
      try {{ window.top.print(); }} catch (e5) {{ window.print(); }}
    }}
  }}, 450);
}})();
</script>
</body></html>
""",
        height=0,
    )


def html_linha_pedido(numero, ubs, status, data_txt):
    return (
        "<div class='linha-pedido'>"
        f"<span class='ped-num'>{html_seguro(numero)}</span>"
        f"<span class='ped-ubs'>{html_seguro(ubs)}</span>"
        f"<span class='ped-meta'>{html_seguro(status)} · {html_seguro(data_txt)}</span>"
        "</div>"
    )


def render_lista_pedidos_clicavel(df_lista, chave, acao="visualizar"):
    if df_lista is None or df_lista.empty:
        if acao == "despachar":
            st.info("Nenhum pedido em despacho ou trânsito. Depois da conferência, ele aparece nesta lista para imprimir e sair para entrega.")
        elif acao == "conferir":
            st.info("Nenhum pedido pendente de conferência.")
        else:
            st.info("Nenhum pedido encontrado.")
        return
    df_lista = df_lista.reset_index(drop=True)
    with st.container(key="lista_pedidos"):
        cab, _espaco_cab = st.columns([7.4, 2.6]) if acao == "despachar" else (
            st.columns([8.5, 1.5]) if acao in {"conferir", "receber"} else st.columns([7.4, 2.6])
        )
        with cab:
            st.markdown(
                "<div class='linha-pedido linha-pedido-cab'>"
                "<span class='ped-num'>Pedido</span>"
                "<span class='ped-ubs'>UBS</span>"
                "<span class='ped-meta'>Situação</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        for i, row in df_lista.iterrows():
            numero = str(row["numero_pedido"])
            data_txt = formatar_datahora_br(row.get("data"))
            ubs = str(row.get("ubs") or "")
            status = str(row.get("status") or "")
            pode_abrir_texto = True
            if acao == "despachar":
                c_txt, c_acao, c_imp = st.columns([7.4, 1.3, 1.3])
            elif acao in {"conferir", "receber"}:
                c_txt, c_acao = st.columns([8.5, 1.5])
            else:
                c_txt, c_ver, c_imp = st.columns([7.4, 1.3, 1.3])
            with c_txt:
                st.markdown(html_linha_pedido(numero, ubs, status, data_txt), unsafe_allow_html=True)
                if pode_abrir_texto:
                    with st.container(key=f"hit_{chave}_{i}"):
                        if st.button("Abrir pedido", key=f"{chave}_txt_{i}_{numero}", use_container_width=True):
                            modo = "visualizar"
                            if acao == "conferir":
                                modo = "conferir"
                            elif acao == "despachar":
                                modo = "despachar" if pedido_separado(status) else "visualizar"
                            elif acao == "receber":
                                modo = "receber" if pedido_em_transito(status) else "visualizar"
                            abrir_pedido_lista(numero, modo)
            if acao == "conferir":
                with c_acao:
                    if st.session_state.perfil == "GESTAO":
                        if st.button("Conferir", key=f"{chave}_conf_{i}_{numero}"):
                            abrir_pedido_lista(numero, "conferir")
            elif acao == "despachar":
                with c_acao:
                    if pedido_separado(status):
                        if st.button("Despachar", key=f"{chave}_desp_{i}_{numero}"):
                            abrir_pedido_lista(numero, "despachar")
                    else:
                        if st.button("Ver", key=f"{chave}_ver_tr_{i}_{numero}"):
                            abrir_pedido_lista(numero, "visualizar")
                with c_imp:
                    if st.button("Imprimir", key=f"{chave}_imp_{i}_{numero}"):
                        modo = "despachar" if pedido_separado(status) else "visualizar"
                        abrir_pedido_lista(numero, modo, imprimir=True)
            elif acao == "receber":
                with c_acao:
                    if pedido_em_transito(status):
                        if st.button("Receber", key=f"{chave}_rec_{i}_{numero}"):
                            abrir_pedido_lista(numero, "receber")
                    else:
                        if st.button("Ver", key=f"{chave}_ver_rc_{i}_{numero}"):
                            abrir_pedido_lista(numero, "visualizar")
            else:
                with c_ver:
                    if st.button("Visualizar", key=f"{chave}_ver_{i}_{numero}"):
                        abrir_pedido_lista(numero, "visualizar")
                with c_imp:
                    if st.button("Imprimir", key=f"{chave}_imp_{i}_{numero}"):
                        abrir_pedido_lista(numero, "visualizar", imprimir=True)


def status_consolidado_pedido(df_itens):
    if df_itens is None or df_itens.empty or "status" not in df_itens.columns:
        return STATUS_PEDIDO_ENVIADO
    statuses = set(df_itens["status"].dropna().astype(str))
    if STATUS_ATENDIDO_PARCIAL in statuses:
        return STATUS_ATENDIDO_PARCIAL
    if statuses and statuses.issubset({STATUS_ATENDIDO_INTEGRAL}):
        return STATUS_ATENDIDO_INTEGRAL
    if STATUS_TRANSITO in statuses:
        return STATUS_TRANSITO
    if STATUS_SEPARADO in statuses:
        return STATUS_SEPARADO
    return str(df_itens["status"].iloc[0])


def slug_arquivo(texto):
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^\w\-]+", "-", sem_acento).strip("-")
    return limpo or "UBS"


def extrair_sequencia_pedido(numero_pedido):
    encontrado = re.search(r"(?i)PED-(\d+)", str(numero_pedido or ""))
    if not encontrado:
        return 0
    numero = int(encontrado.group(1))
    if numero >= 1_000_000:
        return 0
    return numero


def proximo_numero_pedido(ubs_nome):
    proximo = 1
    try:
        resposta = supabase.table("pedidos").select("numero_pedido").execute()
        for linha in resposta.data or []:
            seq = extrair_sequencia_pedido(linha.get("numero_pedido"))
            if seq >= proximo:
                proximo = seq + 1
    except Exception:
        proximo = 1
    data_ref = agora_sispac().strftime("%Y%m%d")
    return f"PED-{proximo:04d}-{slug_arquivo(ubs_nome)}-{data_ref}"


def nome_arquivo_pedido(numero_pedido, ubs_nome, data_ref=None, extensao="csv"):
    if data_ref is None:
            data_fmt = agora_sispac().strftime("%Y-%m-%d")
    else:
        try:
            data_fmt = pd.to_datetime(data_ref).strftime("%Y-%m-%d")
        except Exception:
            data_fmt = agora_sispac().strftime("%Y-%m-%d")
    return f"{slug_arquivo(numero_pedido)}_{slug_arquivo(ubs_nome)}_{data_fmt}.{extensao}"


def aplicar_sufixo_arquivo(nome_arquivo, sufixo):
    if "." not in nome_arquivo:
        return f"{nome_arquivo}_{sufixo}"
    raiz, ext = nome_arquivo.rsplit(".", 1)
    return f"{raiz}_{sufixo}.{ext}"


def texto_pdf(valor):
    texto = str(valor if valor is not None else "")
    return texto.encode("latin-1", "replace").decode("latin-1")


def _pdf_escape(texto):
    return texto_pdf(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def gerar_pdf_basico(linhas):
    """PDF simples (sem biblioteca extra) para o Streamlit Cloud enquanto o fpdf2 nao estiver instalado."""
    linhas_pagina = 48
    paginas = [linhas[i:i + linhas_pagina] or [""] for i in range(0, max(len(linhas), 1), linhas_pagina)]
    conteudos = []
    for pagina in paginas:
        cmds = ["BT /F1 11 Tf 50 800 Td"]
        for i, linha in enumerate(pagina):
            if i:
                cmds.append("0 -15 Td")
            cmds.append(f"({_pdf_escape(linha)}) Tj")
        cmds.append("ET")
        conteudos.append("\n".join(cmds) + "\n")

    objetos = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i} 0 R" for i in range(len(conteudos)))
    objetos.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(conteudos)} >>")
    stream_ids = []
    proximo = 3 + len(conteudos)
    for i, stream in enumerate(conteudos):
        stream_id = proximo + i
        stream_ids.append(stream_id)
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {proximo + len(conteudos)} 0 R >> >> /Contents {stream_id} 0 R >>"
        )
    for stream in conteudos:
        objetos.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}endstream")
    objetos.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = ["%PDF-1.4"]
    offsets = [0]
    cursor = 9
    for i, obj in enumerate(objetos, start=1):
        offsets.append(cursor)
        bloco = f"{i} 0 obj\n{obj}\nendobj\n"
        pdf.append(bloco)
        cursor += len(bloco.encode("latin-1"))
    xref_pos = cursor
    xref = [f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n")
    trailer = f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
    return "".join(["%PDF-1.4\n"] + pdf[1:] + xref + [trailer]).encode("latin-1")


def item_solicitado_nao_reenviado(row, status_pedido):
    status_item = str(row.get("status") or "")
    if not (pedido_concluido(status_item) or pedido_concluido(status_pedido)):
        return False
    return parse_numero(row.get("quantidade"), True) > parse_numero(row.get("quantidade_entregue"), True)


def pedido_tem_item_parcial(detalhes, status_pedido):
    if detalhes is None or detalhes.empty:
        return False
    return any(item_solicitado_nao_reenviado(row, status_pedido) for _, row in detalhes.iterrows())


def html_qtd_solicitada(row, status_pedido):
    qtd = parse_numero(row.get("quantidade"), True)
    if item_solicitado_nao_reenviado(row, status_pedido):
        return f"<s>{qtd}</s>"
    return str(qtd)


AVISO_PARCIAL = (
    "Quantitativo solicitado riscado: a diferença não será enviada depois. "
    "Vale somente a quantidade entregue."
)
RODAPE_IMPRESSAO = "https://pedidos-ubs-pelotas"


def html_rodape_impressao():
    return f"<div class='rodape-impressao'>{html_seguro(RODAPE_IMPRESSAO)}</div>"


def linhas_comprovante(detalhes, status_atual, sem_custo=True):
    via = "via operacional" if sem_custo else "via gerencial"
    linhas = [
        "SECRETARIA MUNICIPAL DE SAUDE DE PELOTAS",
        f"Comprovante de Requisicao e Entrega - SisPAC ({via})",
        "",
        f"No do Pedido: {detalhes['numero_pedido'].iloc[0] if 'numero_pedido' in detalhes.columns else ''}",
        f"Data/Hora do envio: {detalhes['data'].iloc[0]}",
        f"Distrito: {detalhes['distrito'].iloc[0]}",
        f"Unidade (UBS): {detalhes['ubs'].iloc[0]}",
        f"Status: {status_atual}",
        "",
    ]
    if pedido_tem_item_parcial(detalhes, status_atual):
        linhas += [AVISO_PARCIAL, ""]
    if "observacao" in detalhes.columns and pd.notna(detalhes["observacao"].iloc[0]):
        obs = str(detalhes["observacao"].iloc[0]).strip()
        if obs:
            linhas += ["Observacoes:", obs, ""]
    custo_total = 0.0
    for cat in detalhes["categoria"].unique():
        df_cat = detalhes[detalhes["categoria"] == cat]
        linhas.append(f"Categoria: {cat}")
        if sem_custo:
            linhas.append("Material | Solicitado | Entregue")
        else:
            subtotal = float(df_cat["custo_total"].sum()) if "custo_total" in df_cat.columns else 0.0
            custo_total += subtotal
            linhas.append(f"Subtotal: {formatar_moeda_br(subtotal)}")
            linhas.append("Material | Solic. | Entregue | Vl. unitario | Custo")
        for _, linha in df_cat.iterrows():
            q_sol = parse_numero(linha["quantidade"], True)
            if item_solicitado_nao_reenviado(linha, status_atual):
                q_sol = f"{q_sol} (nao reenviado)"
            base = f"{linha['material']} | {q_sol} | {parse_numero(linha.get('quantidade_entregue'), True)}"
            if not sem_custo:
                base += f" | {formatar_moeda_br(linha.get('valor_unitario', 0))} | {formatar_moeda_br(linha.get('custo_total', 0))}"
            linhas.append(base)
        linhas.append("")
    if not sem_custo:
        linhas.append(f"Custo total efetivo: {formatar_moeda_br(custo_total)}")
        linhas.append("")
    linhas += [
        "Almoxarifado Central - Assinatura e carimbo",
        "",
        "Recebimento na UBS - Assinatura do responsavel",
    ]
    return linhas


if FPDF_DISPONIVEL:
    class PdfSisPAC(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 6, texto_pdf(RODAPE_IMPRESSAO), align="L")
else:
    class PdfSisPAC:
        pass


def pdf_para_bytes(pdf):
    saida = pdf.output()
    if isinstance(saida, (bytes, bytearray)):
        return bytes(saida)
    return str(saida).encode("latin-1")


def pdf_celula(pdf, largura, altura, texto, negrito=False, alinhar="L", riscado=False):
    pdf.set_font("Helvetica", "B" if negrito else "", 8)
    limite = max(largura - 2, 8)
    conteudo = texto_pdf(texto)
    while pdf.get_string_width(conteudo) > limite and len(conteudo) > 3:
        conteudo = conteudo[:-4] + "..."
    x = pdf.get_x()
    y = pdf.get_y()
    pdf.cell(largura, altura, conteudo, border=1, align=alinhar)
    if riscado:
        pdf.line(x + 1.5, y + (altura / 2), x + largura - 1.5, y + (altura / 2))


def gerar_pdf_comprovante(detalhes, status_atual, sem_custo=True):
    if not FPDF_DISPONIVEL:
        return gerar_pdf_basico(linhas_comprovante(detalhes, status_atual, sem_custo))
    pdf = PdfSisPAC(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, texto_pdf("SECRETARIA MUNICIPAL DE SAUDE DE PELOTAS"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 11)
    via = "via operacional" if sem_custo else "via gerencial"
    pdf.cell(0, 7, texto_pdf(f"Comprovante de Requisicao e Entrega - SisPAC ({via})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    campos = [
        ("No do Pedido", detalhes["numero_pedido"].iloc[0] if "numero_pedido" in detalhes.columns else ""),
        ("Data/Hora do envio", detalhes["data"].iloc[0]),
        ("Distrito", detalhes["distrito"].iloc[0]),
        ("Unidade (UBS)", detalhes["ubs"].iloc[0]),
        ("Status", status_atual),
    ]
    for rotulo, valor in campos:
        pdf.cell(0, 6, texto_pdf(f"{rotulo}: {valor}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if pedido_tem_item_parcial(detalhes, status_atual):
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, texto_pdf(AVISO_PARCIAL))
        pdf.set_font("Helvetica", "", 10)
    if "observacao" in detalhes.columns and pd.notna(detalhes["observacao"].iloc[0]):
        obs = str(detalhes["observacao"].iloc[0]).strip()
        if obs:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, texto_pdf("Observacoes:"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, texto_pdf(obs))
    pdf.ln(2)
    custo_total = 0.0
    for cat in detalhes["categoria"].unique():
        df_cat = detalhes[detalhes["categoria"] == cat]
        pdf.set_font("Helvetica", "B", 10)
        if sem_custo:
            pdf.cell(0, 7, texto_pdf(f"Categoria: {cat}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            larguras = [118, 36, 36]
            titulos = ["Material", "Solicitado", "Entregue"]
        else:
            subtotal = float(df_cat["custo_total"].sum()) if "custo_total" in df_cat.columns else 0.0
            custo_total += subtotal
            pdf.cell(0, 7, texto_pdf(f"Categoria: {cat}  |  Subtotal: {formatar_moeda_br(subtotal)}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            larguras = [78, 22, 22, 34, 34]
            titulos = ["Material", "Solic.", "Entregue", "Vl. unitario", "Custo"]
        for titulo, largura in zip(titulos, larguras):
            pdf_celula(pdf, largura, 7, titulo, negrito=True, alinhar="C")
        pdf.ln()
        for _, linha in df_cat.iterrows():
            if pdf.get_y() > 265:
                pdf.add_page()
            valores = [
                linha["material"],
                parse_numero(linha["quantidade"], True),
                parse_numero(linha.get("quantidade_entregue"), True),
            ]
            if not sem_custo:
                valores.extend([
                    formatar_moeda_br(linha.get("valor_unitario", 0)),
                    formatar_moeda_br(linha.get("custo_total", 0)),
                ])
            riscar_solicitado = item_solicitado_nao_reenviado(linha, status_atual)
            for i_val, (valor, largura) in enumerate(zip(valores, larguras)):
                pdf_celula(pdf, largura, 6, valor, riscado=(riscar_solicitado and i_val == 1))
            pdf.ln()
        pdf.ln(2)
    if not sem_custo:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, texto_pdf(f"Custo total efetivo: {formatar_moeda_br(custo_total)}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf_bloco_assinaturas(
        pdf,
        "Almoxarifado Central",
        "Assinatura e carimbo",
        "Recebimento na UBS",
        "Assinatura do responsavel",
    )
    return pdf_para_bytes(pdf)


def gerar_pdf_relatorio(df_print, titulo, distrito, ubs, periodo, parecer, extra_cabecalho=None, destacar_ultima=False):
    extra_cabecalho = extra_cabecalho or []
    if not FPDF_DISPONIVEL:
        parecer_limpo = re.sub(r"<[^>]+>", "", str(parecer))
        linhas = [
            "SECRETARIA MUNICIPAL DE SAUDE DE PELOTAS",
            str(titulo),
            "",
            f"Distrito / Unidade: {distrito} / {ubs}",
            f"Periodo abrangido: {periodo}",
            f"Data de emissao: {agora_sispac().strftime('%d/%m/%Y %H:%M')}",
        ]
        linhas.extend(str(item) for item in extra_cabecalho)
        linhas += ["", " | ".join(str(c) for c in df_print.columns)]
        for _, linha in df_print.iterrows():
            linhas.append(" | ".join(str(linha[c]) for c in df_print.columns))
        linhas += ["", "Parecer tecnico:", parecer_limpo, "", "Gestao do Almoxarifado - Assinatura e carimbo"]
        return gerar_pdf_basico(linhas)
    pdf = PdfSisPAC(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, texto_pdf("SECRETARIA MUNICIPAL DE SAUDE DE PELOTAS"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, texto_pdf(titulo), align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, texto_pdf(f"Distrito / Unidade: {distrito} / {ubs}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, texto_pdf(f"Periodo abrangido: {periodo}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, texto_pdf(f"Data de emissao: {agora_sispac().strftime('%d/%m/%Y %H:%M')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if extra_cabecalho:
        pdf.set_font("Helvetica", "B", 10)
        for item in extra_cabecalho:
            pdf.cell(0, 6, texto_pdf(item), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
    pdf.ln(3)
    colunas = [str(c) for c in df_print.columns]
    n = max(len(colunas), 1)
    largura_util = 190
    larguras = [largura_util / n] * n
    if "Material" in colunas:
        idx = colunas.index("Material")
        larguras[idx] = min(80, largura_util * 0.42)
        resto = largura_util - larguras[idx]
        outros = [i for i in range(n) if i != idx]
        if outros:
            largura_outro = resto / len(outros)
            for i in outros:
                larguras[i] = largura_outro
    for titulo_col, largura in zip(colunas, larguras):
        pdf_celula(pdf, largura, 7, titulo_col, negrito=True, alinhar="C")
    pdf.ln()
    ultima = len(df_print) - 1
    for i, (_, linha) in enumerate(df_print.iterrows()):
        if pdf.get_y() > 265:
            pdf.add_page()
        negrito = destacar_ultima and i == ultima
        for coluna, largura in zip(colunas, larguras):
            pdf_celula(pdf, largura, 6, linha[coluna], negrito=negrito)
        pdf.ln()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, texto_pdf("Parecer tecnico / administrativo preliminar:"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    parecer_limpo = re.sub(r"<[^>]+>", "", str(parecer))
    pdf.multi_cell(0, 5, texto_pdf(parecer_limpo))
    pdf_bloco_assinaturas(
        pdf,
        "Gestao do Almoxarifado",
        "Assinatura e carimbo",
    )
    return pdf_para_bytes(pdf)


def html_seguro(texto):
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def dataframe_para_html(df, destacar_ultima=False):
    cabecalho = "".join(f"<th>{html_seguro(col)}</th>" for col in df.columns)
    linhas = []
    total_linhas = len(df)
    for i, (_, linha) in enumerate(df.iterrows()):
        celulas = "".join(f"<td>{html_seguro(valor)}</td>" for valor in linha.tolist())
        estilo = ' style="font-weight:700;background:#eef3f4;"' if destacar_ultima and i == total_linhas - 1 else ""
        linhas.append(f"<tr{estilo}>{celulas}</tr>")
    return f"<table><thead><tr>{cabecalho}</tr></thead><tbody>{''.join(linhas)}</tbody></table>"


def adicionar_linha_total_relatorio(df, qtd_solicitada, qtd_entregue, custo_str=None):
    linha = {col: "" for col in df.columns}
    colunas = list(df.columns)
    if "Categoria" in linha:
        linha["Categoria"] = "TOTAL"
    elif colunas:
        linha[colunas[0]] = "TOTAL"
    if "Material" in linha and "Categoria" in linha:
        linha["Material"] = ""
    elif "Material" in linha:
        linha["Material"] = "TOTAL"
    if "Qtd Solicitada" in linha:
        linha["Qtd Solicitada"] = int(qtd_solicitada)
    if "Qtd Entregue" in linha:
        linha["Qtd Entregue"] = int(qtd_entregue)
    for col in colunas:
        if "Custo" in str(col) and custo_str:
            linha[col] = custo_str
    return pd.concat([df, pd.DataFrame([linha])], ignore_index=True)


def html_bloco_assinaturas(esquerda_titulo, esquerda_legenda, direita_titulo, direita_legenda):
    return textwrap.dedent(f"""\
    <div class="bloco-assinaturas">
    <div class="campo-assinatura">
    <div class="linha"></div>
    <p>{html_seguro(esquerda_titulo)}</p>
    <span>{html_seguro(esquerda_legenda)}</span>
    </div>
    <div class="campo-assinatura">
    <div class="linha"></div>
    <p>{html_seguro(direita_titulo)}</p>
    <span>{html_seguro(direita_legenda)}</span>
    </div>
    </div>
    """).strip()


def pdf_bloco_assinaturas(pdf, esquerda_titulo, esquerda_legenda, direita_titulo=None, direita_legenda=None):
    if pdf.get_y() > 245:
        pdf.add_page()
    pdf.ln(16)
    y = pdf.get_y() + 18
    if direita_titulo:
        pdf.line(20, y, 95, y)
        pdf.line(115, y, 190, y)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(20, y + 3)
        pdf.cell(75, 5, texto_pdf(esquerda_titulo), align="C")
        pdf.set_xy(20, y + 8)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(75, 5, texto_pdf(esquerda_legenda), align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(115, y + 3)
        pdf.cell(75, 5, texto_pdf(direita_titulo), align="C")
        pdf.set_xy(115, y + 8)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(75, 5, texto_pdf(direita_legenda), align="C")
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.line(55, y, 155, y)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(55, y + 3)
        pdf.cell(100, 5, texto_pdf(esquerda_titulo), align="C")
        pdf.set_xy(55, y + 8)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(100, 5, texto_pdf(esquerda_legenda), align="C")
        pdf.set_text_color(0, 0, 0)
    pdf.set_y(y + 16)


def formatar_moeda_br(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def formatar_data_br(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nat", "nan", "none", "nat"}:
        return ""
    try:
        return pd.to_datetime(valor).strftime("%d/%m/%Y")
    except Exception:
        return texto


def campo_valor_reais(rotulo, chave=None, ajuda="Digite como em reais: 1250 ou 87,38"):
    kwargs = {"placeholder": "Ex.: 1.250,00"}
    if chave:
        kwargs["key"] = chave
    if ajuda:
        kwargs["help"] = ajuda
    texto = st.text_input(rotulo, **kwargs)
    return parse_numero(texto)


def campo_data_br(rotulo, chave=None, valor=None):
    kwargs = {"value": valor or date.today(), "format": "DD/MM/YYYY"}
    if chave:
        kwargs["key"] = chave
    try:
        return st.date_input(rotulo, **kwargs)
    except TypeError:
        kwargs.pop("format", None)
        return st.date_input(rotulo, **kwargs)


def montar_html_comprovante(detalhes, status_atual, sem_custo=True):
    obs = ""
    if "observacao" in detalhes.columns and pd.notna(detalhes["observacao"].iloc[0]):
        obs = str(detalhes["observacao"].iloc[0]).strip()
    titulo_extra = " (via operacional)" if sem_custo else " (via gerencial)"
    blocos = []
    custo_total = 0.0
    for cat in detalhes["categoria"].unique():
        df_cat = detalhes[detalhes["categoria"] == cat]
        if sem_custo:
            linhas = "".join(
                f"<tr><td>{html_seguro(r['material'])}</td>"
                f"<td>{html_qtd_solicitada(r, status_atual)}</td>"
                f"<td>{parse_numero(r.get('quantidade_entregue'), True)}</td></tr>"
                for _, r in df_cat.iterrows()
            )
            tabela = (
                "<table><thead><tr><th>Material</th><th>Solicitado</th><th>Entregue</th></tr></thead>"
                f"<tbody>{linhas}</tbody></table>"
            )
            cab_cat = f"<p style='margin:10px 0 4px 0;'><b>Categoria: {html_seguro(cat)}</b></p>"
        else:
            subtotal = float(df_cat["custo_total"].sum()) if "custo_total" in df_cat.columns else 0.0
            custo_total += subtotal
            linhas = "".join(
                f"<tr><td>{html_seguro(r['material'])}</td>"
                f"<td>{html_qtd_solicitada(r, status_atual)}</td>"
                f"<td>{parse_numero(r.get('quantidade_entregue'), True)}</td>"
                f"<td>{formatar_moeda_br(r.get('valor_unitario', 0))}</td>"
                f"<td>{formatar_moeda_br(r.get('custo_total', 0))}</td></tr>"
                for _, r in df_cat.iterrows()
            )
            tabela = (
                "<table><thead><tr><th>Material</th><th>Solicitado</th><th>Entregue</th>"
                "<th>Valor unitário</th><th>Custo entregue</th></tr></thead>"
                f"<tbody>{linhas}</tbody></table>"
            )
            cab_cat = (
                f"<p style='margin:10px 0 4px 0;'><b>Categoria: {html_seguro(cat)}</b>"
                f" &nbsp; Subtotal: {formatar_moeda_br(subtotal)}</p>"
            )
        blocos.append(cab_cat + tabela)
    rodape_custo = "" if sem_custo else (
        f"<p style='margin-top:12px;padding:10px;border:1px solid #1abc9c;background:#e8f8f5;'>"
        f"<b>Custo total efetivo: {formatar_moeda_br(custo_total)}</b></p>"
    )
    obs_html = (
        f"<p style='margin-top:10px;padding:10px;border:1px solid #d35400;'>"
        f"<b>Observações:</b><br>{html_seguro(obs)}</p>" if obs else ""
    )
    aviso_parcial = (
        f"<p style='margin-top:10px;padding:10px;border:1px solid #922b21;background:#fdedec;'>"
        f"<b>{html_seguro(AVISO_PARCIAL)}</b></p>"
        if pedido_tem_item_parcial(detalhes, status_atual) else ""
    )
    meio = "".join(parte for parte in (aviso_parcial, obs_html, "".join(blocos), rodape_custo) if parte)
    assinaturas = html_bloco_assinaturas(
        "Almoxarifado Central",
        "Assinatura e carimbo",
        "Recebimento na UBS",
        "Assinatura do responsável",
    )
    return textwrap.dedent(f"""\
    <div class="area-impressao" style="padding:8px;background:#fff;">
    <h3 style="text-align:center;margin:0;">SECRETARIA MUNICIPAL DE SAÚDE DE PELOTAS</h3>
    <h4 style="text-align:center;color:#555;margin:6px 0 16px 0;">Comprovante de Requisição e Entrega — SisPAC{titulo_extra}</h4>
    <p><b>Nº do Pedido:</b> {html_seguro(detalhes['numero_pedido'].iloc[0] if 'numero_pedido' in detalhes.columns else '')}</p>
    <p><b>Data/Hora do envio:</b> {html_seguro(detalhes['data'].iloc[0])}</p>
    <p><b>Distrito:</b> {html_seguro(detalhes['distrito'].iloc[0])}</p>
    <p><b>Unidade (UBS):</b> {html_seguro(detalhes['ubs'].iloc[0])}</p>
    <p><b>Status:</b> {html_seguro(status_atual)}</p>
    {meio}
    {assinaturas}
    {html_rodape_impressao()}
    </div>
    """).strip()


def mapa_saidas_conferidas():
    saidas = {}
    try:
        resposta = supabase.table("pedidos").select("material,quantidade_entregue,status").execute()
        for linha in resposta.data or []:
            status = str(linha.get("status") or "")
            if status not in STATUS_SAIU_CENTRAL:
                continue
            material = str(linha.get("material") or "").strip()
            saidas[material] = saidas.get(material, 0) + parse_numero(linha.get("quantidade_entregue"), inteiro=True)
    except Exception:
        pass
    return saidas


def mapa_reservas_separadas():
    reservas = {}
    try:
        resposta = supabase.table("pedidos").select("material,quantidade_entregue,status").execute()
        for linha in resposta.data or []:
            if str(linha.get("status") or "") != STATUS_SEPARADO:
                continue
            material = str(linha.get("material") or "").strip()
            reservas[material] = reservas.get(material, 0) + parse_numero(linha.get("quantidade_entregue"), inteiro=True)
    except Exception:
        pass
    return reservas


def mapa_estoque_lotes():
    saldos = {}
    materiais_com_lote = set()
    try:
        resposta = supabase.table("estoque_central").select("material,quantidade_atual").execute()
        for linha in resposta.data or []:
            material = str(linha.get("material") or "").strip()
            if not material:
                continue
            materiais_com_lote.add(material)
            saldos[material] = saldos.get(material, 0) + parse_numero(linha.get("quantidade_atual"), inteiro=True)
    except Exception:
        pass
    return saldos, materiais_com_lote


def estoque_visivel(material, estoque_planilha, saidas, saldos_lote, materiais_com_lote, reservas=None):
    material = str(material or "").strip()
    reservado = (reservas or {}).get(material, 0)
    if material in materiais_com_lote:
        return max(0, saldos_lote.get(material, 0) - reservado)
    return max(0, parse_numero(estoque_planilha, inteiro=True) - (saidas or {}).get(material, 0) - reservado)


def quadro_cadastro_estoque(df_fonte, col_cat, col_mat, col_preco, df_catalogo, col_mat_cat, col_est_cat, saidas, saldos_lote, materiais_com_lote):
    if df_fonte is None or df_fonte.empty:
        return pd.DataFrame(columns=["Categoria", "Material", "Valor unitário", "Estoque atual", "Valor total"])
    mapa_planilha = mapa_estoque_planilha(df_catalogo, col_mat_cat, col_est_cat)
    reservas = mapa_reservas_separadas()
    linhas = []
    for _, row in df_fonte.iterrows():
        material = str(row.get(col_mat) or "").strip()
        if not material or material in MATERIAIS_INVALIDOS:
            continue
        categoria = str(row.get(col_cat) or "").strip() if col_cat else ""
        valor_unit = parse_numero(row.get(col_preco) if col_preco else 0)
        estoque = estoque_visivel(
            material,
            mapa_planilha.get(material, 0),
            saidas or {},
            saldos_lote or {},
            materiais_com_lote or set(),
            reservas=reservas,
        )
        linhas.append({
            "Categoria": categoria,
            "Material": material,
            "Valor unitário": formatar_moeda_br(valor_unit),
            "Estoque atual": int(estoque),
            "Valor total": formatar_moeda_br(estoque * valor_unit),
        })
    if not linhas:
        return pd.DataFrame(columns=["Categoria", "Material", "Valor unitário", "Estoque atual", "Valor total"])
    return pd.DataFrame(linhas)


def mapa_estoque_planilha(df_materiais, col_material, col_estoque):
    mapa = {}
    if df_materiais is None or df_materiais.empty or not col_material:
        return mapa
    for _, linha in df_materiais.iterrows():
        material = str(linha.get(col_material) or "").strip()
        if not material:
            continue
        mapa[material] = parse_numero(linha.get(col_estoque), inteiro=True) if col_estoque else 0
    return mapa


def demanda_pendente_material(df_pedidos, material, numero_pedido_atual=None):
    resumo = {
        "total": 0,
        "este_pedido": 0,
        "outras_ubs": 0,
        "linhas": [],
    }
    if df_pedidos is None or df_pedidos.empty:
        return resumo
    material = str(material or "").strip()
    for _, linha in df_pedidos.iterrows():
        if str(linha.get("material") or "").strip() != material:
            continue
        status = str(linha.get("status") or STATUS_PEDIDO_ENVIADO)
        if status != STATUS_PEDIDO_ENVIADO:
            continue
        quantidade = parse_numero(linha.get("quantidade"), inteiro=True)
        numero = str(linha.get("numero_pedido") or "")
        ubs = str(linha.get("ubs") or "")
        eh_este = numero == str(numero_pedido_atual or "")
        resumo["total"] += quantidade
        if eh_este:
            resumo["este_pedido"] += quantidade
        else:
            resumo["outras_ubs"] += quantidade
        resumo["linhas"].append({
            "ubs": ubs,
            "numero_pedido": numero,
            "quantidade": quantidade,
            "este_pedido": eh_este,
        })
    return resumo


def texto_outras_solicitacoes(resumo):
    if not resumo["linhas"]:
        return "Nenhum outro pedido pendente deste item."
    partes = []
    for linha in resumo["linhas"]:
        if linha["este_pedido"]:
            continue
        partes.append(f"{linha['ubs']} ({linha['numero_pedido']}: {linha['quantidade']} un.)")
    return "; ".join(partes) if partes else "Nenhuma outra UBS aguardando este item."


def quantidade_sugerida_pedido(estoque):
    estoque = parse_numero(estoque, inteiro=True)
    if estoque <= 0:
        return 1
    if estoque <= LIMIAR_ESTOQUE_BAIXO:
        return estoque
    return 10


def ativar_filtro_digitacao():
    components.html(
        """
<script>
(function() {
  const doc = window.parent.document;
  function ligar(input) {
    if (!input || input.dataset.sispacLive === "1") return;
    input.dataset.sispacLive = "1";
    input.addEventListener("input", function() {
      const el = this;
      clearTimeout(el._sispacT);
      el._sispacT = setTimeout(function() {
        const pos = el.selectionStart;
        el.dispatchEvent(new Event("change", { bubbles: true }));
        el.blur();
        el.focus();
        try { if (pos != null) el.setSelectionRange(pos, pos); } catch (err) {}
      }, 140);
    });
  }
  function procurar() {
    doc.querySelectorAll(
      'input[aria-label="Filtrar pelo nome do material"], .st-key-filtro_nome_catalogo input, input[aria-label="Buscar material cadastrado"], .st-key-filtro_materiais_cadastro input'
    ).forEach(ligar);
  }
  procurar();
  new MutationObserver(procurar).observe(doc.body, { childList: true, subtree: true });
})();
</script>
        """,
        height=0,
        width=0,
    )


def incluir_item_carrinho(distrito, ubs, categoria, material, quantidade, valor_unitario):
    quantidade = max(1, parse_numero(quantidade, inteiro=True))
    valor_unitario = parse_numero(valor_unitario)
    item_existente = next(
        (item for item in st.session_state.carrinho
         if item["material"] == material and item["ubs"] == ubs),
        None
    )
    if item_existente:
        item_existente["quantidade"] += quantidade
        item_existente["valor_unitario"] = valor_unitario
        item_existente["subtotal"] = item_existente["quantidade"] * valor_unitario
        return f"Quantidade atualizada: {item_existente['quantidade']}x {material}"
    st.session_state.carrinho.append({
        "distrito": distrito,
        "ubs": ubs,
        "categoria": categoria,
        "material": material,
        "quantidade": quantidade,
        "valor_unitario": valor_unitario,
        "subtotal": quantidade * valor_unitario,
    })
    return f"Adicionado: {quantidade}x {material}"


def sugerir_rateio(quantidades_pedidas, estoque):
    estoque = max(0, parse_numero(estoque, inteiro=True))
    pedidos = [max(0, parse_numero(q, inteiro=True)) for q in quantidades_pedidas]
    demanda = sum(pedidos)
    if not pedidos:
        return []
    if demanda <= 0:
        return [0] * len(pedidos)
    if estoque >= demanda:
        return pedidos[:]
    rateio = [int(estoque * q / demanda) for q in pedidos]
    resto = estoque - sum(rateio)
    while resto > 0:
        avançou = False
        for i, qtd in enumerate(pedidos):
            if resto <= 0:
                break
            if rateio[i] < qtd:
                rateio[i] += 1
                resto -= 1
                avançou = True
        if not avançou:
            break
    return rateio


def _rpc_ausente(erro):
    texto = str(erro).lower()
    return any(trecho in texto for trecho in (
        "could not find the function",
        "pgrst202",
        "schema cache",
        "does not exist",
    ))


def registrar_auditoria(acao, entidade="", detalhe=""):
    try:
        supabase.table("sispac_auditoria").insert({
            "usuario": st.session_state.get("email_usuario"),
            "acao": acao,
            "entidade": entidade,
            "detalhe": str(detalhe)[:500],
        }).execute()
    except Exception:
        pass


def carregar_materiais_banco():
    try:
        resposta = supabase.table("materiais").select("*").execute()
        return pd.DataFrame(resposta.data or [])
    except Exception:
        return pd.DataFrame()


def mesclar_materiais_banco(df_planilha, col_categoria, col_material, col_estoque, col_preco):
    df_banco = carregar_materiais_banco()
    if df_banco.empty:
        return df_planilha
    df_banco.columns = [str(c).strip().lower() for c in df_banco.columns]
    if "material" not in df_banco.columns:
        return df_planilha
    if df_planilha is None or df_planilha.empty:
        col_categoria = col_categoria or "Categoria"
        col_material = col_material or "Material"
        col_preco = col_preco or "Valor Unitário"
        col_estoque = col_estoque or "Estoque"
        linhas = []
        for _, row in df_banco.iterrows():
            linhas.append({
                col_categoria: str(row.get("categoria") or "Cadastro SisPAC").strip(),
                col_material: str(row.get("material") or "").strip(),
                col_preco: parse_numero(row.get("valor_unitario")),
                col_estoque: 0,
            })
        return pd.DataFrame(linhas)
    nomes = set(df_planilha[col_material].astype(str).str.strip()) if col_material else set()
    novas = []
    for _, row in df_banco.iterrows():
        nome = str(row.get("material") or "").strip()
        if not nome:
            continue
        preco = parse_numero(row.get("valor_unitario"))
        cat = str(row.get("categoria") or "Cadastro SisPAC").strip()
        if nome in nomes:
            if col_preco:
                mask = df_planilha[col_material].astype(str).str.strip() == nome
                df_planilha.loc[mask, col_preco] = preco
        else:
            nova = {c: None for c in df_planilha.columns}
            if col_categoria:
                nova[col_categoria] = cat
            if col_material:
                nova[col_material] = nome
            if col_preco:
                nova[col_preco] = preco
            if col_estoque:
                nova[col_estoque] = 0
            novas.append(nova)
            nomes.add(nome)
    if novas:
        df_planilha = pd.concat([df_planilha, pd.DataFrame(novas)], ignore_index=True)
    return df_planilha


def persistir_entregas(atualizacoes, obs_g=""):
    if not atualizacoes:
        return
    usuario = st.session_state.get("email_usuario")
    persistir_entregas_legado(atualizacoes, obs_g, usuario, baixar_estoque=False, creditar_ubs=False)
    numeros = [str(item[2].get("numero_pedido") or "") for item in atualizacoes]
    marcar_pedidos_separados(numeros)
    registrar_auditoria(
        "SEPARACAO",
        "pedidos",
        f"{len(atualizacoes)} item(ns); {', '.join({n for n in numeros if n})}",
    )


def persistir_entregas_legado(atualizacoes, obs_g="", usuario=None, baixar_estoque=False, creditar_ubs=False):
    numeros_afetados = []
    for row_id, nova_qtd, row_original in atualizacoes:
        qtd_ja_entregue = parse_numero(row_original.get("quantidade_entregue"), inteiro=True)
        delta_estoque = nova_qtd - qtd_ja_entregue
        v_unit = float(row_original.get("valor_unitario") or 0)
        dados_update = {
            "quantidade_entregue": nova_qtd,
            "custo_total": nova_qtd * v_unit,
        }
        if obs_g:
            obs_ubs = str(row_original.get("observacao") or "").split(" | Gestão:")[0].strip()
            dados_update["observacao"] = f"{obs_ubs} | Gestão: {obs_g}" if obs_ubs else f"Gestão: {obs_g}"
        consulta = supabase.table("pedidos").update(dados_update).eq("id", row_id)
        if qtd_ja_entregue:
            consulta = consulta.eq("quantidade_entregue", qtd_ja_entregue)
        resposta = consulta.execute()
        if resposta.data is not None and len(resposta.data) == 0:
            raise RuntimeError(
                "Outra pessoa já conferiu um destes itens. Atualize a página e salve de novo."
            )
        if baixar_estoque:
            aplicar_baixa_estoque_central(
                str(row_original.get("material") or "").strip(),
                delta_estoque,
                usuario=usuario,
                numero_pedido=str(row_original.get("numero_pedido") or ""),
                observacao=obs_g,
            )
        numeros_afetados.append(str(row_original.get("numero_pedido") or ""))
    if creditar_ubs:
        creditar_entregas_nas_ubs(atualizacoes, usuario)
    return numeros_afetados


def marcar_pedidos_separados(numeros):
    for numero in {n for n in numeros if n}:
        resposta = supabase.table("pedidos").select("id,quantidade_entregue").eq("numero_pedido", numero).execute()
        linhas = resposta.data or []
        if not linhas:
            continue
        if any(parse_numero(linha.get("quantidade_entregue"), inteiro=True) > 0 for linha in linhas):
            aplicar_status_pedido(numero, STATUS_SEPARADO)


def aplicar_status_pedido(numero, status):
    supabase.table("pedidos").update({"status": status}).eq("numero_pedido", str(numero)).execute()


def despachar_pedido(numero):
    usuario = st.session_state.get("email_usuario")
    resposta = supabase.table("pedidos").select("*").eq("numero_pedido", str(numero)).execute()
    linhas = resposta.data or []
    if not linhas:
        raise RuntimeError("Pedido não encontrado.")
    status = status_consolidado_pedido(pd.DataFrame(linhas))
    if not pedido_separado(status):
        raise RuntimeError("Só é possível despachar pedido já separado pelo almoxarifado.")
    for linha in linhas:
        qtd = parse_numero(linha.get("quantidade_entregue"), inteiro=True)
        if qtd <= 0:
            continue
        aplicar_baixa_estoque_central(
            str(linha.get("material") or "").strip(),
            qtd,
            usuario=usuario,
            numero_pedido=str(numero),
            observacao="Saída para entrega / em trânsito",
        )
    aplicar_status_pedido(numero, STATUS_TRANSITO)
    registrar_auditoria("DESPACHO", "pedidos", str(numero))


def confirmar_recebimento_ubs(numero, recebidos_por_id=None):
    usuario = st.session_state.get("email_usuario")
    resposta = supabase.table("pedidos").select("*").eq("numero_pedido", str(numero)).execute()
    linhas = resposta.data or []
    if not linhas:
        raise RuntimeError("Pedido não encontrado.")
    status = status_consolidado_pedido(pd.DataFrame(linhas))
    if not pedido_em_transito(status):
        raise RuntimeError("Este pedido ainda não saiu para entrega.")
    ubs_pedido = str(linhas[0].get("ubs") or "").strip().lower()
    ubs_sessao = str(st.session_state.get("ubs_nome") or "").strip().lower()
    if st.session_state.get("perfil") == "UBS" and ubs_pedido != ubs_sessao:
        raise RuntimeError("Esta unidade só confirma o recebimento dos próprios pedidos.")
    alguma_falta = False
    atualizacoes_credito = []
    for linha in linhas:
        enviado = parse_numero(linha.get("quantidade_entregue"), inteiro=True)
        recebido = enviado
        if recebidos_por_id is not None:
            recebido = parse_numero(recebidos_por_id.get(linha.get("id"), enviado), inteiro=True)
            recebido = max(0, min(enviado, recebido))
        if recebido < enviado:
            alguma_falta = True
        dados = {"quantidade_recebida": recebido}
        try:
            supabase.table("pedidos").update(dados).eq("id", linha["id"]).execute()
        except Exception:
            pass
        if recebido > 0:
            atualizacoes_credito.append((linha["id"], recebido, {**linha, "quantidade_entregue": 0}))
    if atualizacoes_credito:
        creditar_entregas_nas_ubs(atualizacoes_credito, usuario)
    pedida_ok = True
    for linha in linhas:
        pedida = parse_numero(linha.get("quantidade"), inteiro=True)
        enviado = parse_numero(linha.get("quantidade_entregue"), inteiro=True)
        recebido = enviado
        if recebidos_por_id is not None:
            recebido = parse_numero(recebidos_por_id.get(linha.get("id"), enviado), inteiro=True)
        if recebido < pedida:
            pedida_ok = False
    if alguma_falta or not pedida_ok:
        aplicar_status_pedido(numero, STATUS_ATENDIDO_PARCIAL)
        if alguma_falta:
            registrar_auditoria("RECEBIMENTO_DIVERGENCIA", "pedidos", str(numero))
        else:
            registrar_auditoria("RECEBIMENTO_UBS", "pedidos", str(numero))
    else:
        aplicar_status_pedido(numero, STATUS_ATENDIDO_INTEGRAL)
        registrar_auditoria("RECEBIMENTO_UBS", "pedidos", str(numero))


def atualizar_status_pedidos(numeros):
    for numero in {n for n in numeros if n}:
        resposta = supabase.table("pedidos").select("id,quantidade,quantidade_entregue").eq("numero_pedido", numero).execute()
        linhas = resposta.data or []
        if not linhas:
            continue
        integral = True
        alguma_entrega = False
        for linha in linhas:
            pedida = parse_numero(linha.get("quantidade"), inteiro=True)
            entregue = parse_numero(linha.get("quantidade_entregue"), inteiro=True)
            if entregue > 0:
                alguma_entrega = True
            if entregue < pedida:
                integral = False
        if integral and alguma_entrega:
            status = "Atendido Integralmente"
        elif alguma_entrega:
            status = "Atendido Parcialmente"
        else:
            continue
        for linha in linhas:
            supabase.table("pedidos").update({"status": status}).eq("id", linha["id"]).execute()


def aplicar_baixa_estoque_central(material, delta, usuario=None, numero_pedido=None, observacao=None):
    delta = int(delta or 0)
    if delta == 0 or not material:
        return
    try:
        supabase.rpc("sispac_movimentar_estoque", {
            "p_material": material,
            "p_quantidade": delta,
            "p_usuario": usuario,
            "p_numero_pedido": numero_pedido,
            "p_observacao": observacao,
        }).execute()
        return
    except Exception as erro:
        if not _rpc_ausente(erro):
            return
    try:
        resposta = supabase.table("estoque_central").select("id,quantidade_atual,validade,lote").eq("material", material).execute()
        lotes = resposta.data or []
        if not lotes:
            return
        lotes = sorted(lotes, key=lambda lote: str(lote.get("validade") or "9999-12-31"))
        if delta > 0:
            restante = delta
            for lote in lotes:
                if restante <= 0:
                    break
                atual = parse_numero(lote.get("quantidade_atual"), inteiro=True)
                if atual <= 0:
                    continue
                retirar = min(atual, restante)
                novo_saldo = atual - retirar
                supabase.table("estoque_central").update({
                    "quantidade_atual": novo_saldo
                }).eq("id", lote["id"]).eq("quantidade_atual", atual).execute()
                restante -= retirar
        else:
            devolver = abs(delta)
            lote = lotes[0]
            atual = parse_numero(lote.get("quantidade_atual"), inteiro=True)
            supabase.table("estoque_central").update({
                "quantidade_atual": atual + devolver
            }).eq("id", lote["id"]).eq("quantidade_atual", atual).execute()
    except Exception:
        pass


def creditar_entregas_nas_ubs(atualizacoes, usuario=None):
    for _row_id, nova_qtd, row_original in atualizacoes:
        delta = int(nova_qtd) - parse_numero(row_original.get("quantidade_entregue"), inteiro=True)
        tipo = "ENTRADA" if delta > 0 else "ESTORNO"
        try:
            aplicar_estoque_ubs(
                str(row_original.get("ubs") or "").strip(),
                str(row_original.get("material") or "").strip(),
                delta,
                tipo=tipo,
                usuario=usuario,
                numero_pedido=str(row_original.get("numero_pedido") or ""),
                observacao="Entrada pelo recebimento na UBS",
                distrito=str(row_original.get("distrito") or "").strip(),
            )
        except Exception:
            registrar_auditoria(
                "FALHA_ESTOQUE_UBS",
                "estoque_ubs",
                f"{row_original.get('ubs')} / {row_original.get('material')} / {delta}",
            )


def aplicar_estoque_ubs(
    ubs,
    material,
    delta,
    tipo="CONSUMO",
    usuario=None,
    numero_pedido=None,
    observacao=None,
    distrito=None,
):
    delta = int(delta or 0)
    ubs = str(ubs or "").strip()
    material = str(material or "").strip()
    if delta == 0 or not ubs or not material:
        return
    try:
        supabase.rpc("sispac_movimentar_estoque_ubs", {
            "p_ubs": ubs,
            "p_material": material,
            "p_quantidade": delta,
            "p_usuario": usuario or st.session_state.get("email_usuario"),
            "p_numero_pedido": numero_pedido,
            "p_observacao": observacao,
            "p_distrito": distrito,
            "p_tipo": tipo,
        }).execute()
        return
    except Exception as erro:
        if "SISPAC_UBS_SALDO" in str(erro):
            raise RuntimeError(
                "Esta unidade não tem saldo suficiente deste material para baixar."
            ) from erro
        if not _rpc_ausente(erro):
            raise
    try:
        resposta = supabase.table("estoque_ubs").select("id,quantidade_atual,ubs,material").execute()
        linhas = [
            linha for linha in (resposta.data or [])
            if str(linha.get("ubs") or "").strip().lower() == ubs.lower()
            and str(linha.get("material") or "").strip().lower() == material.lower()
        ]
        if not linhas:
            if delta < 0:
                raise RuntimeError("Esta unidade não tem saldo suficiente deste material para baixar.")
            supabase.table("estoque_ubs").insert({
                "ubs": ubs,
                "distrito": distrito or "",
                "material": material,
                "quantidade_atual": delta,
            }).execute()
            novo = delta
        else:
            atual = parse_numero(linhas[0].get("quantidade_atual"), inteiro=True)
            novo = atual + delta
            if novo < 0:
                raise RuntimeError("Esta unidade não tem saldo suficiente deste material para baixar.")
            supabase.table("estoque_ubs").update({
                "quantidade_atual": novo,
            }).eq("id", linhas[0]["id"]).execute()
        supabase.table("movimentos_estoque_ubs").insert({
            "tipo": tipo,
            "ubs": ubs,
            "distrito": distrito or "",
            "material": material,
            "quantidade": delta,
            "saldo_apos": novo,
            "numero_pedido": numero_pedido,
            "usuario": usuario or st.session_state.get("email_usuario"),
            "observacao": observacao,
        }).execute()
    except RuntimeError:
        raise
    except Exception:
        pass


def carregar_estoque_ubs(ubs=None):
    try:
        resposta = supabase.table("estoque_ubs").select("*").execute()
        df = pd.DataFrame(resposta.data or [])
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    if ubs:
        df = df[df["ubs"].astype(str).str.strip().str.lower() == str(ubs).strip().lower()]
    if "quantidade_atual" in df.columns:
        df = df.sort_values(by=["ubs", "material"], kind="stable")
    return df


def carregar_movimentos_ubs(ubs=None, limite=100):
    try:
        resposta = (
            supabase.table("movimentos_estoque_ubs")
            .select("*")
            .order("criado_em", desc=True)
            .limit(limite)
            .execute()
        )
        df = pd.DataFrame(resposta.data or [])
    except Exception:
        return pd.DataFrame()
    if df.empty or not ubs:
        return df
    return df[df["ubs"].astype(str).str.strip().str.lower() == str(ubs).strip().lower()]


def _erro_tabela_ausente(erro):
    texto = str(erro).lower()
    return any(trecho in texto for trecho in (
        "does not exist",
        "pgrst205",
        "schema cache",
        "could not find the table",
        "relation",
    )) and any(nome in texto for nome in ("sispac_empenhos", "sispac_notas_fiscais", "notas_fiscais"))


@st.cache_data(ttl=30)
def _fetch_empenhos():
    resposta = (
        supabase.table("sispac_empenhos")
        .select("*")
        .order("data_empenho", desc=True)
        .execute()
    )
    return resposta.data or []


@st.cache_data(ttl=30)
def _fetch_notas_resumo():
    resposta = supabase.table("sispac_notas_fiscais").select("id,empenho_id,valor_nf").execute()
    return resposta.data or []


def limpar_cache_empenhos():
    try:
        _fetch_empenhos.clear()
        _fetch_notas_resumo.clear()
    except Exception:
        pass


def carregar_empenhos():
    try:
        return pd.DataFrame(_fetch_empenhos()), None
    except Exception as e:
        return pd.DataFrame(), e


def carregar_notas_empenho(empenho_id=None):
    try:
        if empenho_id is None:
            return pd.DataFrame(_fetch_notas_resumo() or []), None
        consulta = (
            supabase.table("sispac_notas_fiscais")
            .select("*")
            .eq("empenho_id", int(empenho_id))
            .order("data_emissao", desc=True)
        )
        resposta = consulta.execute()
        return pd.DataFrame(resposta.data or []), None
    except Exception as e:
        return pd.DataFrame(), e


BUCKET_DOCUMENTOS = "sispac-documentos"
TIPOS_PDF_EMPENHO = ["pdf", "png", "jpg", "jpeg"]


def mime_arquivo(nome):
    nome = str(nome or "").lower()
    if nome.endswith(".png"):
        return "image/png"
    if nome.endswith(".jpg") or nome.endswith(".jpeg"):
        return "image/jpeg"
    return "application/pdf"


def extensao_arquivo(nome):
    nome = str(nome or "").lower()
    if nome.endswith(".png"):
        return "png"
    if nome.endswith(".jpg") or nome.endswith(".jpeg"):
        return "jpg"
    return "pdf"


def enviar_pdf_sispac(arquivo, pasta, nome_base):
    if arquivo is None:
        return None, None
    conteudo = arquivo.getvalue()
    if not conteudo:
        return None, None
    if len(conteudo) > 15 * 1024 * 1024:
        raise RuntimeError("O arquivo ultrapassa 15 MB. Envie um PDF ou imagem menor.")
    ext = extensao_arquivo(arquivo.name)
    caminho = f"{pasta}/{slug_arquivo(nome_base)}_{agora_sispac().strftime('%Y%m%d%H%M%S')}.{ext}"
    supabase.storage.from_(BUCKET_DOCUMENTOS).upload(
        caminho,
        conteudo,
        {"content-type": mime_arquivo(arquivo.name), "upsert": "true"},
    )
    return caminho, str(arquivo.name)


def url_documento_sispac(caminho):
    if not caminho:
        return None
    try:
        return supabase.storage.from_(BUCKET_DOCUMENTOS).get_public_url(caminho)
    except Exception:
        return None


def gravar_pdf_registro(tabela, registro_id, caminho, nome):
    supabase.table(tabela).update({
        "pdf_caminho": caminho,
        "pdf_nome": nome,
    }).eq("id", int(registro_id)).execute()
    limpar_cache_empenhos()


def bloco_pdf_registro(rotulo, caminho, nome, chave_dl):
    if not caminho:
        st.caption(f"{rotulo}: nenhum arquivo ainda.")
        return
    nome_exibir = nome or "documento.pdf"
    url = url_documento_sispac(caminho)
    if url:
        st.link_button(f"Abrir / baixar {rotulo} ({nome_exibir})", url, use_container_width=True)
    else:
        st.caption("Link do arquivo indisponível.")


def html_linha_empenho(numero, fornecedor, valor, notas, pdf, data, cabecalho=False, selecionado=False):
    classes = "linha-empenho"
    if cabecalho:
        classes += " linha-empenho-cab"
    if selecionado:
        classes += " linha-sel"
    return (
        f"<div class='{classes}'>"
        f"<span class='emp-num'>{html_seguro(numero)}</span>"
        f"<span class='emp-forn'>{html_seguro(fornecedor)}</span>"
        f"<span class='emp-valor'>{html_seguro(valor)}</span>"
        f"<span class='emp-notas'>{html_seguro(notas)}</span>"
        f"<span class='emp-pdf'>{html_seguro(pdf)}</span>"
        f"<span class='emp-data emp-meta'>{html_seguro(data)}</span>"
        "<span class='emp-abrir'></span>"
        "</div>"
    )


def html_linha_nota(numero, emissao, valor, pdf, cabecalho=False, selecionado=False):
    classes = "linha-empenho linha-nota"
    if cabecalho:
        classes += " linha-empenho-cab"
    if selecionado:
        classes += " linha-sel"
    return (
        f"<div class='{classes}'>"
        f"<span class='emp-num'>{html_seguro(numero)}</span>"
        f"<span class='emp-forn'>{html_seguro(emissao)}</span>"
        f"<span class='emp-valor'>{html_seguro(valor)}</span>"
        f"<span class='emp-pdf emp-meta'>{html_seguro(pdf)}</span>"
        "<span class='emp-abrir'></span>"
        "</div>"
    )


def rotulo_empenho(linha):
    numero = str(linha.get("numero_empenho") or "").strip()
    ano = str(linha.get("ano") or "").strip()
    if ano and (numero.endswith(f"/{ano}") or numero.endswith(f"-{ano}")):
        texto = numero
    elif ano:
        texto = f"{numero}/{ano}"
    else:
        texto = numero
    fornecedor = str(linha.get("fornecedor") or "").strip()
    if fornecedor:
        return f"{texto} — {fornecedor}"
    return texto


def abrir_empenho_lista(empenho_id):
    st.session_state.empenho_aberto = int(empenho_id)
    st.session_state.nota_aberta = None
    st.session_state.mostrar_notas_empenho = False
    st.rerun()


def fechar_empenho_lista():
    st.session_state.empenho_aberto = None
    st.session_state.nota_aberta = None
    st.session_state.mostrar_notas_empenho = False
    st.rerun()


def limpar_formulario_nota_fiscal():
    for chave in (
        "sel_nf_empenho",
        "sel_empenho_nota",
        "nf_numero",
        "nf_serie",
        "data_emissao_nf",
        "valor_nota_txt",
        "nf_chave",
        "nf_obs",
        "pdf_nova_nota",
    ):
        st.session_state.pop(chave, None)
    st.session_state.nota_aberta = None
    st.session_state.mostrar_notas_empenho = False


def render_painel_empenhos(usuario_atual):
    st.markdown("#### Empenhos e notas fiscais")
    st.caption(
        "Neste espaço entra só o empenho e as notas fiscais ligadas a ele. "
        "Clique no texto da linha para selecionar. Anexe o PDF do empenho e da nota digitalizada."
    )

    df_empenhos, erro_emp = carregar_empenhos()
    if erro_emp is not None:
        if _erro_tabela_ausente(erro_emp) or _rpc_ausente(erro_emp):
            st.warning(
                "As tabelas de empenho ainda não existem no banco. "
                "Execute o arquivo `supabase/sispac_empenhos.sql` no SQL Editor do Supabase e dê Reboot."
            )
            return
        st.error(f"Não foi possível ler os empenhos: {erro_emp}")
        return

    col_emp, col_nf = st.columns(2, gap="medium")
    with col_emp:
        st.markdown("##### Novo empenho")
        with st.form("form_novo_empenho"):
            numero_emp = st.text_input("Número do empenho")
            data_emp = campo_data_br("Data do empenho")
            fornecedor_emp = st.text_input("Fornecedor")
            cnpj_emp = st.text_input("CNPJ (opcional)")
            valor_emp = campo_valor_reais("Valor do empenho (R$)", chave="valor_empenho_txt")
            objeto_emp = st.text_area("Objeto / descrição (opcional)", height=80)
            obs_emp = st.text_input("Observação (opcional)")
            pdf_emp = st.file_uploader(
                "PDF do empenho (digitalizado)",
                type=TIPOS_PDF_EMPENHO,
                key="pdf_novo_empenho",
            )
            if st.form_submit_button("Registrar empenho"):
                numero_limpo = str(numero_emp or "").strip()
                if not numero_limpo:
                    st.error("Informe o número do empenho.")
                else:
                    pdf_caminho = None
                    pdf_nome = None
                    try:
                        pdf_caminho, pdf_nome = enviar_pdf_sispac(pdf_emp, "empenhos", numero_limpo)
                    except Exception as e:
                        st.warning(f"O empenho será salvo, mas o PDF não entrou: {e}")
                    dados_emp = {
                        "numero_empenho": numero_limpo,
                        "ano": int(data_emp.year),
                        "data_empenho": data_emp.strftime("%Y-%m-%d"),
                        "fornecedor": str(fornecedor_emp or "").strip(),
                        "cnpj": str(cnpj_emp or "").strip(),
                        "objeto": str(objeto_emp or "").strip(),
                        "valor_empenho": float(valor_emp or 0),
                        "observacao": str(obs_emp or "").strip(),
                        "criado_por": usuario_atual,
                    }
                    if pdf_caminho:
                        dados_emp["pdf_caminho"] = pdf_caminho
                        dados_emp["pdf_nome"] = pdf_nome
                    try:
                        resposta = supabase.table("sispac_empenhos").insert(dados_emp).execute()
                        novo_id = (resposta.data or [{}])[0].get("id")
                        if novo_id:
                            st.session_state.empenho_aberto = int(novo_id)
                        registrar_auditoria("CADASTRO_EMPENHO", "sispac_empenhos", numero_limpo)
                        limpar_cache_empenhos()
                        st.success(f"Empenho {numero_limpo} registrado.")
                        st.rerun()
                    except Exception as e:
                        if "duplicate" in str(e).lower() or "23505" in str(e):
                            st.error("Este número de empenho já está cadastrado neste ano.")
                        elif "pdf_caminho" in str(e).lower() or "pgrst" in str(e).lower():
                            try:
                                dados_emp.pop("pdf_caminho", None)
                                dados_emp.pop("pdf_nome", None)
                                supabase.table("sispac_empenhos").insert(dados_emp).execute()
                                st.warning("Empenho salvo. Rode de novo o SQL `sispac_empenhos.sql` para gravar o PDF.")
                                st.rerun()
                            except Exception as e2:
                                st.error(f"Não foi possível registrar o empenho: {e2}")
                        else:
                            st.error(f"Não foi possível registrar o empenho: {e}")

    with col_nf:
        st.markdown("<h5 style='margin:0.15rem 0 0.3rem 0;'>Nota fiscal do empenho</h5>", unsafe_allow_html=True)
        if st.session_state.pop("_limpar_form_nf", False):
            limpar_formulario_nota_fiscal()
        if df_empenhos.empty:
            st.info("Cadastre um empenho ao lado para lançar as notas nele.")
        else:
            opcoes_emp = df_empenhos.to_dict("records")
            rotulos = [rotulo_empenho(r) for r in opcoes_emp]
            escolha = st.selectbox(
                "Empenho da nota",
                rotulos,
                index=None,
                placeholder="Selecione o empenho desta nota",
                key="sel_nf_empenho",
                label_visibility="collapsed",
            )
            if not escolha:
                st.caption("Selecione o empenho desta nota. Depois do lançamento, o campo volta vazio.")
            else:
                empenho_nf = opcoes_emp[[rotulo_empenho(r) for r in opcoes_emp].index(escolha)]
                with st.form("form_nova_nota", clear_on_submit=True):
                    numero_nf = st.text_input("Número da nota fiscal", key="nf_numero")
                    c_ser, c_dt = st.columns(2)
                    with c_ser:
                        serie_nf = st.text_input("Série (opcional)", key="nf_serie")
                    with c_dt:
                        data_nf = campo_data_br("Data de emissão", chave="data_emissao_nf")
                    valor_nf = campo_valor_reais("Valor da nota (R$)", chave="valor_nota_txt")
                    chave_nf = st.text_input("Chave de acesso (opcional)", key="nf_chave")
                    obs_nf = st.text_input("Observação da nota (opcional)", key="nf_obs")
                    pdf_nf = st.file_uploader(
                        "PDF da nota fiscal digitalizada",
                        type=TIPOS_PDF_EMPENHO,
                        key="pdf_nova_nota",
                    )
                    if st.form_submit_button("Lançar nota no empenho"):
                        numero_nf_limpo = str(numero_nf or "").strip()
                        if not numero_nf_limpo:
                            st.error("Informe o número da nota fiscal.")
                        else:
                            pdf_caminho = None
                            pdf_nome = None
                            try:
                                pdf_caminho, pdf_nome = enviar_pdf_sispac(
                                    pdf_nf,
                                    f"notas/{empenho_nf.get('numero_empenho')}",
                                    numero_nf_limpo,
                                )
                            except Exception as e:
                                st.warning(f"A nota será salva, mas o PDF não entrou: {e}")
                            dados_nf = {
                                "empenho_id": int(empenho_nf["id"]),
                                "numero_nf": numero_nf_limpo,
                                "serie": str(serie_nf or "").strip(),
                                "data_emissao": data_nf.strftime("%Y-%m-%d"),
                                "valor_nf": float(valor_nf or 0),
                                "chave_acesso": str(chave_nf or "").strip(),
                                "observacao": str(obs_nf or "").strip(),
                                "criado_por": usuario_atual,
                            }
                            if pdf_caminho:
                                dados_nf["pdf_caminho"] = pdf_caminho
                                dados_nf["pdf_nome"] = pdf_nome
                            try:
                                supabase.table("sispac_notas_fiscais").insert(dados_nf).execute()
                                registrar_auditoria(
                                    "CADASTRO_NF",
                                    "sispac_notas_fiscais",
                                    f"NF {numero_nf_limpo} no empenho {empenho_nf.get('numero_empenho')}",
                                )
                                limpar_cache_empenhos()
                                st.session_state._limpar_form_nf = True
                                st.success(f"Nota {numero_nf_limpo} lançada no empenho {empenho_nf.get('numero_empenho')}.")
                                st.rerun()
                            except Exception as e:
                                if "duplicate" in str(e).lower() or "23505" in str(e):
                                    st.error("Esta nota (número e série) já está lançada neste empenho.")
                                elif "pdf_caminho" in str(e).lower():
                                    try:
                                        dados_nf.pop("pdf_caminho", None)
                                        dados_nf.pop("pdf_nome", None)
                                        supabase.table("sispac_notas_fiscais").insert(dados_nf).execute()
                                        st.session_state._limpar_form_nf = True
                                        st.warning("Nota salva. Rode de novo o SQL `sispac_empenhos.sql` para gravar o PDF.")
                                        st.rerun()
                                    except Exception as e2:
                                        st.error(f"Não foi possível lançar a nota: {e2}")
                                else:
                                    st.error(f"Não foi possível lançar a nota: {e}")

    st.markdown("---")
    st.markdown("##### Empenhos registrados")
    st.caption("Clique no texto da linha para selecionar o empenho.")
    if df_empenhos.empty:
        st.info("Nenhum empenho cadastrado ainda.")
        return

    df_notas_todas, erro_nf = carregar_notas_empenho()
    if erro_nf is not None and not _erro_tabela_ausente(erro_nf) and not _rpc_ausente(erro_nf):
        st.error(f"Não foi possível ler as notas: {erro_nf}")
        df_notas_todas = pd.DataFrame()

    if df_notas_todas is None or df_notas_todas.empty:
        soma_nf = {}
        qtd_nf = {}
    else:
        df_notas_todas["valor_nf"] = pd.to_numeric(df_notas_todas.get("valor_nf"), errors="coerce").fillna(0.0)
        soma_nf = df_notas_todas.groupby("empenho_id")["valor_nf"].sum().to_dict()
        qtd_nf = df_notas_todas.groupby("empenho_id")["id"].count().to_dict()

    busca_emp = st.text_input("Buscar empenho, fornecedor ou objeto", key="filtro_empenhos", placeholder="Digite parte do número ou do nome")
    df_lista = df_empenhos.copy()
    if busca_emp and str(busca_emp).strip():
        termo = str(busca_emp).strip()
        mascara = False
        for col in ["numero_empenho", "fornecedor", "objeto", "cnpj"]:
            if col in df_lista.columns:
                mascara = mascara | df_lista[col].astype(str).str.contains(termo, case=False, regex=False, na=False)
        df_lista = df_lista[mascara] if isinstance(mascara, pd.Series) else df_lista

    if df_lista.empty:
        st.info("Nenhum empenho com esse filtro.")
        return

    df_lista = df_lista.copy()
    df_lista["valor_empenho"] = pd.to_numeric(df_lista.get("valor_empenho"), errors="coerce").fillna(0.0)
    df_lista["notas"] = df_lista["id"].map(lambda i: int(qtd_nf.get(i, 0)))
    df_lista["valor_notas"] = df_lista["id"].map(lambda i: float(soma_nf.get(i, 0.0)))
    df_lista["saldo"] = df_lista["valor_empenho"] - df_lista["valor_notas"]
    df_lista = df_lista.reset_index(drop=True)

    aberto_id = st.session_state.get("empenho_aberto")
    with st.container(key="lista_empenhos"):
        st.markdown(
            html_linha_empenho("Empenho", "Fornecedor", "Valor", "Notas", "PDF", "Data", cabecalho=True),
            unsafe_allow_html=True,
        )
        for i, row in df_lista.iterrows():
            emp_id = int(row["id"])
            numero = f"{row.get('numero_empenho')}/{row.get('ano')}"
            fornecedor = str(row.get("fornecedor") or "")
            tem_pdf = "Com PDF" if str(row.get("pdf_caminho") or "").strip() else "Sem PDF"
            qtd_notas = f"{int(row.get('notas') or 0)}"
            selecionado = aberto_id == emp_id
            with st.container(key=f"emp_row_{i}_{emp_id}"):
                st.markdown(
                    html_linha_empenho(
                        numero,
                        fornecedor,
                        formatar_moeda_br(row.get("valor_empenho")),
                        qtd_notas,
                        tem_pdf,
                        formatar_data_br(row.get("data_empenho")),
                        selecionado=selecionado,
                    ),
                    unsafe_allow_html=True,
                )
                with st.container(key=f"hit_emp_{i}_{emp_id}"):
                    if st.button("Selecionar empenho", key=f"emp_txt_{i}_{emp_id}", use_container_width=True):
                        abrir_empenho_lista(emp_id)
                with st.container(key=f"open_emp_{i}_{emp_id}"):
                    if st.button("Abrir", key=f"emp_abrir_{i}_{emp_id}", use_container_width=True):
                        abrir_empenho_lista(emp_id)

    if not aberto_id:
        st.caption("Clique no texto da linha ou em Abrir para ver o empenho.")
        return

    empenho_ver = next((r for r in df_lista.to_dict("records") if int(r["id"]) == int(aberto_id)), None)
    if empenho_ver is None:
        empenho_ver = next((r for r in df_empenhos.to_dict("records") if int(r["id"]) == int(aberto_id)), None)
    if empenho_ver is None:
        st.session_state.empenho_aberto = None
        st.info("Clique no texto de um empenho para abrir.")
        return

    valor_emp_sel = float(empenho_ver.get("valor_empenho") or 0)
    valor_nf_sel = float(soma_nf.get(empenho_ver["id"], 0.0))
    c_tit, c_fechar = st.columns([6.5, 1.5])
    with c_tit:
        st.markdown("##### Empenho selecionado")
    with c_fechar:
        if st.button("Fechar", key=f"btn_fechar_emp_{empenho_ver['id']}", use_container_width=True):
            fechar_empenho_lista()
    st.caption(
        f"{empenho_ver.get('numero_empenho')} — "
        f"valor {formatar_moeda_br(valor_emp_sel)} · "
        f"notas {formatar_moeda_br(valor_nf_sel)} · "
        f"saldo {formatar_moeda_br(valor_emp_sel - valor_nf_sel)}"
    )
    objeto_txt = str(empenho_ver.get("objeto") or "").strip()
    if objeto_txt:
        st.caption(f"Objeto: {objeto_txt}")

    bloco_pdf_registro(
        "PDF do empenho",
        empenho_ver.get("pdf_caminho"),
        empenho_ver.get("pdf_nome"),
        f"dl_emp_{empenho_ver['id']}",
    )
    pdf_emp_extra = st.file_uploader(
        "Incluir ou substituir PDF do empenho",
        type=TIPOS_PDF_EMPENHO,
        key=f"pdf_anexo_emp_{empenho_ver['id']}",
    )
    if st.button("Salvar PDF do empenho", key=f"btn_pdf_emp_{empenho_ver['id']}"):
        if pdf_emp_extra is None:
            st.warning("Escolha o arquivo digitalizado do empenho.")
        else:
            try:
                caminho, nome = enviar_pdf_sispac(
                    pdf_emp_extra, "empenhos", empenho_ver.get("numero_empenho")
                )
                gravar_pdf_registro("sispac_empenhos", empenho_ver["id"], caminho, nome)
                registrar_auditoria("PDF_EMPENHO", "sispac_empenhos", empenho_ver.get("numero_empenho"))
                st.success("PDF do empenho salvo.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível gravar o PDF. Rode o SQL `sispac_empenhos.sql` se o bucket ainda não existir. ({e})")

    qtd_notas_emp = int(empenho_ver.get("notas") or qtd_nf.get(empenho_ver["id"], 0) or 0)
    if st.session_state.get("mostrar_notas_empenho"):
        if st.button("Ocultar notas", key=f"btn_ocultar_notas_{empenho_ver['id']}"):
            st.session_state.mostrar_notas_empenho = False
            st.session_state.nota_aberta = None
            st.rerun()
    else:
        if st.button(f"Ver notas deste empenho ({qtd_notas_emp})", key=f"btn_ver_notas_{empenho_ver['id']}"):
            st.session_state.mostrar_notas_empenho = True
            st.rerun()

    if not st.session_state.get("mostrar_notas_empenho"):
        return

    st.markdown("##### Notas do empenho selecionado")
    df_notas_sel, _ = carregar_notas_empenho(empenho_ver["id"])
    if df_notas_sel is None or df_notas_sel.empty:
        st.info("Ainda não há nota fiscal neste empenho.")
        return
    df_notas_sel["valor_nf"] = pd.to_numeric(df_notas_sel.get("valor_nf"), errors="coerce").fillna(0.0)
    df_notas_sel = df_notas_sel.reset_index(drop=True)
    nota_aberta = st.session_state.get("nota_aberta")
    with st.container(key="lista_notas_emp"):
        st.markdown(
            html_linha_nota("Nota", "Emissão", "Valor", "PDF", cabecalho=True),
            unsafe_allow_html=True,
        )
        for i, row in df_notas_sel.iterrows():
            nota_id = int(row["id"])
            numero_nf = str(row.get("numero_nf") or "")
            serie = str(row.get("serie") or "").strip()
            if serie:
                numero_nf = f"{numero_nf} s/{serie}"
            tem_pdf = "Com PDF" if str(row.get("pdf_caminho") or "").strip() else "Sem PDF"
            selecionado = nota_aberta == nota_id
            with st.container(key=f"nf_row_{i}_{nota_id}"):
                st.markdown(
                    html_linha_nota(
                        numero_nf,
                        formatar_data_br(row.get("data_emissao")),
                        formatar_moeda_br(row.get("valor_nf")),
                        tem_pdf,
                        selecionado=selecionado,
                    ),
                    unsafe_allow_html=True,
                )
                with st.container(key=f"hit_nf_{i}_{nota_id}"):
                    if st.button("Selecionar nota", key=f"nf_txt_{i}_{nota_id}", use_container_width=True):
                        abrir_nota_lista(nota_id)
                with st.container(key=f"open_nf_{i}_{nota_id}"):
                    if st.button("Abrir", key=f"nf_abrir_{i}_{nota_id}", use_container_width=True):
                        abrir_nota_lista(nota_id)

    if not nota_aberta:
        st.info("Clique no texto de uma nota para abrir o PDF digitalizado.")
        return
    nota_ver = next((r for r in df_notas_sel.to_dict("records") if int(r["id"]) == int(nota_aberta)), None)
    if nota_ver is None:
        st.session_state.nota_aberta = None
        return

    st.markdown("##### Nota selecionada")
    st.caption(
        f"NF {nota_ver.get('numero_nf')} — {formatar_moeda_br(nota_ver.get('valor_nf'))}"
    )
    bloco_pdf_registro(
        "PDF da nota",
        nota_ver.get("pdf_caminho"),
        nota_ver.get("pdf_nome"),
        f"dl_nf_{nota_ver['id']}",
    )
    pdf_nf_extra = st.file_uploader(
        "Incluir ou substituir PDF da nota digitalizada",
        type=TIPOS_PDF_EMPENHO,
        key=f"pdf_anexo_nf_{nota_ver['id']}",
    )
    if st.button("Salvar PDF da nota", key=f"btn_pdf_nf_{nota_ver['id']}"):
        if pdf_nf_extra is None:
            st.warning("Escolha o arquivo digitalizado da nota.")
        else:
            try:
                caminho, nome = enviar_pdf_sispac(
                    pdf_nf_extra,
                    f"notas/{empenho_ver.get('numero_empenho')}",
                    nota_ver.get("numero_nf"),
                )
                gravar_pdf_registro("sispac_notas_fiscais", nota_ver["id"], caminho, nome)
                registrar_auditoria("PDF_NF", "sispac_notas_fiscais", nota_ver.get("numero_nf"))
                st.success("PDF da nota salvo.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível gravar o PDF. Rode o SQL `sispac_empenhos.sql` se o bucket ainda não existir. ({e})")


def render_painel_estoque_ubs(modo_gestao=False):
    ubs_sessao = st.session_state.get("ubs_nome")
    prefixo = "gestao" if modo_gestao else "ubs"
    if modo_gestao:
        df_todos = carregar_estoque_ubs()
        if df_todos.empty:
            st.info("Ainda não há saldo nas unidades. Ele passa a ser registrado nas próximas conferências, depois de executar o SQL `sispac_estoque_ubs.sql` no Supabase.")
            return
        unidades = ["Todas"] + sorted(
            {str(u).strip() for u in df_todos["ubs"].dropna().tolist() if str(u).strip()}
        )
        ubs_filtro = st.selectbox("Unidade", unidades, key=f"est_{prefixo}_filtro_ubs")
        if ubs_filtro == "Todas":
            df_saldo = df_todos
            ubs_mov = None
        else:
            df_saldo = df_todos[df_todos["ubs"].astype(str).str.strip() == ubs_filtro]
            ubs_mov = ubs_filtro
    else:
        df_saldo = carregar_estoque_ubs(ubs_sessao)
        ubs_mov = ubs_sessao
        if df_saldo.empty:
            st.info("Esta unidade ainda não tem saldo. Ele aparece depois que o almoxarifado conferir um pedido (e o SQL do estoque por UBS estiver no banco).")

    busca = st.text_input("Buscar material", key=f"est_{prefixo}_busca", placeholder="Digite parte do nome")
    if busca and not df_saldo.empty and "material" in df_saldo.columns:
        df_saldo = df_saldo[df_saldo["material"].astype(str).str.contains(busca.strip(), case=False, regex=False, na=False)]

    colunas_saldo = [c for c in ["ubs", "distrito", "material", "quantidade_atual", "atualizado_em"] if c in df_saldo.columns]
    if not modo_gestao:
        colunas_saldo = [c for c in colunas_saldo if c != "ubs"]
    if not df_saldo.empty:
        st.dataframe(
            df_saldo[colunas_saldo] if colunas_saldo else df_saldo,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(df_saldo)} material(is) no estoque da unidade.")

    if not modo_gestao:
        st.markdown("##### Registrar consumo")
        df_consumo = carregar_estoque_ubs(ubs_sessao)
        opcoes_mat = []
        if not df_consumo.empty and "material" in df_consumo.columns:
            df_pos = df_consumo
            if "quantidade_atual" in df_pos.columns:
                df_pos = df_pos[pd.to_numeric(df_pos["quantidade_atual"], errors="coerce").fillna(0) > 0]
            opcoes_mat = sorted({str(m).strip() for m in df_pos["material"].dropna() if str(m).strip()})
        with st.form(f"form_consumo_{prefixo}"):
            material_cons = st.selectbox(
                "Material usado",
                opcoes_mat if opcoes_mat else ["Nenhum saldo para baixar"],
            )
            qtd_cons = st.number_input("Quantidade consumida", min_value=1, value=1)
            obs_cons = st.text_input("Observação (opcional)")
            if st.form_submit_button("Baixar do estoque da unidade"):
                if material_cons == "Nenhum saldo para baixar":
                    st.error("Não há material com saldo para consumo.")
                else:
                    try:
                        aplicar_estoque_ubs(
                            ubs_sessao,
                            material_cons,
                            -int(qtd_cons),
                            tipo="CONSUMO",
                            observacao=(obs_cons or "").strip() or "Consumo na unidade",
                        )
                        registrar_auditoria("CONSUMO_UBS", "estoque_ubs", f"{ubs_sessao} / {material_cons} / {qtd_cons}")
                        st.success("Consumo registrado. O saldo desta unidade foi atualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    st.markdown("##### Movimentos recentes")
    df_mov = carregar_movimentos_ubs(ubs_mov, limite=80)
    if df_mov.empty:
        st.caption("Sem movimentos nesta unidade ainda.")
    else:
        colunas_mov = [c for c in ["criado_em", "ubs", "tipo", "material", "quantidade", "saldo_apos", "numero_pedido", "usuario", "observacao"] if c in df_mov.columns]
        if not modo_gestao and "ubs" in colunas_mov:
            colunas_mov.remove("ubs")
        st.dataframe(df_mov[colunas_mov] if colunas_mov else df_mov, use_container_width=True, hide_index=True)


@st.cache_data(ttl=300)
def carregar_materiais(url):
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    col_material = achar_coluna(df, ["Material"])
    if col_material:
        df[col_material] = df[col_material].astype(str).str.strip()
    return df


# ==========================================
# 3. SISTEMA DE LOGIN E SEGURANÇA
# ==========================================
# POR QUE: O session_state é a "memória do navegador". Ele lembra que você já passou pela tela de senha.
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown(
        "<div class='sispac-header'><h1>SisPAC</h1>"
        "<p>Sistema de Pedidos do Almoxarifado Central — Secretaria Municipal de Saúde de Pelotas</p></div>",
        unsafe_allow_html=True,
    )
    col_l1, col_l2, col_l3 = st.columns([1, 1.15, 1])
    with col_l2:
        st.markdown("#### Acesso institucional")
        st.caption("Informe as credenciais da unidade ou da gestão do almoxarifado.")
        with st.form("form_login"):
            email_digitado = st.text_input("E-mail institucional").lower().strip()
            senha_digitada = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

        if entrar:
            try:
                resposta = supabase.auth.sign_in_with_password({
                    "email": email_digitado,
                    "password": senha_digitada
                })
                
                st.session_state.autenticado = True
                st.session_state.email_usuario = resposta.user.email
                
                if "ubs" in st.session_state.email_usuario.lower():
                    st.session_state.perfil = "UBS"
                    distrito_email, ubs_email = identificar_ubs_por_email(st.session_state.email_usuario)
                    st.session_state.ubs_nome = ubs_email or st.session_state.email_usuario.split("@")[0]
                    st.session_state.distrito_ubs = distrito_email
                else:
                    st.session_state.perfil = "GESTAO"
                    st.session_state.ubs_nome = "Visão Global"
                    st.session_state.distrito_ubs = None
                
                st.rerun()
                
            except Exception as e:
                st.error("Credenciais inválidas. Verifique o e-mail e a senha.")
                
    st.stop() 

# ==========================================
# 4. BARRA LATERAL (MENU DE USUÁRIO)
# ==========================================
st.sidebar.markdown("### SisPAC")
st.sidebar.caption("Pedidos, conferência, relatórios e empenhos")
st.sidebar.caption("Almoxarifado Central — SMS Pelotas")
st.sidebar.divider()
st.sidebar.write(f"Usuário: **{st.session_state.email_usuario}**")
perfil_legenda = "Gestão / Almoxarifado" if st.session_state.perfil == "GESTAO" else f"UBS {st.session_state.ubs_nome}"
st.sidebar.write(f"Perfil: **{perfil_legenda}**")
if st.sidebar.button("Encerrar sessão", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.autenticado = False
    st.rerun()

# ==========================================
# 5. CABEÇALHO PRINCIPAL
# ==========================================
# POR QUE: st.columns divide a tela. [1, 1, 6] dita a largura: duas colunas finas para logos, uma enorme para o título.
col_logo1, col_logo2, col_titulo = st.columns([1, 1, 7])

with col_logo1:
    st.image("horizontalloggoverr.png", width=88)
    
with col_logo2:
    st.image("brasao-cidade-pelotas-rs.jpg", width=88)

with col_titulo:
    st.markdown(
        "<div class='sispac-header'><h1>SisPAC — Sistema de Pedidos do Almoxarifado Central</h1>"
        "<p>Secretaria Municipal de Saúde de Pelotas</p></div>",
        unsafe_allow_html=True,
    )

if st.session_state.perfil == "GESTAO":
    opcoes_topo = ["Novo pedido", "Pedidos", "Painel gerencial"]
    opcoes_gerencial = ["Relatórios", "Cadastro e estoque", "Empenhos e notas"]
    st.session_state.pop("em_relatorios", None)
    if "secao_topo_gestao" not in st.session_state:
        antiga = st.session_state.get("secao_gestao")
        if antiga in opcoes_gerencial:
            st.session_state.secao_topo_gestao = "Painel gerencial"
            st.session_state.secao_gerencial_area = antiga
        elif antiga in opcoes_topo:
            st.session_state.secao_topo_gestao = antiga
        else:
            st.session_state.secao_topo_gestao = "Pedidos"
    if st.session_state.get("secao_gerencial_area") not in opcoes_gerencial:
        st.session_state.secao_gerencial_area = "Relatórios"
    secao_topo = st.radio(
        "Seção",
        opcoes_topo,
        horizontal=True,
        key="secao_topo_gestao",
    )
    if secao_topo == "Painel gerencial":
        if st.session_state.get("radio_secao_gerencial") not in opcoes_gerencial:
            st.session_state.radio_secao_gerencial = st.session_state.secao_gerencial_area
        secao_gerencial = st.radio(
            "Painel gerencial",
            opcoes_gerencial,
            horizontal=True,
            key="radio_secao_gerencial",
        )
        st.session_state.secao_gerencial_area = secao_gerencial
        secao_gestao = secao_gerencial
    else:
        secao_gestao = secao_topo
    aba1 = aba2 = aba3 = aba4 = None
    aba_estoque_ubs = None
else:
    aba1, aba2, aba_estoque_ubs = st.tabs(["Novo pedido", "Acompanhar pedidos", "Estoque da unidade"])
    aba3 = None
    aba4 = None
    secao_gestao = None

ctx_pedido = aba1 if aba1 is not None else nullcontext()
ctx_painel = aba2 if aba2 is not None else nullcontext()

if secao_gestao != "Empenhos e notas":
    try:
        df_materiais = carregar_materiais(url_google_sheets_materiais)
        col_categoria = achar_coluna(df_materiais, ["Categoria"])
        col_material = achar_coluna(df_materiais, ["Material"])
        col_estoque = achar_coluna(df_materiais, ["Estoque", "Qtd", "Quantidade", "Estoque Atual"])
        col_preco = achar_coluna(df_materiais, ["Valor Unitário", "Valor Unitario", "Preço", "Preco"])
        df_materiais = mesclar_materiais_banco(df_materiais, col_categoria, col_material, col_estoque, col_preco)
        if (df_materiais is None or df_materiais.empty) is False and not col_categoria:
            col_categoria = achar_coluna(df_materiais, ["Categoria"])
            col_material = achar_coluna(df_materiais, ["Material"])
            col_estoque = achar_coluna(df_materiais, ["Estoque", "Qtd", "Quantidade", "Estoque Atual"])
            col_preco = achar_coluna(df_materiais, ["Valor Unitário", "Valor Unitario", "Preço", "Preco"])
        lista_categorias = df_materiais[col_categoria].dropna().unique().tolist() if col_categoria and not df_materiais.empty else ["Erro"]
    except Exception as e:
        df_materiais = mesclar_materiais_banco(pd.DataFrame(), "Categoria", "Material", "Estoque", "Valor Unitário")
        col_categoria = achar_coluna(df_materiais, ["Categoria"]) if not df_materiais.empty else "Categoria"
        col_material = achar_coluna(df_materiais, ["Material"]) if not df_materiais.empty else "Material"
        col_estoque = achar_coluna(df_materiais, ["Estoque"]) if not df_materiais.empty else "Estoque"
        col_preco = achar_coluna(df_materiais, ["Valor Unitário"]) if not df_materiais.empty else "Valor Unitário"
        lista_categorias = df_materiais[col_categoria].dropna().unique().tolist() if col_categoria and not df_materiais.empty else ["Erro"]
        _erro_materiais = e
    else:
        _erro_materiais = None
    saidas_conferidas = mapa_saidas_conferidas()
    saldos_lote, materiais_com_lote = mapa_estoque_lotes()
else:
    df_materiais = pd.DataFrame()
    col_categoria = col_material = col_estoque = col_preco = None
    lista_categorias = []
    saidas_conferidas = {}
    saldos_lote, materiais_com_lote = {}, set()
    _erro_materiais = None

# --- ABA 1: FORMULÁRIO (Visão da UBS com Indicador de Estoque) ---
if secao_gestao in (None, "Novo pedido"):
  with ctx_pedido:
    st.markdown("#### Requisição de materiais")
    if st.session_state.perfil == "GESTAO":
        st.caption("Selecione o distrito e a unidade, escolha a categoria e o material e inclua os itens antes de enviar a requisição.")
    else:
        st.caption("Escolha a categoria e o material e inclua os itens no pedido antes de enviar a requisição.")
    
    col_distrito, col_ubs = st.columns(2)
    placeholder_dist = "Selecione o distrito"
    placeholder_ubs = "Selecione a unidade"
    
    if st.session_state.perfil == "GESTAO":
        with col_distrito:
            distrito_selecionado = st.selectbox(
                "Distrito",
                [placeholder_dist] + list(distritos_ubs.keys()),
                index=0,
                key="sel_distrito_pedido",
            )
        with col_ubs:
            if distrito_selecionado == placeholder_dist:
                ubs_selecionada = st.selectbox(
                    "Unidade",
                    [placeholder_ubs],
                    index=0,
                    disabled=True,
                    key="sel_ubs_pedido_vazio",
                )
            else:
                ubs_selecionada = st.selectbox(
                    "Unidade",
                    [placeholder_ubs] + distritos_ubs[distrito_selecionado],
                    index=0,
                    key="sel_ubs_pedido",
                )
        unidade_ok = (
            distrito_selecionado != placeholder_dist
            and ubs_selecionada != placeholder_ubs
        )
    else:
        unidade_usuario = st.session_state.ubs_nome
        distrito_detectado = st.session_state.get("distrito_ubs") or "Não Encontrado"
        if distrito_detectado == "Não Encontrado":
            for distrito, unidades in distritos_ubs.items():
                if unidade_usuario in unidades:
                    distrito_detectado = distrito
                    break
        distrito_selecionado = distrito_detectado
        ubs_selecionada = unidade_usuario
        unidade_ok = True
        with col_distrito:
            st.markdown("**Distrito**")
            st.write(distrito_selecionado)
        with col_ubs:
            st.markdown("**Unidade**")
            st.write(ubs_selecionada)
            
    st.markdown("---")

    if st.session_state.get("msg_pedido_ok"):
        st.success(st.session_state.msg_pedido_ok)
        st.session_state.msg_pedido_ok = None
    if _erro_materiais is not None:
        st.error(f"Erro ao carregar materiais. Verifique o link do Google Sheets. ({_erro_materiais})")

    opcoes_categoria = ["Selecione a categoria"] + [c for c in lista_categorias if c not in MATERIAIS_INVALIDOS]
    categoria_selecionada = st.selectbox("Categoria", opcoes_categoria, index=0, key="sel_categoria_pedido")

    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []

    if not unidade_ok:
        st.info("Selecione o distrito e a unidade antes de montar o pedido.")
    elif (
        not df_materiais.empty
        and col_categoria
        and col_material
        and categoria_selecionada not in MATERIAIS_INVALIDOS
    ):
        df_filtrado = df_materiais[df_materiais[col_categoria] == categoria_selecionada].copy()
        df_filtrado[col_material] = df_filtrado[col_material].astype(str).str.strip()
        df_filtrado = df_filtrado[~df_filtrado[col_material].isin(MATERIAIS_INVALIDOS)]
        df_filtrado = df_filtrado.drop_duplicates(subset=[col_material], keep="first")

        with st.container(key="catalogo_marcacao"):
            st.markdown("##### Catálogo da categoria")
            st.caption("Informe a quantidade e clique em Incluir. O catálogo mostra até 10 itens; o restante fica na rolagem desta lista.")
            filtro_nome = st.text_input(
                "Filtrar pelo nome do material",
                key="filtro_nome_catalogo",
                placeholder="Comece a digitar o nome do item",
            )
            ativar_filtro_digitacao()
            filtro_nome = str(filtro_nome or "")
            if filtro_nome.strip():
                df_filtrado = df_filtrado[df_filtrado[col_material].str.contains(filtro_nome.strip(), case=False, regex=False, na=False)]

            if df_filtrado.empty:
                st.info("Nenhum material nesta categoria com o filtro atual.")
            else:
                with st.container(height=320, key="catalogo_lista"):
                    cab_item, cab_qtd, cab_btn = st.columns([4.4, 0.9, 1.2])
                    cab_item.markdown("<div class='linha-catalogo linha-catalogo-cab'>Item</div>", unsafe_allow_html=True)
                    cab_qtd.markdown("<div class='linha-catalogo linha-catalogo-cab'>Qtd</div>", unsafe_allow_html=True)
                    cab_btn.markdown("<div class='linha-catalogo linha-catalogo-cab'></div>", unsafe_allow_html=True)
                    for _, item_row in df_filtrado.iterrows():
                        material_cat = str(item_row[col_material]).strip()
                        valor_item = parse_numero(item_row[col_preco]) if col_preco else 0.0
                        chave_mat = re.sub(r"\W+", "_", material_cat)[:80]
                        c_item, c_qtd, c_btn = st.columns([4.4, 0.9, 1.2])
                        c_item.markdown(
                            f"<div class='linha-catalogo'>{html_seguro(material_cat)}</div>",
                            unsafe_allow_html=True,
                        )
                        qtd_item = c_qtd.number_input(
                            "Qtd",
                            min_value=1,
                            value=1,
                            step=1,
                            key=f"pedido_qtd_{categoria_selecionada}_{chave_mat}",
                            label_visibility="collapsed",
                        )
                        if c_btn.button("Incluir", key=f"pedido_add_{categoria_selecionada}_{chave_mat}"):
                            incluir_item_carrinho(
                                distrito_selecionado,
                                ubs_selecionada,
                                categoria_selecionada,
                                material_cat,
                                qtd_item,
                                valor_item,
                            )
                            st.success(f"Incluído: {qtd_item}x {material_cat}")
                            st.rerun()
    else:
        if unidade_ok:
            st.caption("Selecione a categoria para ver o catálogo e incluir os itens.")

    if unidade_ok:
        st.markdown("---")
        st.markdown("##### Itens da requisição")
        if len(st.session_state.carrinho) == 0:
            st.caption("Nenhum item ainda. Inclua no catálogo acima.")
        elif st.session_state.perfil == "UBS":
            col_cab1, col_cab2, col_cab3 = st.columns([5.2, 1, 0.6])
            col_cab1.write("**Item**")
            col_cab2.write("**Qtd**")
            col_cab3.write("")
            st.divider()
            for i, item in enumerate(st.session_state.carrinho):
                c1, c2, c3 = st.columns([5.2, 1, 0.6])
                c1.write(item["material"])
                c2.write(str(item["quantidade"]))
                if c3.button("🗑️", help="Remover item", key=f"excluir_{i}_{item['material']}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
        else:
            col_cab1, col_cab2, col_cab3, col_cab4, col_cab5 = st.columns([1.5, 2, 3, 1, 0.55])
            col_cab1.write("**UBS**")
            col_cab2.write("**Categoria**")
            col_cab3.write("**Material**")
            col_cab4.write("**Qtd**")
            col_cab5.write("")
            st.divider()
            for i, item in enumerate(st.session_state.carrinho):
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1, 0.55])
                c1.write(item["ubs"])
                c2.write(item["categoria"])
                c3.write(item["material"])
                c4.write(item["quantidade"])
                if c5.button("🗑️", help="Remover item", key=f"excluir_{i}_{item['material']}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()

        observacao_geral = st.text_area(
            "Observações (opcional)",
            placeholder="Informe urgência, horário de recebimento ou outras orientações à gestão.",
            key="input_observacao_geral",
        )
        if st.button("Enviar requisição", type="primary", key="btn_enviar_pedido"):
            if not unidade_ok:
                st.warning("Selecione o distrito e a unidade antes de enviar.")
            elif not st.session_state.carrinho:
                st.warning("⚠️ O carrinho está vazio! Adicione pelo menos um item antes de enviar.")
            elif not supabase:
                st.error("❌ Erro crítico: A conexão com o Supabase não foi estabelecida.")
            else:
                numero_pedido = proximo_numero_pedido(ubs_selecionada)
                data_pedido = texto_agora_sispac()
                obs_limpa = observacao_geral.strip() if observacao_geral else ""
                texto_observacao = obs_limpa if obs_limpa else "Sem observação"
                with st.spinner("Salvando pedido no servidor..."):
                    lista_insercao = []
                    for item in st.session_state.carrinho:
                        lista_insercao.append({
                            "numero_pedido": numero_pedido,
                            "data": data_pedido,
                            "distrito": item["distrito"],
                            "ubs": item["ubs"],
                            "categoria": item["categoria"],
                            "material": item["material"],
                            "quantidade": item["quantidade"],
                            "valor_unitario": item.get("valor_unitario", 0.0),
                            "custo_total": item.get("subtotal", 0.0),
                            "observacao": texto_observacao,
                            "status": "Pedido enviado",
                        })
                    try:
                        supabase.table("pedidos").insert(lista_insercao).execute()
                        st.session_state.carrinho = []
                        st.session_state.msg_pedido_ok = f"✅ Pedido {numero_pedido} enviado com sucesso!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro retornado pelo Banco de Dados: {e}")

# --- ABA 2: PAINEL GERENCIAL E RELATÓRIOS OFICIAIS ---
if secao_gestao in (None, "Pedidos", "Relatórios"):
  with ctx_painel:
    if st.session_state.perfil == "GESTAO" and secao_gestao == "Relatórios":
        st.markdown(
            "<div class='nao-imprimir'><h4>Relatórios</h4>"
            "<p style='color:#5d6d6e;font-size:0.9rem;margin-top:0;'>Painel analítico, documento oficial e centro de custos.</p></div>",
            unsafe_allow_html=True,
        )
    elif st.session_state.perfil == "GESTAO":
        st.markdown(
            "<div class='nao-imprimir'><h4>Pedidos</h4>"
            "<p style='color:#5d6d6e;font-size:0.9rem;margin-top:0;'>Conferência, despacho e acompanhamento. Relatórios, cadastro e empenhos ficam no Painel gerencial.</p></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='nao-imprimir'><h4>Acompanhar pedidos</h4>"
            "<p style='color:#5d6d6e;font-size:0.9rem;margin-top:0;'>Consulte os pedidos da unidade. Clique em um item da lista para abrir.</p></div>",
            unsafe_allow_html=True,
        )
    
    if not supabase:
        st.error("Banco de dados desconectado.")
    else:
        try:
            response = supabase.table("pedidos").select("*").execute()
            dados = response.data
            
            if not dados:
                st.info("Nenhum pedido registrado no sistema.")
            else:
                df_supabase = pd.DataFrame(dados)
                df_supabase['data_dt'] = pd.to_datetime(df_supabase['data'])
                
                # Garante que as colunas numéricas existem e estão limpas
                for col in ['valor_unitario', 'custo_total', 'quantidade']:
                    if col not in df_supabase.columns:
                        df_supabase[col] = 0.0
                    else:
                        df_supabase[col] = pd.to_numeric(df_supabase[col], errors='coerce').fillna(0.0)
                
                if 'quantidade_entregue' not in df_supabase.columns:
                    df_supabase['quantidade_entregue'] = 0.0
                else:
                    df_supabase['quantidade_entregue'] = pd.to_numeric(df_supabase['quantidade_entregue'], errors='coerce').fillna(0.0)

                # Se for UBS, filtra apenas os pedidos dela
                if st.session_state.perfil == "UBS":
                    df_supabase = df_supabase[df_supabase['ubs'].str.lower() == st.session_state.ubs_nome.lower()]
                    st.info(f"Visualizando dados exclusivos da unidade: **{st.session_state.ubs_nome}**")
                
                if df_supabase.empty:
                    st.warning("Não há registros de pedidos para esta unidade até o momento.")
                else:
                    if st.session_state.perfil == "GESTAO" and secao_gestao == "Relatórios":
                        st.caption("Painel analítico: gráficos do dia a dia. Documento oficial: PDF para assinatura. Centro de custos: valores efetivamente despachados.")
                        sub_relatorio = st.radio(
                            "Tipo de relatório",
                            ["Painel analítico", "Documento oficial", "Centro de custos"],
                            horizontal=True,
                            key="tipo_relatorio_pagina",
                        )
                        modo_aba2 = "Relatórios"
                    else:
                        modo_aba2 = "Pedidos e conferência"
                        sub_relatorio = None
                    
                    st.markdown("---")
                    
                    if modo_aba2 == "Pedidos e conferência":
                        if 'status' not in df_supabase.columns:
                            df_supabase['status'] = 'Pedido enviado'

                        pedidos_unicos = (
                            df_supabase.sort_values(by="data", ascending=True)
                            .drop_duplicates(subset=["numero_pedido"])
                            .reset_index(drop=True)
                        )
                        pedidos_unicos["status"] = pedidos_unicos["numero_pedido"].map(
                            lambda n: status_consolidado_pedido(df_supabase[df_supabase["numero_pedido"] == n])
                        )
                        qtd_itens_pedido = df_supabase.groupby("numero_pedido")["material"].count().to_dict()
                        pedidos_unicos["itens"] = pedidos_unicos["numero_pedido"].map(lambda n: int(qtd_itens_pedido.get(n, 0)))
                        pedidos_unicos = pedidos_unicos[["numero_pedido", "data", "distrito", "ubs", "status", "itens"]]

                        conferencia_por_material = False

                        if st.session_state.get("lista_tipo_pedidos") == "Pendentes":
                            st.session_state.lista_tipo_pedidos = "Pendentes (conferência)"
                        elif st.session_state.get("lista_tipo_pedidos") == "Concluídos":
                            st.session_state.lista_tipo_pedidos = "Concluídos (visualizar / imprimir)"
                        if st.session_state.perfil == "GESTAO":
                            opcoes_lista_ped = [
                                "Pendentes (conferência)",
                                "Despacho e trânsito",
                                "Concluídos (visualizar / imprimir)",
                            ]
                        else:
                            opcoes_lista_ped = [
                                "Pendentes (acompanhar / receber)",
                                "Concluídos (visualizar / imprimir)",
                            ]
                        ir_lista = st.session_state.pop("_ir_lista_pedidos", None)
                        if ir_lista in opcoes_lista_ped:
                            st.session_state.lista_tipo_pedidos = ir_lista
                            st.session_state._lista_tipo_ant = ir_lista
                        lista_tipo_atual = st.session_state.get("lista_tipo_pedidos") or opcoes_lista_ped[0]
                        if lista_tipo_atual not in opcoes_lista_ped:
                            lista_tipo_atual = opcoes_lista_ped[0]
                            st.session_state.lista_tipo_pedidos = lista_tipo_atual

                        lista_tipo = st.radio(
                            "Lista",
                            opcoes_lista_ped,
                            horizontal=True,
                            key="lista_tipo_pedidos",
                        )
                        tipo_lista = tipo_lista_pedidos(lista_tipo, st.session_state.perfil)
                        so_pendentes = tipo_lista == "pendentes"
                        so_despacho = tipo_lista == "despacho"
                        if st.session_state.get("_lista_tipo_ant") is None:
                            st.session_state._lista_tipo_ant = lista_tipo
                        elif st.session_state.get("_lista_tipo_ant") != lista_tipo:
                            st.session_state.pedido_aberto = None
                            st.session_state.modo_abertura = None
                            if "busca_num_pedido_acomp" in st.session_state:
                                st.session_state.busca_num_pedido_acomp = ""
                            st.session_state._lista_tipo_ant = lista_tipo
                        pedido_selecionado = resolver_pedido_aberto(
                            pedidos_unicos, tipo_lista, st.session_state.perfil
                        )

                        if pedido_selecionado == "Selecione...":
                            filtro_status = tipo_lista
                            if so_despacho and st.session_state.perfil == "GESTAO":
                                st.caption("Aqui ficam os pedidos já conferidos. Imprima e depois registre a saída para entrega. O estoque só baixa nessa saída.")

                            if st.session_state.perfil == "GESTAO":
                                col_f_dist, col_f_ubs, col_f_agr = st.columns(3)
                                with col_f_dist:
                                    filtro_distrito = st.selectbox(
                                        "Distrito",
                                        ["Todos"] + list(distritos_ubs.keys()),
                                        key="filtro_dist_conf",
                                    )
                                with col_f_ubs:
                                    ubs_filtro_base = ["Todas"] + sorted(pedidos_unicos["ubs"].dropna().astype(str).unique().tolist())
                                    filtro_ubs = st.selectbox("UBS", ubs_filtro_base, key="filtro_ubs_conf")
                                with col_f_agr:
                                    if not so_pendentes and st.session_state.get("agrupamento_conf") == "Por material (rateio)":
                                        st.session_state.agrupamento_conf = "Por pedido"
                                    opcoes_agr = ["Por pedido", "Por UBS"]
                                    if so_pendentes:
                                        opcoes_agr.append("Por material (rateio)")
                                    agrupamento = st.selectbox(
                                        "Agrupar conferência",
                                        opcoes_agr,
                                        key="agrupamento_conf",
                                    )
                            else:
                                filtro_distrito = "Todos"
                                filtro_ubs = "Todas"
                                agrupamento = "Por pedido"
                                if so_pendentes:
                                    st.caption("Acompanhe o pedido. Quando estiver em trânsito, confirme o recebimento. Só avise divergência se algum item separado não chegou.")
    
                            df_lista = pedidos_unicos.copy()
                            df_lista = df_lista[df_lista["status"].map(
                                lambda s: pedido_pertence_lista(s, tipo_lista, st.session_state.perfil)
                            )]
                            if filtro_distrito != "Todos":
                                df_lista = df_lista[df_lista["distrito"] == filtro_distrito]
                            if filtro_ubs != "Todas":
                                df_lista = df_lista[df_lista["ubs"] == filtro_ubs]
                            if so_pendentes:
                                df_lista = df_lista.sort_values(by="data", ascending=True)
                            else:
                                df_lista = df_lista.sort_values(by="data", ascending=False)
    
                            conferencia_por_material = agrupamento == "Por material (rateio)" and st.session_state.perfil == "GESTAO"
    
                            if conferencia_por_material:
                                    st.markdown("#### Rateio por material (pedidos ainda não conferidos)")
                                    st.caption("Informe a quantidade que será separada para cada UBS. O estoque só baixa na saída para entrega.")
                                    pendentes = df_supabase[df_supabase["status"].astype(str) == STATUS_PEDIDO_ENVIADO].copy()
                                    if filtro_distrito != "Todos":
                                        pendentes = pendentes[pendentes["distrito"] == filtro_distrito]
                                    if filtro_ubs != "Todas":
                                        pendentes = pendentes[pendentes["ubs"] == filtro_ubs]
                                    materiais_pendentes = sorted(pendentes["material"].dropna().astype(str).str.strip().unique().tolist()) if not pendentes.empty else []
                                    material_rateio = st.selectbox("Material para conferir", ["Selecione..."] + materiais_pendentes, key="mat_rateio_conf")
                                    if material_rateio != "Selecione..." and not pendentes.empty:
                                        linhas_mat = pendentes[pendentes["material"].astype(str).str.strip() == material_rateio].copy()
                                        saidas_conf = mapa_saidas_conferidas()
                                        saldos_lote_conf, materiais_lote_conf = mapa_estoque_lotes()
                                        mapa_planilha_conf = mapa_estoque_planilha(df_materiais, col_material, col_estoque)
                                        reservas_conf = mapa_reservas_separadas()
                                        estoque_atual = estoque_visivel(
                                            material_rateio,
                                            mapa_planilha_conf.get(material_rateio, 0),
                                            saidas_conf,
                                            saldos_lote_conf,
                                            materiais_lote_conf,
                                            reservas=reservas_conf,
                                        )
                                        qtds_pedidas = [parse_numero(q, inteiro=True) for q in linhas_mat["quantidade"].tolist()]
                                        demanda_total = sum(qtds_pedidas)
                                        m1, m2, m3 = st.columns(3)
                                        m1.metric("Estoque atual", f"{estoque_atual} un.")
                                        m2.metric("Demanda pendente", f"{demanda_total} un.")
                                        m3.metric("UBS solicitantes", linhas_mat["ubs"].nunique())
                                        if demanda_total > estoque_atual:
                                            st.warning("Estoque insuficiente para atender todas as unidades. Informe o que será enviado a cada UBS.")
    
                                        with st.form(key=f"form_rateio_{material_rateio}"):
                                            novas_quantidades_entregues = {}
                                            for i, (idx, row) in enumerate(linhas_mat.iterrows()):
                                                qtd_pedida = parse_numero(row["quantidade"], inteiro=True)
                                                qtd_ja = parse_numero(row.get("quantidade_entregue", 0), inteiro=True) if "quantidade_entregue" in row else 0
                                                c1, c2, c3, c4 = st.columns([1.3, 2.2, 1, 1])
                                                c1.write(f"**{row['ubs']}**")
                                                c2.write(f"{row['numero_pedido']}")
                                                c3.write(f"Pediu: {qtd_pedida}")
                                                val_entregue = c4.number_input(
                                                    f"Entregar ({row['ubs']})",
                                                    min_value=0,
                                                    max_value=qtd_pedida,
                                                    value=min(qtd_ja, qtd_pedida),
                                                    key=f"rateio_{row['id'] if 'id' in row else idx}",
                                                )
                                                novas_quantidades_entregues[row["id"] if "id" in row else idx] = val_entregue
                                            obs_gestao = st.text_input("Observação da Gestão (Opcional)", key=f"obs_rateio_{material_rateio}")
                                            btn_salvar_rateio = st.form_submit_button("Salvar rateio (separar)")
                                            if btn_salvar_rateio:
                                                try:
                                                    soma_entrega = sum(novas_quantidades_entregues.values())
                                                    if soma_entrega > estoque_atual:
                                                        st.error(f"A soma separada ({soma_entrega}) ultrapassa o estoque ({estoque_atual}). Ajuste o rateio.")
                                                    else:
                                                        atualizacoes = []
                                                        for row_id, nova_qtd in novas_quantidades_entregues.items():
                                                            row_original = linhas_mat[linhas_mat["id"] == row_id].iloc[0] if "id" in linhas_mat.columns else linhas_mat.iloc[list(novas_quantidades_entregues.keys()).index(row_id)]
                                                            atualizacoes.append((row_id, nova_qtd, row_original))
                                                        persistir_entregas(atualizacoes, (obs_gestao or "").strip())
                                                        st.success("Rateio salvo. O material foi separado; a baixa no estoque ocorre na saída para entrega.")
                                                        st.rerun()
                                                except Exception as e:
                                                    st.error(f"Erro ao salvar rateio: {e}")
    
                                    st.markdown("---")
                                    st.write("**Pedidos deste filtro:**")
                                    busca_rateio = st.text_input("Buscar número do pedido", key="busca_num_pedido_rateio")
                                    df_lista_rateio = filtrar_pedidos_por_numero(df_lista, busca_rateio)
                                    if busca_rateio.strip() and (df_lista_rateio is None or df_lista_rateio.empty):
                                        st.warning("Nenhum pedido com esse número.")
                                    elif df_lista_rateio is not None and not df_lista_rateio.empty:
                                        st.dataframe(
                                            df_lista_rateio[["numero_pedido", "ubs", "status", "data"]],
                                            hide_index=True,
                                            use_container_width=True,
                                        )
                            else:
                                if agrupamento == "Por UBS" and st.session_state.perfil == "GESTAO" and filtro_ubs == "Todas":
                                    ubs_grupo = st.selectbox(
                                        "Escolha a UBS para ver os pedidos agrupados",
                                        ["Selecione..."] + sorted(df_lista["ubs"].dropna().astype(str).unique().tolist()),
                                        key="ubs_grupo_conf",
                                    )
                                    if ubs_grupo != "Selecione...":
                                        df_lista = df_lista[df_lista["ubs"] == ubs_grupo]
    
                                busca_pedido = st.text_input("Buscar número do pedido", placeholder="Ex.: PED-0012", key="busca_num_pedido_acomp")
                                df_lista = filtrar_pedidos_por_numero(df_lista, busca_pedido)
                                if busca_pedido.strip() and (df_lista is None or df_lista.empty):
                                    st.warning("Nenhum pedido com esse número.")
                                else:
                                    if busca_pedido.strip() and len(df_lista) == 1:
                                        st.session_state.pedido_aberto = str(df_lista.iloc[0]["numero_pedido"])
                                        if so_pendentes and st.session_state.perfil == "GESTAO":
                                            st.session_state.modo_abertura = "conferir"
                                        elif so_despacho:
                                            st.session_state.modo_abertura = "despachar"
                                        else:
                                            st.session_state.modo_abertura = "receber" if st.session_state.perfil == "UBS" else "visualizar"
                                        st.rerun()
                                    if so_pendentes and st.session_state.perfil == "GESTAO":
                                        acao_lista = "conferir"
                                    elif so_despacho:
                                        acao_lista = "despachar"
                                    elif so_pendentes and st.session_state.perfil == "UBS":
                                        acao_lista = "receber"
                                    else:
                                        acao_lista = "visualizar"
                                    render_lista_pedidos_clicavel(
                                        df_lista,
                                        "acomp",
                                        acao=acao_lista,
                                    )

                        if pedido_selecionado != "Selecione...":
                            if st.button("← Voltar à lista", key="btn_voltar_pedido"):
                                st.session_state.pedido_aberto = None
                                st.session_state.modo_abertura = None
                                st.rerun()
                            detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                            status_atual = status_consolidado_pedido(detalhes)
                            modo_abertura = st.session_state.get("modo_abertura") or (
                                "conferir"
                                if so_pendentes and st.session_state.perfil == "GESTAO"
                                else "despachar" if so_despacho else "visualizar"
                            )

                            if st.session_state.perfil != "GESTAO" and not pedido_concluido(status_atual):
                                if pedido_em_transito(status_atual):
                                    st.info("O material saiu do almoxarifado e está em trânsito. Confirme o recebimento abaixo.")
                                elif pedido_separado(status_atual):
                                    st.info("O almoxarifado já separou o que será enviado. Aguarde a saída para entrega.")
                                else:
                                    st.info("Pedido aguardando o almoxarifado. A unidade só consulta — não é possível alterar quantidades.")

                            if (
                                st.session_state.perfil == "GESTAO"
                                and modo_abertura == "conferir"
                                and str(status_atual) == STATUS_PEDIDO_ENVIADO
                            ):
                                st.markdown("### Conferência do almoxarifado")
                                st.caption("Informe o que foi separado. O estoque só baixa quando o pedido sair para entrega.")

                                saidas_conf = mapa_saidas_conferidas()
                                reservas_conf = mapa_reservas_separadas()
                                saldos_lote_conf, materiais_lote_conf = mapa_estoque_lotes()
                                mapa_planilha_conf = mapa_estoque_planilha(df_materiais, col_material, col_estoque)
                                ja_baixou_estoque = str(status_atual) in STATUS_SAIU_CENTRAL
                                
                                with st.form(key=f"form_conferencia_{pedido_selecionado}"):
                                    novas_quantidades_entregues = {}
                                    
                                    for idx, row in detalhes.iterrows():
                                        mat = str(row['material']).strip()
                                        qtd_pedida = int(row['quantidade'])
                                        qtd_db_entregue = int(row['quantidade_entregue']) if pd.notna(row['quantidade_entregue']) else 0
                                        estoque_atual = estoque_visivel(
                                            mat,
                                            mapa_planilha_conf.get(mat, 0),
                                            saidas_conf,
                                            saldos_lote_conf,
                                            materiais_lote_conf,
                                            reservas=reservas_conf,
                                        )
                                        teto_fisico = estoque_atual + (qtd_db_entregue if ja_baixou_estoque else 0)
                                        max_entregue = max(0, min(qtd_pedida, teto_fisico))
                                        demanda = demanda_pendente_material(df_supabase, mat, pedido_selecionado)
                                        qtd_inicial = min(qtd_db_entregue, max_entregue)
                                            
                                        c_mat, c_est, c_ped, c_ent = st.columns([2.2, 1.6, 1, 1])
                                        c_mat.write(f"**{mat}** (Cat: {row['categoria']})")
                                        if demanda["outras_ubs"] > 0:
                                            c_est.markdown(
                                                f"**Estoque:** {estoque_atual} un.<br>"
                                                f"<span style='color:#d35400; font-size:12px;'>Outras UBS pediram {demanda['outras_ubs']} un. (ainda não conferido)</span>",
                                                unsafe_allow_html=True,
                                            )
                                        elif 0 < estoque_atual <= LIMIAR_ESTOQUE_BAIXO:
                                            c_est.markdown(f"**Estoque baixo:** {estoque_atual} un.")
                                        else:
                                            c_est.markdown(f"**Estoque:** {estoque_atual} un.")
                                        c_ped.write(f"Solicitado: {qtd_pedida}")
                                        
                                        val_entregue = c_ent.number_input(
                                            f"Entregue ({mat})", 
                                            min_value=0, 
                                            max_value=max(max_entregue, 0), 
                                            value=qtd_inicial,
                                            key=f"ent_{row['id'] if 'id' in row else idx}"
                                        )
                                        novas_quantidades_entregues[row['id'] if 'id' in row else idx] = val_entregue
                                        if demanda["total"] > estoque_atual and not ja_baixou_estoque:
                                            st.warning(
                                                f"Demanda pendente de **{mat}** ({demanda['total']} un., incluindo este pedido) é maior que o estoque ({estoque_atual} un.)."
                                            )

                                    obs_gestao = st.text_input("Observação da Gestão / Almoxarifado (Opcional)", value="", key=f"obs_g_{pedido_selecionado}")
                                    
                                    btn_salvar_conf = st.form_submit_button("Salvar conferência (separar)")
                                    if btn_salvar_conf:
                                        try:
                                            atualizacoes = []
                                            for row_id, nova_qtd in novas_quantidades_entregues.items():
                                                row_original = detalhes[detalhes['id'] == row_id].iloc[0] if 'id' in detalhes.columns else detalhes.iloc[list(novas_quantidades_entregues.keys()).index(row_id)]
                                                atualizacoes.append((row_id, nova_qtd, row_original))
                                            persistir_entregas(atualizacoes, (obs_gestao or "").strip())
                                            st.success("Conferência salva. Pedido separado. Imprima e registre a saída para entrega.")
                                            st.session_state._ir_lista_pedidos = rotulo_lista_por_status(
                                                STATUS_SEPARADO, st.session_state.perfil, opcoes_lista_ped
                                            )
                                            st.session_state.pedido_aberto = pedido_selecionado
                                            st.session_state.modo_abertura = "despachar"
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao salvar conferência no Supabase: {e}")
                                
                                st.markdown("---")

                            if st.session_state.perfil == "GESTAO" and pedido_separado(status_atual):
                                st.markdown("### Saída para entrega")
                                st.caption("Imprima o pedido e, em seguida, registre a saída. O estoque central baixa e o pedido fica em trânsito até a UBS confirmar.")
                                if st.button("Registrar saída para entrega", type="primary", key=f"btn_despachar_{pedido_selecionado}"):
                                    try:
                                        despachar_pedido(pedido_selecionado)
                                        st.success("Pedido em trânsito. Estoque central baixado. Aguardando confirmação da UBS.")
                                        st.session_state._ir_lista_pedidos = rotulo_lista_por_status(
                                            STATUS_TRANSITO, st.session_state.perfil, opcoes_lista_ped
                                        )
                                        st.session_state.pedido_aberto = pedido_selecionado
                                        st.session_state.modo_abertura = "visualizar"
                                        st.rerun()
                                    except Exception as e:
                                        st.error(str(e))

                            if st.session_state.perfil == "UBS" and pedido_em_transito(status_atual):
                                st.markdown("### Confirmar recebimento")
                                st.caption("Confirme se o que foi separado chegou. Só altere quantidade se algum item não chegou.")
                                with st.form(key=f"form_recebimento_{pedido_selecionado}"):
                                    recebidos = {}
                                    for idx, row in detalhes.iterrows():
                                        enviado = parse_numero(row.get("quantidade_entregue"), inteiro=True)
                                        c1, c2 = st.columns([3, 1])
                                        c1.write(f"**{row.get('material')}** — separado: {enviado}")
                                        recebidos[row["id"]] = c2.number_input(
                                            "Chegou",
                                            min_value=0,
                                            max_value=max(enviado, 0),
                                            value=enviado,
                                            key=f"rec_{row['id']}",
                                            label_visibility="collapsed",
                                        )
                                    if st.form_submit_button("Confirmar recebimento", type="primary"):
                                        try:
                                            confirmar_recebimento_ubs(pedido_selecionado, recebidos)
                                            st.success("Recebimento confirmado. O saldo da unidade foi atualizado.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(str(e))

                            if modo_abertura != "conferir":
                                response_atu = supabase.table("pedidos").select("*").eq("numero_pedido", pedido_selecionado).execute()
                                detalhes = pd.DataFrame(response_atu.data)
                                status_atual = status_consolidado_pedido(detalhes) if not detalhes.empty else status_atual

                                obs_geral = detalhes['observacao'].iloc[0] if 'observacao' in detalhes.columns and pd.notna(detalhes['observacao'].iloc[0]) else ""

                                if st.session_state.perfil == "GESTAO":
                                    chave_via = f"modelo_imp_{pedido_selecionado}"
                                    if st.session_state.get(chave_via) == "Sem valores (via operacional)":
                                        st.session_state[chave_via] = "Via operacional"
                                    elif st.session_state.get(chave_via) == "Com custos (via gerencial)":
                                        st.session_state[chave_via] = "Via gerencial (com custos)"
                                    modelo_impressao = st.radio(
                                        "Modelo de impressão do pedido",
                                        ["Via operacional", "Via gerencial (com custos)"],
                                        horizontal=True,
                                        key=f"modelo_imp_{pedido_selecionado}",
                                    )
                                    sem_custo_print = "gerencial" not in modelo_impressao.lower()
                                else:
                                    sem_custo_print = True
                                    st.caption("A via impressa desta unidade não inclui valores unitários nem custo total.")

                                html_pedido = montar_html_comprovante(detalhes, status_atual, sem_custo=sem_custo_print)
                                st.markdown(textwrap.dedent(html_pedido).strip(), unsafe_allow_html=True)
                                render_iframe_impressao()

                                sufixo_via = "sem_valores" if sem_custo_print else "com_custos"
                                nome_pdf = aplicar_sufixo_arquivo(
                                    nome_arquivo_pedido(
                                        pedido_selecionado,
                                        detalhes["ubs"].iloc[0],
                                        detalhes["data"].iloc[0],
                                        extensao="pdf",
                                    ),
                                    sufixo_via,
                                )
                                nome_csv_final = nome_pdf.replace(".pdf", ".csv")
                                pdf_bytes = gerar_pdf_comprovante(detalhes, status_atual, sem_custo=sem_custo_print)

                                csv_cols = [c for c in ["numero_pedido", "data", "distrito", "ubs", "categoria", "material", "quantidade", "quantidade_entregue", "status", "observacao"] if c in detalhes.columns]
                                if sem_custo_print and csv_cols:
                                    csv_pedido = detalhes[csv_cols].to_csv(index=False).encode("utf-8")
                                else:
                                    csv_pedido = detalhes.to_csv(index=False).encode("utf-8")

                                st.caption(f"Nome do arquivo: `{nome_pdf}`")
                                c_pdf, c_csv, c_imp = st.columns(3)
                                with c_pdf:
                                    st.download_button(
                                        "Baixar comprovante em PDF",
                                        data=pdf_bytes,
                                        file_name=nome_pdf,
                                        mime="application/pdf",
                                        key=f"dl_pdf_{pedido_selecionado}",
                                    )
                                with c_csv:
                                    st.download_button(
                                        "Baixar planilha (CSV)",
                                        data=csv_pedido,
                                        file_name=nome_csv_final,
                                        mime="text/csv",
                                        key=f"dl_comp_{pedido_selecionado}",
                                    )
                                with c_imp:
                                    if st.button("Imprimir", key=f"print_comp_{pedido_selecionado}"):
                                        pedir_impressao()
                                        st.rerun()
                                st.caption("Na janela de impressão, em Destino, escolha a impressora. Se aparecer só Salvar como PDF, abra a lista de destinos.")

                    elif sub_relatorio == "Centro de custos":
                        st.write("### Centro de custos")
                        st.caption("Somente o que já foi conferido e despachado — base para orçamento.")
                        
                        col_f1, col_f2, col_f3 = st.columns(3)
                        with col_f1:
                            lista_distritos_filtro = ["Todos os Distritos"] + list(distritos_ubs.keys())
                            distrito_escolhido_cc = st.selectbox("Filtrar por Distrito", lista_distritos_filtro, key="cc_distrito")
                        
                        with col_f2:
                            if distrito_escolhido_cc == "Todos os Distritos":
                                lista_ubs_disponiveis = ["Todas as UBS"] + list(df_supabase['ubs'].unique())
                            else:
                                lista_ubs_disponiveis = ["Todas as UBS"] + distritos_ubs.get(distrito_escolhido_cc, [])
                            ubs_escolhida_cc = st.selectbox("Filtrar por UBS", lista_ubs_disponiveis, key="cc_ubs_filtro")
                            
                        with col_f3:
                            periodo_cc = st.selectbox("Período de Análise", ["Todo o Período", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"], key="cc_periodo")

                        df_cc = df_supabase.copy()
                        if distrito_escolhido_cc != "Todos os Distritos":
                            unidades_do_distrito = distritos_ubs.get(distrito_escolhido_cc, [])
                            df_cc = df_cc[df_cc['ubs'].isin(unidades_do_distrito)]
                            
                        if ubs_escolhida_cc != "Todas as UBS":
                            df_cc = df_cc[df_cc['ubs'] == ubs_escolhida_cc]
                            
                        agora = pd.Timestamp.now()
                        if periodo_cc == "Última Semana (7 dias)":
                            df_cc = df_cc[df_cc['data_dt'] >= (agora - pd.Timedelta(days=7))]
                        elif periodo_cc == "Último Mês (30 dias)":
                            df_cc = df_cc[df_cc['data_dt'] >= (agora - pd.Timedelta(days=30))]
                        elif periodo_cc == "Ano Atual":
                            df_cc = df_cc[df_cc['data_dt'].dt.year == agora.year]

                        if 'status' in df_cc.columns:
                            df_cc = df_cc[df_cc['status'].isin(list(STATUS_SAIU_CENTRAL))]
                        else:
                            df_cc = df_cc[df_cc['quantidade_entregue'] > 0]

                        st.markdown("---")

                        if df_cc.empty:
                            st.warning("⚠️ Nenhum registro financeiro encontrado para os filtros aplicados.")
                        else:
                            custo_geral_acumulado = df_cc['custo_total'].sum()
                            total_pedidos_filtro = df_cc['numero_pedido'].nunique()
                            total_pecas_entregues = df_cc['quantidade_entregue'].sum()
                            
                            custo_geral_str = f"R$ {custo_geral_acumulado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Custo Total Efetivo Acumulado", custo_geral_str)
                            m2.metric("Total de Pedidos", total_pedidos_filtro)
                            m3.metric("Total de Peças Entregues", int(total_pecas_entregues))
                            
                            st.markdown("---")
                            
                            col_tab1, col_tab2 = st.columns(2)
                            with col_tab1:
                                st.write("#### 📊 Custo Efetivo por Unidade (UBS)")
                                df_por_ubs = df_cc.groupby('ubs')['custo_total'].sum().reset_index()
                                df_por_ubs.columns = ["Unidade (UBS)", "Custo Total"]
                                df_por_ubs = df_por_ubs.sort_values(by="Custo Total", ascending=False).reset_index(drop=True)
                                df_por_ubs["Custo Total (R$)"] = df_por_ubs["Custo Total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                st.dataframe(df_por_ubs[["Unidade (UBS)", "Custo Total (R$)"]], use_container_width=True, hide_index=True)
                                
                                st.markdown("##### Gráfico de Custos por UBS")
                                st.bar_chart(df_por_ubs.set_index("Unidade (UBS)")["Custo Total"])

                            with col_tab2:
                                st.write("#### 📂 Custo Efetivo por Categoria de Insumo")
                                df_por_cat = df_cc.groupby('categoria')['custo_total'].sum().reset_index()
                                df_por_cat.columns = ["Categoria", "Custo Total"]
                                df_por_cat = df_por_cat.sort_values(by="Custo Total", ascending=False).reset_index(drop=True)
                                df_por_cat["Custo Total (R$)"] = df_por_cat["Custo Total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                st.dataframe(df_por_cat[["Categoria", "Custo Total (R$)"]], use_container_width=True, hide_index=True)
                                
                                st.markdown("##### Gráfico de Custos por Categoria")
                                st.bar_chart(df_por_cat.set_index("Categoria")["Custo Total"])

                            st.markdown("---")
                            st.write("#### 📝 Parecer Técnico Orçamentário e Administrativo (Efetivo)")
                            
                            material_top = df_cc.groupby("material")["quantidade_entregue"].sum().reset_index().sort_values(by="quantidade_entregue", ascending=False)
                            nome_material_top = material_top.iloc[0]["material"] if not material_top.empty else "N/A"
                            qtd_material_top = material_top.iloc[0]["quantidade_entregue"] if not material_top.empty else 0
                            
                            texto_escopo_cc = f"Distrito **{distrito_escolhido_cc}** / UBS **{ubs_escolhida_cc}**" if distrito_escolhido_cc != "Todos os Distritos" or ubs_escolhida_cc != "Todas as UBS" else "Rede de Atenção Primária (Consolidado Geral)"
                            
                            parecer_cc = (
                                f"O presente demonstrativo consubstancia a execução orçamentária do centro de custos com base estritamente nos insumos efetivamente entregues, "
                                f"referente ao escopo: {texto_escopo_cc}, abrangendo o período de **{periodo_cc}**. "
                                f"Registrou-se um montante financeiro efetivo de **{custo_geral_str}**, distribuído em **{total_pedidos_filtro} pedidos** e totalizando **{int(total_pecas_entregues)} unidades** despachadas. "
                                f"Evidencia-se maior expressividade de entrega no item **{nome_material_top}** (com **{int(qtd_material_top)} unidades** efetivamente fornecidas). "
                                f"A execução orçamentária reflete diretamente os quantitativos liberados pelo almoxarifado central."
                            )
                            
                            st.markdown(f"""
                            <div style="border: 1px solid #16a085; padding: 15px; border-radius: 6px; background-color: #f4fcfb;">
                                <p style="text-align: justify; color: #2c3e50; font-size: 14px; line-height: 1.6; margin: 0;">
                                    {parecer_cc}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            csv_cc = df_cc.to_csv(index=False).encode('utf-8')
                            st.download_button("📥 Baixar Dados Completos do Centro de Custos (CSV)", data=csv_cc, file_name="centro_de_custos_efetivo_sispac.csv", mime="text/csv", key="dl_cc")

                    elif sub_relatorio == "Painel analítico":
                        st.write("### Painel analítico — solicitado vs entregue")
                        st.caption("Consulta gerencial com tabela e gráfico. Não substitui o documento oficial.")
                        
                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                        with col_r1:
                            tipo_relatorio = st.selectbox("Tipo", ["Geral (Consolidado)", "Por Categoria"], key="tr_analitico")
                        with col_r2:
                            periodo = st.selectbox(
                                "Período",
                                ["Todo o Período", "Data específica", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"],
                                key="per_analitico",
                            )
                        with col_r3:
                            lista_dist_rel = ["Todos os Distritos"] + list(distritos_ubs.keys())
                            dist_rel_esc = st.selectbox("Distrito", lista_dist_rel, key="dist_rel_filtro")
                        with col_r4:
                            if st.session_state.perfil == "GESTAO":
                                if dist_rel_esc == "Todos os Distritos":
                                    ubs_list_rel = ["Todas as UBS"] + list(df_supabase['ubs'].unique())
                                else:
                                    ubs_list_rel = ["Todas as UBS"] + distritos_ubs.get(dist_rel_esc, [])
                                ubs_escolhida = st.selectbox("UBS", ubs_list_rel, key="ubs_analitico_gestao")
                            else:
                                ubs_escolhida = st.session_state.ubs_nome
                                st.text_input("UBS", value=ubs_escolhida, disabled=True, key="ubs_analitico_ubs")

                        data_analitico = None
                        if periodo == "Data específica":
                            data_analitico = campo_data_br("Data", chave="data_analitico")

                        df_rel = df_supabase.copy()
                        if dist_rel_esc != "Todos os Distritos":
                            unidades_d_rel = distritos_ubs.get(dist_rel_esc, [])
                            df_rel = df_rel[df_rel['ubs'].isin(unidades_d_rel)]
                        if st.session_state.perfil == "GESTAO" and ubs_escolhida != "Todas as UBS":
                            df_rel = df_rel[df_rel['ubs'] == ubs_escolhida]
                            
                        agora = pd.Timestamp.now()
                        rotulo_periodo = periodo
                        if periodo == "Data específica" and data_analitico:
                            datas_pedido = pd.to_datetime(df_rel["data_dt"], errors="coerce")
                            df_rel = df_rel[datas_pedido.dt.date == data_analitico]
                            rotulo_periodo = formatar_data_br(data_analitico)
                        elif periodo == "Última Semana (7 dias)":
                            df_rel = df_rel[df_rel['data_dt'] >= (agora - pd.Timedelta(days=7))]
                        elif periodo == "Último Mês (30 dias)":
                            df_rel = df_rel[df_rel['data_dt'] >= (agora - pd.Timedelta(days=30))]
                        elif periodo == "Ano Atual":
                            df_rel = df_rel[df_rel['data_dt'].dt.year == agora.year]

                        st.markdown("---")
                        
                        if df_rel.empty:
                            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
                        else:
                            df_rel = df_rel.copy()
                            datas_lista = pd.to_datetime(df_rel["data_dt"], errors="coerce")
                            df_rel["_dia"] = datas_lista.dt.date
                            if tipo_relatorio == "Geral (Consolidado)":
                                st.write(f"**Consolidado Geral (Solicitado vs Entregue) - Escopo: {ubs_escolhida} ({rotulo_periodo})**")
                                
                                if st.session_state.perfil == "GESTAO":
                                    df_consolidado = df_rel.groupby(["_dia", "categoria", "material"], dropna=False).agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_consolidado.columns = ["_dia", "Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_consolidado["Custo Efetivo (R$)"] = df_consolidado["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_consolidado["Data"] = df_consolidado["_dia"].map(formatar_data_br)
                                    df_exibicao = df_consolidado.sort_values(by=["_dia", "Categoria", "Material"])[
                                        ["Data", "Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]
                                    ]
                                else:
                                    df_exibicao = df_rel.groupby(["_dia", "categoria", "material"], dropna=False).agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_exibicao.columns = ["_dia", "Categoria", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                    df_exibicao["Data"] = df_exibicao["_dia"].map(formatar_data_br)
                                    df_exibicao = df_exibicao.sort_values(by=["_dia", "Categoria", "Material"])[
                                        ["Data", "Categoria", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                    ]
                                
                                st.dataframe(df_exibicao, use_container_width=True, hide_index=True, column_order=list(df_exibicao.columns))
                                
                                st.markdown("#### 📊 Comparativo Gráfico: Solicitado vs Entregue")
                                df_grafico = df_rel.groupby("material")[["quantidade", "quantidade_entregue"]].sum()
                                df_grafico.columns = ["Solicitado", "Entregue"]
                                st.bar_chart(df_grafico)
                                
                                csv = df_exibicao.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Baixar Relatório Comparativo em CSV", data=csv, file_name="relatorio_solicitado_vs_entregue.csv", mime="text/csv", key="dl_geral")
                                
                            else:
                                cat_disponiveis = df_rel["categoria"].unique().tolist()
                                cat_escolhida = st.selectbox("Selecione a Categoria Desejada", cat_disponiveis, key="cat_escolhida_sel")
                                
                                df_cat_filtrado = df_rel[df_rel["categoria"] == cat_escolhida]
                                
                                if st.session_state.perfil == "GESTAO":
                                    df_cat_cons = df_cat_filtrado.groupby(["_dia", "material"], dropna=False).agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_cat_cons.columns = ["_dia", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_cat_cons["Custo Efetivo (R$)"] = df_cat_cons["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_cat_cons["Data"] = df_cat_cons["_dia"].map(formatar_data_br)
                                    df_cat_ex = df_cat_cons.sort_values(by=["_dia", "Material"])[
                                        ["Data", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]
                                    ]
                                else:
                                    df_cat_ex = df_cat_filtrado.groupby(["_dia", "material"], dropna=False).agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_cat_ex.columns = ["_dia", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                    df_cat_ex["Data"] = df_cat_ex["_dia"].map(formatar_data_br)
                                    df_cat_ex = df_cat_ex.sort_values(by=["_dia", "Material"])[
                                        ["Data", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                    ]
                                
                                st.write(f"**Consolidado da Categoria: {cat_escolhida} | Escopo: {ubs_escolhida} ({rotulo_periodo})**")
                                st.dataframe(df_cat_ex, use_container_width=True, hide_index=True, column_order=list(df_cat_ex.columns))
                                
                                st.markdown(f"#### 📊 Gráfico Comparativo - {cat_escolhida}")
                                df_grafico_cat = df_cat_filtrado.groupby("material")[["quantidade", "quantidade_entregue"]].sum()
                                df_grafico_cat.columns = ["Solicitado", "Entregue"]
                                st.bar_chart(df_grafico_cat)
                                
                                csv = df_cat_ex.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Baixar Relatório da Categoria em CSV", data=csv, file_name=f"relatorio_categoria_{cat_escolhida}.csv", mime="text/csv", key="dl_cat")

                    elif sub_relatorio == "Documento oficial":
                        st.write("### Documento oficial")
                        st.caption("Peça para impressão ou PDF, com totais e espaço de assinatura.")
                        
                        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                        with col_e1:
                            tipo_imp_oficial = st.selectbox("Formato", ["Consolidado Geral", "Por Categoria"], key="tipo_imp_oficial")
                        with col_e2:
                            periodo_imp = st.selectbox("Período", ["Todo o Período", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"], key="p_imp_oficial")
                        with col_e3:
                            lista_dist_imp = ["Todos os Distritos"] + list(distritos_ubs.keys())
                            dist_imp_esc = st.selectbox("Distrito", lista_dist_imp, key="dist_imp_filtro")
                        with col_e4:
                            if st.session_state.perfil == "GESTAO":
                                if dist_imp_esc == "Todos os Distritos":
                                    ubs_list_imp = ["Todas as UBS"] + list(df_supabase['ubs'].unique())
                                else:
                                    ubs_list_imp = ["Todas as UBS"] + distritos_ubs.get(dist_imp_esc, [])
                                ubs_imp = st.selectbox("Unidade", ubs_list_imp, key="u_imp_oficial")
                            else:
                                ubs_imp = st.session_state.ubs_nome
                                st.text_input("Unidade", value=ubs_imp, disabled=True, key="u_imp_lock_oficial")

                        df_imp = df_supabase.copy()
                        if dist_imp_esc != "Todos os Distritos":
                            unidades_d_imp = distritos_ubs.get(dist_imp_esc, [])
                            df_imp = df_imp[df_imp['ubs'].isin(unidades_d_imp)]
                        if st.session_state.perfil == "GESTAO" and ubs_imp != "Todas as UBS":
                            df_imp = df_imp[df_imp['ubs'] == ubs_imp]
                            
                        agora = pd.Timestamp.now()
                        if periodo_imp == "Última Semana (7 dias)":
                            df_imp = df_imp[df_imp['data_dt'] >= (agora - pd.Timedelta(days=7))]
                        elif periodo_imp == "Último Mês (30 dias)":
                            df_imp = df_imp[df_imp['data_dt'] >= (agora - pd.Timedelta(days=30))]
                        elif periodo_imp == "Ano Atual":
                            df_imp = df_imp[df_imp['data_dt'].dt.year == agora.year]

                        cat_escolhida_imp = None
                        if tipo_imp_oficial == "Por Categoria":
                            if not df_imp.empty:
                                cat_disponiveis_imp = df_imp["categoria"].unique().tolist()
                                cat_escolhida_imp = st.selectbox("Selecione a Categoria para o Relatório Oficial", cat_disponiveis_imp, key="cat_oficial_sel")
                                df_imp = df_imp[df_imp["categoria"] == cat_escolhida_imp]

                        st.markdown("---")
                        
                        if df_imp.empty:
                            st.warning("⚠️ Nenhum registro encontrado para gerar este relatório oficial com os filtros selecionados.")
                        else:
                            if tipo_imp_oficial == "Consolidado Geral":
                                if st.session_state.perfil == "GESTAO":
                                    df_rel_final = df_imp.groupby(["categoria", "material"]).agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_rel_final.columns = ["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_rel_final["Custo Efetivo (R$)"] = df_rel_final["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_rel_final = df_rel_final[["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]]
                                else:
                                    df_rel_final = df_imp.groupby(["categoria", "material"]).agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_rel_final.columns = ["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                titulo_rel_oficial = "Relatório Oficial Consolidado (Solicitado vs Entregue) - SisPAC"
                            else:
                                if st.session_state.perfil == "GESTAO":
                                    df_rel_final = df_imp.groupby("material").agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_rel_final.columns = ["Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_rel_final["Custo Efetivo (R$)"] = df_rel_final["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_rel_final = df_rel_final[["Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]]
                                else:
                                    df_rel_final = df_imp.groupby("material").agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_rel_final.columns = ["Material", "Qtd Solicitada", "Qtd Entregue"]
                                titulo_rel_oficial = f"Relatório Oficial por Categoria ({cat_escolhida_imp}) - SisPAC"

                            df_rel_final = df_rel_final.sort_values(by="Qtd Solicitada", ascending=False).reset_index(drop=True)

                            if st.session_state.perfil == "GESTAO":
                                if st.session_state.get("modelo_imp_oficial") == "Sem valores (via operacional)":
                                    st.session_state.modelo_imp_oficial = "Via operacional"
                                elif st.session_state.get("modelo_imp_oficial") == "Com custos (via gerencial)":
                                    st.session_state.modelo_imp_oficial = "Via gerencial (com custos)"
                                modelo_oficial = st.radio(
                                    "Modelo de impressão do relatório",
                                    ["Via operacional", "Via gerencial (com custos)"],
                                    horizontal=True,
                                    key="modelo_imp_oficial",
                                )
                                sem_custo_oficial = "gerencial" not in modelo_oficial.lower()
                            else:
                                sem_custo_oficial = True

                            df_print = df_rel_final.copy()
                            if sem_custo_oficial:
                                df_print = df_print.drop(columns=[c for c in df_print.columns if "Custo" in str(c)], errors="ignore")

                            custo_global_periodo = df_imp["custo_total"].sum() if "custo_total" in df_imp.columns else 0.0
                            custo_global_str = formatar_moeda_br(custo_global_periodo)
                            total_geral_pedidas = df_rel_final["Qtd Solicitada"].sum()
                            total_geral_entregues = df_rel_final["Qtd Entregue"].sum()
                            df_print = adicionar_linha_total_relatorio(
                                df_print,
                                total_geral_pedidas,
                                total_geral_entregues,
                                None if sem_custo_oficial else custo_global_str,
                            )
                            escopo_texto = f"categoria <b>{html_seguro(cat_escolhida_imp)}</b>" if tipo_imp_oficial == "Por Categoria" else "escopo geral consolidado"
                            via_txt = " (via operacional)" if sem_custo_oficial else " (via gerencial)"
                            extra_cabecalho = [
                                f"Totais: {int(total_geral_pedidas)} un. solicitadas | {int(total_geral_entregues)} un. entregues"
                            ]
                            if not sem_custo_oficial:
                                extra_cabecalho.insert(0, f"Custo efetivo total: {custo_global_str}")
                            cabecalho_html_totais = "".join(
                                f"<p><b>{html_seguro(item.split(':', 1)[0])}:</b>{html_seguro(item.split(':', 1)[1])}</p>"
                                for item in extra_cabecalho
                            )

                            if st.session_state.perfil == "GESTAO" and not sem_custo_oficial:
                                parecer_tecnico = (
                                    f"O presente relatório oficial demonstra o comparativo entre a demanda solicitada e os quantitativos efetivamente entregues referentes ao {escopo_texto} "
                                    f"para o distrito/unidade (<b>{html_seguro(dist_imp_esc)} / {html_seguro(ubs_imp)}</b>), considerando o período de <b>{html_seguro(periodo_imp)}</b>. "
                                    f"Registrou-se um total de <b>{int(total_geral_pedidas)} unidades solicitadas</b> frente a <b>{int(total_geral_entregues)} unidades efetivamente entregues</b>, "
                                    f"totalizando um <b>custo efetivo de {custo_global_str}</b> para o centro de custos."
                                )
                            else:
                                parecer_tecnico = (
                                    f"O presente relatório oficial demonstra o comparativo entre a demanda solicitada e os quantitativos efetivamente entregues referentes ao {escopo_texto} "
                                    f"para a unidade <b>{html_seguro(ubs_imp)}</b>, considerando o período de <b>{html_seguro(periodo_imp)}</b>. "
                                    f"Registrou-se um total de <b>{int(total_geral_pedidas)} unidades solicitadas</b> frente a <b>{int(total_geral_entregues)} unidades efetivamente entregues</b>."
                                )

                            nome_rel = nome_arquivo_pedido(
                                f"Relatorio-{tipo_imp_oficial}",
                                ubs_imp,
                                agora_sispac(),
                                extensao="pdf",
                            )
                            nome_rel = aplicar_sufixo_arquivo(nome_rel, "sem_valores" if sem_custo_oficial else "com_custos")
                            tabela_html = dataframe_para_html(df_print, destacar_ultima=True)
                            html_relatorio = f"""
                            <div class="area-impressao" style="padding: 8px; background-color: #ffffff;">
                                <h3 style="text-align: center; margin: 0;">SECRETARIA MUNICIPAL DE SAÚDE DE PELOTAS</h3>
                                <h4 style="text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;">{html_seguro(titulo_rel_oficial)}{via_txt}</h4>
                                <p><b>Distrito / Unidade:</b> {html_seguro(dist_imp_esc)} / {html_seguro(ubs_imp)}</p>
                                <p><b>Período abrangido:</b> {html_seguro(periodo_imp)}</p>
                                <p><b>Data de emissão:</b> {agora_sispac().strftime('%d/%m/%Y %H:%M')}</p>
                                {cabecalho_html_totais}
                                <p><b>1. Relação consolidada (demanda vs despacho):</b></p>
                                {tabela_html}
                                <p style="margin-top:16px;"><b>2. Parecer técnico / administrativo preliminar:</b></p>
                                <p style="text-align:justify;border:1px solid #7f8c8d;padding:12px;">{parecer_tecnico}</p>
                                {html_bloco_assinaturas(
                                    "Gestão do Almoxarifado",
                                    "Assinatura e carimbo",
                                    "Ciência da unidade",
                                    "Assinatura do responsável",
                                )}
                                {html_rodape_impressao()}
                            </div>
                            """
                            st.markdown(textwrap.dedent(html_relatorio).strip(), unsafe_allow_html=True)
                            st.caption(f"Nome do arquivo: `{nome_rel}`")
                            pdf_rel = gerar_pdf_relatorio(
                                df_print,
                                f"{titulo_rel_oficial}{via_txt}",
                                dist_imp_esc,
                                ubs_imp,
                                periodo_imp,
                                parecer_tecnico,
                                extra_cabecalho=extra_cabecalho,
                                destacar_ultima=True,
                            )
                            c_dl_rel, c_imp_rel = st.columns(2)
                            with c_dl_rel:
                                st.download_button(
                                    "Baixar relatório em PDF",
                                    data=pdf_rel,
                                    file_name=nome_rel,
                                    mime="application/pdf",
                                    key="dl_rel_oficial_pdf",
                                )
                            with c_imp_rel:
                                if st.button("Imprimir", key="btn_print_rel_oficial"):
                                    pedir_impressao()
                                    st.rerun()
                            render_iframe_impressao()
        except Exception as e:
            st.error(f"Erro ao carregar painel e relatórios: {e}")

if secao_gestao == "Cadastro e estoque":
    with nullcontext():
        st.markdown("#### Cadastro, lotes e histórico")
        st.caption("Itens do banco somam-se à planilha. Entrada de lote baixa FIFO na conferência, com trava se duas pessoas salvarem ao mesmo tempo.")
        usuario_atual = st.session_state.get("email_usuario")
        df_cat_banco = carregar_materiais_banco()
        categorias_cadastro = set()
        if col_categoria and df_materiais is not None and not df_materiais.empty:
            for c in df_materiais[col_categoria].dropna():
                nome_cat = str(c).strip()
                if nome_cat and nome_cat not in MATERIAIS_INVALIDOS:
                    categorias_cadastro.add(nome_cat)
        if df_cat_banco is not None and not df_cat_banco.empty and "categoria" in df_cat_banco.columns:
            for c in df_cat_banco["categoria"].dropna():
                nome_cat = str(c).strip()
                if nome_cat and nome_cat not in MATERIAIS_INVALIDOS:
                    categorias_cadastro.add(nome_cat)
        opcoes_cat_cadastro = sorted(categorias_cadastro, key=lambda x: x.casefold())

        col_cat, col_est = st.columns(2, gap="medium")
        with col_cat:
            st.markdown("##### Novo material")
            if not opcoes_cat_cadastro:
                st.warning("Nenhuma categoria encontrada no catálogo. Inclua categorias na planilha para cadastrar materiais.")
            else:
                cat_novo = st.selectbox("Categoria", opcoes_cat_cadastro, key="cad_sel_categoria")
                with st.form("form_cadastro_material"):
                    mat_novo = st.text_input("Nome do material")
                    preco_novo = st.number_input("Valor unitário (R$)", min_value=0.0, value=0.0, format="%.2f")
                    if st.form_submit_button("Cadastrar material"):
                        if not str(cat_novo).strip() or not mat_novo.strip():
                            st.error("Informe categoria e material.")
                        else:
                            try:
                                supabase.table("materiais").insert({
                                    "categoria": str(cat_novo).strip(),
                                    "material": mat_novo.strip(),
                                    "valor_unitario": float(preco_novo),
                                    "criado_por": usuario_atual,
                                }).execute()
                                registrar_auditoria("CADASTRO_MATERIAL", "materiais", f"{str(cat_novo).strip()} / {mat_novo.strip()}")
                                st.success("Material cadastrado. Ele já pode aparecer no pedido.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Não foi possível cadastrar. Rode o SQL do SisPAC no Supabase se a tabela ainda não existir. ({e})")

        with col_est:
            st.markdown("##### Entrada de lote")
            cat_lote = st.selectbox(
                "Categoria",
                ["Selecione a categoria"] + opcoes_cat_cadastro,
                key="lote_sel_categoria",
            )
            nomes_catalogo = []
            if (
                cat_lote not in MATERIAIS_INVALIDOS
                and col_material
                and df_materiais is not None
                and not df_materiais.empty
            ):
                if col_categoria:
                    df_lote_cat = df_materiais[df_materiais[col_categoria].astype(str).str.strip() == str(cat_lote).strip()]
                else:
                    df_lote_cat = df_materiais
                nomes_catalogo = sorted({
                    str(x).strip()
                    for x in df_lote_cat[col_material].dropna()
                    if str(x).strip() not in MATERIAIS_INVALIDOS
                })
            with st.form("form_entrada_lote"):
                material_lote = st.selectbox(
                    "Material",
                    nomes_catalogo if nomes_catalogo else ["Selecione a categoria primeiro"],
                )
                lote_input = st.text_input("Lote")
                c_val, c_qtd = st.columns(2)
                with c_val:
                    validade_input = st.date_input("Validade", value=date.today())
                with c_qtd:
                    qtd_entrada = st.number_input("Quantidade", min_value=1, value=1)
                fornecedor_input = st.text_input("Fornecedor (opcional)")
                if st.form_submit_button("Registrar entrada"):
                    if material_lote in MATERIAIS_INVALIDOS or material_lote == "Selecione a categoria primeiro" or not lote_input.strip():
                        st.error("Informe material e lote.")
                    else:
                        try:
                            supabase.rpc("sispac_entrada_lote", {
                                "p_material": material_lote,
                                "p_lote": lote_input.strip(),
                                "p_validade": validade_input.strftime("%Y-%m-%d"),
                                "p_quantidade": int(qtd_entrada),
                                "p_fornecedor": fornecedor_input.strip(),
                                "p_usuario": usuario_atual,
                            }).execute()
                            st.success("Entrada registrada. O saldo deste material passa a ser o dos lotes.")
                            st.rerun()
                        except Exception as e:
                            if _rpc_ausente(e):
                                try:
                                    supabase.table("estoque_central").insert({
                                        "material": material_lote,
                                        "lote": lote_input.strip(),
                                        "validade": validade_input.strftime("%Y-%m-%d"),
                                        "quantidade_atual": int(qtd_entrada),
                                        "fornecedor": fornecedor_input.strip() or "Não informado",
                                    }).execute()
                                    registrar_auditoria("ENTRADA_LOTE", "estoque_central", f"{material_lote} lote {lote_input.strip()}")
                                    st.success("Entrada registrada (modo simples). Rode o SQL no Supabase para histórico completo e trava.")
                                    st.rerun()
                                except Exception as e2:
                                    st.error(f"Erro ao registrar lote: {e2}")
                            else:
                                st.error(f"Erro ao registrar lote: {e}")

        st.markdown("---")
        df_lista_cad = df_materiais.copy() if df_materiais is not None else pd.DataFrame()
        col_cat_lista, col_mat_lista, col_preco_lista = col_categoria, col_material, col_preco
        if df_cat_banco.empty:
            st.info("Ainda não há materiais só no banco. A lista abaixo é o catálogo (planilha), com estoque e valor.")
        if df_lista_cad is None or df_lista_cad.empty:
            pass
        else:
            st.markdown("##### Materiais cadastrados")
            f_cat_b, f_nome_b = st.columns(2, gap="medium")
            with f_cat_b:
                filtro_cat_banco = st.selectbox(
                    "Categoria",
                    ["Todas"] + opcoes_cat_cadastro,
                    key="filtro_cat_materiais_banco",
                )
            with f_nome_b:
                filtro_mat_banco = st.text_input(
                    "Buscar material cadastrado",
                    key="filtro_materiais_cadastro",
                    placeholder="Digite parte do nome",
                )
            ativar_filtro_digitacao()
            df_show_banco = df_lista_cad.copy()
            col_cat_filtro = col_cat_lista if col_cat_lista in df_show_banco.columns else None
            col_mat_filtro = col_mat_lista if col_mat_lista in df_show_banco.columns else None
            if filtro_cat_banco != "Todas" and col_cat_filtro:
                df_show_banco = df_show_banco[
                    df_show_banco[col_cat_filtro].astype(str).str.strip() == str(filtro_cat_banco).strip()
                ]
            termo_banco = str(filtro_mat_banco or "").strip()
            if termo_banco:
                if col_mat_filtro:
                    mascara = df_show_banco[col_mat_filtro].astype(str).str.contains(
                        termo_banco, case=False, regex=False, na=False
                    )
                    if col_cat_filtro:
                        mascara = mascara | df_show_banco[col_cat_filtro].astype(str).str.contains(
                            termo_banco, case=False, regex=False, na=False
                        )
                    df_show_banco = df_show_banco[mascara]
                else:
                    mascara = False
                    for col in df_show_banco.columns:
                        mascara = mascara | df_show_banco[col].astype(str).str.contains(
                            termo_banco, case=False, regex=False, na=False
                        )
                    df_show_banco = df_show_banco[mascara]
            df_quadro = quadro_cadastro_estoque(
                df_show_banco,
                col_cat_lista,
                col_mat_lista,
                col_preco_lista,
                df_materiais,
                col_material,
                col_estoque,
                saidas_conferidas,
                saldos_lote,
                materiais_com_lote,
            )
            st.caption(f"Mostrando {len(df_quadro)} de {len(df_lista_cad)} material(is). Valor total = estoque atual × valor unitário.")
            if df_quadro.empty:
                st.info("Nenhum material com esse filtro.")
            else:
                st.dataframe(df_quadro, use_container_width=True, hide_index=True)

        st.markdown("##### Lotes no estoque central")
        try:
            res_est = supabase.table("estoque_central").select("*").execute()
            if res_est.data:
                df_est = pd.DataFrame(res_est.data)
                colunas_est = [c for c in ["material", "lote", "validade", "quantidade_atual", "fornecedor"] if c in df_est.columns]
                st.dataframe(df_est[colunas_est] if colunas_est else df_est, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum lote cadastrado. Enquanto isso, o saldo pode vir da planilha menos o já conferido.")
        except Exception as e:
            st.error(f"Erro ao ler estoque_central: {e}")

        st.markdown("##### Histórico de movimentos")
        try:
            res_mov = (
                supabase.table("movimentos_estoque")
                .select("*")
                .order("criado_em", desc=True)
                .limit(200)
                .execute()
            )
            if res_mov.data:
                st.dataframe(pd.DataFrame(res_mov.data), use_container_width=True, hide_index=True)
            else:
                st.caption("Sem movimentos ainda. Eles aparecem após o SQL do SisPAC e a primeira entrada ou conferência.")
        except Exception:
            st.caption("Histórico indisponível até o SQL ser executado no Supabase.")

        st.markdown("##### Auditoria")
        try:
            res_aud = (
                supabase.table("sispac_auditoria")
                .select("*")
                .order("criado_em", desc=True)
                .limit(100)
                .execute()
            )
            if res_aud.data:
                st.dataframe(pd.DataFrame(res_aud.data), use_container_width=True, hide_index=True)
            else:
                st.caption("Sem registros de auditoria ainda.")
        except Exception:
            st.caption("Tabela de auditoria ainda não existe no banco.")

        st.markdown("---")
        st.markdown("##### Estoque das unidades (piloto)")
        st.caption("Saldo que chegou na UBS após a conferência. A unidade registra o consumo. Não mistura com o estoque central.")
        render_painel_estoque_ubs(modo_gestao=True)

if secao_gestao == "Empenhos e notas":
    render_painel_empenhos(st.session_state.get("email_usuario"))

if aba_estoque_ubs is not None:
    with aba_estoque_ubs:
        st.markdown("#### Estoque desta unidade")
        st.caption("O que o almoxarifado enviou entra aqui. Informe o que foi usado no dia a dia para o saldo ficar correto.")
        render_painel_estoque_ubs(modo_gestao=False)
