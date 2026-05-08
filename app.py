import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector DIAN Ultra", page_icon="🦖", layout="wide")

# CSS para mejorar la legibilidad
st.markdown("""
    <style>
    .header-style { font-size: 25px; color: #1E88E5; font-weight: bold; border-bottom: 2px solid #1E88E5; margin-bottom: 15px; }
    .data-card { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

def generar_pdf(v, c, f, prods):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "SOPORTE DE AUDITORIA FISCAL", ln=True, align="C")
    pdf.ln(5)
    
    # Bloques de datos en el PDF
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(95, 8, " INFORMACION DEL VENDEDOR", 1, 0, 'L', True)
    pdf.cell(95, 8, " INFORMACION DEL COMPRADOR", 1, 1, 'L', True)
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, f"Nombre: {v['nombre'][:45]}", 1)
    pdf.cell(95, 7, f"Nombre: {c['nombre'][:45]}", 1, 1)
    pdf.cell(95, 7, f"NIT/ID: {v['nit']}", 1)
    pdf.cell(95, 7, f"NIT/ID: {c['id']}", 1, 1)
    pdf.cell(95, 7, f"Direccion: {v['dir'][:45]}", 1)
    pdf.cell(95, 7, f"Direccion: {c['dir'][:45]}", 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 8, "Descripcion del Producto", 1, 0, 'C', True)
    pdf.cell(45, 8, "Precio Unit.", 1, 0, 'C', True)
    pdf.cell(45, 8, "IVA", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 8)
    for p in prods:
        pdf.cell(100, 7, p['Descripcion'][:60], 1)
        pdf.cell(45, 7, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"${p['IVA']:,.2f}", 1, 1, 'R')
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL FACTURADO: {f['total_str']}", 0, 1, 'R')
    return pdf.output(dest='S')

st.title("🦖 Godzilla XML: Auditoría Suprema")
st.write("Sube cualquier XML (Adidas, Arturo Calle, Servientrega, etc.)")

archivo = st.file_uploader("", type="xml")

if archivo:
    try:
        raw_data = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_definitivo(texto_xml):
            inicio = texto_xml.find('<')
            if inicio == -1: return None, None, None, []
            texto_xml = texto_xml[inicio:]
            
            try:
                root = ET.fromstring(texto_xml)
            except: return None, None, None, []

            v = {"nombre": "No detectado", "nit": "N/A", "dir": "N/A"}
            c = {"nombre": "No detectado", "id": "N/A", "dir": "N/A", "email": "N/A"}
            f = {"nro": "N/A", "fecha": "N/A", "total": 0.0, "qr": "No disponible", "total_str": "$0.00"}
            items = []

            # 1. Escaneo exhaustivo de etiquetas (Namespace agnostic)
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                # Datos de Factura y Totales
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try:
                        val = float(txt)
                        if val > f["total"]: 
                            f["total"] = val
                            f["total_str"] = f"${val:,.2f}"
                    except: pass
                if tag == 'ID' and len(txt) < 35 and not txt.startswith('http'): f["nro"] = txt
                if tag == 'IssueDate': f["fecha"] = txt
                if tag == 'QRCode': f["qr"] = txt

            # 2. Vendedor (Búsqueda por jerarquía)
            v_node = root.find('.//{*}AccountingSupplierParty')
            if v_node is not None:
                v["nombre"] = v_node.findtext('.//{*}RegistrationName') or v_node.findtext('.//{*}Name') or "N/A"
                v["nit"] = v_node.findtext('.//{*}CompanyID') or "N/A"
                v["dir"] = v_node.findtext('.//{*}Line') or "N/A"

            # 3. Comprador
            c_node = root.find('.//{*}AccountingCustomerParty')
            if c_node is not None:
                c["nombre"] = c_node.findtext('.//{*}RegistrationName') or c_node.findtext('.//{*}Name') or "Persona Natural"
                c["id"] = c_node.findtext('.//{*}CompanyID') or "N/A"
                c["dir"] = c_node.findtext('.//{*}Line') or "N/A"
                c["email"] = c_node.findtext('.//{*}ElectronicMail') or "N/A"

            # 4. Productos
            for line in root.findall('.//{*}InvoiceLine'):
                desc = line.findtext('.//{*}Item/{*}Description') or "Producto"
                pre = line.findtext('.//{*}Price/{*}PriceAmount') or "0"
                iva = line.findtext('.//{*}TaxTotal/{*}TaxAmount') or "0"
                items.append({"Descripcion": desc, "Precio": float(pre), "IVA": float(iva)})

            # 5. Recursividad Extrema (Para archivos tipo Servientrega/Adidas)
            if not items or f["total"] == 0:
                for nodo in root.iter():
                    contenido = (nodo.text or "").strip()
                    if "<?xml" in contenido or "<Invoice" in contenido:
                        v_r, c_r, f_r, it_r = motor_definitivo(contenido)
                        if it_r: return v_r, c_r, f_r, it_r

            return v, c, f, items

        v_final, c_final, f_final, it_final = motor_definitivo(raw_data)

        if f_final and (f_final["total"] > 0 or it_final):
            st.success("✅ Documento procesado correctamente")
            
            # Interfaz de Usuario
            st.markdown(f'<div class="header-style">🏢 EMISOR: {v_final["nombre"]}</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.write(f"**NIT:** {v_final['nit']}")
            col2.write(f"**Dirección:** {v_final['dir']}")

            st.markdown(f'<div class="header-style">👤 COMPRADOR: {c_final["nombre"]}</div>', unsafe_allow_html=True)
            col3, col4, col5 = st.columns(3)
            col3.write(f"**ID/Cédula:** {c_final['id']}")
            col4.write(f"**Dirección:** {c_final['dir']}")
            col5.write(f"**Email:** {c_final['email']}")

            st.markdown('<div class="header-style">📊 DETALLE DE LA OPERACION</div>', unsafe_allow_html=True)
            cola, colb = st.columns([1, 2])
            with cola:
                st.metric("Total Facturado", f_final["total_str"])
                st.write(f"**Factura Nro:** {f_final['nro']}")
                st.write(f"**Fecha
