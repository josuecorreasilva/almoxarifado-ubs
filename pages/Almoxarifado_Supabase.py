import streamlit as st
import pandas as pd
from datetime import datetime, date
import time

# Tente importar o cliente do Supabase
try:
    from supabase import create_client, Client
    SUPABASE_DISPONIVEL = True
except ImportError:
    SUPABASE_DISPONIVEL = False

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="SisPAC - Sistema de Pedidos e Almoxarifado Central",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO VISUAL PROFISSIONAL (CSS Customizado) ---
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stButton>button { width: 100%; border-radius: 6px; font-weight: bold; }
        .metric-card { background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def init_supabase():
    if SUPABASE_DISPONIVEL and "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    return None

supabase = init_supabase()

# --- DICIONÁRIO DE DISTRITOS E UBS (Pelotas - RS) ---
distritos_ubs = {
    "Distrito A": ["UBS Bom Jesus", "UBS Pestano", "UBS Areal", "UBS Guabiroba"],
    "Distrito B": ["UBS Vila Municipal", "UBS Três Vendas", "UBS Fragata", "UBS Laranjal"],
    "Distrito C": ["UBS Z3", "UBS Santa Arivada", "UBS Colônia Maciel", "UBS Cascata"]
}

# --- GERENCIAMENTO DE SESSÃO E AUTENTICAÇÃO NA BARRA LATERAL ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital.png", width=70)
    st.title("SisPAC v3.1")
    st.markdown("**Secretaria Municipal de Saúde**\n*Pelotas - RS*")
    st.markdown("---")
    
    # Inicializa estados se não existirem
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.subheader("🔐 Identificação de Acesso")
        perfil_escolhido = st.selectbox("Selecione o Perfil", ["UBS", "ALMOXARIFADO", "GESTAO"])
        
        if perfil_escolhido == "UBS":
            todos_UBS = [ubs for lista in distritos_ubs.values() for ubs in lista]
            ubs_logada = st.selectbox("Selecione sua Unidade", todos_UBS)
            if st.button("🚪 Entrar no Sistema"):
                st.session_state.autenticado = True
                st.session_state.perfil = "UBS"
                st.session_state.ubs_nome = ubs_logada
                st.rerun()
        else:
            if st.button("🚪 Entrar como Gestão/Almoxarifado"):
                st.session_state.autenticado = True
                st.session_state.perfil = perfil_escolhido
                st.session_state.ubs_nome = "Almoxarifado Central" if perfil_escolhido == "ALMOXARIFADO" else "Gestão Central"
                st.rerun()
    else:
        st.success(f"Logado como: **{st.session_state.perfil}**")
        st.info(f"Unidade: **{st.session_state.ubs_nome}**")
        
        st.markdown("---")
        if st.button("🔄 Sair / Trocar Perfil"):
            st.session_state.autenticado = False
            st.session_state.carrinho = []
            st.rerun()

    st.markdown("---")
    st.markdown("💡 *Integrado ao Supabase.*")

# Se não estiver autenticado, exibe tela de boas-vindas bloqueada
if not st.session_state.get('autenticado', False):
    st.title("📦 SisPAC - Bem-vindo")
    st.warning("👈 Por favor, selecione seu perfil e unidade na barra lateral ao lado para acessar o sistema.")
    st.stop()

# --- CABEÇALHO PRINCIPAL ---
st.title("📦 SisPAC - Gestão Inteligente de Insumos")
st.markdown("Plataforma integrada de solicitação, controle de estoque central, lotes, validades e conferência logística.")

# --- CARREGAMENTO DE MATERIAIS DO SUPABASE ---
@st.cache_data(ttl=30)
def carregar_materiais_supabase():
    if not supabase:
        return pd.DataFrame(columns=["id", "categoria", "material", "valor_unitario"])
    try:
        res = supabase.table("materiais").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = df.columns.str.lower()
            return df
    except Exception as e:
        st.error(f"Erro ao carregar materiais do banco: {e}")
    return pd.DataFrame(columns=["id", "categoria", "material", "valor_unitario"])

df_materiais = carregar_materiais_supabase()

# --- ESTRUTURA DE ABAS DINÂMICA POR PERFIL ---
if st.session_state.perfil == "GESTAO":
    aba1, aba2, aba3, aba4 = st.tabs([
        "📝 1. Novo Pedido (UBS)", 
        "📦 2. Almoxarifado & Estoque", 
        "📊 3. Painel Gerencial & Conferência", 
        "⚙️ 4. Gestão de Catálogo"
    ])
elif st.session_state.perfil == "ALMOXARIFADO":
    aba1, aba2, aba4 = st.tabs([
        "📝 1. Novo Pedido (UBS)", 
        "📦 2. Almoxarifado & Estoque", 
        "⚙️ 4. Gestão de Catálogo"
    ])
else: # Perfil UBS
    aba1, aba2 = st.tabs([
        "📝 1. Novo Pedido (UBS)", 
        "📦 2. Consulta de Estoque"
    ])


# ==============================================================================
# --- ABA 1: FORMULÁRIO DE PEDIDO (UBS) ---
# ==============================================================================
with aba1:
    st.subheader(f"Solicitação de Insumos - {st.session_state.ubs_nome}")
    
    col_distrito, col_ubs = st.columns(2)
    
    # Identifica o distrito exato com base na UBS logada de forma robusta
    distrito_detectado = "Distrito A"
    for distrito, unidades in distritos_ubs.items():
        if st.session_state.ubs_nome in unidades:
            distrito_detectado = distrito
            break

    with col_distrito:
        st.text_input("Distrito Vinculado", value=distrito_detectado, disabled=True)
    with col_ubs:
        st.text_input("Unidade Requisitante", value=st.session_state.ubs_nome, disabled=True)
            
    st.markdown("---")
    
    if df_materiais.empty:
        st.warning("⚠️ Nenhum material cadastrado na base de dados. Utilize a aba de Catálogo para cadastrar itens.")
        lista_categorias = []
    else:
        lista_categorias = df_materiais["categoria"].dropna().unique().tolist()
        
    categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias if lista_categorias else ["Nenhuma"])
    
    if not df_materiais.empty and categoria_selecionada:
         df_filtrado = df_materiais[df_materiais["categoria"] == categoria_selecionada]
         lista_de_itens = df_filtrado["material"].dropna().tolist()
    else:
         lista_de_itens = []
         
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        material = st.selectbox("2. Selecione o Material", lista_de_itens if lista_de_itens else ["Sem itens"])
        
    # Consulta o saldo atual no estoque central do Supabase
    estoque_disponivel_total = 0
    if supabase and material and material != "Sem itens":
        try:
            res_est = supabase.table("estoque_central").select("quantidade_atual").eq("material", material).execute()
            if res_est.data:
                estoque_disponivel_total = sum(int(item.get("quantidade_atual", 0)) for item in res_est.data)
        except:
            estoque_disponivel_total = 0

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if estoque_disponivel_total > 50:
            st.markdown(f"**Estoque:** <span style='color: green;'>🟢 Disponível ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
        elif estoque_disponivel_total > 0:
            st.markdown(f"**Estoque:** <span style='color: orange;'>🟡 Baixo ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Estoque:** <span style='color: red;'>🔴 Ruptura / Zero</span>", unsafe_allow_html=True)

    with col3:
        quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
        
    valor_unitario_atual = 0.0
    if not df_materiais.empty and material:
        item_row = df_materiais[df_materiais["material"] == material]
        if not item_row.empty:
            try:
                valor_unitario_atual = float(item_row["valor_unitario"].values[0])
            except:
                valor_unitario_atual = 0.0
        
    if st.button("➕ Adicionar Item ao Pedido", key="btn_adicionar_item"):
        if material and material != "Sem itens":
            subtotal = quantidade * valor_unitario_atual
            st.session_state.carrinho.append({
                "distrito": distrito_detectado, 
                "ubs": st.session_state.ubs_nome,
                "categoria": categoria_selecionada,
                "material": material,
                "quantidade": quantidade,
                "valor_unitario": valor_unitario_atual,
                "subtotal": subtotal
            })
            st.success(f"Adicionado: {quantidade}x {material}")
        else:
            st.error("Selecione um material válido.")

    # --- RESUMO DO CARRINHO ---
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        st.subheader("🛒 Itens no Carrinho do Pedido")
        
        for i, item in enumerate(st.session_state.carrinho):
            c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1, 0.5])
            c1.write(f"**Cat:** {item['categoria']}")
            c2.write(f"**Mat:** {item['material']}")
            c3.write(f"**Qtd:** {item['quantidade']}")
            c4.write(f"**Subt:** R$ {item['subtotal']:.2f}" if st.session_state.perfil in ["GESTAO", "ALMOXARIFADO"] else "")
            if c5.button("🗑️", key=f"excluir_{i}_{item['material']}"):
                st.session_state.carrinho.pop(i)
                st.rerun()

    st.markdown("---")
    observacao_geral = st.text_area("📝 Observações Gerais (Opcional)", placeholder="Ex: Urgência na entrega...")

    if st.button("✅ Enviar Pedido Completo", key="btn_enviar_pedido"):
        if not st.session_state.carrinho:
            st.warning("⚠️ O carrinho está vazio!")
        elif not supabase:
            st.error("❌ Erro de conexão com o Supabase.")
        else:
            numero_pedido = f"PED-{int(time.time())}"
            data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            obs_limpa = observacao_geral.strip() if observacao_geral else "Sem observação"

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
                        "observacao": obs_limpa,
                        "status": "Pedido enviado"
                    })

                try:
                    supabase.table("pedidos").insert(lista_insercao).execute()
                    st.success(f"✅ Pedido {numero_pedido} enviado com sucesso!")
                    st.session_state.carrinho = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar no Banco de Dados: {e}")


