import streamlit as st
import pandas as pd
import plotly.express as px
from collections import defaultdict

st.set_page_config(
    layout="wide",
    page_title="Resultados - EcoTrace",
    page_icon="📊"
)

with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.markdown("""
<div class="titulo-principal">Resultados</div>
<div class="subtitulo">Pegada de Carbono das Peças Calculadas</div>
<hr class="---">""", unsafe_allow_html=True)

def mostrar_resultados(nome_peca, tipo_peca, co2_total, co2_contribuicoes, idx=0):
    # Formatar CO2 total em kg ou g
    if co2_total < 1:
        co2_display = f"{co2_total * 1000:.2f} g CO₂"
    else:
        co2_display = f"{co2_total:.3f} kg CO₂"
    
    st.success(f"CO₂ total da peça {nome_peca} ({tipo_peca}): {co2_display}")

    partes_dict = defaultdict(list)
    for contrib in co2_contribuicoes:
        partes_dict[contrib["parte"]].append(contrib)

    with st.expander(f"Ver detalhes por parte - {nome_peca}"):
        for parte, fibras in partes_dict.items():
            st.markdown(f"---\n#### Parte: **{parte}**")
            cols = st.columns(len(fibras))
            for idx_fibra, fibra in enumerate(fibras):
                with cols[idx_fibra]:
                    # Formatar CO2 da fibra
                    co2_fibra = fibra['co2_fibra']
                    if co2_fibra < 1:
                        co2_fibra_display = f"{co2_fibra * 1000:.2f} g"
                    else:
                        co2_fibra_display = f"{co2_fibra:.3f} kg"
                    
                    st.markdown(f"**Fibra:** {fibra['fibra']}")
                    st.markdown(f"**Percentagem:** {fibra['percentagem']}%")
                    st.markdown(f"**Área:** {fibra['area']} m²")
                    st.markdown(f"**Gramagem:** {fibra['gramagem']} g/m²")
                    st.markdown(f"**CO₂:** {co2_fibra_display}")

    df_grafico = pd.DataFrame(co2_contribuicoes)
    df_fibras = df_grafico.groupby("fibra")["co2_fibra"].sum().reset_index()

    fig_pie = px.pie(
        df_fibras,
        names="fibra",
        values="co2_fibra",
        title=f"Distribuição do CO₂ por matéria-prima ({nome_peca})",
        hole=0.3
    )
    fig_pie.update_layout(width=600, height=600)
    
    # Formatar valores no gráfico
    if co2_total < 1:
        df_fibras['co2_fibra_g'] = df_fibras['co2_fibra'] * 1000
        fig_pie = px.pie(
            df_fibras,
            names="fibra",
            values="co2_fibra_g",
            title=f"Distribuição do CO₂ por matéria-prima ({nome_peca})",
            hole=0.3
        )
        fig_pie.update_layout(width=600, height=600)
        fig_pie.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>%{percent}<br>(%{value:.2f} g)')
    else:
        fig_pie.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>%{percent}<br>(%{value:.3f} kg)')
    
    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{idx}_{nome_peca}")

# Verificar se há peças calculadas
if "todas_pecas" not in st.session_state or not st.session_state.todas_pecas:
    st.warning("⚠️ Nenhuma peça foi calculada ainda. Volte à página principal para introduzir dados.")
    if st.button("← Voltar à página principal"):
        st.switch_page("app.py")
else:
    st.markdown('<div class="secao-comparacao">📊 Resultados das Peças Calculadas</div>', unsafe_allow_html=True)
    
    for idx, peca in enumerate(st.session_state.todas_pecas):
        st.markdown(f"### 🧵 {peca['nome']} ({peca['tipo']})")
        mostrar_resultados(
            peca["nome"],
            peca["tipo"],
            peca["co2_total"],
            peca["co2_contribuicoes"],
            idx
        )

    # Gráfico de comparação
    if len(st.session_state.todas_pecas) >= 2:
        df_comp = pd.DataFrame([
            {"nome": p["nome"], "co2_total": p["co2_total"]}
            for p in st.session_state.todas_pecas
        ])
        
        # Determinar se usa kg ou g
        max_co2 = df_comp["co2_total"].max()
        if max_co2 < 1:
            df_comp["co2_display"] = df_comp["co2_total"] * 1000
            unidade = "g"
            label_y = "CO₂ Total (g)"
        else:
            df_comp["co2_display"] = df_comp["co2_total"]
            unidade = "kg"
            label_y = "CO₂ Total (kg)"
        
        fig_comp = px.bar(
            df_comp,
            x="nome",
            y="co2_display",
            title="Comparação da Pegada de Carbono entre Peças",
            labels={"nome": "Peça", "co2_display": label_y},
            text_auto=".2f"
        )
        fig_comp.update_traces(texttemplate=f'%{{y:.2f}} {unidade}')
        st.plotly_chart(fig_comp, use_container_width=True)
    
    # Botões
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Voltar e adicionar nova peça"):
            st.switch_page("Calculadora.py")
    with col2:
        if st.button("🗑️ Limpar todos os resultados"):
            st.session_state.todas_pecas = []
            st.rerun()