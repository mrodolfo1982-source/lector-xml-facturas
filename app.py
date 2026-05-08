import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import base64
import re

st.set_page_config(page_title="Lector DIAN Pro", page_icon="🧾")

def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Representacion Grafica de Factura", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Extractor Maestro de Facturas (ADIDAS/Servientrega)")
st.info("Este motor ahora 'desencripta' el contenido interno para hallar el monto real.")

archivo = st.file_uploader("Sube tu archivo XML", type="xml")

if archivo:
    try:
        raw_content = archivo.read()
        xml_text = raw_content.decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)

        # --- FUNCIÓN DE BÚSQUEDA PROFUNDA ---
        def obtener_todos_los_montos(nodo):
            encontrados = []
            for e in nodo.iter():
                tag = e.tag.split('}')[-1]
                if any(k in tag for k in ['Amount', 'Total', 'Payable']) and e.text:
                    try:
                        val = float(e.text)
                        if val > 1000: encontrados.append(val)
                    except: continue
            return encontrados

        # 1. Intentar leer la factura interna (Base64)
        factura_interna_encontrada = False
        montos_finales = []
        
        for e in root.iter():
            tag = e.tag.split('}')[-1]
            if tag == 'Description' and e.text and len(e.text) > 100:
                try:
                    # Intentamos decodificar el contenido oculto
                    decoded_xml = base64.b64decode(e.text).decode('utf-8', errors='ignore')
                    sub_root = ET.fromstring(decoded_xml)
                    montos_finales = obtener_todos_los_montos(sub_root)
                    factura_interna_encontrada = True
                    break
                except: continue

        # 2. Si no hay factura interna, buscar en la superficie
        if not montos_finales:
            montos_finales = obtener_todos_los_montos(root)

        # 3. Consolidar Datos
        def buscar_valor(tags):
            for e in root.iter():
                if e.tag.split('}')[-1] in tags and e.text:
                    t = e.text.strip()
                    if not t.startswith('http') and t != "0": return t
            return "No encontrado"

        total_detectado = max(montos_finales) if montos_finales else 0
        
        resumen = {
            "Factura Nro": buscar_valor(['ParentDocumentID', 'ID']),
            "Emisor": buscar_valor(['RegistrationName', 'Name']),
            "Fecha": buscar_valor(['IssueDate', 'Date']),
            "Monto Total": f"${total_detectado:,.2f}" if total_detectado > 0 else "Consultar Soporte",
            "Moneda": buscar_valor(['DocumentCurrencyCode', 'CurrencyCode']) or "COP"
        }

        # --- MOSTRAR RESULTADOS ---
        st.success("✅ Documento procesado con éxito")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Real", resumen["Monto Total"])
            st.write(f"**Comercio:** {resumen['Emisor']}")
        with c2:
            st.metric("Factura", resumen["Factura Nro"])
            st.write(f"**Fecha:** {resumen['Fecha']}")

        st.table(pd.DataFrame(list(resumen.items()), columns=["Campo", "Valor"]))

        # --- DESCARGA ---
        pdf_out = generar_pdf(resumen)
        st.download_button(
            label="📥 Descargar Soporte PDF",
            data=bytes(pdf_out) if isinstance(pdf_out, (bytearray, bytes)) else pdf_out,
            file_name=f"Factura_{resumen['Factura Nro']}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error al procesar: {e}")
