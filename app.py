import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Lector de Datos XML", page_icon="🔍")

def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Datos de Facturación", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🔍 Extractor de Datos Reales XML")
st.write("Sube el XML recibido (incluso de ADIDAS o Servientrega) para ver el monto total real.")

archivo = st.file_uploader("Selecciona tu archivo XML", type="xml")

if archivo:
    try:
        xml_data = archivo.read()
        # Intentar decodificar el XML ignorando errores de caracteres especiales
        xml_text = xml_data.decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)

        def buscar_dato(nombres_posibles):
            for elemento in root.iter():
                tag_limpio = elemento.tag.split('}')[-1]
                if tag_limpio in nombres_posibles:
                    return elemento.text
            return None

        # --- LÓGICA DE BÚSQUEDA AGRESIVA PARA EL TOTAL ---
        # Buscamos en todas las etiquetas comunes de la DIAN para montos totales
        etiquetas_monto = ['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount', 'LegalMonetaryTotal']
        monto_encontrado = buscar_dato(etiquetas_monto)

        # Si sigue sin aparecer, buscamos cualquier etiqueta que contenga "Amount" y tenga un valor numérico
        if not monto_encontrado:
            for elemento in root.iter():
                if "Amount" in elemento.tag and elemento.text:
                    try:
                        if float(elemento.text) > 0:
                            monto_encontrado = elemento.text
                    except: continue

        # Extracción de datos principales
        datos = {
            "Número de Factura (ID)": buscar_dato(["ParentDocumentID", "ID"]) or "No encontrado",
            "Fecha de Emisión": buscar_dato(["IssueDate", "Date"]) or "No encontrado",
            "Nombre Emisor": buscar_dato(["RegistrationName", "Name"]) or "No encontrado",
            "Monto Total": f"{monto_encontrado}" if monto_encontrado else "Ver original",
            "Moneda": buscar_dato(["DocumentCurrencyCode", "CurrencyCode"]) or "COP"
        }

        # --- VISUALIZACIÓN ---
        st.subheader("Datos Extraídos del XML")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Factura Nro", datos["Número de Factura (ID)"])
            st.write(f"**Emisor:** {datos['Nombre Emisor']}")
        with c2:
            st.metric("Total Detectado", f"{datos['Monto Total']} {datos['Moneda']}")
            st.write(f"**Fecha:** {datos['Fecha de Emisión']}")

        df = pd.DataFrame(list(datos.items()), columns=["Campo", "Valor Real"])
        st.table(df)

        # --- DESCARGA ---
        st.write("---")
        pdf_raw = generar_pdf(datos)
        st.download_button(
            label="📥 Descargar Resumen en PDF",
            data=bytes(pdf_raw) if isinstance(pdf_raw, (bytearray, bytes)) else pdf_raw.encode('latin-1'),
            file_name=f"Factura_{datos['Número de Factura (ID)']}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Hubo un problema al procesar el archivo: {e}")
