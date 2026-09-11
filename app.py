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
    with col1:
        material = st.selectbox("Material de Enfermagem", ["Álcool 70%", "Seringa 5ml", "Gaze", "Luva M", "Soro Fisiológico"])
    with col2:
        quantidade = st.number_input("Quantidade Necessária", min_value=1, value=10)
    
    if st.button("Registrar Pedido no Sistema"):
        novo_dado = pd.DataFrame([[date.today(), distrito_selecionado, ubs_selecionada, material, quantidade]], 
                                 columns=["Data", "Distrito", "UBS", "Material", "Quantidade"])
        novo_dado.to_csv(ARQUIVO_DADOS, mode='a', header=False, index=False)
        st.success("Pedido registrado! Acesse o Painel Gerencial para ver a atualização.")

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