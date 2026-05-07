import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Lector Factura XML", page_icon="📄")

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'REPRESENTACIÓN GRÁFICA DE FACTURA ELECTRÓNICA', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf(datos, items):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Bloque de información
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Factura Nro: {datos['folio']}", ln=True, fill=True)
    pdf.cell(0, 10, f"Fecha de Emisión: {datos['fecha']}", ln=True)
    pdf.ln(5)
    
    # Emisor y Receptor
    pdf.set_font("Arial", 'B', 10)
    col_width = pdf.epw / 2
    pdf.cell(col_width, 10, "EMISOR:", ln=0)
    pdf.cell(col_width, 10, "RECEPTOR:", ln=1)
    
    pdf.set_font("Arial", size=10)
    pdf.cell(col_width, 10, datos['emisor'], ln=0)
    pdf.cell(col_width, 10, datos['receptor'], ln=1)
    pdf.ln(10)
    
    # Tabla de productos
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 10, "Descripción", 1)
    pdf.cell(30, 10, "Cant.", 1)
    pdf.cell(60, 10, "Precio Unit.", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(100, 10, str(item['Producto']), 1)
        pdf.cell(30, 10, str(item['Cant']), 1)
        pdf.cell(60, 10, f"${item['Precio Unit']}", 1)
        pdf.ln()
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"TOTAL A PAGAR: {datos['total']}", 0, 1, 'R')
    
    return pdf.output()

# --- INTERFAZ DE STREAMLIT ---
st.title("📄 Lector XML a PDF")
st.markdown("Extrae datos de tu factura y descarga el soporte legal.")

NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
}

archivo = st.file_uploader("Sube tu archivo AttachedDocument.xml", type="xml")

if archivo:
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()

        # Extracción de datos (Ajustado para Colombia)
        folio = root.find(".//cbc:ParentDocumentID", NS).text if root.find(".//cbc:ParentDocumentID", NS) is not None else "S/N"
        fecha = root.find(".//cbc:IssueDate", NS).text if root.find(".//cbc:IssueDate",
