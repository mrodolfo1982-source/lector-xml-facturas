import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector DIAN Ultra", page_icon="🦖", layout="wide")

st.markdown("""
    <style>
    .section-header { font-size: 22px; color: #1E88E5; font-weight: bold; margin-top: 15px; border-bottom: 2px solid #eee; }
    .company-title { font-size: 28px; font-weight: bold; color: #0D47A1; }
    </style>
    """, unsafe_allow_html=True)

def generar_pdf(datos_v, datos_c, productos, total_f, factura_n):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Auditoria de Factura", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, "EMISOR (VENDEDOR)", 1, 0, 'C')
    pdf.cell(95, 7, "RECEPTOR (COMPRADOR)", 1, 1, 'C')
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, f"Nombre: {datos_v['nombre'][:40]}", 1)
    pdf.cell(95, 7, f"Nombre: {datos_c['nombre'][:40]}", 1, 1)
    pdf.cell(95, 7, f"NIT: {datos_v['nit']}", 1)
    pdf.cell(95, 7, f"ID: {datos_c['id']}", 1, 1)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 8, "Item", 1, 0, 'C')
    pdf.cell(45, 8, "Base", 1, 0, 'C')
    pdf.cell(45, 8, "IVA", 1, 1, 'C')
    pdf.set_font("Arial", "", 8)
    for p in productos:
        pdf.cell(100, 7, p['Descripcion'][:55], 1)
        pdf.cell(45, 7, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"${p['IVA']:,.2f}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL FACTURA: {total_f}", 0, 1, 'R')
    return pdf.output(dest='S')

st.title("🦖 Godzilla XML: El Rompe-Muros")
st.info("Esta versión busca la factura incluso si está oculta dentro de otro archivo (como Servientrega).")

archivo = st.file_uploader("Sube el XML problemático aquí", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_robusto(xml_text):
            # Limpiar basura antes del primer tag
            inicio = xml_text.find('<')
            if inicio == -1: return None
            xml_text = xml_text[inicio:]
            
            try:
                root = ET.fromstring(xml_text)
            except: return None

            vendedor = {"nombre": "N/A", "nit": "N/A", "dir": "N/A"}
            comprador = {"nombre": "N/A", "id": "N/A", "dir": "N/A", "email": "N/A"}
            factura = {"nro": "N/A", "prefijo": "", "fecha": "N/A", "total": 0.0, "qr": "N/A"}
            items = []

            # --- ESCANEO DE DATOS ---
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                # Totales e ID
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try: 
                        val = float(txt)
                        if val > factura["total"]: factura["total"] = val
                    except: pass
                if tag == 'ID' and len(txt) < 35 and not txt.startswith('http'): factura["nro"] = txt
                if tag == 'Prefix': factura["prefijo"] = txt
                if tag == 'IssueDate': factura["fecha"] = txt
                if tag == 'QRCode': factura["qr"] = txt

            # --- BUSCAR VENDEDOR Y COMPRADOR ESPECÍFICOS ---
            v_node = root.find('.//{*}AccountingSupplierParty')
