import streamlit as st
import pandas as pd
from datetime import date
import os
import time

st.set_page_config(page_title="Almoxarifado Saúde", layout="wide")

# Lista completa de distritos e unidades de Pelotas
distritos_ubs = {
    "Centro/Porto": ["Balsa", "Porto", "Cruzeiro", "Navegantes - UBAI", "Fátima", "Osório", "Sansca"],
    "Areal": ["Areal I", "Areal Leste", "CSU", "Obelisco", "Leocadia", "Bom Jesus", "Dunas"],
    "Praias": ["Laranjal", "Barro Duro", "Z3"],
    "Três Vendas I": ["Santa Terezinha", "Py Crespo", "Lindóia", "Sítio Floresta", "Vila Princesa", "União de Bairros", "Jardim de Allah"],
    "Três Vendas II": ["Cohab Pestano", "CAIC Pestano", "Getúlio Vargas", "Sanga Funda", "Arco-íris", "Vila Municipal", "Salgado Filho", "Saúde Prisional"],
    "Fragata I": ["Simões Lopes", "Dom Pedro", "Fraget", "Guabiroba"],
    "Fragata II": ["Fragata", "Cohab Fragata", "Virgílio Costa"],
    "Colônia": ["Cascata", "Maciel", "Triunfo", "Grupelli", "Monte Bonito", "Cordeiro de Farias", "Pedreiras", "Vila Nova", "Cerrito Alegre", "Colônia Osório", "Corrientes", "Santa Silvana", "Posto Branco"]
}

ARQUIVO_DADOS = 'pedidos_oficiais_v2.csv'

# Atualizamos o banco vazio para incluir a coluna Categoria, caso o arquivo ainda não exista
if not os.path.exists(ARQUIVO_DADOS):
    df_vazio = pd.DataFrame(columns=["Nº do Pedido", "Data", "Distrito", "UBS", "Categoria", "Material", "Quantidade"])
    df_vazio.to_csv(ARQUIVO_DADOS, index=False)

st.title("📦 Sistema de Pedidos - Almoxarifado Central")

aba1, aba2, aba3 = st.tabs(["Fazer Novo Pedido", "Painel Gerencial (Resumo)", "Filtros e Relatórios Avançados"])

with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    
    # Organizando o layout dos distritos e unidades
    col_distrito, col_ubs = st.columns(2)
    with col_distrito:
        distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
    with col_ubs:
        ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
        
    st.markdown("---")
    
    # ATENÇÃO: COLE O SEU LINK DO GOOGLE SHEETS AQUI DENTRO DAS ASPAS
    url_google_sheets = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pubhtml"
    
    try:
        df_materiais = pd.read_csv(url_google_sheets)
        # O sistema lê a nova coluna Categoria e remove valores vazios
        lista_categorias = df_materiais["Categoria"].dropna().unique().tolist()
    except:
        lista_categorias = ["Erro ao carregar planilha"]
        df_materiais = pd.DataFrame()
        
    # 1. Filtro principal: O usuário escolhe a Categoria primeiro
    categoria_selecionada = st.selectbox("1. Selecione a Categoria", lista_categorias)
    
    # A lista de materiais é filtrada instantaneamente com base na categoria escolhida
    if not df_materiais.empty and "Categoria" in df_materiais.columns:
         df_filtrado = df_materiais[df_materiais["Categoria"] == categoria_selecionada]
         lista_de_itens = df_filtrado["Material"].dropna().tolist()
    else:
         lista_de_itens = ["Erro na leitura"]
         
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    # 2 e 3. Escolha do Item e Quantidade
    col1, col2 = st.columns(2)
    with col1:
        material = st.selectbox("2. Selecione o Material", lista_de_itens)
    with col2:
        quantidade = st.number_input("3. Quantidade Necessária", min_value=1, value=10)
        
    if st.button("➕ Adicionar Item à Lista"):
        st.session_state.carrinho.append({
            "Distrito": distrito_selecionado,
            "UBS": ubs_selecionada,
            "Categoria": categoria_selecionada, # Registra a categoria no pedido
            "Material": material,
            "Quantidade": quantidade
        })
        st.success(f"Adicionado: {quantidade}x {material} ({categoria_selecionada})")
        
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        st.write("**🛒 Resumo do Pedido Atual:**")
        
        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df_carrinho, use_container_width=True)
        
        if st.button("✅ Enviar Pedido Completo ao Almoxarifado"):
            numero_pedido = f"PED-{int(time.time())}"
            dados_finais = df_carrinho.copy()
            dados_finais.insert(0, "Data", date.today())
            dados_finais.insert(0, "Nº do Pedido", numero_pedido)
            
            dados_finais.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
            st.session_state.carrinho = []
            st.success(f"Pedido {numero_pedido} enviado com sucesso! Acesse o Painel Gerencial.")

