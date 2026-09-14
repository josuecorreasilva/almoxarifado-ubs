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

st.markdown("""
    <style>
    @media print {
        /* Oculta a barra lateral, cabeçalhos do Streamlit, botões e elementos marcados na hora de imprimir */
        [data-testid="stSidebar"], header, button, .stButton, .nao-imprimir {
            display: none !important;
        }
        body {
            background-color: white;
        }
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
    st.image("horizontalloggoverr.png", width=90) 
    
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
    
    # POR QUE: Tenta (try) ler o Google Sheets. Se a internet cair, o aplicativo não quebra a tela toda.
    try:
        df_materiais = pd.read_csv(url_google_sheets_materiais)
        lista_categorias = df_materiais["Categoria"].dropna().unique().tolist()
    except:
        st.error("Erro ao carregar materiais. Verifique o link do Google Sheets no início do código.")
        lista_categorias = ["Erro"]
        df_materiais = pd.DataFrame()
        
    categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias)
    
    # Lógica que cruza os dados do Sheets para listar apenas materiais da categoria selecionada
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
            
            # Chave única para exclusão linha por linha sem perder o estado da página
            if c5.button("🗑️", key=f"excluir_{i}_{item['material']}"):
                st.session_state.carrinho.pop(i)
                st.rerun()

    st.markdown("---")
    
    # --- OBSERVAÇÃO GERAL E ENVIO ---
    # Adicionamos uma key para controlar o estado do campo de texto
    observacao_geral = st.text_area(
        "📝 Observações Gerais (Opcional)", 
        placeholder="Ex: Urgência na entrega, horário preferencial, restrição de acesso ou orientações ao almoxarifado...",
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
                    # Grava no Supabase
                    response = supabase.table("pedidos").insert(lista_insercao).execute()
                    st.success(f"✅ Pedido {numero_pedido} enviado com sucesso!")
                    
                    # SEGURANÇA: Limpa o carrinho e reseta a caixa de observação geral automaticamente
                    st.session_state.carrinho = []
                    st.session_state["input_observacao_geral"] = ""
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro retornado pelo Banco de Dados: {e}")

# --- ABA 2: PAINEL GERENCIAL E RELATÓRIOS OFICIAIS ---
with aba2:
    st.subheader("📊 Painel de Controle e Relatórios")
    
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
                
                # Converte a coluna de data para o formato de data/hora do Pandas
                df_supabase['data_dt'] = pd.to_datetime(df_supabase['data'])
                
                # SEGURANÇA: Se o perfil for UBS, restringe estritamente aos pedidos dela
                if st.session_state.perfil == "UBS":
                    df_supabase = df_supabase[df_supabase['ubs'].str.lower() == st.session_state.ubs_nome.lower()]
                    st.info(f"Visualizando dados exclusivos da unidade: **{st.session_state.ubs_nome}**")
                
                if df_supabase.empty:
                    st.warning("Não há registros de pedidos para esta unidade até o momento.")
                else:
                    # Sub-navegação interna na Aba 2
                    modo_aba2 = st.radio(
                        "Escolha a visualização:", 
                        ["📋 Acompanhar Pedidos e Comprovantes", "📈 Relatórios Analíticos e Gráficos", "🖨️ Emitir Relatório Oficial (Imprimir)"],
                        horizontal=True,
                        key="radio_modo_aba2"
                    )
                    
                    st.markdown("---")
                    
                    # ==========================================
                    # VISÃO 1: ACOMPANHAR PEDIDOS E COMPROVANTES
                    # ==========================================
                    if modo_aba2 == "📋 Acompanhar Pedidos e Comprovantes":
                        # Garante que a coluna status existe no dataframe para exibição
                        if 'status' not in df_supabase.columns:
                            df_supabase['status'] = 'Pedido enviado'

                        pedidos_unicos = df_supabase[["numero_pedido", "data", "distrito", "ubs", "status"]].drop_duplicates().sort_values(by="data", ascending=False).reset_index(drop=True)
                        
                        lista_opcoes = ["Selecione..."] + list(pedidos_unicos["numero_pedido"].unique())
                        pedido_selecionado = st.selectbox("Escolha o número do pedido para ver o comprovante oficial:", lista_opcoes)
                        
                        if pedido_selecionado == "Selecione...":
                            st.write("**Lista de Pedidos Realizados (com Status atualizado):**")
                            st.dataframe(pedidos_unicos, use_container_width=True, hide_index=True)
                        else:
                            detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                            status_atual = detalhes['status'].iloc[0] if 'status' in detalhes.columns else "Pedido enviado"

                            # AUTOMATIZAÇÃO DE STATUS PARA A GESTÃO:
                            # Se quem abriu é a GESTÃO e o status ainda era "Pedido enviado", atualiza para "Pedido recebido"
                            if st.session_state.perfil == "GESTAO" and status_atual == "Pedido enviado":
                                try:
                                    supabase.table("pedidos").update({"status": "Pedido recebido"}).eq("numero_pedido", pedido_selecionado).execute()
                                    status_atual = "Pedido recebido"
                                except Exception as e:
                                    pass # Mantém o fluxo caso ocorra falha de rede momentânea

                            st.markdown("---")
                            obs_geral = detalhes['observacao'].iloc[0] if 'observacao' in detalhes.columns and pd.notna(detalhes['observacao'].iloc[0]) else ""

                            # COMPROVANTE OFICIAL COM BADGE DE STATUS
                            st.markdown(f"""
                            <div style="border: 2px solid #333; padding: 20px; border-radius: 8px; background-color: #ffffff;">
                                <h3 style="text-align: center; color: #222; margin: 0;">SECRETARIA MUNICIPAL DE SAÚDE</h3>
                                <h4 style="text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;">Comprovante de Requisição de Materiais - SisPAC</h4>
                                <hr style="border: 0.5px solid #ccc;">
                                <p style="margin: 5px 0;"><b>Nº do Pedido:</b> {pedido_selecionado}</p>
                                <p style="margin: 5px 0;"><b>Data/Hora do Envio:</b> {detalhes['data'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Distrito:</b> {detalhes['distrito'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Unidade (UBS):</b> {detalhes['ubs'].iloc[0]}</p>
                                <p style="margin: 5px 0;"><b>Status Atual:</b> <span style="background-color: #e67e22; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{status_atual}</span></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if obs_geral.strip():
                                st.markdown(f"""
                                <div style="margin-top: 10px; padding: 12px; border: 1px solid #d35400; background-color: #fdfaf6; border-radius: 5px;">
                                    <span style="color: #d35400; font-weight: bold;">📌 Observações Gerais do Pedido:</span><br>
                                    <span style="color: #333; font-size: 14px;">{obs_geral}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("<br>", unsafe_allow_html=True)
                            st.write("**Relação de Itens Solicitados (Separados por Categoria):**")
                            
                            categorias_presentes = detalhes["categoria"].unique()
                            for cat in categorias_presentes:
                                st.markdown(f"<p style='margin-bottom: 5px; color: #2c3e50;'><b>📂 Categoria: {cat}</b></p>", unsafe_allow_html=True)
                                df_cat = detalhes[detalhes["categoria"] == cat][["material", "quantidade"]].rename(columns={"material": "Material", "quantidade": "Qtd"})
                                st.dataframe(df_cat, use_container_width=True, hide_index=True)
                                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
                            
                            st.markdown("<br><br>", unsafe_allow_html=True)
                            st.markdown("____________________________________________________")
                            st.markdown("Assinatura do Responsável / Recebimento no Almoxarifado Central")
                            st.markdown("<br>", unsafe_allow_html=True)

                            # BOTÃO DE IMPRESSÃO QUE ATUALIZA O STATUS PARA "Em processamento"
                            if st.button("🖨️ Imprimir ou Salvar Pedido em PDF"):
                                if st.session_state.perfil == "GESTAO":
                                    try:
                                        supabase.table("pedidos").update({"status": "Em processamento"}).eq("numero_pedido", pedido_selecionado).execute()
                                    except:
                                        pass

                                st.info("💡 **Dica:** Na janela de impressão, altere o destino para **'Salvar como PDF'** se preferir o arquivo digital.")
                                st.components.v1.html("""<script>window.parent.print();</script>""", height=0)

                    # ==========================================
                    # VISÃO 2: RELATÓRIOS ANALÍTICOS COM GRÁFICOS
                    # ==========================================
                    elif modo_aba2 == "📈 Relatórios Analíticos e Gráficos":
                        st.write("### 📈 Painel Analítico e Gráficos de Consumo")
                        
                        col_r1, col_r2, col_r3 = st.columns(3)
                        with col_r1:
                            tipo_relatorio = st.selectbox("Tipo de Relatório", ["Geral (Consolidado)", "Por Categoria"], key="tr_analitico")
                        with col_r2:
                            periodo = st.selectbox("Período", ["Todo o Período", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"], key="per_analitico")
                        with col_r3:
                            if st.session_state.perfil == "GESTAO":
                                lista_ubs_filtro = ["Todas as UBS"] + list(df_supabase['ubs'].unique())
                                ubs_escolhida = st.selectbox("Filtrar Unidade", lista_ubs_filtro, key="ubs_analitico_gestao")
                            else:
                                ubs_escolhida = st.session_state.ubs_nome
                                st.text_input("Filtrar Unidade", value=ubs_escolhida, disabled=True, key="ubs_analitico_ubs")

                        df_rel = df_supabase.copy()
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
                                st.write(f"**Consolidado Geral - Unidade(s): {ubs_escolhida} ({periodo})**")
                                df_consolidado = df_rel.groupby(["categoria", "material"])["quantidade"].sum().reset_index()
                                df_consolidado.columns = ["Categoria", "Material", "Quantidade Total Solicitada"]
                                
                                st.dataframe(df_consolidado, use_container_width=True, hide_index=True)
                                
                                st.markdown("#### 📊 Gráfico de Consumo por Material")
                                df_grafico = df_consolidado.set_index("Material")["Quantidade Total Solicitada"]
                                st.bar_chart(df_grafico)
                                
                                csv = df_consolidado.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Baixar Relatório em CSV", data=csv, file_name="relatorio_geral_materiais.csv", mime="text/csv", key="dl_geral")
                                
                            else:
                                cat_disponiveis = df_rel["categoria"].unique().tolist()
                                cat_escolhida = st.selectbox("Selecione a Categoria Desejada", cat_disponiveis, key="cat_escolhida_sel")
                                
                                df_cat_filtrado = df_rel[df_rel["categoria"] == cat_escolhida]
                                df_cat_cons = df_cat_filtrado.groupby(["material"])["quantidade"].sum().reset_index()
                                df_cat_cons.columns = ["Material", "Quantidade Total Solicitada"]
                                
                                st.write(f"**Consolidado da Categoria: {cat_escolhida} | Unidade(s): {ubs_escolhida}**")
                                st.dataframe(df_cat_cons, use_container_width=True, hide_index=True)
                                
                                st.markdown(f"#### 📊 Gráfico de Consumo - {cat_escolhida}")
                                df_grafico_cat = df_cat_cons.set_index("Material")["Quantidade Total Solicitada"]
                                st.bar_chart(df_grafico_cat)
                                
                                csv = df_cat_cons.to_csv(index=False).encode('utf-8')
                                st.download_button("📥 Baixar Relatório da Categoria em CSV", data=csv, file_name=f"relatorio_categoria_{cat_escolhida}.csv", mime="text/csv", key="dl_cat")

                    # ==========================================
                    # VISÃO 3: EMITIR RELATÓRIO OFICIAL COM PARECER TÉCNICO
                    # ==========================================
                    else:
                        st.write("### 🖨️ Emissão de Relatório Oficial e Parecer Técnico")
                        
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            tipo_imp_oficial = st.selectbox("Formato do Relatório", ["Consolidado Geral", "Por Categoria"], key="tipo_imp_oficial")
                        with col_e2:
                            periodo_imp = st.selectbox("Período de Impressão", ["Todo o Período", "Última Semana (7 dias)", "Último Mês (30 dias)", "Ano Atual"], key="p_imp_oficial")
                        with col_e3:
                            if st.session_state.perfil == "GESTAO":
                                ubs_imp = st.selectbox("Unidade Referência", ["Todas as UBS"] + list(df_supabase['ubs'].unique()), key="u_imp_oficial")
                            else:
                                ubs_imp = st.session_state.ubs_nome
                                st.text_input("Unidade Referência", value=ubs_imp, disabled=True, key="u_imp_lock_oficial")

                        df_imp = df_supabase.copy()
                        if st.session_state.perfil == "GESTAO" and ubs_imp != "Todas as UBS":
                            df_imp = df_imp[df_imp['ubs'] == ubs_imp]
                            
                        agora = pd.Timestamp.now()
                        if periodo_imp == "Última Semana (7 dias)":
                            df_imp = df_imp[df_imp['data_dt'] >= (agora - pd.Timedelta(days=7))]
                        elif periodo_imp == "Último Mês (30 dias)":
                            df_imp = df_imp[df_imp['data_dt'] >= (agora - pd.Timedelta(days=30))]
                        elif periodo_imp == "Ano Atual":
                            df_imp = df_imp[df_imp['data_dt'].dt.year == agora.year]

                        # Se escolhido por categoria, exibe seletor específico
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
                                df_rel_final = df_imp.groupby(["categoria", "material"])["quantidade"].sum().reset_index()
                                df_rel_final.columns = ["Categoria", "Material", "Quantidade Total"]
                                titulo_rel_oficial = "Relatório Oficial Consolidado Geral de Insumos - SisPAC"
                            else:
                                df_rel_final = df_imp.groupby(["material"])["quantidade"].sum().reset_index()
                                df_rel_final.columns = ["Material", "Quantidade Total"]
                                titulo_rel_oficial = f"Relatório Oficial por Categoria ({cat_escolhida_imp}) - SisPAC"

                            df_rel_final = df_rel_final.sort_values(by="Quantidade Total", ascending=False).reset_index(drop=True)

                            # --- DOCUMENTO OFICIAL FORMATADO PARA IMPRESSÃO ---
                            st.markdown(f"""
                            <div style="border: 2px solid #333; padding: 25px; border-radius: 8px; background-color: #ffffff;">
                                <h3 style="text-align: center; color: #222; margin: 0;">SECRETARIA MUNICIPAL DE SAÚDE DE PELOTAS</h3>
                                <h4 style="text-align: center; color: #555; margin-top: 5px; margin-bottom: 20px;">{titulo_rel_oficial}</h4>
                                <hr style="border: 0.5px solid #ccc;">
                                <p style="margin: 5px 0;"><b>Unidade / Escopo:</b> {ubs_imp}</p>
                                <p style="margin: 5px 0;"><b>Período Abrangido:</b> {periodo_imp}</p>
                                <p style="margin: 5px 0;"><b>Data de Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.write(f"**1. Relação de Itens Solicitados:**")
                            st.dataframe(df_rel_final, use_container_width=True, hide_index=True)
                            
                            # --- GERAÇÃO AUTOMÁTICA DO PARECER TÉCNICO ADAPTADO ---
                            total_itens_diferentes = len(df_rel_final)
                            total_geral_pecas = df_rel_final["Quantidade Total"].sum()
                            material_destaque = df_rel_final.iloc[0]["Material"] if not df_rel_final.empty else "N/A"
                            qtd_destaque = df_rel_final.iloc[0]["Quantidade Total"] if not df_rel_final.empty else 0
                            
                            escopo_texto = f"categoria <b>{cat_escolhida_imp}</b>" if tipo_imp_oficial == "Por Categoria" else "escopo geral consolidado"
                            
                            parecer_tecnico = (
                                f"O presente documento consubstancia o relatório gerencial de requisição de insumos referente ao {escopo_texto} "
                                f"para a unidade <b>{ubs_imp}</b>, considerando o período de <b>{periodo_imp}</b>. "
                                f"Constatou-se a movimentação de <b>{total_geral_pecas} unidades</b> solicitadas, englobando <b>{total_itens_diferentes} itens distintos</b>. "
                                f"Evidencia-se maior proeminência no consumo do item <b>{material_destaque}</b>, com o patamar de <b>{qtd_destaque} unidades</b> requisitadas. "
                                f"O fluxo atende aos parâmetros operacionais vigentes, recomendando-se o acompanhamento contínuo dos estoques pelo Almoxarifado Central."
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
