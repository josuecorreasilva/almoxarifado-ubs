import streamlit as st
import pandas as pd
import time
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="Almoxarifado Saúde", page_icon="🏥", layout="wide")

st.markdown("""
    <style>
    @media print {
        [data-testid="stSidebar"], header, button, .stButton, .nao-imprimir {
            display: none !important;
        }
        body {
            background-color: white;
        }
    }
    </style>
""", unsafe_allow_html=True)

supabase_url = "https://dglgicnsdelxvhkxwfzd.supabase.co"
supabase_key = "sb_publishable_D6M75JYkHMrtR40Caw1Ruw_RYO3qWbF"
supabase = create_client(supabase_url, supabase_key)

# ==========================================
# 2. VARIÁVEIS FUNDAMENTAIS (DADOS BASE)
# ==========================================
distritos_ubs = {
    "Centro/Porto": ["Balsa", "Bom Jesus", "Simões Lopes"],
    "Areal": ["Areal Leste", "Areal Fundão"],
    "Três Vendas": ["Fernando Osório", "Lindoia"],
    "Fragata": ["Guabiroba", "Simões Lopes"],
    "Rural": ["Coronel Maciel", "Gruppelli"]
}

url_google_sheets_materiais = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pub?output=csv"

# ==========================================
# 3. SISTEMA DE LOGIN E SEGURANÇA
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    caixa_login = st.container()
    with caixa_login:
        st.subheader("🔒 Acesso Restrito")
        
        email_digitado = st.text_input("E-mail").lower().strip()
        senha_digitada = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            try:
                resposta = supabase.auth.sign_in_with_password({
                    "email": email_digitado,
                    "password": senha_digitada
                })
                
                st.session_state.autenticado = True
                st.session_state.email_usuario = resposta.user.email
                
                if "ubs" in st.session_state.email_usuario:
                    st.session_state.perfil = "UBS"
                    nome_limpo = email_digitado.split('@')[0].replace("ubs", "").replace("_", "").replace(".", "")
                    st.session_state.ubs_nome = nome_limpo.capitalize()
                else:
                    st.session_state.perfil = "GESTAO"
                    st.session_state.ubs_nome = "Visão Global"
                
                st.rerun()
                
            except Exception as e:
                st.error("Credenciais inválidas. Verifique o e-mail e a senha.")
                
    st.stop()

# ==========================================
# 4. BARRA LATERAL (MENU DE USUÁRIO)
# ==========================================
st.sidebar.write(f"👤 Acesso: **{st.session_state.email_usuario}**")
st.sidebar.write(f"🏥 Perfil: {st.session_state.perfil}")
if st.sidebar.button("Sair do Sistema"):
    supabase.auth.sign_out()
    st.session_state.autenticado = False
    st.rerun()

# ==========================================
# 5. CABEÇALHO PRINCIPAL
# ==========================================
col_logo1, col_logo2, col_titulo = st.columns([1, 1, 6])

with col_logo1:
    st.image("horizontalloggoverr.png", width=90) 
    
with col_logo2:
    st.image("brasao-cidade-pelotas-rs.jpg", width=90)

with col_titulo:
    st.markdown("### 📦 SisPAC (Sistema de Pedidos - Almoxarifado Central) - SMS<br>*(BD Profissional)*", unsafe_allow_html=True)

# ==========================================
# 6. ABAS DINÂMICAS POR PERFIL DE ACESSO
# ==========================================
if st.session_state.perfil == "UBS":
    aba1, aba2 = st.tabs(["Fazer Novo Pedido", "Acompanhar Meus Pedidos"])
else:
    aba1, aba2, aba3 = st.tabs(["Painel Gerencial", "Relatórios e Parecer Técnico", "Acompanhar e Buscar Pedidos"])

