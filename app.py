import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Lector de Facturas Pro", page_icon="🧾")

# --- Generador de PDF Robusto ---
def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Factura Electrónica", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Extractor Inteligente de Facturas")
st.write("Optimizado para Adidas, Servientrega y otros proveedores DIAN.")

archivo = st.file_uploader("Sube tu archivo XML", type="xml")

if archivo:
    try:
        contenido_completo = archivo.read().decode("utf-8", errors="ignore")
        
        def procesar_capas(texto_xml):
            try:
                # Limpieza de posibles prefijos raros
                inicio_xml = texto_xml.find('<')
                if inicio_xml == -1: return None
                root = ET.fromstring(texto_xml[inicio_xml:])
            except: return None

            datos = {"id": None, "emisor": None, "fecha": None, "monto": 0.0}
            
            for e in root.iter():
                tag = e.tag.split('}')[-1]
                texto = (e.text or "").strip()

                # 1. Búsqueda de ID (Folio) - Buscamos el patrón de Adidas/Servientrega
                if tag in ['ID', 'ParentDocumentID'] and texto:
                    if not texto.startswith('http') and texto != "0" and len(texto) > 4:
                        # Si encontramos un ID con letras y números (ej: 025A...), ese es el ganador
                        if any(c.isalpha() for c in texto) or not datos["id"]:
                            datos["id"] = texto

                # 2. Búsqueda de Emisor
                if tag in ['RegistrationName', 'Name'] and len(texto) > 3:
                    if not datos["emisor"] or "COLOMBIA" in texto.upper():
                        datos["emisor"] = texto

                # 3. Búsqueda de Fecha
                if tag in ['IssueDate', 'Date'] and texto:
                    datos["fecha"] = texto

                # 4. Búsqueda de Monto (El máximo valor financiero)
                if any(k in tag for k in ['Amount', 'Total', 'Payable']) and texto:
                    try:
                        val = float(texto)
                        if val > datos["monto"]: datos["monto"] = val
                    except: pass

                # 5. RECURSIVIDAD: Si hay un XML dentro, lo exploramos
                if "<?xml" in texto:
                    interno = procesar_capas(texto)
                    if interno:
                        if interno["monto"] > datos["monto"]: datos["monto"] = interno["monto"]
                        if interno["id"]: datos["id"] = interno["id"]
                        if interno["emisor"]: datos["emisor"] = interno["emisor"]
            
            return datos

        # Ejecución
        final = procesar_capas(contenido_completo)

        if final:
            resumen = {
                "Factura Nro": final["id"] or "No detectado",
                "Comercio": final["emisor"] or "No detectado",
                "Fecha": final["fecha"] or "No detectada",
                "Monto Total": f"${final['monto']:,.2f}",
                "Moneda": "COP"
            }

            # --- Visualización ---
            st.success("✅ Datos extraídos correctamente")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Detectado", resumen["Monto Total"])
                st.write(f"**Vendedor:** {resumen['Comercio']}")
            with col2:
                st.metric("Número Factura", resumen["Factura Nro"])
                st.write(f"**Fecha:** {resumen['Fecha']}")

            st.table(pd.DataFrame(list(resumen.items()), columns=["Campo", "Valor"]))

            # --- PDF ---
            pdf_bytes = generar_pdf(resumen)
            st.download_button(
                label="📥 Descargar PDF",
                data=bytes(pdf_bytes) if isinstance(pdf_bytes, (bytearray, bytes)) else pdf_bytes,
                file_name=f"Factura_{resumen['Factura Nro']}.pdf",
                mime="application/pdf"
            )
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
