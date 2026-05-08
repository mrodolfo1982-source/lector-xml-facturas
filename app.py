import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Lector de Facturas Pro", page_icon="🧾")

def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Facturacion Extraido", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Lector de Facturas Reales (DIAN)")
st.write("Este motor está diseñado para extraer el total real, incluso si está oculto.")

archivo = st.file_uploader("Sube el XML de ADIDAS, Servientrega o cualquier comercio", type="xml")

if archivo:
    try:
        xml_data = archivo.read()
        xml_text = xml_data.decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)

        # 1. BUSCADOR DE FOLIO (Evita URLs, busca el código real)
        folios_reales = []
        for e in root.iter():
            tag = e.tag.split('}')[-1]
            if tag in ['ID', 'ParentDocumentID'] and e.text:
                if not e.text.startswith('http') and len(e.text) < 25:
                    folios_reales.append(e.text)
        folio_final = folios_reales[0] if folios_reales else "0"

        # 2. BUSCADOR DE TOTALES (Escaneo Agresivo)
        # Buscamos etiquetas financieras estándar y no estándar
        etiquetas_dinero = ['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount', 'LegalMonetaryTotal', 'PriceAmount']
        valores_encontrados = []

        for e in root.iter():
            tag = e.tag.split('}')[-1]
            if any(k in tag for k in ['Amount', 'Total']) and e.text:
                try:
                    val = float(e.text)
                    if val > 100: # Filtramos valores pequeños para no confundir con IVA o centavos
                        valores_encontrados.append(val)
                except: continue
        
        # El total suele ser el valor más alto encontrado en el documento
        total_real = max(valores_encontrados) if valores_encontrados else 0
        total_str = f"${total_real:,.2f}" if total_real > 0 else "No detectado automáticamente"

        # 3. DATOS DE EMISOR Y FECHA
        def buscar_simple(claves):
            for e in root.iter():
                if e.tag.split('}')[-1] in claves: return e.text
            return "No encontrado"

        resumen = {
            "Número de Factura (ID)": folio_final,
            "Fecha de Emisión": buscar_simple(['IssueDate', 'Date']),
            "Nombre Emisor": buscar_simple(['RegistrationName', 'Name']),
            "Monto Total": total_str,
            "Moneda": buscar_simple(['DocumentCurrencyCode', 'CurrencyCode']) or "COP"
        }

        # --- MOSTRAR RESULTADOS ---
        st.success(f"✅ Procesado: Factura {folio_final}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Factura", total_str)
            st.write(f"**Comercio:** {resumen['Nombre Emisor']}")
        with col2:
            st.metric("Nro Documento", folio_final)
            st.write(f"**Fecha:** {resumen['Fecha de Emisión']}")

        st.table(pd.DataFrame(list(resumen.items()), columns=["Campo", "Valor en XML"]))

        # --- BOTON DE DESCARGA ---
        pdf_bytes = generar_pdf(resumen)
        st.download_button(
            label="📥 Descargar Soporte PDF",
            data=bytes(pdf_bytes) if isinstance(pdf_bytes, (bytearray, bytes)) else pdf_bytes,
            file_name=f"Factura_{folio_final}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error técnico: {e}")
