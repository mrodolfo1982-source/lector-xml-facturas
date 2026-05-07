import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector de Datos XML", page_icon="🔍")

# --- Función para generar el PDF ---
def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Datos XML", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    # Recorremos el diccionario para escribir cada fila en el PDF
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(60, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{valor}", border=0, ln=True)
    
    # Retornamos los bytes del PDF
    return pdf.output(dest='S')

st.title("🔍 Extractor de Datos Reales XML")
st.write("Sube tu archivo para ver la información y descargar el resumen en PDF.")

archivo = st.file_uploader("Selecciona tu archivo XML", type="xml")

if archivo:
    try:
        # Leer el contenido del archivo
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # Función para buscar datos sin que importen los "namespaces"
        def buscar_dato(nombre_etiqueta):
            for elemento in root.iter():
                tag_limpio = elemento.tag.split('}')[-1]
                if tag_limpio == nombre_etiqueta:
                    return elemento.text
            return "No encontrado"

        # Extraer los datos
        datos = {
            "Número de Factura (ID)": buscar_dato("ParentDocumentID") if buscar_dato("ParentDocumentID") != "No encontrado" else buscar_dato("ID"),
            "Fecha de Emisión": buscar_dato("IssueDate"),
            "Nombre Emisor": buscar_dato("RegistrationName"),
            "Monto Total": buscar_dato("PayableAmount") or buscar_dato("TaxInclusiveAmount"),
            "Moneda": buscar_dato("DocumentCurrencyCode")
        }

        # --- MOSTRAR EN PANTALLA ---
        st.subheader("Datos Principales Encontrados")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Factura Nro", datos["Número de Factura (ID)"])
            st.write(f"**Emisor:** {datos['Nombre Emisor']}")
        
        with col2:
            st.metric("Total", f"{datos['Monto Total']} {datos['Moneda']}")
            st.write(f"**Fecha:** {datos['Fecha de Emisión']}")

        st.subheader("Resumen de Información")
        df = pd.DataFrame(list(datos.items()), columns=["Campo", "Valor Real"])
        st.table(df)

        # --- BOTÓN DE DESCARGA PDF ---
        st.write("---")
        pdf_bytes = generar_pdf(datos)
        
        st.download_button(
            label="📥 Descargar esta información en PDF",
            data=pdf_bytes,
            file_name=f"Resumen_{datos['Número de Factura (ID)']}.pdf",
            mime="application/pdf"
        )

        # Sección para "Curiosos"
        with st.expander("Ver estructura técnica completa (XML Crudo)"):
            st.code(xml_data.decode("utf-8"), language="xml")

    except Exception as e:
        st.error(f"Hubo un problema al leer el archivo: {e}")
