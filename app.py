import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Configuração da Página
st.set_page_config(page_title="Almoxarifado Saúde (Profissional)", page_icon="🏥", layout="wide")

# ==========================================
# 1. CONEXÃO COM O BANCO DE DADOS
# ==========================================
supabase_url = "https://dglgicnsdelxvhkxwfzd.supabase.co"
# COLOQUE A SUA CHAVE GIGANTE DE VOLTA AQUI EMBAIXO:
supabase_key = "sb_publishable_D6M75JYkHMrtR40Caw1Ruw_RYO3qWbF" 
supabase = create_client(supabase_url, supabase_key)

# ==========================================
# 2. MEMÓRIA DE SESSÃO DO SISTEMA
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# ==========================================
# 3. TELA DE LOGIN PROFISSIONAL (Supabase Auth)
# ==========================================
if not st.session_state.autenticado:
    caixa_login = st.container()
    with caixa_login:
        st.subheader("🔒 Acesso Restrito - Diretoria de Atenção Primária")
        
        email_digitado = st.text_input("E-mail da Unidade / Gestão").lower().strip()
        senha_digitada = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            try:
                # O Python envia os dados para o cofre do Supabase validar
                resposta = supabase.auth.sign_in_with_password({
                    "email": email_digitado,
                    "password": senha_digitada
                })
                
                # Se a senha estiver correta, o sistema libera o acesso
                st.session_state.autenticado = True
                st.session_state.email_usuario = resposta.user.email
                
                # Define se é a visão global (Gestão) ou visão restrita (UBS)
                if "gestao" in st.session_state.email_usuario:
                    st.session_state.perfil = "GESTAO"
                    st.session_state.ubs_nome = "Visão Global"
                else:
                    st.session_state.perfil = "UBS"
                    st.session_state.ubs_nome = email_digitado.split('@')[0].capitalize()
                
                st.rerun() # Atualiza a tela
                
            except Exception as e:
                st.error("Credenciais inválidas. Verifique o e-mail e a senha.")
                
    st.stop() # Bloqueio de segurança: nada abaixo desta linha é lido sem login.

# ==========================================
# 4. BOTÃO DE SAIR (Barra Lateral)
# ==========================================
st.sidebar.write(f"👤 Acesso: **{st.session_state.email_usuario}**")
st.sidebar.write(f"🏥 Perfil: {st.session_state.perfil}")
if st.sidebar.button("Sair do Sistema"):
    supabase.auth.sign_out() # Encerra a sessão no servidor
    st.session_state.autenticado = False
    st.rerun()

# ==========================================
# 5. INÍCIO DO APLICATIVO (Logos e Título)
# ==========================================
col_logo1, col_logo2, col_titulo = st.columns([1, 1, 6])

with col_logo1:
    st.image("brasao-cidade-pelotas-rs.jpg", width=90)

with col_logo2:
    st.image("horizontalloggoverr.png", width=90)

with col_titulo:
    st.markdown("### 📦 Sistema de Pedidos - Almoxarifado Central - Secretaria Municipal de Saúde<br>*(BD Profissional)*", unsafe_allow_html=True)


# DAQUI PARA BAIXO, MANTENHA O SEU CÓDIGO ORIGINAL DAS ABAS (aba1, aba2 = st.tabs...)
with col_logo1:
    st.image("horizontalloggoverr.png", width=350)
    
with col_logo2:
    # IMPORTANTE: Coloque o nome exato da nova imagem que você fará upload no GitHub
    st.image("brasao-cidade-pelotas-rs.jpg", width=90) # Diminuí um pouco a largura para caberem dois

with col_titulo:
    # O comando st.markdown com '###' é equivalente ao subheader.
    # O '<br>' força a quebra de linha exatamente onde você deseja.
    st.markdown("### 📦 SisPAC (Sistema de Pedidos - Almoxarifado Central) - Secretaria Municipal de Saúde.<br>*(BD Profissional)*", unsafe_allow_html=True)

aba1, aba2 = st.tabs(["Fazer Novo Pedido", "Painel Gerencial (Pedidos Salvos)"])

