import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
from datetime import datetime

st.set_page_config(page_title="Painel de Pressão e Abastecimento", layout="wide")

DATA_PAINEL = datetime.now().strftime("%d/%m/%Y")
DATA_ARQUIVO = datetime.now().strftime("%Y-%m-%d")

# Estado da sessão para armazenamento temporário/memória
if "pontos" not in st.session_state:
    st.session_state.pontos = {}

def normalizar_texto(valor):
    if not valor:
        return ""
    return re.sub(r"\s+", " ", str(valor).strip()).upper()

def processar_pressao_e_cor(valor_input, tipo_ocorrencia="baixa_pressao"):
    if tipo_ocorrencia == "sem_abastecimento":
        return "SEM ABASTECIMENTO", "red"

    texto = str(valor_input).strip()
    texto_upper = normalizar_texto(texto)

    if "SEM" in texto_upper or "ABASTECIMENTO" in texto_upper:
        return "SEM ABASTECIMENTO", "red"

    texto_limpo = texto.replace(",", ".")
    texto_limpo = re.sub(r"[^0-9.\-]", "", texto_limpo)

    if not texto_limpo:
        raise ValueError("Informe a pressão para registrar 'Baixa Pressão'.")

    try:
        numero = float(texto_limpo)
    except ValueError:
        raise ValueError("Pressão inválida. Digite um valor numérico.")

    if numero < 0:
        raise ValueError("A pressão não pode ser negativa.")

    if numero == 0:
        return "SEM ABASTECIMENTO", "red"
    elif numero < 5.0:
        formatado = str(int(numero)) if numero.is_integer() else f"{numero:.2f}".rstrip("0").rstrip(".")
        return f"{formatado} mca", "orange"
    elif numero == 5.0:
        return "5 mca", "yellow"
    else:
        formatado = str(int(numero)) if numero.is_integer() else f"{numero:.2f}".rstrip("0").rstrip(".")
        return f"{formatado} mca", "blue"

def converter_coordenadas(texto):
    if not texto:
        raise ValueError("Informe as coordenadas.")
    partes = [p.strip() for p in str(texto).split(",")]
    if len(partes) != 2:
        raise ValueError("Formato inválido. Use: -5.09909, -42.90982")
    try:
        lat = float(partes[0].replace(",", "."))
        lng = float(partes[1].replace(",", "."))
    except ValueError:
        raise ValueError("Coordenadas devem ser numéricas.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Latitude ou Longitude fora dos limites.")
    return lat, lng

# TÍTULO
st.title("📍 PAINEL DIÁRIO DE PRESSÃO E ABASTECIMENTO")
st.write(f"**Data:** {DATA_PAINEL}")

# FORMULÁRIO DE CADASTRO
with st.sidebar:
    st.header("➕ Registrar Ocorrência")
    os_num = st.text_input("Nº da O.S.", placeholder="Ex.: 123456")
    pressao_in = st.text_input("Pressão (mca)", placeholder="Ex.: 5 ou 4,2")
    bairro_in = st.text_input("Bairro", placeholder="Ex.: Centro")
    coord_in = st.text_input("Coordenadas", placeholder="Ex.: -5.09909, -42.90982")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        btn_pressao = st.button("🟡/🟠/🔵 Registrar Pressão", type="primary")
    with col_btn2:
        btn_sem_abast = st.button("🔴 Sem Abastecimento")

    if btn_pressao or btn_sem_abast:
        tipo = "sem_abastecimento" if btn_sem_abast else "baixa_pressao"
        try:
            if not os_num.strip():
                st.error("Informe o Nº da O.S.")
            elif not bairro_in.strip():
                st.error("Informe o Bairro.")
            else:
                lat, lng = converter_coordenadas(coord_in)
                pressao_txt, cor = processar_pressao_e_cor(pressao_in, tipo)
                chave = normalizar_texto(bairro_in)

                st.session_state.pontos[chave] = {
                    "Nº da O.S.": os_num.strip(),
                    "Pressão": pressao_txt,
                    "Cor": cor,
                    "Bairro": bairro_in.strip(),
                    "Coordenadas": f"{lat:.6f}, {lng:.6f}",
                    "Latitude": lat,
                    "Longitude": lng,
                    "Data": DATA_PAINEL
                }
                st.success(f"Ocorrência registrada para {bairro_in}!")
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")
    st.header("🗑️ Remover Registro")
    bairro_rem = st.text_input("Bairro a remover")
    if st.button("Remover"):
        chave_rem = normalizar_texto(bairro_rem)
        if chave_rem in st.session_state.pontos:
            st.session_state.pontos.pop(chave_rem)
            st.success(f"Registro de {bairro_rem} removido.")
        else:
            st.warning("Bairro não encontrado.")

# EXIBIÇÃO DO MAPA E TABELA
col_mapa, col_tabela = st.columns([3, 2])

with col_mapa:
    st.subheader("🗺️ Mapa Operacional")
    
    tiles_provider = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
    attr_provider = "Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS"
    
    registros = sorted(st.session_state.pontos.values(), key=lambda x: normalizar_texto(x["Bairro"]))
    
    if registros:
        m = folium.Map(location=[registros[0]["Latitude"], registros[0]["Longitude"]], zoom_start=12, tiles=tiles_provider, attr=attr_provider)
        coordenadas = []
        for r in registros:
            lat, lng = r["Latitude"], r["Longitude"]
            coordenadas.append([lat, lng])
            folium.Marker(
                location=[lat, lng],
                popup=f"O.S.: {r['Nº da O.S.']}<br>Bairro: {r['Bairro']}<br>Status: {r['Pressão']}",
                tooltip=f"{r['Bairro']} — {r['Pressão']}",
                icon=folium.Icon(color=r.get("Cor", "red"), icon="tint", prefix="fa")
            ).add_to(m)
        if len(coordenadas) > 1:
            m.fit_bounds(coordenadas, padding=(30, 30))
    else:
        m = folium.Map(location=[-5.0920, -42.8038], zoom_start=12, tiles=tiles_provider, attr=attr_provider)

    st_folium(m, width=700, height=500)

with col_tabela:
    st.subheader("📋 Ocorrências do Dia")
    if registros:
        df = pd.DataFrame(registros)[["Nº da O.S.", "Pressão", "Bairro", "Coordenadas"]]
        st.dataframe(df, use_container_width=True)
        
        # Download Excel
        excel_data = pd.DataFrame(registros)[["Data", "Nº da O.S.", "Pressão", "Bairro", "Coordenadas", "Latitude", "Longitude"]]
        st.download_button(
            label="📊 Baixar Excel do Dia",
            data=excel_data.to_csv(index=False).encode('utf-8'),
            file_name=f"Baixa_Pressao_{DATA_ARQUIVO}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhuma ocorrência registrada hoje.")
