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
        self.cell(0, 10, 'REPRESENTACIÓN DE DATOS EXTRAÍDOS', 0, 1, 'C')
        self.ln(5)

def crear_pdf(datos):
    pdf = FacturaPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    # Encabezado gris
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f" Documento Nro: {datos['Folio']}", ln=True, fill=True)
    pdf.ln(5)
    
    # Contenido detallado
    for clave, valor in datos.items():
        if clave != "Folio":
            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(50, 8, f"{clave}:", 0)
            pdf.set_font("Helvetica", size=11)
            pdf.cell(0, 8, f"{str(valor)}", 0, 1)
    
    pdf.ln(10)
    # Retornamos el PDF como bytes puros para evitar errores de codificación
    return pdf.output(dest='S')

# --- INTERFAZ ---
st.title("🔍 Extractor y Conversor XML (DIAN)")

archivo = st.file_uploader("Sube tu archivo XML", type="xml")

if archivo:
    try:
        # Leemos el archivo una sola vez
        raw_data = archivo.read()
        xml_text = raw_data.decode('utf-8', errors='ignore')
        
        # Limpieza para evitar errores de parseo
        xml_text = re.sub(r'<\?xml.*\?>', '', xml_text)
        root = ET.fromstring(xml_text)

        # 1. Función de búsqueda profunda mejorada
        def buscar_profundo(palabras_clave):
            for elem in root.iter():
                tag_limpio = elem.tag.split('}')[-1]
                if any(k.lower() == tag_limpio.lower() for k in palabras_clave) and elem.text:
                    return elem.text
            return "No encontrado"

        # 2. Extracción de Folio (Número de factura real)
        folios = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ['ID', 'ParentDocumentID'] and elem.text:
                if not elem.text.startswith('http') and len(elem.text) < 20:
                    folios.append(elem.text)
        folio_final = folios[0] if folios else "S/N"

        # 3. Extracción de Montos (Escaneo total)
        # Buscamos cualquier etiqueta que contenga 'Amount' y tenga un valor numérico
        posibles_valores = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if 'Amount' in tag and elem.text:
                try:
                    val = float(elem.text)
                    if val > 0: posibles_valores.append(val)
                except: continue
        
        total_num = max(posibles_valores) if posibles_valores else 0
        total_final = f"${total_num:,.2f}" if total_num > 0 else "Consultar Original"

        # 4. Consolidado de información
        resumen = {
            "Folio": folio_final,
            "Fecha": buscar_profundo(['IssueDate', 'Date']),
            "Emisor": buscar_profundo(['RegistrationName']),
            "Monto Total": total_final,
            "Moneda": buscar_profundo(['DocumentCurrencyCode', 'CurrencyCode'])
        }

        # --- MOSTRAR EN STREAMLIT ---
        st.success(f"✅ Archivo {folio_final} procesado correctamente")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Número de Factura", resumen["Folio"])
            st.write(f"**Emisor:** {resumen['Emisor']}")
        with c2:
            st.metric("Total Detectado", resumen["Monto Total"])
            st.write(f"**Fecha:** {resumen['Fecha']}")

        st.write("### Tabla de Resumen")
        st.table(pd.DataFrame([resumen]))

        # --- BOTÓN DE DESCARGA (CORREGIDO) ---
        pdf_output = crear_pdf(resumen)
        
        # IMPORTANTE: Aquí pasamos los bytes directamente sin .encode()
        st.download_button(
            label="📥 Descargar PDF con estos datos",
            data=bytes(pdf_output) if isinstance(pdf_output, (bytearray, bytes)) else pdf_output,
            file_name=f"Reporte_{folio_final}.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error al procesar: {e}")