# ==============================================================================
# --- ABA 2: ALMOXARIFADO & ENTRADA DE LOTES ---
# ==============================================================================
if st.session_state.perfil in ["ALMOXARIFADO", "GESTAO"]:
    with aba2:
        st.subheader("📦 Gestão de Estoque Central - Lotes e Validades")
        st.markdown("Registre a chegada de novas remessas de materiais, informando lote, validade e quantidade física.")
        
        with st.form("form_entrada_estoque"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                material_estoque = st.selectbox("Selecione o Material para Entrada", df_materiais["material"].tolist() if not df_materiais.empty else ["Nenhum"])
            with col_m2:
                lote_input = st.text_input("Número do Lote", placeholder="Ex: LOT-2026-09A")
                
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                validade_input = st.date_input("Data de Validade", value=date.today())
            with col_e2:
                quantidade_entrada = st.number_input("Quantidade Física que Chegou", min_value=1, value=100)
            with col_e3:
                fornecedor_input = st.text_input("Fornecedor / Fabricante", placeholder="Nome da empresa")
                
            btn_salvar_lote = st.form_submit_button("📥 Registrar Entrada no Estoque Central")
            
            if btn_salvar_lote:
                if not material_estoque or material_estoque == "Nenhum" or not lote_input:
                    st.error("Preencha o material e o número do lote corretamente.")
                elif not supabase:
                    st.error("Erro de conexão com o Supabase.")
                else:
                    try:
                        dados_lote = {
                            "material": material_estoque,
                            "lote": lote_input.strip(),
                            "validade": validade_input.strftime("%Y-%m-%d"),
                            "quantidade_atual": int(quantidade_entrada),
                            "fornecedor": fornecedor_input.strip() if fornecedor_input else "Não informado"
                        }
                        supabase.table("estoque_central").insert(dados_lote).execute()
                        st.success(f"✅ Entrada registrada com sucesso para o lote {lote_input}!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao registrar lote: {e}")

        st.markdown("---")
        st.subheader("📋 Estoque Central Atual (Lotes Ativos)")
        try:
            res_estoque_atual = supabase.table("estoque_central").select("*").execute()
            if res_estoque_atual.data:
                df_est_geral = pd.DataFrame(res_estoque_atual.data)
                st.dataframe(df_est_geral, use_container_width=True)
            else:
                st.info("Nenhum lote registrado no estoque central no momento. Utilize o formulário acima para registrar a primeira entrada.")
        except Exception as e:
            st.error(f"Erro ao carregar estoque: {e}")

elif st.session_state.perfil == "UBS":
    with aba2:
        st.subheader("🔍 Consulta Geral de Disponibilidade")
        st.markdown("Consulte abaixo o panorama de estoque dos insumos disponíveis na Secretaria.")
        if not df_materiais.empty:
            st.dataframe(df_materiais[["categoria", "material"]], use_container_width=True)
        else:
            st.info("Nenhum material disponível.")


# ==============================================================================
# --- ABA 3: PAINEL GERENCIAL & CONFERÊNCIA (Apenas Gestão) ---
# ==============================================================================
if st.session_state.perfil == "GESTAO":
    with aba3:
        st.subheader("📊 Painel Gerencial de Pedidos e Entregas")
        st.markdown("Acompanhamento completo de solicitações, custos e controle financeiro restrito.")
        
        try:
            res_pedidos = supabase.table("pedidos").select("*").execute()
            if res_pedidos.data:
                df_pedidos = pd.DataFrame(res_pedidos.data)
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Total de Solicitações", len(df_pedidos))
                custo_total_geral = df_pedidos["custo_total"].sum() if "custo_total" in df_pedidos.columns else 0.0
                col_m2.metric("Custo Global Estimado", f"R$ {custo_total_geral:,.2f}")
                unidades_ativas = df_pedidos["ubs"].nunique() if "ubs" in df_pedidos.columns else 0
                col_m3.metric("UBSs Ativas", unidades_ativas)
                
                st.markdown("---")
                st.dataframe(df_pedidos, use_container_width=True)
            else:
                st.info("Nenhum pedido registrado no sistema.")
        except Exception as e:
            st.error(f"Erro ao carregar painel gerencial: {e}")


# ==============================================================================
# --- ABA 4: GESTÃO DE CATÁLOGO (Almoxarifado & Gestão) ---
# ==============================================================================
if st.session_state.perfil in ["ALMOXARIFADO", "GESTAO"]:
    with aba4:
        st.subheader("⚙️ Cadastro de Novos Materiais no Catálogo")
        st.markdown("Adicione novos itens que passarão a ficar disponíveis instantaneamente para todas as UBSs.")
        
        with st.form("form_novo_material"):
            cat_novo = st.text_input("Categoria do Material", placeholder="Ex: Material de Enfermagem")
            mat_novo = st.text_input("Nome do Material / Descrição", placeholder="Ex: Seringa 20ml")
            preco_novo = st.number_input("Valor Unitário de Referência (R$)", min_value=0.0, value=1.00, format="%.2f")
            
            btn_cadastrar_mat = st.form_submit_button("➕ Cadastrar Novo Material no Sistema")
            
            if btn_cadastrar_mat:
                if not cat_novo or not mat_novo:
                    st.error("Preencha a categoria e o nome do material.")
                elif not supabase:
                    st.error("Erro de conexão com o Supabase.")
                else:
                    try:
                        novo_item_db = {
                            "categoria": cat_novo.strip(),
                            "material": mat_novo.strip().upper(),
                            "valor_unitario": float(preco_novo)
                        }
                        supabase.table("materiais").insert(novo_item_db).execute()
                        st.success(f"✅ Material '{mat_novo}' cadastrado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar material: {e}")

        st.markdown("---")
        st.subheader("📚 Catálogo Atual de Insumos (Base Supabase)")
        if not df_materiais.empty:
            st.dataframe(df_materiais, use_container_width=True)
        else:
            st.info("O catálogo está vazio.")
