import streamlit as st
import pandas as pd
import time
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
# POR QUE: Define como a página vai aparecer na aba do navegador e usa a tela toda (layout wide)
st.set_page_config(page_title="Almoxarifado Saúde", page_icon="🏥", layout="wide")

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
# IMPORTANTE: Cole o seu link real aqui entre as aspas (aquele terminado em output=csv)!
url_google_sheets_materiais = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pub?output=csv"

# ==========================================
# 3. SISTEMA DE LOGIN E SEGURANÇA
# ==========================================
# POR QUE: O session_state é a "memória do navegador". Ele lembra que você já passou pela tela de senha.
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
                # O Python envia os dados para o cofre do Supabase validar
                resposta = supabase.auth.sign_in_with_password({
                    "email": email_digitado,
                    "password": senha_digitada
                })
                
                # Se a senha estiver correta, salva os dados básicos
                st.session_state.autenticado = True
                st.session_state.email_usuario = resposta.user.email
                
                # Regra que define quem enxerga o que:
                if "ubs" in st.session_state.email_usuario:
                    st.session_state.perfil = "UBS"
                    nome_limpo = email_digitado.split('@')[0].replace("ubs", "").replace("_", "").replace(".", "")
                    st.session_state.ubs_nome = nome_limpo.capitalize()
                else:
                    st.session_state.perfil = "GESTAO"
                    st.session_state.ubs_nome = "Visão Global"
                
                st.rerun() # Atualiza a tela para liberar o sistema
                
            except Exception as e:
                st.error("Credenciais inválidas. Verifique o e-mail e a senha.")
                
    st.stop() # Bloqueio de segurança 

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
# POR QUE: st.columns divide a tela. [1, 1, 6] dita a largura: duas colunas finas para logos, uma enorme para o título.
col_logo1, col_logo2, col_titulo = st.columns([1, 1, 6])

with col_logo1:
    st.image("horizontalloggoverr.png", width=90) # ATENÇÃO: Verifique se o nome exato da imagem no GitHub é este
    
with col_logo2:
    st.image("brasao-cidade-pelotas-rs.jpg", width=90)

with col_titulo:
    st.markdown("### 📦 SisPAC (Sistema de Pedidos - Almoxarifado Central) - SMS<br>*(BD Profissional)*", unsafe_allow_html=True)

# ==========================================
# 6. ABAS DO SISTEMA
# ==========================================
aba1, aba2 = st.tabs(["Fazer Novo Pedido", "Painel Gerencial"])

# --- ABA 1: FORMULÁRIO ---
with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    
    col_distrito, col_ubs = st.columns(2)
    
    # Se for Gestão, as caixas ficam livres para escolher qualquer distrito
    if st.session_state.perfil == "GESTAO":
        with col_distrito:
            distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
        with col_ubs:
            ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
            
    # Se for UBS, o sistema trava as caixas na unidade exata que veio do banco de dados
    else:
        unidade_usuario = st.session_state.ubs_nome # Puxa "Balsa" do Supabase
        
        # O Python procura automaticamente a qual distrito essa UBS pertence
        distrito_detectado = "Não Encontrado"
        for distrito, unidades in distritos_ubs.items():
            if unidade_usuario in unidades:
                distrito_detectado = distrito
                break
                
        # Cria as caixas cinzas e bloqueadas (disabled=True)
        with col_distrito:
            distrito_selecionado = st.selectbox("Distrito (Acesso Restrito)", [distrito_detectado], disabled=True)
        with col_ubs:
            ubs_selecionada = st.selectbox("Unidade (Acesso Restrito)", [unidade_usuario], disabled=True)
            
    st.markdown("---")
    
    # POR QUE: Tenta (try) ler o Google Sheets. Se a internet do usuário cair (except), o aplicativo não quebra a tela toda.
    try:
        df_materiais = pd.read_csv(url_google_sheets_materiais)
        lista_categorias = df_materiais["Categoria"].dropna().unique().tolist()
    except:
        st.error("Erro ao carregar materiais. Verifique o link do Google Sheets no início do código.")
        lista_categorias = ["Erro"]
        df_materiais = pd.DataFrame()
        
    categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias)
    
    # Lógica que cruza os dados do Sheets para listar apenas materiais da categoria que você acabou de clicar
    if not df_materiais.empty and "Categoria" in df_materiais.columns:
         df_filtrado = df_materiais[df_materiais["Categoria"] == categoria_selecionada]
         lista_de_itens = df_filtrado["Material"].dropna().tolist()
    else:
         lista_de_itens = ["Selecione Categoria"]
         
    # POR QUE: O carrinho só é criado (vazio) se for a primeira vez que você abre a página.
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    # 3. Adição de Itens
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox("2. Selecione o Material", lista_de_itens)
    with col2:
        quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
        
    # Nova caixa de observação logo abaixo da quantidade
    observacao = st.text_input("4. Observação do Item (Opcional)", placeholder="Ex: Tamanho M, Marca específica, etc.")
        
    if st.button("➕ Adicionar Item ao Pedido"):
        st.session_state.carrinho.append({
            "distrito": distrito_selecionado, 
            "ubs": ubs_selecionada,
            "categoria": categoria_selecionada,
            "material": material,
            "quantidade": quantidade,
            "observacao": observacao # <- Informação nova guardada na memória
        })
        st.success(f"Adicionado: {quantidade}x {material}")
        
    # --- RESUMO DO CARRINHO ---
    # Só desenha a tabela e a lixeira se houver itens no carrinho (maior que 0)
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        col_cab1, col_cab2, col_cab3, col_cab4, col_cab5 = st.columns([1.5, 2, 3, 1, 0.5])
        col_cab1.write("**UBS**")
        col_cab2.write("**Categoria**")
        col_cab3.write("**Material**")
        col_cab4.write("**Qtd**")
        col_cab5.write("**Excluir**")
        st.markdown("---")
        
        # POR QUE: enumerate gera um número de índice (i) para cada item, usado para saber qual linha a lixeira deve excluir
        for i, item in enumerate(st.session_state.carrinho):
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 1, 0.5])
            c1.write(item["ubs"])
            c2.write(item["categoria"])
            c3.write(item["material"])
            c4.write(item["quantidade"])
            
            if c5.button("🗑️", key=f"excluir_{i}"):
                st.session_state.carrinho.pop(i) # pop = remove o item exato da memória
                st.rerun() # Atualiza a tela para a lixeira funcionar instantaneamente
        
        # --- ENVIO PARA O BANCO DE DADOS ---
        if st.button("✅ Enviar Pedido Completo"):
            if not supabase:
                st.error("Falha na conexão com Supabase.")
            else:
                # POR QUE: time.time() gera um número em milissegundos, garantindo que nenhum pedido terá o mesmo código
                numero_pedido = f"PED-{int(time.time())}"
                data_pedido = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with st.spinner('Salvando pedido no servidor...'):
                    # Pega tudo que está no carrinho e transforma em uma estrutura pronta para o banco de dados
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
                            "observacao": item["observacao"]
                        })

                    try:
                        response = supabase.table("pedidos").insert(lista_insercao).execute()
                        if not response.data:
                            st.error("Falha ao salvar dados (resposta vazia).")
                        else:
                            st.success(f"Pedido {numero_pedido} salvo com sucesso!")
                            st.session_state.carrinho = [] # O pedido deu certo, então esvaziamos o carrinho
                    except Exception as e:
                        st.error(f"Erro na gravação Supabase: {e}")