with aba2:
    st.subheader("Controle Central de Solicitações")
    df_dados = pd.read_csv(ARQUIVO_DADOS)
    
    if not df_dados.empty:
        resumo_pedidos = df_dados.groupby(["Nº do Pedido", "Data", "Distrito", "UBS"]).size().reset_index(name="Total de Itens Diferentes")
        
        st.write("**📋 Lista de Pedidos Realizados (Visão Geral):**")
        st.dataframe(resumo_pedidos, use_container_width=True)
        
        st.markdown("---")
        st.write("**🔍 Detalhar um Pedido Específico:**")
        
        lista_pedidos = resumo_pedidos["Nº do Pedido"].tolist()
        pedido_selecionado = st.selectbox("Selecione o Nº do Pedido para conferir a lista de materiais:", ["Selecione..."] + lista_pedidos)
        
        if pedido_selecionado != "Selecione...":
            detalhes = df_dados[df_dados["Nº do Pedido"] == pedido_selecionado]
            st.write(f"Materiais solicitados no pedido **{pedido_selecionado}**:")
            # Exibe a categoria também na visão detalhada
            colunas_exibicao = [col for col in ["Categoria", "Material", "Quantidade"] if col in detalhes.columns]
            st.dataframe(detalhes[colunas_exibicao], use_container_width=True)
            
        st.markdown("---")
        st.write("**📊 Total de Materiais Solicitados por Distrito:**")
        grafico_dados = df_dados.groupby("Distrito")["Quantidade"].sum()
        st.bar_chart(grafico_dados)
    else:
        st.info("Nenhum pedido registrado ainda.")

with aba3:
    st.subheader("Filtros Avançados e Geração de Relatórios")
    df_dados = pd.read_csv(ARQUIVO_DADOS)
    
    if not df_dados.empty:
        # Adicionado um 5º filtro para as categorias
        filtro1, filtro2, filtro3, filtro4, filtro5 = st.columns(5)
        
        with filtro1:
            distritos_unicos = df_dados["Distrito"].unique().tolist()
            filtro_distrito = st.multiselect("Distrito", distritos_unicos)
        with filtro2:
            ubs_unicas = df_dados["UBS"].unique().tolist()
            filtro_ubs = st.multiselect("UBS", ubs_unicas)
        with filtro3:
            # Previne erros caso a base de relatórios antiga não tenha a coluna categoria
            if "Categoria" in df_dados.columns:
                categorias_unicas = df_dados["Categoria"].dropna().unique().tolist()
            else:
                categorias_unicas = []
            filtro_categoria = st.multiselect("Categoria", categorias_unicas)
        with filtro4:
            materiais_unicos = df_dados["Material"].unique().tolist()
            filtro_material = st.multiselect("Material", materiais_unicos)
        with filtro5:
            datas_unicas = df_dados["Data"].unique().tolist()
            filtro_data = st.multiselect("Data", datas_unicas)
            
        df_filtrado = df_dados.copy()
        
        if filtro_distrito:
            df_filtrado = df_filtrado[df_filtrado["Distrito"].isin(filtro_distrito)]
        if filtro_ubs:
            df_filtrado = df_filtrado[df_filtrado["UBS"].isin(filtro_ubs)]
        if filtro_categoria and "Categoria" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(filtro_categoria)]
        if filtro_material:
            df_filtrado = df_filtrado[df_filtrado["Material"].isin(filtro_material)]
        if filtro_data:
            df_filtrado = df_filtrado[df_filtrado["Data"].isin(filtro_data)]
            
        st.markdown("---")
        st.write(f"**Resultado:** {len(df_filtrado)} registros encontrados.")
        st.dataframe(df_filtrado, use_container_width=True)
        
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Relatório",
            data=csv,
            file_name='relatorio_pedidos_almoxarifado.csv',
            mime='text/csv',
        )
    else:
        st.info("O banco de dados ainda está vazio. Os relatórios aparecerão após o primeiro pedido.")
