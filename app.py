import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Almoxarifado Saúde", layout="wide")

# Lista real de distritos e unidades
distritos_ubs = {
    "Centro/Porto": ["Balsa", "Porto", "Cruzeiro", "Navegantes - UBAI", "Fátima", "Osório", "Sansca"],
    "Areal": ["Areal I", "Areal Leste", "CSU", "Obelisco", "Leocadia", "Bom Jesus", "Dunas"],
    "Praias": ["Laranjal", "Barro Duro", "Z3"],
    "Três Vendas I": ["Santa Terezinha", "Py Crespo", "Lindóia", "Sítio Floresta", "Vila Princesa", "União de Bairros", "Jardim de Allah"]
}

ARQUIVO_DADOS = 'pedidos_demo.csv'

# Função para criar o arquivo se não existir
if not os.path.exists(ARQUIVO_DADOS):
    df_vazio = pd.DataFrame(columns=["Data", "Distrito", "UBS", "Material", "Quantidade"])
    df_vazio.to_csv(ARQUIVO_DADOS, index=False)

st.title("📦 Sistema de Pedidos - Almoxarifado Central")

aba1, aba2 = st.tabs(["Fazer Novo Pedido", "Painel Gerencial (Relatórios)"])

with aba1:
    st.subheader("Formulário da Unidade Básica de Saúde")
    distrito_selecionado = st.selectbox("Selecione o Distrito", list(distritos_ubs.keys()))
    ubs_selecionada = st.selectbox("Selecione a Unidade", distritos_ubs[distrito_selecionado])
    
    col1, col2 = st.columns(2)
    # Link da planilha do Google
    url_google_sheets = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR9dB5LFv3DRH9HRGwdmINwp2F0nE4V84gvV2L1EDPL4ETicGscJm-wGS1vMRacWjatmtmu2z29fppw/pub?output=csv"
    df_materiais = pd.read_csv(url_google_sheets)
    lista_de_itens = df_materiais["Material"].tolist()

    # Cria a memória temporária (carrinho) do sistema
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    with col1:
        material = st.selectbox("Material de Enfermagem", lista_de_itens)
    with col2:
        quantidade = st.number_input("Quantidade Necessária", min_value=1, value=10)
        
    # Botão 1: Apenas guarda o item na memória temporária
    if st.button("➕ Adicionar Item à Lista"):
        st.session_state.carrinho.append({
            "Data": date.today(),
            "Distrito": distrito_selecionado,
            "UBS": ubs_selecionada,
            "Material": material,
            "Quantidade": quantidade
        })
        st.success(f"Adicionado: {quantidade}x {material}")
        
    # Se a lista tiver itens, mostra a tabela de resumo e o botão de envio final
    if len(st.session_state.carrinho) > 0:
        st.markdown("---")
        st.write("**🛒 Resumo do Pedido Atual:**")
        
        # Gera uma tabela virtual apenas com os itens selecionados agora
        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df_carrinho, use_container_width=True)
        
        # Botão 2: Grava toda a lista de uma vez no banco de dados geral
        if st.button("✅ Enviar Pedido Completo ao Almoxarifado"):
            df_carrinho.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
            st.session_state.carrinho = [] # Esvazia o carrinho para a próxima UBS
            st.success("Pedido enviado com sucesso! Acesse a aba de Relatórios.")
with aba2:
    st.subheader("Relatório de Consumo em Tempo Real")
    df_dados = pd.read_csv(ARQUIVO_DADOS)
    if not df_dados.empty:
        st.dataframe(df_dados, use_container_width=True)
        st.write("Total de Materiais Solicitados por Distrito:")
        grafico_dados = df_dados.groupby("Distrito")["Quantidade"].sum()
        st.bar_chart(grafico_dados)
    else:
        st.info("Nenhum pedido registrado ainda. Faça um pedido na aba ao lado.")