# --- ABA 2: PAINEL GERENCIAL ---
with aba2:
    st.subheader("Painel de Controle Central")
    
    if supabase:
        with st.spinner('Carregando pedidos históricos...'):
            try:
                # POR QUE: ".select('*')" pede TODAS as colunas. ".order('id', desc=True)" traz os mais novos no topo.
                response = supabase.table("pedidos").select("*").order("id", desc=True).execute()
                df_supabase = pd.DataFrame(response.data)
            except Exception as e:
                st.error("Erro ao carregar dados.")
                df_supabase = pd.DataFrame()

        if not df_supabase.empty:
            if 'id' in df_supabase.columns:
                df_supabase = df_supabase.sort_values(by='id', ascending=False)
            
            # POR QUE: A tabela tem todos os materiais soltos. O groupby junta eles em "blocos" pelo número do pedido.
            if 'numero_pedido' in df_supabase.columns:
                resumo_pedidos = df_supabase.groupby(["numero_pedido", "data", "distrito", "ubs"]).size().reset_index(name="Total Itens")
                df_exibicao_painel = resumo_pedidos.rename(columns={"numero_pedido":"Nº Pedido", "data":"Data", "distrito":"Distrito", "ubs":"UBS"})
                
                st.dataframe(df_exibicao_painel, use_container_width=True)
                
                st.markdown("---")
                lista_pedidos_drop = resumo_pedidos["numero_pedido"].unique().tolist()
                pedido_selecionado = st.selectbox("Detalhar Pedido:", ["Selecione..."] + lista_pedidos_drop)
                
               # Se a pessoa escolher um pedido na caixa de seleção, o sistema exibe a folha de impressão
                if pedido_selecionado != "Selecione...":
                    detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                    
                    st.markdown("---")
                    
                    # 📄 CABEÇALHO DO DOCUMENTO OFICIAL PARA O ALMOXARIFADO
                    st.markdown(f"""
                    <div style="border: 2px solid #ccc; padding: 20px; border-radius: 10px; background-color: #fafafa;">
                        <h3 style="text-align: center; color: #333;">📦 SECRETARIA MUNICIPAL DE SAÚDE</h3>
                        <h4 style="text-align: center; color: #666; margin-bottom: 20px;">Comprovante de Requisição de Materiais - SisPAC</h4>
                        <hr>
                        <p><b>Nº do Pedido:</b> {pedido_selecionado}</p>
                        <p><b>Data/Hora do Envio:</b> {detalhes['data'].iloc[0]}</p>
                        <p><b>Distrito:</b> {detalhes['distrito'].iloc[0]}</p>
                        <p><b>Unidade (UBS):</b> {detalhes['ubs'].iloc[0]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.write("**Relação de Itens Solicitados:**")
                    
                    # Tabela detalhada incluindo a nova coluna de observação
                    colunas_mostra = [c for c in ["categoria", "material", "quantidade", "observacao"] if c in detalhes.columns]
                    df_detalhes_exib = detalhes[colunas_mostra].rename(columns={
                        "categoria": "Categoria", 
                        "material": "Material", 
                        "quantidade": "Qtd", 
                        "observacao": "Observação"
                    })
                    st.dataframe(df_detalhes_exib, use_container_width=True)
                    
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.markdown("____________________________________________________")
                    st.markdown("Assinatura do Responsável / Recebimento no Almoxarifado Central")
                    st.markdown("<br>", unsafe_allow_html=True)

                    # Botão que aciona a impressão do navegador
                    if st.button("🖨️ Imprimir ou Salvar Pedido em PDF"):
                        st.info("💡 **Dica:** Na janela de impressão que vai abrir, altere a impressora destino para **'Salvar como PDF'** caso queira guardar o arquivo digitalmente.")
                        st.components.v1.html("""
                            <script>
                                window.parent.print();
                            </script>
                        """, height=0)
