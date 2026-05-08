import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

# Configuración de página
st.set_page_config(page_title="Lector DIAN Pro", page_icon="🦖", layout="wide")

# Estilo para que el nombre de la empresa resalte
st.markdown("""
    <style>
    .company-header { font-size: 32px; color: #1E88E5; font-weight: bold; margin-bottom: 0px; }
    .user-header { font-size: 20px; color: #424242; font-weight: bold; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def generar_pdf(datos_gral, productos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Soporte de Facturacion Digital", ln=True, align="C")
    pdf.ln(5)
    for k, v in datos_gral.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(50, 7, f"{k}:", 0)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"{v}", 0, ln=True)
    pdf.ln(10)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 10, "Descripcion", 1, 0, 'C', True)
    pdf.cell(50, 10, "Precio Unitario", 1, 0, 'C', True)
    pdf.cell(50, 10, "IVA", 1, 1, 'C', True)
    pdf.set_font("Arial", "", 9)
    for p in productos:
        pdf.cell(90, 8, str(p['Descripcion'])[:55], 1)
        pdf.cell(50, 8, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(50, 8, f"${p['IVA']:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S')

st.title("🦖 Godzilla XML: El Final Boss + Comprador")
st.info("Este código extrae Razón Social, NIT de empresa y datos completos del Comprador.")

archivo = st.file_uploader("Sube tu factura XML", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_supremo(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except: return None, []

            info = {
                "id": "", "prefijo": "", "empresa": "No encontrada", 
                "nit_empresa": "No detectado", "fecha": "N/A", "total": 0.0,
                "comprador_nombre": "No detectado", "comprador_id": "No detectado"
            }
            items = []
            prohibidos = ["DIAN", "DIRECCION DE IMPUESTOS", "UNIDAD ESPECIAL", "N/A"]

            # --- 1. Búsqueda de Vendedor (AccountingSupplierParty) ---
            vendedor_node = root.find('.//{*}AccountingSupplierParty')
            if vendedor_node is not None:
                info["nit_empresa"] = vendedor_node.findtext('.//{*}CompanyID') or "N/A"
                info["empresa"] = vendedor_node.findtext('.//{*}RegistrationName') or vendedor_node.findtext('.//{*}Name') or "No encontrada"

            # --- 2. Búsqueda de Comprador (AccountingCustomerParty) ---
            comprador_node = root.find('.//{*}AccountingCustomerParty')
            if comprador_node is not None:
                info["comprador_nombre"] = comprador_node.findtext('.//{*}RegistrationName') or comprador_node.findtext('.//{*}Name') or "Persona Natural"
                info["comprador_id"] = comprador_node.findtext('.//{*}CompanyID') or "N/A"

            # --- 3. Búsqueda exhaustiva de datos generales (Totales, Fechas, IDs) ---
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try: 
                        v = float(txt)
                        if v > info["total"]: info["total"] = v
                    except: pass
                
                if tag == 'ID' and txt and not txt.startswith('http'):
                    if len(txt) < 40: info["id"] = txt
                
                if tag == 'Prefix' and txt:
                    info["prefijo"] = txt

                if tag == 'IssueDate' and txt:
                    info["fecha"] = txt

            # --- 4. Búsqueda de Productos ---
            lineas = root.findall('.//{*}InvoiceLine')
            for line in lineas:
                d_node = line.find('.//{*}Item/{*}Description')
                p_node = line.find('.//{*}Price/{*}PriceAmount')
                i_node = line.find('.//{*}TaxTotal/{*}TaxAmount')
                try:
                    desc = d_node.text.strip() if d_node is not None else "Sin descripción"
                    pre = float(p_node.text) if p_node is not None else 0.0
                    iva = float(i_node.text) if i_node is not None else 0.0
                    items.append({"Descripcion": desc, "Precio": pre, "IVA": iva})
                except: continue

            # --- 5. Recursividad para AttachedDocuments ---
            if not items or info["total"] == 0:
                for nodo in root.iter():
                    contenido = (nodo.text or "").strip()
                    if "<?xml" in contenido or "<Invoice" in contenido:
                        i_f, i_i = motor_supremo(contenido)
                        if i_f and i_f["total"] > 0: return i_f, i_i
            
            return info, items

        res_gral, lista_prod = motor_supremo(raw_content)

        if res_gral and res_gral["total"] > 0:
            num_factura = f"{res_gral['prefijo']} {res_gral['id']
