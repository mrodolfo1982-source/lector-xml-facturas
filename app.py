import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Lector Universal XML", page_icon="🔍")

# --- CLASE PARA EL PDF ---
class FacturaPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'EXTRACCIÓN DE DATOS XML (DIAN)', 0, 1, 'C')
        self.ln(5)

def crear_pdf(datos):
    pdf = FacturaPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # Colores y estructura
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f" Documento: {datos['Folio']}", ln=True, fill=True)
    pdf.ln(5)
    
    # Cuerpo del reporte
    for clave, valor in datos.items():
        if clave != "Folio":
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(50, 8, f"{clave}:", 0)
            pdf.set_font("Helvetica", size=11)
            pdf.cell(0, 8, f"{valor}", 0, 1)
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.cell(0, 10, "Este documento es una representacion de los datos extraidos del XML.", 0, 0, 'C')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ DE STREAMLIT ---
st.title("🔍 Extractor y Conversor XML")
st.info("Sube tu archivo XML para visualizar los datos reales y descargar el soporte en PDF.")

archivo = st.file_uploader("Cargar AttachedDocument.xml", type="xml")

if archivo:
    try:
        xml_content = archivo.read().decode('utf-8')
        xml_content = re.sub(r'<\?xml.*\?>', '', xml_content) # Limpieza técnica
        root = ET.fromstring(xml_content)

        # Función de búsqueda profunda
        def buscar(etiquetas):
            for e in root.iter():
                tag = e.tag.split('}')[-1]
                if tag in etiquetas and e.text:
                    return e.text
            return "No encontrado"

        # Extracción de Folio Real (como C54687702)
        folios = []
        for e in root.iter():
            tag = e.tag.split('}')[-1]
            if tag in ['ID', 'ParentDocumentID'] and e.text:
                if not e.text.startswith('http') and len(e.text) < 20:
                    folios.append(e.text)
        
        # Consolidación de datos reales
        resumen = {
            "Folio": folios[0] if folios else "S/N",
            "Fecha": buscar(['IssueDate', 'Date']),
            "Emisor": buscar(['RegistrationName']),
            "Total": buscar(['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount']),
            "Moneda": buscar(['DocumentCurrencyCode', 'CurrencyCode'])
        }

        # --- MOSTRAR EN PANTALLA ---
        st.subheader("Datos Principales Encontrados")
        c1, c2, c3 = st.columns(3)
        c1.metric("Factura", resumen["Folio"])
        c2.metric("Monto", f"{resumen['Total']} {resumen['Moneda']}")
        c3.metric("Fecha", resumen["Fecha"])

        st.table(pd.DataFrame([resumen]))

        # --- BOTÓN DE DESCARGA ---
        st.write("---")
        pdf_data = crear_pdf(resumen)
        
        st.download_button(
            label="📥 DESCARGAR ESTA INFORMACIÓN EN PDF",
            data=pdf_data,
            file_name=f"Datos_Factura_{resumen['Folio']}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error al procesar: {e}")