with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    
    # 1. Identificação
    col_distrito, col_ubs = st.columns(2)
    with col_distrito:
        distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
    with col_ubs:
        ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
        
    st.markdown("---")
    
    # 2. Carregamento de Materiais (Google Sheets)
    try:
        df_materiais = pd.read_csv(url_google_sheets_materiais)
        lista_categorias = df_materiais["Categoria"].dropna().unique().tolist()
    except:
        st.error("Erro crítico ao carregar a lista de materiais do Google Drive. Verifique o link no código do GitHub e se a planilha está publicada como CSV.")
        lista_categorias = ["Erro ao carregar"]
        df_materiais = pd.DataFrame()
        
    # Filtro de Categoria
    categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias)
    
    # Filtra materiais com base na categoria
    if not df_materiais.empty and "Categoria" in df_materiais.columns:
         df_filtrado = df_materiais[df_materiais["Categoria"] == categoria_selecionada]
         lista_de_itens = df_filtrado["Material"].dropna().tolist()
    else:
         lista_de_itens = ["Selecione Categoria"]
         
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    # 3. Adição de Itens
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox("2. Selecione o Material", lista_de_itens)
    with col2:
        quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
        
    if st.button("➕ Adicionar Item à Lista"):
        st.session_state.carrinho.append({
            "distrito": distrito_selecionado, # Nomes minúsculos batendo com o Supabase
            "ubs": ubs_selecionada,
            "categoria": categoria_selecionada,
            "material": material,
            "quantidade": quantidade
        })
        st.success(f"Adicionado ao carrinho: {quantidade}x {material}")
        
    # Resumo do Carrinho e Envio
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        st.write("**🛒 Resumo do Pedido Atual:**")
       # 1. Cria o cabeçalho da nossa tabela interativa
        col_cab1, col_cab2, col_cab3, col_cab4, col_cab5 = st.columns([1.5, 2, 3, 1, 0.5])
        col_cab1.write("**UBS**")
        col_cab2.write("**Categoria**")
        col_cab3.write("**Material**")
        col_cab4.write("**Qtd**")
        col_cab5.write("**Excluir**")
        
        st.markdown("---")
        
        # 2. Lista cada item do carrinho com o botão da lixeira ao lado
        for i, item in enumerate(st.session_state.carrinho):
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1, 0.5])
            c1.write(item["ubs"])
            c2.write(item["categoria"])
            c3.write(item["material"])
            c4.write(item["quantidade"])
            
            if c5.button("🗑️", key=f"excluir_{i}"):
                st.session_state.carrinho.pop(i)
                st.rerun()
        
        # O BOTÃO MÁGICO: ENVIO PARA O SUPABASE
        if st.button("✅ Enviar Pedido Completo (Salvar Permanentemente no Banco de Dados)"):
            if not supabase:
                st.error("Falha na conexão com o banco de dados profissional Supabase. Verifique as credenciais no código e a conexão com a internet. O pedido não foi salvo de forma persistente.")
            else:
                # Gera número do pedido e data únicos baseados no momento do envio
                numero_pedido = f"PED-{int(time.time())}"
                data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with st.spinner('Salvando pedido permanentemente no banco de dados profissional... Por favor, aguarde.'):
                    erro_insercao = False
                    
                    # Prepara a lista de dicionários para inserção múltipla (muito mais rápido e eficiente)
                    lista_insercao = []
                    for item in st.session_state.carrinho:
                        lista_insercao.append({
                            "numero_pedido": numero_pedido,
                            # A coluna 'Data' na tabela Supabase 'pedidos' receberá o valor manual data_pedido ( text )
                            # ou se configurado como timestamp, o Supabase ignora se tiver created_at automático.
                            # Para garantir, enviamos a data manual.
                            "data": data_pedido, 
                            "distrito": item["distrito"],
                            "ubs": item["ubs"],
                            "categoria": item["categoria"],
                            "material": item["material"],
                            "quantidade": item["quantidade"]
                        })

                    try:
                        # Insere todos os itens de uma vez só na tabela 'pedidos' do Supabase
                        response = supabase.table("pedidos").insert(lista_insercao).execute()
                        if not response.data:
                            erro_insercao = True
                            st.error("O Supabase retornou sucesso na requisição, mas nenhum dado foi salvo de forma persistente (response.data vazio). Contate o administrador do banco de dados.")
                    except Exception as e:
                        erro_insercao = True
                        st.error(f"Erro crítico durante a gravação no banco de dados Supabase: {e}. Verifique as permissões da tabela e RLS.")

                if not erro_insercao:
                    st.success(f"Pedido {numero_pedido} enviado com sucesso e salvo permanentemente no banco de dados profissional! Acesse o Painel Gerencial para conferir.")
                    # LIMPA O CARRINHO SOMENTE SE A GRAVAÇÃO NO SUPABASE FUNCIONOU
                    st.session_state.carrinho = []
                else:
                    st.warning("Aviso: O pedido completo não pôde ser salvo permanentemente no banco de dados profissional Supabase. Por segurança, ele permanece na lista acima (carrinho) para que você tente novamente. Se o erro persistir, tire um print desta tela com os materiais e contate o Almoxarifado.")

