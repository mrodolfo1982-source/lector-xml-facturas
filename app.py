import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Lector Universal DIAN", layout="wide")

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'REPRESENTACIÓN GRÁFICA DE FACTURA ELECTRÓNICA', 0, 1, 'C')
        self.ln(5)

def generar_pdf(datos, items):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f" DOCUMENTO NRO: {datos['folio']}", ln=True, fill=True)
    pdf.ln(2)
    pdf.cell(0, 8, f"Fecha de Emisión: {datos['fecha']}", ln=True)
    pdf.cell(0, 8, f"Emisor: {datos['emisor']}", ln=True)
    pdf.cell(0, 8, f"Receptor: {datos['receptor']}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(110, 10, " Descripción del Servicio/Producto", 1, 0, 'L', True)
    pdf.cell(25, 10, " Cant", 1, 0, 'C', True)
    pdf.cell(50, 10, " Valor Total", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", size=10)
    for item in items:
        pdf.cell(110, 10, str(item['Producto'])[:55], 1)
        pdf.cell(25, 10, str(item['Cant']), 1, 0, 'C')
        pdf.cell(50, 10, f"{item['Precio']}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL: {datos['total']}  ", 0, 1, 'R')
    return pdf.output()

st.title("📄 Escáner Universal de XML (DIAN)")
st.markdown("Sube cualquier archivo XML de facturación para extraer sus datos automáticamente.")

archivo = st.file_uploader("Arrastra aquí tu archivo XML", type="xml")

if archivo:
    try:
        xml_content = archivo.read().decode('utf-8')
        xml_content = re.sub(r'<\?xml.*\?>', '', xml_content)
        root = ET.fromstring(xml_content)

        # --- LÓGICA UNIVERSAL ---

        # 1. Función para buscar cualquier etiqueta que contenga una palabra clave (ignorando namespaces)
        def buscar_etiqueta(keywords):
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1]
                if any(key.lower() == tag_name.lower() for key in keywords):
                    return elem.text
            return None

        # 2. Extracción de Folio (Busca ID corto que no sea URL)
        ids_encontrados = []
        for elem in root.iter():
            if elem.tag.split('}')[-1] in ['ID', 'ParentDocumentID'] and elem.text:
                if not elem.text.startswith('http') and len(elem.text) < 25:
                    ids_encontrados.append(elem.text)
        folio = ids_encontrados[0] if ids_encontrados else "S/N"

        # 3. Extracción de Nombres (Emisor suele ser el primero, Receptor el segundo)
        nombres = [e.text for e in root.iter() if 'RegistrationName' in e.tag and e.text]
        emisor = nombres[0] if len(nombres) > 0 else "Emisor no identificado"
        receptor = nombres[1] if len(nombres) > 1 else "Receptor no identificado"

        # 4. Extracción de Fecha
        fecha = buscar_etiqueta(['IssueDate', 'Date']) or "No hallada"

        # 5. Escáner de Montos (Busca valores numéricos en etiquetas financieras)
        montos = []
        etiquetas_valor = ['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount', 'PriceAmount']
        for elem in root.iter():
            if elem.tag.split('}')[-1] in etiquetas_valor and elem.text:
                try:
                    val = float(elem.text)
                    if val > 0: montos.append(val)
                except: continue
        
        monto_max = max(montos) if montos else 0
        total_str = f"${monto_max:,.2f} COP" if monto_max > 0 else "Ver original"

        # 6. Construcción de Items
        items = []
        # Intentamos buscar descripciones reales
        descripciones = [e.text for e in root.iter() if 'Description' in e.tag and e.text]
        if descripciones:
            # Tomamos la primera descripción como producto principal
            items.append({"Producto": descripciones[0], "Cant": "1", "Precio": total_str})
        else:
            items.append({"Producto": "Servicio/Producto General", "Cant": "1", "Precio": total_str})

        # --- INTERFAZ ---
        st.success(f"✅ Documento {folio} procesado")
        
        pdf_bytes = generar_pdf({
            "folio": folio, "fecha": fecha, "emisor": emisor, 
            "receptor": receptor, "total": total_str
        }, items)
        
        st.download_button(
            label="📥 Descargar Representación PDF",
            data=bytes(pdf_bytes),
            file_name=f"Factura_{folio}.pdf",
            mime="application/pdf"
        )

        st.write("### Datos Extraídos")
        st.table(pd.DataFrame([{
            "Folio": folio, "Emisor": emisor, "Receptor": receptor, "Total": total_str
        }]))

    except Exception as e:
        st.error(f"Error al procesar este formato de XML: {e}")