# ==========================================
# FLUXO DA UBS
# ==========================================
if st.session_state.perfil == "UBS":
    with aba1:
        st.subheader("Formulário da Unidade Básica de Saúde")
        
        col_distrito, col_ubs = st.columns(2)
        unidade_usuario = st.session_state.ubs_nome 
        
        distrito_detectado = "Não Encontrado"
        for distrito, unidades in distritos_ubs.items():
            if unidade_usuario in unidades:
                distrito_detectado = distrito
                break
                
        with col_distrito:
            distrito_selecionado = st.selectbox("Distrito (Acesso Restrito)", [distrito_detectado], disabled=True)
        with col_ubs:
            ubs_selecionada = st.selectbox("Unidade (Acesso Restrito)", [unidade_usuario], disabled=True)
            
        st.markdown("---")
        
        try:
            df_materiais = pd.read_csv(url_google_sheets_materiais)
            lista_categorias = df_materiais["Categoria"].dropna().unique().tolist()
        except:
            st.error("Erro ao carregar materiais. Verifique o link do Google Sheets.")
            lista_categorias = ["Erro"]
            df_materiais = pd.DataFrame()
            
        categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias)
        
        if not df_materiais.empty and "Categoria" in df_materiais.columns:
             df_filtrado = df_materiais[df_materiais["Categoria"] == categoria_selecionada]
             lista_de_itens = df_filtrado["Material"].dropna().tolist()
        else:
             lista_de_itens = ["Selecione Categoria"]
             
        if 'carrinho' not in st.session_state:
            st.session_state.carrinho = []
            
        col1, col2 = st.columns(2)
        with col1:
            material = st.selectbox("2. Selecione o Material", lista_de_itens)
        with col2:
            quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
            
        if st.button("➕ Adicionar Item ao Pedido", key="btn_adicionar_item"):
            st.session_state.carrinho.append({
                "distrito": distrito_selecionado, 
                "ubs": ubs_selecionada,
                "categoria": categoria_selecionada,
                "material": material,
                "quantidade": quantidade
            })
            st.success(f"Adicionado: {quantidade}x {material}")

        # --- RESUMO DO CARRINHO ---
        if len(st.session_state.carrinho) > 0:
            st.markdown("---")
            col_cab1, col_cab2, col_cab3, col_cab4, col_cab5 = st.columns([1.5, 2, 3, 1, 0.5])
            col_cab1.write("**UBS**")
            col_cab2.write("**Categoria**")
            col_cab3.write("**Material**")
            col_cab4.write("**Qtd**")
            col_cab5.write("**Excluir**")
            st.markdown("---")
            
            for i, item in enumerate(st.session_state.carrinho):
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1, 0.5])
                c1.write(item["ubs"])
                c2.write(item["categoria"])
                c3.write(item["material"])
                c4.write(item["quantidade"])
                
                if c5.button("🗑️", key=f"excluir_{i}_{item['material']}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()

        st.markdown("---")
        
        observacao_geral = st.text_area(
            "📝 Observações Gerais (Opcional)", 
            placeholder="Ex: Urgência na entrega, horário preferencial...",
            key="input_observacao_geral"
        )

        if st.button("✅ Enviar Pedido Completo", key="btn_enviar_pedido"):
            if not st.session_state.carrinho:
                st.warning("⚠️ O carrinho está vazio! Adicione pelo menos um item antes de enviar.")
            elif not supabase:
                st.error("❌ Erro crítico: A conexão com o Supabase não foi estabelecida.")
            else:
                numero_pedido = f"PED-{int(time.time())}"
                data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                obs_limpa = observacao_geral.strip() if observacao_geral else ""
                if not obs_limpa or obs_limpa.upper() == "EMPTY":
                    texto_observacao = "Sem observação"
                else:
                    texto_observacao = obs_limpa

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
                            "observacao": texto_observacao,
                            "status": "Pedido enviado"
                        })

                    try:
                        response = supabase.table("pedidos").insert(lista_insercao).execute()
                        st.success(f"✅ Pedido {numero_pedido} enviado com sucesso!")
                        st.session_state.carrinho = []
                        st.session_state["input_observacao_geral"] = ""
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro retornado pelo Banco de Dados: {e}")

    # --- ABA 2 DA UBS: ACOMPANHAR E HISTÓRICO COM PESQUISA ---
    with aba2:
        st.subheader("🔍 Acompanhamento e Histórico de Pedidos da Unidade")
        
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
                    df_supabase = df_supabase[df_supabase['ubs'].str.lower() == st.session_state.ubs_nome.lower()]
                    
                    if df_supabase.empty:
                        st.warning("Sua unidade ainda não possui pedidos cadastrados.")
                    else:
                        if 'status' not in df_supabase.columns:
                            df_supabase['status'] = 'Pedido enviado'

                        st.write("### 🔎 Pesquisa no Histórico")
                        termo_busca = st.text_input("Digite o número do pedido ou nome do material:", placeholder="Ex: PED-171829...")
                        
                        df_filtrado_ubs = df_supabase.copy()
                        if termo_busca:
                            df_filtrado_ubs = df_filtrado_ubs[
                                df_filtrado_ubs['numero_pedido'].astype(str).str.contains(termo_busca, case=False, na=False) |
                                df_filtrado_ubs['material'].astype(str).str.contains(termo_busca, case=False, na=False)
                            ]
                        
                        pedidos_unicos = df_filtrado_ubs[["numero_pedido", "data", "status"]].drop_duplicates().sort_values(by="data", ascending=False).reset_index(drop=True)
                        
                        if pedidos_unicos.empty:
                            st.warning("Nenhum pedido encontrado com esse critério de busca.")
                        else:
                            st.dataframe(pedidos_unicos, use_container_width=True, hide_index=True)
                            
                            st.markdown("---")
                            lista_opcoes = ["Selecione..."] + list(pedidos_unicos["numero_pedido"].unique())
                            pedido_escolhido = st.selectbox("Selecione um número de pedido para ver o comprovante:", lista_opcoes, key="sel_hist_ubs")
                            
                            if pedido_escolhido != "Selecione...":
                                detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_escolhido]
                                status_atual = detalhes['status'].iloc[0] if 'status' in detalhes.columns else "Pedido enviado"
                                
                                st.markdown(f"""
                                <div style="border: 2px solid #333; padding: 20px; border-radius: 8px; background-color: #ffffff;">
                                    <h4 style="text-align: center; color: #222; margin: 0;">Comprovante de Requisição - {pedido_escolhido}</h4>
                                    <p style="margin: 5px 0;"><b>Data/Hora do Envio:</b> {detalhes['data'].iloc[0]}</p>
                                    <p style="margin: 5px 0;"><b>Status Atual:</b> <span style="background-color: #e67e22; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{status_atual}</span></p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.write("**Itens Solicitados:**")
                                df_itens_ubs = detalhes[["categoria", "material", "quantidade"]].rename(columns={"categoria": "Categoria", "material": "Material", "quantidade": "Qtd"})
                                st.dataframe(df_itens_ubs, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Erro ao carregar histórico: {e}")

# ==========================================
# FLUXO DA GESTÃO (3 ABAS)
# ==========================================
else:
    with aba1:
        st.subheader("📊 Painel Gerencial (Visão Global)")
        st.info("Painel gerencial centralizado para visualização de todas as unidades da rede.")
        
    with aba2:
        st.subheader("📈 Relatórios Analíticos, Gráficos e Parecer Técnico")
        st.info("Gerador de relatórios analíticos, gráficos de consumo e emissão de documentos oficiais.")
        
    with aba3:
        st.subheader("🔍 Acompanhamento e Busca Avançada na Rede")
        st.info("Módulo de busca global e acompanhamento de pedidos de todas as unidades.")