with aba2:
    st.subheader("Controle Central de Solicitações (Dados do Banco de Dados Profissional Supabase)")
    
    if not supabase:
        st.info("A conexão com o banco de dados profissional Supabase não está configurada corretamente no código do GitHub.")
    else:
        # Busca TODOS os pedidos do Supabase
        with st.spinner('Carregando pedidos históricos do banco de dados profissional... Isso pode levar alguns segundos.'):
            try:
                # Retorna todos os registros ordenados pelo 'id' de forma descendente (mais recentes primeiro)
                response = supabase.table("pedidos").select("*").order("id", desc=True).execute()
                df_supabase = pd.DataFrame(response.data)
            except Exception as e:
                st.error(f"Erro ao carregar dados históricos do banco de dados Supabase: {e}")
                df_supabase = pd.DataFrame()

        if not df_supabase.empty:
            # Garante ordenação (criado_em descendente, se existir, ou numero_pedido)
            # Como ordenamos no select, o df já deve vir certo, mas garantimos.
            if 'id' in df_supabase.columns:
                df_supabase = df_supabase.sort_values(by='id', ascending=False)
            
            # Resumo por Nº do Pedido para a visão geral
            # Precisamos checar se as colunas minúsculas do Supabase vieram
            if 'numero_pedido' in df_supabase.columns and 'distrito' in df_supabase.columns:
                # Agrupa e conta total de itens diferentes por pedido
                resumo_pedidos = df_supabase.groupby(["numero_pedido", "data", "distrito", "ubs"]).size().reset_index(name="Total Itens")
                
                # Exibição Amigável (Ajustando nomes de colunas apenas para a exibição amigável na tela do Painel)
                df_exibicao_painel = resumo_pedidos.rename(columns={"numero_pedido":"Nº do Pedido", "data":"Data Envio", "distrito":"Distrito", "ubs":"UBS", "Total Itens":"Total Itens Diferentes"})
                st.write("**📋 Lista de Pedidos Realizados (Visão Geral - Dados Profissionais):**")
                st.dataframe(df_exibicao_painel, use_container_width=True)
                
                st.markdown("---")
                # Detalhes de um pedido específico
                st.write("**🔍 Detalhar um Pedido Específico:**")
                lista_pedidos_drop = resumo_pedidos["numero_pedido"].unique().tolist()
                pedido_selecionado = st.selectbox("Selecione o Nº do Pedido para conferir a lista completa de materiais solicitados:", ["Selecione..."] + lista_pedidos_drop)
                
                if pedido_selecionado != "Selecione...":
                    # Filtra os detalhes do Supabase apenas para o pedido escolhido
                    detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                    st.write(f"Materiais solicitados no pedido **{pedido_selecionado}** pela unidade **{detalhes['ubs'].iloc[0]}** (Enviado em: {detalhes['data'].iloc[0]}):")
                    
                    # Colunas para exibir amigavelmente
                    colunas_mostra = [c for c in ["categoria", "material", "quantidade"] if c in detalhes.columns]
                    # Exibição amigável dos detalhes
                    df_detalhes_exib = detalhes[colunas_mostra].rename(columns={"categoria":"Categoria", "material":"Material", "quantidade":"Quantidade"})
                    st.dataframe(df_detalhes_exib, use_container_width=True)
            else:
                st.warning("Aviso crítico: As colunas esperadas (ex: 'numero_pedido', 'distrito') não foram encontradas na resposta do banco de dados Supabase. Verifique se o nome das colunas na tabela Supabase 'pedidos' estão exatamente minúsculas e batem com o código.")
        else:
            st.info("Nenhum pedido histórico foi registrado no banco de dados profissional Supabase ainda. Faça o primeiro pedido na Aba 1.")
