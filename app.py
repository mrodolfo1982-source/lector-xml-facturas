import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Visor de Facturas Real", page_icon="🧾")

def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Factura Extraido", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Extractor Maestro de Facturas")
st.info("Sube el XML de ADIDAS o cualquier comercio. Ahora leeremos el número real.")

archivo = st.file_uploader("Selecciona tu archivo XML", type="xml")

if archivo:
    try:
        xml_text = archivo.read().decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)

        # --- LÓGICA DE EXTRACCIÓN MEJORADA ---
        
        # 1. Buscar el Número de Factura Real
        numero_factura = "No encontrado"
        for e in root.iter():
            tag = e.tag.split('}')[-1]
            # Priorizamos ParentDocumentID que es donde ADIDAS guarda el número real
            if tag in ['ParentDocumentID', 'ID'] and e.text:
                texto = e.text.strip()
                # Filtro: Que no sea un link, que no sea "0" y que tenga longitud razonable
                if not texto.startswith('http') and texto != "0" and 4 < len(texto) < 30:
                    numero_factura = texto
                    break 

        # 2. Buscar el Total (Selecciona el valor más alto con sentido)
        montos = []
        for e in root.iter():
            if any(k in e.tag for k in ['Amount', 'Total']) and e.text:
                try:
                    val = float(e.text)
                    if val > 100: montos.append(val)
                except: continue
        total_val = max(montos) if montos else 0
        total_final = f"${total_val:,.2f}" if total_val > 0 else "Consultar Original"

        # 3. Buscar Emisor y Fecha
        def buscar_tag(lista_tags):
            for e in root.iter():
                if e.tag.split('}')[-1] in lista_tags and e.text: return e.text
            return "No encontrado"

        resumen = {
            "Factura Nro": numero_factura,
            "Emisor": buscar_tag(['RegistrationName', 'Name']),
            "Fecha": buscar_tag(['IssueDate', 'Date']),
            "Monto Total": total_final,
            "Moneda": buscar_tag(['DocumentCurrencyCode', 'CurrencyCode']) or "COP"
        }

        # --- INTERFAZ ---
        st.success(f"✅ Documento Detectado")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nro de Factura", resumen["Factura Nro"])
            st.write(f"**Comercio:** {resumen['Emisor']}")
        with col2:
            st.metric("Total", resumen["Monto Total"])
            st.write(f"**Fecha:** {resumen['Fecha']}")

        st.table(pd.DataFrame(list(resumen.items()), columns=["Campo", "Valor"]))

        # --- BOTÓN DE DESCARGA ---
        pdf_out = generar_pdf(resumen)
        st.download_button(
            label="📥 Descargar Soporte PDF",
            data=bytes(pdf_out) if isinstance(pdf_out, (bytearray, bytes)) else pdf_out,
            file_name=f"Factura_{resumen['Factura Nro']}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error al leer: {e}")
