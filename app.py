import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Visor Factura DIAN", layout="wide")

class PDF(FPDF):
    def header(self):
        # Usamos fuentes estándar para evitar problemas de compatibilidad
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'REPRESENTACIÓN GRÁFICA DE FACTURA', 0, 1, 'C')
        self.ln(5)

def generar_pdf(datos, items):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    
    # Información de cabecera
    pdf.cell(0, 10, f"Factura Nro: {datos['folio']}", ln=True)
    pdf.cell(0, 10, f"Fecha: {datos['fecha']}", ln=True)
    pdf.cell(0, 10, f"Emisor: {datos['emisor']}", ln=True)
    pdf.cell(0, 10, f"Receptor: {datos['receptor']}", ln=True)
    pdf.ln(10)
    
    # Tabla de productos
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(100, 10, "Producto", 1)
    pdf.cell(30, 10, "Cant", 1)
    pdf.cell(50, 10, "Precio", 1)
    pdf.ln()
    
    pdf.set_font("Helvetica", size=10)
    for item in items:
        pdf.cell(100, 10, str(item['Producto'])[:50], 1) # Acortamos texto si es muy largo
        pdf.cell(30, 10, str(item['Cant']), 1)
        pdf.cell(50, 10, str(item['Precio']), 1)
        pdf.ln()
        
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL: {datos['total']}", 0, 1, 'R')
    
    # IMPORTANTE: Retornamos los bytes directamente
    return pdf.output()

st.title("📄 Lector XML a PDF")

NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
}

archivo = st.file_uploader("Sube tu XML de Servientrega", type="xml")

if archivo:
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()

        # Extracción de datos
        folio_node = root.find(".//cbc:ParentDocumentID", NS)
        folio = folio_node.text if folio_node is not None else "S/N"
        
        fecha_node = root.find(".//cbc:IssueDate", NS)
        fecha = fecha_node.text if fecha_node is not None else "N/A"
        
        emisor_node = root.find(".//cac:SenderParty//cbc:RegistrationName", NS)
        emisor = emisor_node.text if emisor_node is not None else "Emisor Desconocido"
        
        receptor_node = root.find(".//cac:ReceiverParty//cbc:RegistrationName", NS)
        receptor = receptor_node.text if receptor_node is not None else "Receptor Desconocido"

        total_node = root.find(".//cac:LegalMonetaryTotal/cbc:PayableAmount", NS)
        total = f"${float(total_node.text):,.2f}" if total_node is not None else "$0.00"

        items = []
        for line in root.findall(".//cac:InvoiceLine", NS):
            desc_node = line.find(".//cbc:Description", NS)
            desc = desc_node.text if desc_node is not None else "Sin descripción"
            cant = line.find(".//cbc:InvoicedQuantity", NS).text
            precio = line.find(".//cac:Price/cbc:PriceAmount", NS).text
            items.append({"Producto": desc, "Cant": cant, "Precio": precio})

        st.success(f"Factura {folio} cargada correctamente")

        # GENERACIÓN DEL PDF
        pdf_content = generar_pdf({"folio": folio, "fecha": fecha, "emisor": emisor, "receptor": receptor, "total": total}, items)
        
        # EL CAMBIO CLAVE: Convertimos a bytes explícitamente para el botón
        st.download_button(
            label="📥 Descargar Factura en PDF",
            data=bytes(pdf_content),
            file_name=f"Factura_{folio}.pdf",
            mime="application/pdf"
        )
        
        st.subheader("Detalle visual")
        st.dataframe(pd.DataFrame(items))

    except Exception as e:
        st.error(f"Error crítico: {e}")
