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

# Criamos um novo arquivo CSV para suportar a nova coluna "Nº do Pedido" sem dar erro no banco antigo
ARQUIVO_DADOS = 'pedidos_oficiais_v2.csv'

if not os.path.exists(ARQUIVO_DADOS):
    df_vazio = pd.DataFrame(columns=["Nº do Pedido", "Data", "Distrito", "UBS", "Material", "Quantidade"])
    df_vazio.to_csv(ARQUIVO_DADOS, index=False)

st.title("📦 Sistema de Pedidos - Almoxarifado Central")

aba1, aba2 = st.tabs(["Fazer Novo Pedido", "Painel Gerencial (Relatórios)"])

with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
    ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
    
    col1, col2 = st.columns(2)
    
    # ATENÇÃO: COLE O SEU LINK DO GOOGLE SHEETS AQUI DENTRO DAS ASPAS
    url_google_sheets = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pub?output=csv"
    
    try:
        df_materiais = pd.read_csv(url_google_sheets)
        lista_de_itens = df_materiais["Material"].tolist()
    except:
        lista_de_itens = ["Erro ao carregar planilha. Verifique o link."]
        
    # Sistema de memória (Carrinho)
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    with col1:
        material = st.selectbox("Material de Enfermagem", lista_de_itens)
    with col2:
        quantidade = st.number_input("Quantidade Necessária", min_value=1, value=10)
        
    if st.button("➕ Adicionar Item à Lista"):
        st.session_state.carrinho.append({
            "Distrito": distrito_selecionado,
            "UBS": ubs_selecionada,
            "Material": material,
            "Quantidade": quantidade
        })
        st.success(f"Adicionado: {quantidade}x {material}")
        
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        st.write("**🛒 Resumo do Pedido Atual:**")
        
        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df_carrinho, use_container_width=True)
        
        if st.button("✅ Enviar Pedido Completo ao Almoxarifado"):
            # Gera um código único para o pedido
            numero_pedido = f"PED-{int(time.time())}"
            
            # Formata os dados para salvar no banco
            dados_finais = df_carrinho.copy()
            dados_finais.insert(0, "Data", date.today())
            dados_finais.insert(0, "Nº do Pedido", numero_pedido)
            
            dados_finais.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
            st.session_state.carrinho = [] # Limpa a tela para a próxima unidade
            st.success(f"Pedido {numero_pedido} enviado com sucesso! Acesse o Painel Gerencial.")

with aba2:
    st.subheader("Controle Central de Solicitações")
    df_dados = pd.read_csv(ARQUIVO_DADOS)
    
    if not df_dados.empty:
        # Agrupa os itens para gerar a tabela de resumo de pedidos
        resumo_pedidos = df_dados.groupby(["Nº do Pedido", "Data", "Distrito", "UBS"]).size().reset_index(name="Total de Itens Diferentes")
        
        st.write("**📋 Lista de Pedidos Realizados (Visão Geral):**")
        st.dataframe(resumo_pedidos, use_container_width=True)
        
        st.markdown("---")
        st.write("**🔍 Detalhar um Pedido Específico:**")
        
        # Cria a caixa para selecionar e expandir um pedido
        lista_pedidos = resumo_pedidos["Nº do Pedido"].tolist()
        pedido_selecionado = st.selectbox("Selecione o Nº do Pedido para conferir a lista de materiais:", ["Selecione..."] + lista_pedidos)
        
        if pedido_selecionado != "Selecione...":
            detalhes = df_dados[df_dados["Nº do Pedido"] == pedido_selecionado]
            st.write(f"Materiais solicitados no pedido **{pedido_selecionado}**:")
            st.dataframe(detalhes[["Material", "Quantidade"]], use_container_width=True)
            
        st.markdown("---")
        st.write("**📊 Total de Materiais Solicitados por Distrito:**")
        grafico_dados = df_dados.groupby("Distrito")["Quantidade"].sum()
        st.bar_chart(grafico_dados)
    else:
        st.info("Nenhum pedido registrado ainda.")
