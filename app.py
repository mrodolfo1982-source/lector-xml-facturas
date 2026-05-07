import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.set_page_config(page_title="Lector de Datos XML", page_icon="🔍")

st.title("🔍 Extractor de Datos Reales XML")
st.write("Sube tu archivo para ver la información que contiene sin generar documentos adicionales.")

# El cargador de archivos
archivo = st.file_uploader("Selecciona tu archivo XML", type="xml")

if archivo:
    try:
        # Leer el contenido del archivo
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # Función para buscar datos sin que importen los "namespaces" (las URL largas)
        def buscar_dato(nombre_etiqueta):
            for elemento in root.iter():
                # Quitamos la parte técnica del nombre de la etiqueta
                tag_limpio = elemento.tag.split('}')[-1]
                if tag_limpio == nombre_etiqueta:
                    return elemento.text
            return "No encontrado"

        # Extraer los datos que realmente importan
        datos = {
            "Número de Factura (ID)": buscar_dato("ParentDocumentID") if buscar_dato("ParentDocumentID") != "No encontrado" else buscar_dato("ID"),
            "Fecha de Emisión": buscar_dato("IssueDate"),
            "Nombre Emisor": buscar_dato("RegistrationName"), # El primer RegistrationName suele ser el emisor
            "Monto Total": buscar_dato("PayableAmount") or buscar_dato("TaxInclusiveAmount"),
            "Moneda": buscar_dato("DocumentCurrencyCode")
        }

        # Mostrar resultados destacados
        st.subheader("Datos Principales Encontrados")
        
        # Crear columnas para que se vea ordenado
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Factura Nro", datos["Número de Factura (ID)"])
            st.write(f"**Emisor:** {datos['Nombre Emisor']}")
        
        with col2:
            st.metric("Total", f"{datos['Monto Total']} {datos['Moneda']}")
            st.write(f"**Fecha:** {datos['Fecha de Emisión']}")

        # Mostrar todos los datos en una tabla para mayor claridad
        st.subheader("Resumen de Información")
        df = pd.DataFrame(list(datos.items()), columns=["Campo", "Valor Real"])
        st.table(df)

        # Sección para "Curiosos": Ver el XML tal cual
        with st.expander("Ver estructura técnica completa (XML Crudo)"):
            st.code(xml_data.decode("utf-8"), language="xml")

    except Exception as e:
        st.error(f"Hubo un problema al leer el archivo: {e}")
