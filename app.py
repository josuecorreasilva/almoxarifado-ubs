import streamlit as st
import pandas as pd
import time
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
# POR QUE: Define como a página vai aparecer na aba do navegador e usa a tela toda (layout wide)
st.set_page_config(page_title="SisPAC - Sistema de Pedidos e Almoxarifado Central",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CSS PARA IMPRESSÃO LIMPA ---
st.markdown("""
<style>
@media print {
    /* Oculta a barra lateral, cabeçalhos, botões e menus de escolha na hora de imprimir/salvar PDF */
    [data-testid="stSidebar"], header, button, .stRadio, .stSelectbox {
        display: none !important;
    }
    .block-container {
        padding-top: 0rem !important;
    }
}
</style>
""", unsafe_allow_html=True)
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

# --- ABA 1: FORMULÁRIO (Visão da UBS com Indicador de Estoque) ---
with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    
    col_distrito, col_ubs = st.columns(2)
    
    if st.session_state.perfil == "GESTAO":
        with col_distrito:
            distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
        with col_ubs:
            ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
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
    
    try:
        df_materiais = pd.read_csv(url_google_sheets_materiais)
        df_materiais.columns = df_materiais.columns.str.strip()
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
        
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        material = st.selectbox("2. Selecione o Material", lista_de_itens)
        
   # Consulta o saldo atual no estoque central baseado na planilha do Google Sheets
    estoque_disponivel_total = 0
    if not df_materiais.empty and "Material" in df_materiais.columns and "Estoque" in df_materiais.columns:
        # Filtra a linha correspondente ao material selecionado
        item_row = df_materiais[df_materiais["Material"] == material]
        if not item_row.empty:
            # Pega o valor da coluna 'Estoque' e converte para número de forma segura
            val_estoque = item_row["Estoque"].values[0]
            try:
                estoque_disponivel_total = int(float(str(val_estoque).replace(',', '.')))
            except:
                estoque_disponivel_total = 0

    # Indicador visual de disponibilidade para a UBS
    with col2:
        if estoque_disponivel_total > 50:
            st.markdown(f"**Estoque:** <span style='color: green;'>🟢 Disponível ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
        elif estoque_disponivel_total > 0:
            st.markdown(f"**Estoque:** <span style='color: orange;'>🟡 Baixo ({estoque_disponivel_total} un.)</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"**Estoque:** <span style='color: red;'>🔴 Ruptura / Zero</span>", unsafe_allow_html=True)

    with col2: # Ajuste de espaçamento visual
        pass

    with col3:
        quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
        
    # Puxa o valor unitário da planilha silenciosamente em segundo plano
    valor_unitario_atual = 0.0
    if not df_materiais.empty and material:
        item_row = df_materiais[df_materiais["Material"] == material]
        col_preco = next((c for c in ["Valor Unitario", "Valor Unitário", "Preço", "Preco"] if c in df_materiais.columns), None)
        if col_preco and not item_row.empty:
            val_raw = item_row[col_preco].values[0]
            
            try:
        if isinstance(val_raw, str):
            # Remove R$, espaços e ajusta o formato brasileiro (vírgula para ponto)
            val_limpo = val_raw.replace("R$", "").strip().replace(".", "").replace(",", ".")
            valor_unitario_atual = float(val_limpo)
        else:
            valor_unitario_atual = float(val_raw)
    except:
        valor_unitario_atual = 0.0
        
    if st.button("➕ Adicionar Item ao Pedido", key="btn_adicionar_item"):
        subtotal = quantidade * valor_unitario_atual
        st.session_state.carrinho.append({
            "distrito": distrito_selecionado, 
            "ubs": ubs_selecionada,
            "categoria": categoria_selecionada,
            "material": material,
            "quantidade": quantidade,
            "valor_unitario": valor_unitario_atual,
            "subtotal": subtotal
        })
        st.success(f"Adicionado: {quantidade}x {material}")

    # --- RESUMO DO CARRINHO (Sem exibição de preços para a UBS) ---
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
                    st.success(f"✅ Pedido {numero_pedido} enviado com sucesso!")
                    st.session_state.carrinho = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro retornado pelo Banco de Dados: {e}")

# --- ABA 2: PAINEL GERENCIAL E RELATÓRIOS OFICIAIS ---
with aba2:
    st.subheader("📊 Painel de Controle, Conferência e Relatórios")
    
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
                    
                    if modo_aba2 == "📋 Acompanhar Pedidos, Conferência e Comprovantes":
                        if 'status' not in df_supabase.columns:
                            df_supabase['status'] = 'Pedido enviado'

                        pedidos_unicos = df_supabase[["numero_pedido", "data", "distrito", "ubs", "status"]].drop_duplicates().sort_values(by="data", ascending=False).reset_index(drop=True)
                        
                        lista_opcoes = ["Selecione..."] + list(pedidos_unicos["numero_pedido"].unique())
                        pedido_selecionado = st.selectbox("Escolha o número do pedido para ver ou conferir o comprovante:", lista_opcoes)
                        
                        if pedido_selecionado == "Selecione...":
                            st.write("**Lista de Pedidos Realizados (com Status atualizado):**")
                            st.dataframe(pedidos_unicos, use_container_width=True, hide_index=True)
                        else:
                            detalhes = df_supabase[df_supabase["numero_pedido"] == pedido_selecionado]
                            status_atual = detalhes['status'].iloc[0] if 'status' in detalhes.columns else "Pedido enviado"

                            # Tela de Conferência exclusiva para a Gestão
                            if st.session_state.perfil == "GESTAO":
                                st.markdown("### 📦 Painel de Conferência do Almoxarifado (Itens Entregues)")
                                st.info("Insira abaixo a quantidade que foi **efetivamente entregue/despachada** para a UBS. O custo financeiro e o centro de custos serão calculados estritamente sobre o entregue.")
                                
                                with st.form(key=f"form_conferencia_{pedido_selecionado}"):
                                    novas_quantidades_entregues = {}
                                    
                                    for idx, row in detalhes.iterrows():
                                        mat = row['material']
                                        qtd_pedida = int(row['quantidade'])
                                        qtd_atual_entregue = int(row['quantidade_entregue']) if pd.notna(row['quantidade_entregue']) else 0
                                        if qtd_atual_entregue == 0 and status_atual == "Pedido enviado":
                                            qtd_atual_entregue = qtd_pedida # Sugere o total pedido por padrão na primeira conferência
                                            
                                        c_mat, c_ped, c_ent = st.columns([3, 1, 1])
                                        c_mat.write(f"**{mat}** (Cat: {row['categoria']})")
                                        c_ped.write(f"Solicitado: {qtd_pedida}")
                                        
                                        val_entregue = c_ent.number_input(
                                            f"Entregue ({mat})", 
                                            min_value=0, 
                                            max_value=100000, 
                                            value=qtd_atual_entregue,
                                            key=f"ent_{row['id'] if 'id' in row else idx}"
                                        )
                                        novas_quantidades_entregues[row['id'] if 'id' in row else idx] = val_entregue

                                    obs_gestao = st.text_input("Observação da Gestão / Almoxarifado (Opcional)", value="", key=f"obs_g_{pedido_selecionado}")
                                    
                                    btn_salvar_conf = st.form_submit_button("💾 Salvar Conferência e Atualizar Entregas")
                                    if btn_salvar_conf:
                                        try:
                                            for row_id, nova_qtd in novas_quantidades_entregues.items():
                                                # Recalcula o custo total com base na quantidade entregue
                                                row_original = detalhes[detalhes['id'] == row_id].iloc[0] if 'id' in detalhes.columns else detalhes.iloc[list(novas_quantidades_entregues.keys()).index(row_id)]
                                                v_unit = float(row_original['valor_unitario'])
                                                novo_custo_total = nova_qtd * v_unit
                                                
                                                supabase.table("pedidos").update({
                                                    "quantidade_entregue": nova_qtd,
                                                    "custo_total": novo_custo_total,
                                                    "status": "Atendido Parcialmente" if nova_qtd < int(row_original['quantidade']) else "Atendido Integralmente"
                                                }).eq("id", row_id).execute()
                                            
                                            st.success("✅ Conferência de entrega salva com sucesso! O centro de custos foi atualizado.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao salvar conferência no Supabase: {e}")
                                
                                st.markdown("---")

                            # Atualiza os detalhes locais após possível alteração
                            response_atu = supabase.table("pedidos").select("*").eq("numero_pedido", pedido_selecionado).execute()
                            detalhes = pd.DataFrame(response_atu.data)
                            status_atual = detalhes['status'].iloc[0] if 'status' in detalhes.columns else status_atual

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

                            if st.button("🖨️ Imprimir ou Salvar Comprovante em PDF"):
                                st.info("💡 **Dica:** Na janela de impressão, altere o destino para **'Salvar como PDF'** se preferir o arquivo digital.")
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
