import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector DIAN Ultra", page_icon="🦖", layout="wide")

# Estilos visuales
st.markdown("""
    <style>
    .section-header { font-size: 24px; color: #1E88E5; font-weight: bold; margin-top: 20px; border-bottom: 2px solid #eee; }
    .data-label { font-weight: bold; color: #555; }
    .qr-box { background-color: #f9f9f9; padding: 10px; border: 1px dashed #ccc; border-radius: 5px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

def generar_pdf(datos_v, datos_c, productos, total_f, factura_n):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Soporte Legal de Facturacion", ln=True, align="C")
    
    # Datos Factura
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Factura Nro: {factura_n}", ln=True)
    pdf.ln(5)

    # Vendedor vs Comprador
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, "DATOS DEL VENDEDOR", 1, 0, 'C', True)
    pdf.cell(95, 7, "DATOS DEL COMPRADOR", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 9)
    # Fila 1: Nombres
    pdf.cell(95, 7, f"Nombre: {datos_v['nombre'][:45]}", 1)
    pdf.cell(95, 7, f"Nombre: {datos_c['nombre'][:45]}", 1, 1)
    # Fila 2: IDs
    pdf.cell(95, 7, f"NIT: {datos_v['nit']}", 1)
    pdf.cell(95, 7, f"ID: {datos_c['id']}", 1, 1)
    # Fila 3: Direccion
    pdf.cell(95, 7, f"Dir: {datos_v['dir'][:45]}", 1)
    pdf.cell(95, 7, f"Dir: {datos_c['dir'][:45]}", 1, 1)
    
    pdf.ln(10)
    # Tabla Productos
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 8, "Descripcion", 1, 0, 'C')
    pdf.cell(45, 8, "Precio Base", 1, 0, 'C')
    pdf.cell(45, 8, "IVA", 1, 1, 'C')
    
    pdf.set_font("Arial", "", 8)
    for p in productos:
        pdf.cell(100, 7, p['Descripcion'][:60], 1)
        pdf.cell(45, 7, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(45, 7, f"${p['IVA']:,.2f}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL: {total_f}", 0, 1, 'R')
    return pdf.output(dest='S')

st.title("🦖 Godzilla XML: Auditoría Completa")

archivo = st.file_uploader("Sube tu XML para inspección total", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_auditor(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            root = ET.fromstring(xml_text)
            
            # Estructuras de datos
            vendedor = {"nombre": "N/A", "nit": "N/A", "dir": "N/A"}
            comprador = {"nombre": "N/A", "id": "N/A", "dir": "N/A", "email": "N/A"}
            factura = {"nro": "N/A", "prefijo": "", "fecha": "N/A", "total": 0.0, "qr": "N/A"}
            items = []

            # 1. Buscar Vendedor (AccountingSupplierParty)
            sup = root.find('.//{*}AccountingSupplierParty')
            if sup is not None:
                vendedor["nombre"] = sup.findtext('.//{*}RegistrationName') or sup.findtext('.//{*}Name') or "N/A"
                vendedor["nit"] = sup.findtext('.//{*}CompanyID') or "N/A"
                vendedor["dir"] = sup.findtext('.//{*}Line') or "N/A"

            # 2. Buscar Comprador (AccountingCustomerParty)
            cust = root.find('.//{*}AccountingCustomerParty')
            if cust is not None:
                comprador["nombre"] = cust.findtext('.//{*}RegistrationName') or cust.findtext('.//{*}Name') or "Persona Natural"
                comprador["id"] = cust.findtext('.//{*}CompanyID') or "N/A"
                comprador["dir"] = cust.findtext('.//{*}Line') or "N/A"
                comprador["email"] = cust.findtext('.//{*}ElectronicMail') or "N/A"

            # 3. Datos Generales y QR
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                if tag in ['PayableAmount', 'TaxInclusiveAmount']:
                    try: val = float(txt); factura["total"] = max(factura["total"], val)
                    except: pass
                if tag == 'ID' and len(txt) < 30 and not txt.startswith('http'): factura["nro"] = txt
                if tag == 'Prefix': factura["prefijo"] = txt
                if tag == 'IssueDate': factura["fecha"] = txt
                # El QR en el XML de la DIAN suele estar en esta etiqueta
                if tag == 'QRCode': factura["qr"] = txt

            # 4. Productos
            for line in root.findall('.//{*}InvoiceLine'):
                desc = line.findtext('.//{*}Item/{*}Description') or "Sin nombre"
                pre = line.findtext('.//{*}Price/{*}PriceAmount') or "0"
                iva = line.findtext('.//{*}TaxTotal/{*}TaxAmount') or "0"
                items.append({"Descripcion": desc, "Precio": float(pre), "IVA": float(iva)})

            # Recursividad si es AttachedDocument
            if not items:
                desc_interna = root.findtext('.//{*}Description')
                if desc_interna and "<?xml" in desc_interna:
                    return motor_auditor(desc_interna)

            return vendedor, comprador, factura, items

        v, c, f, prods = motor_auditor(raw_content)

        if f["total"] > 0:
            num_full = f"{f['prefijo']} {f['nro']}".strip()
            
            # --- INTERFAZ STREAMLIT ---
            st.markdown(f'<p class="section-header">🏢 VENDEDOR: {v["nombre"]}</p>', unsafe_allow_html=True)
            colv1, colv2 = st.columns(2)
            colv1.write(f"**NIT:** {v['nit']}")
            colv2.write(f"**Ubicación:** {v['dir']}")

            st.markdown(f'<p class="section-header">👤 COMPRADOR: {c["nombre"]}</p>', unsafe_allow_html=True)
            colc1, colc2, colc3 = st.columns(3)
            colc1.write(f"**ID/Cédula:** {c['id']}")
            colc2.write(f"**Dirección:** {c['dir']}")
            colc3.write(f"**Email:** {c['email']}")

            st.markdown('<p class="section-header">💰 RESUMEN Y PRODUCTOS</p>', unsafe_allow_html=True)
            colr1, colr2 = st.columns([1, 2])
            with colr1:
                st.metric("Total", f"${f['total']:,.2f}")
                st.write(f"**Factura:** {num_full}")
                st.write(f"**Fecha:** {f['fecha']}")
                if f["qr"] != "N/A":
                    st.write("**Enlace QR DIAN:**")
                    st.code(f["qr"][:50] + "...")
            with colr2:
                st.table(pd.DataFrame(prods).style.format({"Precio": "${:,.2f}", "IVA": "${:,.2f}"}))

            # PDF
            res_pdf = generar_pdf(v, c, prods, f"${f['total']:,.2f}", num_full)
            st.download_button("📥 Descargar Soporte Completo", data=bytes(res_pdf), file_name=f"Auditoria_{num_full}.pdf")

    except Exception as e:
        st.error(f"Error en el análisis: {e}")
