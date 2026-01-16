import streamlit as st
import pandas as pd
import plotly.express as px
import json
import unicodedata
import re
from collections import defaultdict

st.set_page_config(
    layout="wide",
    page_title="EcoTrace Calculator",
    page_icon="🌱"
)

with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --------- Função para normalizar textos -----------
def normalizar_texto(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    texto = re.sub(r'\s+', ' ', texto)
    return texto

# --------- Inicialização de Sessão -----------
if 'df_materiais' not in st.session_state:
    try:
        df_raw = pd.read_csv("materiais_co2.csv")
        if not {"materia", "co2_por_kg"}.issubset(df_raw.columns):
            st.error("O ficheiro 'materiais_co2.csv' deve conter as colunas: 'materia' e 'co2_por_kg'")
            st.session_state.df_materiais = None
        else:
            df_raw["materia_normalizada"] = df_raw["materia"].apply(normalizar_texto)
            if "sigla" in df_raw.columns:
                df_raw["sigla_normalizada"] = df_raw["sigla"].apply(normalizar_texto)
            else:
                df_raw["sigla_normalizada"] = ""
            st.session_state.df_materiais = df_raw
            st.success("Base de dados de materiais carregada com sucesso.")
    except Exception as e:
        st.error(f"Erro ao carregar o ficheiro 'materiais_co2.csv': {e}")
        st.session_state.df_materiais = None

# Inicialização de estado de sessão
if "resetar_campos" not in st.session_state:
    st.session_state.resetar_campos = False
if "todas_pecas" not in st.session_state:
    st.session_state.todas_pecas = []

# --------- Verificação da base de dados -----------
if "df_materiais" in st.session_state and st.session_state.df_materiais is not None:
    df = st.session_state.df_materiais

    st.markdown("""
    <div class="titulo-principal">EcoTrace Calculator</div>
    <div class="subtitulo">Calculadora de Sustentabilidade no Design de Moda</div>
    <hr class="---">""", unsafe_allow_html=True)

    def processar_peca(dados_peca):
        nome_peca = dados_peca.get("nome_peca", "Peça sem nome")
        tipo_peca = dados_peca.get("tipo_peca", "Tipo não definido")
        materiais = dados_peca.get("partes") or dados_peca.get("materiais") or []

        co2_total = 0
        co2_contribuicoes = []
        erros_detectados = False

        for parte in materiais:
            nome_parte = parte.get("nome_parte") or parte.get("nome", "Parte sem nome")

            if "area" not in parte or "gramagem" not in parte or "percentagens" not in parte:
                st.warning(f"Parte '{nome_parte}' da peça '{nome_peca}' está incompleta.")
                erros_detectados = True
                continue

            area = parte["area"]
            gramagem = parte["gramagem"]
            percentagens = parte["percentagens"]

            if not isinstance(percentagens, dict):
                st.warning(f"Percentagens da parte '{nome_parte}' da peça '{nome_peca}' estão mal definidas.")
                erros_detectados = True
                continue

            if area == 0 or gramagem == 0:
                st.warning(f"Área e gramagem da parte '{nome_parte}' devem ser superiores a zero.")
                erros_detectados = True
                continue

            peso_parte_kg = area * gramagem / 1000
            soma_percentagens = sum(percentagens.values())

            if not abs(soma_percentagens - 100.0) < 0.1:
                st.error(f"❌ A parte '{nome_parte}' da peça '{nome_peca}' não têm as percentagens corretas: {soma_percentagens:.2f}% — deve ser exatamente 100%.")
                erros_detectados = True
                continue

            for materia_raw, percentagem in percentagens.items():
                materia = normalizar_texto(materia_raw)

                linha = df.loc[
                    (df["materia_normalizada"] == materia) |
                    (df["sigla_normalizada"] == materia)
                ]

                if linha.empty:
                    st.error(f"❌ Matéria '{materia_raw}' (normalizada: '{materia}') da parte '{nome_parte}' da peça '{nome_peca}' não foi encontrada no ficheiro CSV.")
                    erros_detectados = True
                    continue

                co2_por_kg = linha["co2_por_kg"].values[0]
                peso_fibra_kg = peso_parte_kg * (percentagem / 100)
                co2_fibra = peso_fibra_kg * co2_por_kg

                co2_contribuicoes.append({
                    "parte": nome_parte,
                    "fibra": materia_raw.strip(),
                    "percentagem": percentagem,
                    "area": area,
                    "gramagem": gramagem,
                    "co2_fibra": co2_fibra
                })

                co2_total += co2_fibra

        if erros_detectados:
            st.warning(f"⚠️ Erros foram detetados na peça '{nome_peca}'. O cálculo da pegada de carbono foi cancelado.")
            return nome_peca, tipo_peca, None, []

        return nome_peca, tipo_peca, co2_total, co2_contribuicoes

    def mostrar_resultados(nome_peca, tipo_peca, co2_total, co2_contribuicoes):
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
                for idx, fibra in enumerate(fibras):
                    with cols[idx]:
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

        if co2_total < 1:
            df_fibras['co2_fibra_g'] = df_fibras['co2_fibra'] * 1000
            fig_pie = px.pie(df_fibras, names="fibra", values="co2_fibra_g",
                           title=f"Distribuição do CO₂ por matéria-prima ({nome_peca})", hole=0.3)
            fig_pie.update_layout(width=600, height=600)
            fig_pie.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>%{percent}<br>(%{value:.2f} g)')
        else:
            fig_pie = px.pie(df_fibras, names="fibra", values="co2_fibra",
                           title=f"Distribuição do CO₂ por matéria-prima ({nome_peca})", hole=0.3)
            fig_pie.update_layout(width=600, height=600)
            fig_pie.update_traces(textinfo='label+percent+value', texttemplate='%{label}<br>%{percent}<br>(%{value:.3f} kg)')
        
        st.plotly_chart(fig_pie, use_container_width=True)

    # --------- Secção de Upload de Ficheiros -----------
    st.markdown('<div class="secao-upload">📂 Carregar ficheiros <strong>JSON</strong></div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Selecionar ficheiro(s)", type=["json"], accept_multiple_files=True)
    dados_importados = False
    resultados_pecas = []
    nomes_ficheiros_importados = set()
    nomes_pecas_globais = set()

    if uploaded_files:
        for uploaded_file in uploaded_files:
            nome_ficheiro = uploaded_file.name

            if nome_ficheiro in nomes_ficheiros_importados:
                st.warning(f"⚠️ O ficheiro '{nome_ficheiro}' já foi importado. Ignorado.")
                continue

            try:
                if not nome_ficheiro.endswith(".json"):
                    st.warning(f"⚠️ Formato não suportado: {nome_ficheiro}")
                    continue

                data = json.load(uploaded_file)
                pecas = data.get("pecas") or [data]

                nomes_pecas_ficheiro = set()
                pecas_validas = []

                for peca in pecas:
                    nome_peca_atual = peca.get("nome_peca", "").strip()

                    if nome_peca_atual in nomes_pecas_ficheiro:
                        st.error(f"❌ O ficheiro '{nome_ficheiro}' contém peças com o mesmo nome: '{nome_peca_atual}'. Ficheiro ignorado.")
                        break

                    if nome_peca_atual in nomes_pecas_globais:
                        st.error(f"❌ A peça '{nome_peca_atual}' já foi carregada de outro ficheiro. '{nome_ficheiro}' ignorado.")
                        break

                    nomes_pecas_ficheiro.add(nome_peca_atual)
                    nome_peca, tipo_peca, co2_total, co2_contribuicoes = processar_peca(peca)

                    if co2_contribuicoes:
                        pecas_validas.append((nome_peca, tipo_peca, co2_total, co2_contribuicoes))
                    else:
                        st.error(f"❌ Erros encontrados na peça '{nome_peca}' do ficheiro '{nome_ficheiro}'.")
                        break
                else:
                    for nome_peca, tipo_peca, co2_total, co2_contribuicoes in pecas_validas:
                        mostrar_resultados(nome_peca, tipo_peca, co2_total, co2_contribuicoes)
                        resultados_pecas.append({"nome": nome_peca, "tipo": tipo_peca, "co2": co2_total})
                        nomes_pecas_globais.add(nome_peca)
                        
                        if not any(p["nome"] == nome_peca for p in st.session_state.todas_pecas):
                            st.session_state.todas_pecas.append({
                                "nome": nome_peca,
                                "tipo": tipo_peca,
                                "co2_total": co2_total,
                                "co2_contribuicoes": co2_contribuicoes
                            })

                    nomes_ficheiros_importados.add(nome_ficheiro)
                    dados_importados = True

            except Exception as e:
                st.error(f"❌ Erro ao processar o ficheiro '{nome_ficheiro}': {e}")

    if len(resultados_pecas) >= 2:
        df_resultados = pd.DataFrame(resultados_pecas)
        st.markdown('<div class="secao-comparacao">📈 Comparação entre peças carregadas</div>', unsafe_allow_html=True)

        max_co2 = df_resultados["co2"].max()
        if max_co2 < 1:
            df_resultados["co2_display"] = df_resultados["co2"] * 1000
            unidade, label_y = "g", "CO₂ Total (g)"
        else:
            df_resultados["co2_display"] = df_resultados["co2"]
            unidade, label_y = "kg", "CO₂ Total (kg)"

        fig_barras = px.bar(df_resultados, x="nome", y="co2_display",
                          title="Comparação de Pegada de Carbono (CO₂ Total por Peça)",
                          text_auto=".2f", labels={"nome": "Peça", "co2_display": label_y})
        fig_barras.update_traces(texttemplate=f'%{{y:.2f}} {unidade}')
        st.plotly_chart(fig_barras, use_container_width=True)
    
    if dados_importados:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Adicionar Peça Manualmente", use_container_width=True):
                st.session_state.mostrar_manual = True
                st.rerun()
        with col2:
            if st.button("📊 Ver Todos os Resultados", use_container_width=True, type="primary"):
                st.switch_page("pages/resultados.py")

    # --------- Introdução manual -----------
    if (not dados_importados and not uploaded_files) or st.session_state.get("mostrar_manual", False):
        st.markdown("---")
        st.markdown('<div class="secao-manual"><h3>📝 Introdução Manual dos Dados</h3></div>', unsafe_allow_html=True)

        if st.session_state.resetar_campos:
            st.session_state.nome_peca = ""
            st.session_state.tipo_peca = ""
            st.session_state.num_partes = 1
            for i in range(10):
                st.session_state[f"parte_nome_{i}"] = ""
                st.session_state[f"materias_{i}"] = []
                st.session_state[f"area_{i}"] = 0.0
                st.session_state[f"gramagem_{i}"] = 0.0
                for materia in df["materia"].unique():
                    st.session_state[f"percentagem_{i}_{materia}"] = 0.0
            st.session_state.resetar_campos = False

        st.markdown('<div class="campo-principal">', unsafe_allow_html=True)
        nome_peca = st.text_input("🏷️ Nome da Peça", key="nome_peca").strip() or "Peça sem nome"
        tipo_peca = st.text_input("📋 Tipo da Peça", key="tipo_peca").strip() or "Tipo não definido"
        num_partes = st.number_input("🧩 Número de partes da peça", min_value=1, max_value=10, step=1, key="num_partes")
        st.markdown('</div>', unsafe_allow_html=True)

        dados_partes = {}

        st.markdown("**Nomes das partes:**")
        nomes_partes = []
        
        for i in range(0, num_partes, 2):
            cols_nomes = st.columns(2)
            for j in range(2):
                idx = i + j
                if idx < num_partes:
                    with cols_nomes[idx % 2]:
                        nome = st.text_input(f"Parte {idx+1}", key=f"parte_nome_{idx}", label_visibility="visible")
                        nomes_partes.append(nome if nome else f"Parte {idx+1}")

        st.markdown("---")

        for i in range(num_partes):
            st.markdown(f'<div class="parte-container"><div class="parte-titulo">{nomes_partes[i]}</div>', unsafe_allow_html=True)
            
            materias_selecionadas = st.multiselect(f"Matérias-primas", df["materia"].unique(), key=f"materias_{i}")
            area = st.number_input(f"Área (m²)", min_value=0.0, step=0.1, key=f"area_{i}")
            gramagem = st.number_input(f"Gramagem (g/m²)", min_value=0.0, step=0.1, key=f"gramagem_{i}")

            percentagens = {}
            soma_percentagens = 0.0

            if materias_selecionadas:
                st.markdown("**Percentagens das matérias:**")
                for materia in materias_selecionadas:
                    key_percent = f"percentagem_{i}_{materia}"
                    if key_percent not in st.session_state:
                        st.session_state[key_percent] = 0.0
                    percentagem = st.number_input(f"% de {materia}", min_value=0.0, max_value=100.0, step=0.1, key=key_percent)
                    percentagens[materia] = percentagem
                    soma_percentagens += percentagem

                if not abs(soma_percentagens - 100.0) < 0.1:
                    st.warning(f"⚠️ A soma deve ser 100% (atual: {soma_percentagens:.1f}%)")

            st.markdown('</div>', unsafe_allow_html=True)
            
            dados_partes[nomes_partes[i]] = {
                "materias": materias_selecionadas,
                "percentagens": percentagens,
                "area": area,
                "gramagem": gramagem
            }

        if st.button("Calcular CO₂", key="btn_calcular_manual"):
            if not dados_partes:
                st.warning("Nenhuma parte válida foi introduzida. Verifique os dados e tente novamente.")
            else:
                peca_manual = {
                    "nome_peca": nome_peca,
                    "tipo_peca": tipo_peca,
                    "materiais": [
                        {"nome_parte": parte, "area": dados["area"], "gramagem": dados["gramagem"], "percentagens": dados["percentagens"]}
                        for parte, dados in dados_partes.items()
                    ]
                }

                nome_peca_resultado, tipo_peca_resultado, co2_total, co2_contribuicoes = processar_peca(peca_manual)

                if co2_contribuicoes:
                    if not any(p["nome"] == nome_peca_resultado for p in st.session_state.todas_pecas):
                        st.session_state.todas_pecas.append({
                            "nome": nome_peca_resultado,
                            "tipo": tipo_peca_resultado,
                            "co2_total": co2_total,
                            "co2_contribuicoes": co2_contribuicoes
                        })
                    st.session_state.resetar_campos = True
                    st.switch_page("pages/resultados.py")
                else:
                    st.warning("Não foi possível calcular a pegada de carbono com os dados introduzidos.")