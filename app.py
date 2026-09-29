import streamlit as st
import pandas as pd
import time
import re
import unicodedata
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
# POR QUE: Define como a página vai aparecer na aba do navegador e usa a tela toda (layout wide)
st.set_page_config(page_title="SisPAC — SMS Pelotas", page_icon="🏥", layout="wide")

st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"], header, button, .stButton, .nao-imprimir {
            display: none !important;
        }
        body { background-color: white; }
    }
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1400px; }
    [data-testid="stSidebar"] { background: #f4f7f8; }
    [data-testid="stHeader"] { background: transparent; }
    .sispac-header {
        background: linear-gradient(90deg, #0e4d56 0%, #1a6b75 100%);
        color: #fff;
        border-radius: 10px;
        padding: 14px 22px;
        margin-bottom: 8px;
    }
    .sispac-header h1 { font-size: 1.35rem; margin: 0; font-weight: 650; color: #fff; }
    .sispac-header p { margin: 4px 0 0 0; font-size: 0.88rem; opacity: 0.9; }
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


def status_consolidado_pedido(df_itens):
    if df_itens is None or df_itens.empty or "status" not in df_itens.columns:
        return "Pedido enviado"
    statuses = set(df_itens["status"].dropna().astype(str))
    if "Atendido Parcialmente" in statuses:
        return "Atendido Parcialmente"
    if statuses and statuses.issubset({"Atendido Integralmente"}):
        return "Atendido Integralmente"
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
    data_ref = datetime.now().strftime("%Y%m%d")
    return f"PED-{proximo:04d}-{slug_arquivo(ubs_nome)}-{data_ref}"


def nome_arquivo_pedido(numero_pedido, ubs_nome, data_ref=None, extensao="csv"):
    if data_ref is None:
        data_fmt = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            data_fmt = pd.to_datetime(data_ref).strftime("%Y-%m-%d")
        except Exception:
            data_fmt = datetime.now().strftime("%Y-%m-%d")
    return f"{slug_arquivo(numero_pedido)}_{slug_arquivo(ubs_nome)}_{data_fmt}.{extensao}"


def mapa_saidas_conferidas():
    saidas = {}
    try:
        resposta = supabase.table("pedidos").select("material,quantidade_entregue,status").execute()
        for linha in resposta.data or []:
            status = str(linha.get("status") or "")
            if status not in {"Atendido Parcialmente", "Atendido Integralmente"}:
                continue
            material = str(linha.get("material") or "").strip()
            saidas[material] = saidas.get(material, 0) + parse_numero(linha.get("quantidade_entregue"), inteiro=True)
    except Exception:
        pass
    return saidas


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


def estoque_visivel(material, estoque_planilha, saidas, saldos_lote, materiais_com_lote):
    material = str(material or "").strip()
    if material in materiais_com_lote:
        return max(0, saldos_lote.get(material, 0))
    return max(0, parse_numero(estoque_planilha, inteiro=True) - saidas.get(material, 0))


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
        status = str(linha.get("status") or "Pedido enviado")
        if status in {"Atendido Parcialmente", "Atendido Integralmente"}:
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


def persistir_entregas(atualizacoes, obs_g=""):
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
        supabase.table("pedidos").update(dados_update).eq("id", row_id).execute()
        aplicar_baixa_estoque_central(str(row_original.get("material") or "").strip(), delta_estoque)
        numeros_afetados.append(str(row_original.get("numero_pedido") or ""))
    atualizar_status_pedidos(numeros_afetados)


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


def aplicar_baixa_estoque_central(material, delta):
    delta = int(delta or 0)
    if delta == 0:
        return
    try:
        resposta = supabase.table("estoque_central").select("id,quantidade_atual,validade").eq("material", material).execute()
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
                supabase.table("estoque_central").update({
                    "quantidade_atual": atual - retirar
                }).eq("id", lote["id"]).execute()
                restante -= retirar
        else:
            devolver = abs(delta)
            lote = lotes[0]
            atual = parse_numero(lote.get("quantidade_atual"), inteiro=True)
            supabase.table("estoque_central").update({
                "quantidade_atual": atual + devolver
            }).eq("id", lote["id"]).execute()
    except Exception:
        pass


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
        email_digitado = st.text_input("E-mail institucional").lower().strip()
        senha_digitada = st.text_input("Senha", type="password")
        
        if st.button("Entrar", type="primary", use_container_width=True):
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
st.sidebar.markdown("**SisPAC**")
st.sidebar.caption("Almoxarifado Central · SMS Pelotas")
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

aba1, aba2 = st.tabs(["Novo pedido", "Painel gerencial"])

# --- ABA 1: FORMULÁRIO (Visão da UBS com Indicador de Estoque) ---
with aba1:
    st.markdown("#### Requisição de materiais")
    st.caption("Preencha a unidade, escolha categoria e material e inclua os itens antes de enviar a requisição.")
    
    col_distrito, col_ubs = st.columns(2)
    
    if st.session_state.perfil == "GESTAO":
        with col_distrito:
            distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
        with col_ubs:
            ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
    else:
        unidade_usuario = st.session_state.ubs_nome
        distrito_detectado = st.session_state.get("distrito_ubs") or "Não Encontrado"
        if distrito_detectado == "Não Encontrado":
            for distrito, unidades in distritos_ubs.items():
                if unidade_usuario in unidades:
                    distrito_detectado = distrito
                    break
                
        with col_distrito:
            distrito_selecionado = st.selectbox("Distrito (Acesso Restrito)", [distrito_detectado], disabled=True)
        with col_ubs:
            ubs_selecionada = st.selectbox("Unidade (Acesso Restrito)", [unidade_usuario], disabled=True)
            
    st.markdown("---")

    if st.session_state.get("msg_pedido_ok"):
        st.success(st.session_state.msg_pedido_ok)
        st.session_state.msg_pedido_ok = None
    
    try:
        df_materiais = carregar_materiais(url_google_sheets_materiais)
        col_categoria = achar_coluna(df_materiais, ["Categoria"])
        col_material = achar_coluna(df_materiais, ["Material"])
        col_estoque = achar_coluna(df_materiais, ["Estoque", "Qtd", "Quantidade", "Estoque Atual"])
        col_preco = achar_coluna(df_materiais, ["Valor Unitário", "Valor Unitario", "Preço", "Preco"])
        lista_categorias = df_materiais[col_categoria].dropna().unique().tolist() if col_categoria else ["Erro"]
    except Exception as e:
        st.error(f"Erro ao carregar materiais. Verifique o link do Google Sheets. ({e})")
        lista_categorias = ["Erro"]
        df_materiais = pd.DataFrame()
        col_categoria = col_material = col_estoque = col_preco = None

    saidas_conferidas = mapa_saidas_conferidas()
    saldos_lote, materiais_com_lote = mapa_estoque_lotes()

    opcoes_categoria = ["Selecione a categoria"] + [c for c in lista_categorias if c not in MATERIAIS_INVALIDOS]
    categoria_selecionada = st.selectbox("Categoria", opcoes_categoria, index=0, key="sel_categoria_pedido")
    
    if (
        not df_materiais.empty
        and col_categoria
        and col_material
        and categoria_selecionada not in MATERIAIS_INVALIDOS
    ):
         df_filtrado = df_materiais[df_materiais[col_categoria] == categoria_selecionada]
         lista_de_itens = ["Selecione o material"] + df_filtrado[col_material].dropna().tolist()
    else:
         lista_de_itens = ["Selecione o material"]
         
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    col1, col2, col3 = st.columns([2.2, 1.4, 1.2])
    with col1:
        material = st.selectbox("Material", lista_de_itens, index=0, key="sel_material_pedido")
        
    material_valido = material not in MATERIAIS_INVALIDOS
    estoque_disponivel_total = 0
    valor_unitario_atual = 0.0

    if material_valido and not df_materiais.empty and col_material:
        item_row = df_materiais[df_materiais[col_material] == material]
        if not item_row.empty:
            estoque_planilha = parse_numero(item_row[col_estoque].values[0], inteiro=True) if col_estoque else 0
            estoque_disponivel_total = estoque_visivel(
                material, estoque_planilha, saidas_conferidas, saldos_lote, materiais_com_lote
            )
            if col_preco:
                valor_unitario_atual = parse_numero(item_row[col_preco].values[0])

    with col2:
        if not material_valido:
            st.markdown("**Disponibilidade**")
            st.caption("Selecione um material para consultar o estoque.")
        elif estoque_disponivel_total > LIMIAR_ESTOQUE_BAIXO:
            st.markdown(f"**Disponibilidade:** <span style='color: #1e7a46;'>Regular ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
            st.caption("A baixa no estoque ocorre somente após conferência e despacho pelo Almoxarifado Central.")
        elif estoque_disponivel_total > 0:
            st.markdown(f"**Disponibilidade:** <span style='color: #b86a00;'>Estoque reduzido ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
            st.caption("A baixa no estoque ocorre somente após conferência e despacho pelo Almoxarifado Central.")
        else:
            st.markdown("**Disponibilidade:** <span style='color: #b42318;'>Indisponível</span>", unsafe_allow_html=True)
            st.caption("A baixa no estoque ocorre somente após conferência e despacho pelo Almoxarifado Central.")

    with col3:
        if material_valido:
            qtd_sugerida_form = quantidade_sugerida_pedido(estoque_disponivel_total)
            quantidade = st.number_input(
                "Quantidade",
                min_value=1,
                value=qtd_sugerida_form,
                key=f"qtd_nec_{material}",
            )
            if 0 < estoque_disponivel_total <= LIMIAR_ESTOQUE_BAIXO:
                st.caption(f"Sugestão: {qtd_sugerida_form} un. (estoque reduzido).")
            elif estoque_disponivel_total <= 0:
                st.caption("Sem saldo. A quantidade registra a demanda da unidade.")
        else:
            quantidade = 1
            st.number_input("Quantidade", min_value=1, value=1, disabled=True, key="qtd_nec_placeholder")
        
    if st.button("Adicionar item", key="btn_adicionar_item"):
        if not material or material in MATERIAIS_INVALIDOS:
            st.error("Selecione um material válido antes de adicionar.")
        else:
            if quantidade > estoque_disponivel_total:
                st.warning(f"A quantidade pedida ({quantidade}) é maior que o estoque indicado ({estoque_disponivel_total} un.). O item foi incluído mesmo assim.")

            item_existente = next(
                (item for item in st.session_state.carrinho
                 if item["material"] == material and item["ubs"] == ubs_selecionada),
                None
            )
            if item_existente:
                item_existente["quantidade"] += quantidade
                item_existente["valor_unitario"] = valor_unitario_atual
                item_existente["subtotal"] = item_existente["quantidade"] * valor_unitario_atual
                st.success(f"Quantidade atualizada: {item_existente['quantidade']}x {material}")
            else:
                st.session_state.carrinho.append({
                    "distrito": distrito_selecionado,
                    "ubs": ubs_selecionada,
                    "categoria": categoria_selecionada,
                    "material": material,
                    "quantidade": quantidade,
                    "valor_unitario": valor_unitario_atual,
                    "subtotal": quantidade * valor_unitario_atual
                })
                st.success(f"Adicionado: {quantidade}x {material}")

    # --- RESUMO DO CARRINHO (Sem exibição de preços para a UBS) ---
    if len(st.session_state.carrinho) > 0:
        st.markdown("##### Itens da requisição")
        col_cab1, col_cab2, col_cab3, col_cab4, col_cab5 = st.columns([1.5, 2, 3, 1, 0.5])
        col_cab1.write("**UBS**")
        col_cab2.write("**Categoria**")
        col_cab3.write("**Material**")
        col_cab4.write("**Qtd**")
        col_cab5.write("")
        st.divider()
        
        for i, item in enumerate(st.session_state.carrinho):
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1, 0.5])
            c1.write(item["ubs"])
            c2.write(item["categoria"])
            c3.write(item["material"])
            c4.write(item["quantidade"])
            
            if c5.button("Remover", key=f"excluir_{i}_{item['material']}"):
                st.session_state.carrinho.pop(i)
                st.rerun()

    observacao_geral = st.text_area(
        "Observações (opcional)", 
        placeholder="Informe urgência, horário de recebimento ou outras orientações à gestão.",
        key="input_observacao_geral"
    )

    if st.button("Enviar requisição", type="primary", key="btn_enviar_pedido"):
        if not st.session_state.carrinho:
            st.warning("⚠️ O carrinho está vazio! Adicione pelo menos um item antes de enviar.")
        elif not supabase:
            st.error("❌ Erro crítico: A conexão com o Supabase não foi estabelecida.")
        else:
            numero_pedido = proximo_numero_pedido(ubs_selecionada)
            data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            obs_limpa = observacao_geral.strip() if observacao_geral else ""
            texto_observacao = obs_limpa if obs_limpa else "Sem observação"

            with st.spinner('Salvando pedido no servidor...'):
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
                        "status": "Pedido enviado"
                    })

                try:
                    response = supabase.table("pedidos").insert(lista_insercao).execute()
                    st.session_state.carrinho = []
                    st.session_state.msg_pedido_ok = f"✅ Pedido {numero_pedido} enviado com sucesso!"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro retornado pelo Banco de Dados: {e}")

# --- ABA 2: PAINEL GERENCIAL E RELATÓRIOS OFICIAIS ---
with aba2:
    st.markdown("#### Painel de controle")
    st.caption("Fila de chegada, conferência de entregas, centro de custos e relatórios oficiais.")
    
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
                    # Opções de visualização adaptadas ao perfil
                    opcoes_visao = [
                        "📥 Fila de Chegada (ordem de entrada)",
                        "📋 Acompanhar Pedidos, Conferência e Comprovantes", 
                        "📈 Relatórios Analíticos e Gráficos", 
                        "🖨️ Emitir Relatório Oficial (Imprimir)"
                    ]
                    
                    if st.session_state.perfil == "GESTAO":
                        opcoes_visao.insert(1, "💰 Centro de Custos e Orçamento (Efetivo)")

                    modo_aba2 = st.radio(
                        "Escolha a visualização:", 
                        opcoes_visao,
                        horizontal=True,
                        key="radio_modo_aba2"
                    )
                    
                    st.markdown("---")
                    
                    if modo_aba2 in ("📥 Fila de Chegada (ordem de entrada)", "📋 Acompanhar Pedidos, Conferência e Comprovantes"):
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

                        pedido_selecionado = "Selecione..."
                        conferencia_por_material = False

                        if modo_aba2 == "📥 Fila de Chegada (ordem de entrada)":
                            st.markdown("### 📥 Fila de Chegada")
                            st.caption("Área independente dos filtros. Os pedidos aparecem na ordem em que chegaram (do mais antigo ao mais recente), com identificação da unidade.")

                            col_fila_1, col_fila_2 = st.columns([2, 1])
                            with col_fila_1:
                                so_pendentes = st.checkbox(
                                    "Mostrar só os que aguardam conferência",
                                    value=(st.session_state.perfil == "GESTAO"),
                                    key="fila_so_pendentes",
                                )

                            df_fila = pedidos_unicos.copy()
                            if so_pendentes:
                                df_fila = df_fila[df_fila["status"] == "Pedido enviado"]
                            df_fila = df_fila.sort_values(by="data", ascending=True).reset_index(drop=True)
                            df_fila.insert(0, "ordem", range(1, len(df_fila) + 1))
                            df_fila_exibir = df_fila.rename(columns={
                                "ordem": "Ordem de chegada",
                                "numero_pedido": "Identificação do pedido",
                                "data": "Data/hora",
                                "distrito": "Distrito",
                                "ubs": "UBS",
                                "status": "Status",
                                "itens": "Itens",
                            })
                            with col_fila_2:
                                st.metric("Pedidos na fila", len(df_fila_exibir))

                            if df_fila_exibir.empty:
                                st.info("Não há pedidos nesta fila no momento.")
                            else:
                                st.dataframe(df_fila_exibir, use_container_width=True, hide_index=True)

                                mapa_fila = {
                                    f"#{int(row['Ordem de chegada']):02d} | {row['UBS']} | {row['Identificação do pedido']} | {row['Data/hora']} | {row['Status']}": row["Identificação do pedido"]
                                    for _, row in df_fila_exibir.iterrows()
                                }
                                rotulo_fila = st.selectbox(
                                    "Abrir pedido da fila (do primeiro que chegou ao último):",
                                    ["Selecione..."] + list(mapa_fila.keys()),
                                    key="select_fila_chegada",
                                )
                                pedido_selecionado = mapa_fila.get(rotulo_fila, "Selecione...")
                        else:
                            col_f_st, col_f_dist, col_f_ubs, col_f_agr = st.columns(4)
                            with col_f_st:
                                filtro_status = st.selectbox(
                                    "Status",
                                    ["Todos", "Pedido enviado", "Atendido Parcialmente", "Atendido Integralmente"],
                                    key="filtro_status_conf",
                                )
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
                                if st.session_state.perfil == "GESTAO":
                                    agrupamento = st.selectbox(
                                        "Agrupar conferência",
                                        ["Por pedido", "Por UBS", "Por material (rateio)"],
                                        key="agrupamento_conf",
                                    )
                                else:
                                    agrupamento = "Por pedido"
                                    st.selectbox("Agrupar conferência", ["Por pedido"], disabled=True, key="agrupamento_conf_ubs")

                            df_lista = pedidos_unicos.copy()
                            if filtro_status != "Todos":
                                df_lista = df_lista[df_lista["status"] == filtro_status]
                            if filtro_distrito != "Todos":
                                df_lista = df_lista[df_lista["distrito"] == filtro_distrito]
                            if filtro_ubs != "Todas":
                                df_lista = df_lista[df_lista["ubs"] == filtro_ubs]
                            df_lista = df_lista.sort_values(by="data", ascending=False)

                            conferencia_por_material = agrupamento == "Por material (rateio)" and st.session_state.perfil == "GESTAO"

                            if conferencia_por_material:
                                st.markdown("#### Rateio por material (pedidos ainda não conferidos)")
                                st.caption("Quando várias UBS pedem o mesmo item com estoque baixo, o sistema sugere a divisão proporcional do saldo.")
                                pendentes = df_supabase[~df_supabase["status"].isin(["Atendido Parcialmente", "Atendido Integralmente"])].copy()
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
                                    estoque_atual = estoque_visivel(
                                        material_rateio,
                                        mapa_planilha_conf.get(material_rateio, 0),
                                        saidas_conf,
                                        saldos_lote_conf,
                                        materiais_lote_conf,
                                    )
                                    qtds_pedidas = [parse_numero(q, inteiro=True) for q in linhas_mat["quantidade"].tolist()]
                                    sugestoes = sugerir_rateio(qtds_pedidas, estoque_atual)
                                    demanda_total = sum(qtds_pedidas)
                                    m1, m2, m3 = st.columns(3)
                                    m1.metric("Estoque atual", f"{estoque_atual} un.")
                                    m2.metric("Demanda pendente", f"{demanda_total} un.")
                                    m3.metric("UBS solicitantes", linhas_mat["ubs"].nunique())
                                    if demanda_total > estoque_atual:
                                        st.warning("Estoque insuficiente para atender todas as unidades. As quantidades sugeridas já estão rateadas.")

                                    with st.form(key=f"form_rateio_{material_rateio}"):
                                        novas_quantidades_entregues = {}
                                        for i, (idx, row) in enumerate(linhas_mat.iterrows()):
                                            qtd_pedida = parse_numero(row["quantidade"], inteiro=True)
                                            max_entregue = max(0, min(qtd_pedida, estoque_atual if demanda_total <= estoque_atual else qtd_pedida))
                                            sugerido = min(sugestoes[i] if i < len(sugestoes) else 0, max_entregue)
                                            c1, c2, c3, c4 = st.columns([1.3, 2.2, 1, 1])
                                            c1.write(f"**{row['ubs']}**")
                                            c2.write(f"{row['numero_pedido']}")
                                            c3.write(f"Pediu: {qtd_pedida}")
                                            val_entregue = c4.number_input(
                                                f"Entregar ({row['ubs']})",
                                                min_value=0,
                                                max_value=qtd_pedida,
                                                value=sugerido,
                                                key=f"rateio_{row['id'] if 'id' in row else idx}",
                                            )
                                            novas_quantidades_entregues[row["id"] if "id" in row else idx] = val_entregue
                                        obs_gestao = st.text_input("Observação da Gestão (Opcional)", key=f"obs_rateio_{material_rateio}")
                                        btn_salvar_rateio = st.form_submit_button("💾 Salvar rateio e baixar estoque")
                                        if btn_salvar_rateio:
                                            try:
                                                soma_entrega = sum(novas_quantidades_entregues.values())
                                                if soma_entrega > estoque_atual:
                                                    st.error(f"A soma entregue ({soma_entrega}) ultrapassa o estoque ({estoque_atual}). Ajuste o rateio.")
                                                else:
                                                    atualizacoes = []
                                                    for row_id, nova_qtd in novas_quantidades_entregues.items():
                                                        row_original = linhas_mat[linhas_mat["id"] == row_id].iloc[0] if "id" in linhas_mat.columns else linhas_mat.iloc[list(novas_quantidades_entregues.keys()).index(row_id)]
                                                        atualizacoes.append((row_id, nova_qtd, row_original))
                                                    persistir_entregas(atualizacoes, (obs_gestao or "").strip())
                                                    st.success("Rateio salvo. Estoque baixado com o total entregue deste material.")
                                                    st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro ao salvar rateio: {e}")

                                st.markdown("---")
                                st.write("**Fila de pedidos (para comprovante):**")
                                st.dataframe(df_lista, use_container_width=True, hide_index=True)
                                lista_opcoes = ["Selecione..."] + list(df_lista["numero_pedido"].unique())
                                pedido_selecionado = st.selectbox("Abrir comprovante de um pedido:", lista_opcoes, key="pedido_comp_rateio")
                            else:
                                if agrupamento == "Por UBS" and st.session_state.perfil == "GESTAO" and filtro_ubs == "Todas":
                                    ubs_grupo = st.selectbox(
                                        "Escolha a UBS para ver os pedidos agrupados",
                                        ["Selecione..."] + sorted(df_lista["ubs"].dropna().astype(str).unique().tolist()),
                                        key="ubs_grupo_conf",
                                    )
                                    if ubs_grupo != "Selecione...":
                                        df_lista = df_lista[df_lista["ubs"] == ubs_grupo]

                                def rotulo_pedido(row):
                                    return f"{row['ubs']} | {row['data']} | {row['status']} | {row['numero_pedido']}"

                                mapa_rotulos = {rotulo_pedido(row): row["numero_pedido"] for _, row in df_lista.iterrows()}
                                lista_rotulos = ["Selecione..."] + list(mapa_rotulos.keys())
                                rotulo_escolhido = st.selectbox("Escolha o pedido para conferir ou ver o comprovante:", lista_rotulos, key="pedido_rotulo_conf")
                                pedido_selecionado = mapa_rotulos.get(rotulo_escolhido, "Selecione...")

                                if rotulo_escolhido == "Selecione...":
                                    st.write("**Lista de Pedidos (agrupada pelos filtros acima):**")
                                    st.dataframe(df_lista, use_container_width=True, hide_index=True)
                        
                        if pedido_selecionado != "Selecione...":
                            detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                            status_atual = status_consolidado_pedido(detalhes)

                            # Tela de Conferência exclusiva para a Gestão
                            if st.session_state.perfil == "GESTAO" and not conferencia_por_material:
                                st.markdown("### 📦 Painel de Conferência do Almoxarifado (Itens Entregues)")
                                st.info("Com estoque baixo, a quantidade sugerida já considera o rateio com outras UBS que pediram o mesmo item.")

                                saidas_conf = mapa_saidas_conferidas()
                                saldos_lote_conf, materiais_lote_conf = mapa_estoque_lotes()
                                mapa_planilha_conf = mapa_estoque_planilha(df_materiais, col_material, col_estoque)
                                ja_baixou_estoque = status_atual in {"Atendido Parcialmente", "Atendido Integralmente"}
                                
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
                                        )
                                        teto_fisico = estoque_atual + (qtd_db_entregue if ja_baixou_estoque else 0)
                                        max_entregue = max(0, min(qtd_pedida, teto_fisico))
                                        demanda = demanda_pendente_material(df_supabase, mat, pedido_selecionado)
                                        if qtd_db_entregue == 0 and not ja_baixou_estoque:
                                            if demanda["outras_ubs"] > 0:
                                                qtd_sugerida = sugerir_rateio([qtd_pedida, demanda["outras_ubs"]], estoque_atual)[0]
                                            else:
                                                qtd_sugerida = min(qtd_pedida, max_entregue)
                                            qtd_sugerida = min(qtd_sugerida, max_entregue)
                                            if 0 < estoque_atual <= LIMIAR_ESTOQUE_BAIXO:
                                                qtd_sugerida = min(qtd_sugerida, estoque_atual, qtd_pedida)
                                        else:
                                            qtd_sugerida = min(qtd_db_entregue, max_entregue)
                                            
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
                                            value=qtd_sugerida,
                                            key=f"ent_{row['id'] if 'id' in row else idx}"
                                        )
                                        novas_quantidades_entregues[row['id'] if 'id' in row else idx] = val_entregue
                                        if 0 < estoque_atual <= LIMIAR_ESTOQUE_BAIXO or demanda["outras_ubs"] > 0:
                                            st.caption(f"Quantidade sugerida: **{qtd_sugerida} un.** (estoque baixo / rateio). {texto_outras_solicitacoes(demanda)}")
                                        if demanda["total"] > estoque_atual and not ja_baixou_estoque:
                                            st.warning(
                                                f"Demanda pendente de **{mat}** ({demanda['total']} un., incluindo este pedido) é maior que o estoque ({estoque_atual} un.)."
                                            )

                                    obs_gestao = st.text_input("Observação da Gestão / Almoxarifado (Opcional)", value="", key=f"obs_g_{pedido_selecionado}")
                                    
                                    btn_salvar_conf = st.form_submit_button("💾 Salvar Conferência e Atualizar Entregas")
                                    if btn_salvar_conf:
                                        try:
                                            atualizacoes = []
                                            for row_id, nova_qtd in novas_quantidades_entregues.items():
                                                row_original = detalhes[detalhes['id'] == row_id].iloc[0] if 'id' in detalhes.columns else detalhes.iloc[list(novas_quantidades_entregues.keys()).index(row_id)]
                                                atualizacoes.append((row_id, nova_qtd, row_original))
                                            persistir_entregas(atualizacoes, (obs_gestao or "").strip())
                                            st.success("✅ Conferência salva. Estoque baixado com a quantidade entregue e centro de custos atualizado.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao salvar conferência no Supabase: {e}")
                                
                                st.markdown("---")

                            # Atualiza os detalhes locais após possível alteração
                            response_atu = supabase.table("pedidos").select("*").eq("numero_pedido", pedido_selecionado).execute()
                            detalhes = pd.DataFrame(response_atu.data)
                            status_atual = status_consolidado_pedido(detalhes) if not detalhes.empty else status_atual

                            obs_geral = detalhes['observacao'].iloc[0] if 'observacao' in detalhes.columns and pd.notna(detalhes['observacao'].iloc[0]) else ""

                            st.markdown(f"""
                            <div style="border: 2px solid #333; padding: 20px; border-radius: 8px; background-color: #ffffff;">
                                <h3 style="text-align: center; color: #222; margin: 0;">SECRETARIA MUNICIPAL DE SAÚDE</h3>
                                <h4 style="text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;">Comprovante Oficial de Requisição e Entrega - SisPAC</h4>
                                <hr style="border: 0.5px solid #ccc;">
                                <p style="margin: 5px 0;"><b>Nº do Pedido:</b> {pedido_selecionado}</p>
                                <p style="margin: 5px 0;"><b>Data/Hora do Envio:</b> {detalhes['data'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Distrito:</b> {detalhes['distrito'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Unidade (UBS):</b> {detalhes['ubs'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Status Atual:</b> <span style="background-color: #2980b9; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{status_atual}</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if obs_geral.strip():
                                st.markdown(f"""
                                <div style="margin-top: 10px; padding: 12px; border: 1px solid #d35400; background-color: #fdfaf6; border-radius: 5px;">
                                    <span style="color: #d35400; font-weight: bold;">📌 Observações Gerais:</span><br>
                                    <span style="color: #333; font-size: 14px;">{obs_geral}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.write("**Detalhamento de Itens (Solicitado vs. Entregue e Custos):**")
                            
                            categorias_presentes = detalhes["categoria"].unique()
                            custo_total_pedido_efetivo = 0.0

                            for cat in categorias_presentes:
                                df_cat_raw = detalhes[detalhes["categoria"] == cat]
                                
                                if st.session_state.perfil == "GESTAO":
                                    custo_cat_efetivo = df_cat_raw["custo_total"].sum()
                                    custo_total_pedido_efetivo += custo_cat_efetivo
                                    
                                    st.markdown(f"<p style='margin-bottom: 2px; color: #2c3e50;'><b>📂 Categoria: {cat}</b> <span style='float: right; color: #16a085;'>Subtotal Entregue (Efetivo): R$ {custo_cat_efetivo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + "</span></p>", unsafe_allow_html=True)
                                    
                                    df_cat = df_cat_raw[["material", "quantidade", "quantidade_entregue", "valor_unitario", "custo_total"]].copy()
                                    df_cat.columns = ["Material", "Solicitado", "Entregue", "Valor Unitário (R$)", "Custo Total Entregue (R$)"]
                                    
                                    df_cat["Valor Unitário (R$)"] = df_cat["Valor Unitário (R$)"].apply(lambda x: f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "R$ 0,00")
                                    df_cat["Custo Total Entregue (R$)"] = df_cat["Custo Total Entregue (R$)"].apply(lambda x: f"R$ {float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "R$ 0,00")
                                else:
                                    st.markdown(f"<p style='margin-bottom: 2px; color: #2c3e50;'><b>📂 Categoria: {cat}</b></p>", unsafe_allow_html=True)
                                    df_cat = df_cat_raw[["material", "quantidade", "quantidade_entregue"]].rename(columns={"material": "Material", "quantidade": "Qtd Solicitada", "quantidade_entregue": "Qtd Entregue"})
                                
                                st.dataframe(df_cat, use_container_width=True, hide_index=True)
                                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                            
                            if st.session_state.perfil == "GESTAO":
                                custo_total_str = f"R$ {custo_total_pedido_efetivo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                                st.markdown(f"""
                                <div style="padding: 12px; background-color: #e8f8f5; border: 1px solid #1abc9c; border-left: 6px solid #16a085; border-radius: 4px; margin-top: 15px; margin-bottom: 15px;">
                                    <span style="color: #117a65; font-size: 16px; font-weight: bold;">💰 Custo Total Efetivo deste Pedido (Centro de Custos): {custo_total_str}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("<br><br>", unsafe_allow_html=True)
                            st.markdown("____________________________________________________")
                            st.markdown("Assinatura do Responsável / Recebimento na UBS")
                            st.markdown("<br>", unsafe_allow_html=True)

                            nome_csv_pedido = nome_arquivo_pedido(
                                pedido_selecionado,
                                detalhes["ubs"].iloc[0],
                                detalhes["data"].iloc[0],
                                extensao="csv",
                            )
                            csv_pedido = detalhes.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "📥 Baixar comprovante do pedido (CSV)",
                                data=csv_pedido,
                                file_name=nome_csv_pedido,
                                mime="text/csv",
                                key=f"dl_comp_{pedido_selecionado}",
                            )

                            if st.button("🖨️ Imprimir ou Salvar Comprovante em PDF"):
                                st.info(f"💡 Na janela de impressão, escolha **Salvar como PDF**. Nome sugerido: **{nome_csv_pedido.replace('.csv', '.pdf')}**")
                                st.components.v1.html("""<script>window.parent.print();</script>""", height=0)

                    elif modo_aba2 == "💰 Centro de Custos e Orçamento (Efetivo)":
                        st.write("### 💰 Centro de Custos e Orçamento (Baseado nas Entregas Efetivas)")
                        st.markdown("Acompanhamento financeiro oficial calculado estritamente sobre o que foi despachado aos centros de custos.")
                        
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
                            df_cc = df_cc[df_cc['status'].isin(["Atendido Parcialmente", "Atendido Integralmente"])]
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

                    elif modo_aba2 == "📈 Relatórios Analíticos e Gráficos":
                        st.write("### 📈 Painel Analítico: Solicitado vs. Entregue")
                        
                        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                        with col_r1:
                            tipo_relatorio = st.selectbox("Tipo", ["Geral (Consolidado)", "Por Categoria"], key="tr_analitico")
                        with col_r2:
                            periodo = st.selectbox("Período", ["Todo o Período", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"], key="per_analitico")
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

                        df_rel = df_supabase.copy()
                        if dist_rel_esc != "Todos os Distritos":
                            unidades_d_rel = distritos_ubs.get(dist_rel_esc, [])
                            df_rel = df_rel[df_rel['ubs'].isin(unidades_d_rel)]
                        if st.session_state.perfil == "GESTAO" and ubs_escolhida != "Todas as UBS":
                            df_rel = df_rel[df_rel['ubs'] == ubs_escolhida]
                            
                        agora = pd.Timestamp.now()
                        if periodo == "Última Semana (7 dias)":
                            df_rel = df_rel[df_rel['data_dt'] >= (agora - pd.Timedelta(days=7))]
                        elif periodo == "Último Mês (30 dias)":
                            df_rel = df_rel[df_rel['data_dt'] >= (agora - pd.Timedelta(days=30))]
                        elif periodo == "Ano Atual":
                            df_rel = df_rel[df_rel['data_dt'].dt.year == agora.year]

                        st.markdown("---")
                        
                        if df_rel.empty:
                            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
                        else:
                            if tipo_relatorio == "Geral (Consolidado)":
                                st.write(f"**Consolidado Geral (Solicitado vs Entregue) - Escopo: {ubs_escolhida} ({periodo})**")
                                
                                if st.session_state.perfil == "GESTAO":
                                    df_consolidado = df_rel.groupby(["categoria", "material"]).agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_consolidado.columns = ["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_consolidado["Custo Efetivo (R$)"] = df_consolidado["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_exibicao = df_consolidado[["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]]
                                else:
                                    df_exibicao = df_rel.groupby(["categoria", "material"]).agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_exibicao.columns = ["Categoria", "Material", "Qtd Solicitada", "Qtd Entregue"]
                                
                                st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
                                
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
                                    df_cat_cons = df_cat_filtrado.groupby("material").agg({"quantidade": "sum", "quantidade_entregue": "sum", "custo_total": "sum"}).reset_index()
                                    df_cat_cons.columns = ["Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo"]
                                    df_cat_cons["Custo Efetivo (R$)"] = df_cat_cons["Custo Efetivo"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                                    df_cat_ex = df_cat_cons[["Material", "Qtd Solicitada", "Qtd Entregue", "Custo Efetivo (R$)"]]
                                else:
                                    df_cat_ex = df_cat_filtrado.groupby("material").agg({"quantidade": "sum", "quantidade_entregue": "sum"}).reset_index()
                                    df_cat_ex.columns = ["Material", "Qtd Solicitada", "Qtd Entregue"]
                                
                                st.write(f"**Consolidado da Categoria: {cat_escolhida} | Escopo: {ubs_escolhida}**")
                                st.dataframe(df_cat_ex, use_container_width=True, hide_index=True)
                                
                                st.markdown(f"#### 📊 Gráfico Comparativo - {cat_escolhida}")
                                df_grafico_cat = df_cat_filtrado.groupby("material")[["quantidade", "quantidade_entregue"]].sum()
                                df_grafico_cat.columns = ["Solicitado", "Entregue"]
                                st.bar_chart(df_grafico_cat)
                                
                                csv = df_cat_ex.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Baixar Relatório da Categoria em CSV", data=csv, file_name=f"relatorio_categoria_{cat_escolhida}.csv", mime="text/csv", key="dl_cat")

                    else:
                        st.write("### 🖨️ Emissão de Relatório Oficial (Planejado vs Efetivo)")
                        
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

                            st.markdown(f"""
                            <div style="border: 2px solid #333; padding: 25px; border-radius: 8px; background-color: #ffffff;">
                                <h3 style="text-align: center; color: #222; margin: 0;">SECRETARIA MUNICIPAL DE SAÚDE DE PELOTAS</h3>
                                <h4 style="text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;">{titulo_rel_oficial}</h4>
                                <hr style="border: 0.5px solid #ccc;">
                                <p style="margin: 5px 0;"><b>Distrito / Unidade:</b> {dist_imp_esc} / {ubs_imp}</p>
                                <p style="margin: 5px 0;"><b>Período Abrangido:</b> {periodo_imp}</p>
                                <p style="margin: 5px 0;"><b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.write(f"**1. Relação Consolidada (Demanda vs Despacho):**")
                            st.dataframe(df_rel_final, use_container_width=True, hide_index=True)
                            
                            custo_global_periodo = df_imp["custo_total"].sum() if "custo_total" in df_imp.columns else 0.0
                            custo_global_str = f"R$ {custo_global_periodo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                            total_geral_pedidas = df_rel_final["Qtd Solicitada"].sum()
                            total_geral_entregues = df_rel_final["Qtd Entregue"].sum()
                            
                            escopo_texto = f"categoria <b>{cat_escolhida_imp}</b>" if tipo_imp_oficial == "Por Categoria" else "escopo geral consolidado"
                            
                            if st.session_state.perfil == "GESTAO":
                                parecer_tecnico = (
                                    f"O presente relatório oficial demonstra o comparativo entre a demanda solicitada e os quantitativos efetivamente entregues referentes ao {escopo_texto} "
                                    f"para o distrito/unidade (**{dist_imp_esc} / {ubs_imp}**), considerando o período de <b>{periodo_imp}</b>. "
                                    f"Registrou-se um total de <b>{int(total_geral_pedidas)} unidades solicitadas</b> frente a <b>{int(total_geral_entregues)} unidades efetivamente entregues</b>, "
                                    f"totalizando um **custo efetivo de {custo_global_str}** para o centro de custos. "
                                    f"As variações identificadas entre o solicitado e o entregue refletem a gestão de estoque e a disponibilidade do almoxarifado central."
                                )
                            else:
                                parecer_tecnico = (
                                    f"O presente relatório oficial demonstra o comparativo entre a demanda solicitada e os quantitativos efetivamente entregues referentes ao {escopo_texto} "
                                    f"para a unidade <b>{ubs_imp}</b>, considerando o período de <b>{periodo_imp}</b>. "
                                    f"Registrou-se um total de <b>{int(total_geral_pedidas)} unidades solicitadas</b> frente a <b>{int(total_geral_entregues)} unidades efetivamente entregues</b>."
                                )

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.write("**2. Parecer Técnico / Administrativo Preliminar:**")
                            st.markdown(f"""
                            <div style="border: 1px solid #7f8c8d; padding: 15px; border-radius: 6px; background-color: #fcfcfc;">
                                <p style="text-align: justify; color: #2c3e50; font-size: 14px; line-height: 1.6; margin: 0;">
                                    {parecer_tecnico}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br><br>", unsafe_allow_html=True)
                            st.markdown("____________________________________________________")
                            st.markdown("Assinatura e Carimbo do Responsável / Gestão do Almoxarifado")
                            st.markdown("<br>", unsafe_allow_html=True)

                            if st.button("🖨️ Imprimir ou Salvar Relatório Oficial em PDF", key="btn_print_rel_oficial"):
                                st.info("💡 **Dica:** Na janela de impressão, altere o destino para **'Salvar como PDF'** se preferir o arquivo digital.")
                                st.components.v1.html("""<script>window.parent.print();</script>""", height=0)
        except Exception as e:
            st.error(f"Erro ao carregar painel e relatórios: {e}")
