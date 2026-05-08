import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

# Configuración de página
st.set_page_config(page_title="Lector DIAN Pro", page_icon="🦖", layout="wide")

# Estilos visuales
st.markdown("""
    <style>
    .company-header { font-size: 32px; color: #1E88E5; font-weight: bold; margin-bottom: 0px; }
    .user-header { font-size: 20px; color: #424242; font-weight: bold; margin-top: 10px; }
    .section-divider { border-bottom: 2px solid #eee; margin-bottom: 15px; }
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

st.title("🦖 Godzilla XML: El Final Boss")
st.info("Extrayendo Razón Social, NIT de empresa y datos del Comprador.")

archivo = st.file_uploader("Sube tu factura XML", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_supremo(xml_text):
            # Limpieza inicial del XML
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except:
                return None, []

            info = {
                "id": "", "prefijo": "", "empresa": "No encontrada", 
                "nit_empresa": "No detectado", "fecha": "N/A", "total": 0.0,
                "comprador_nombre": "No detectado", "comprador_id": "No detectado"
            }
            items = []

            # 1. Datos del Vendedor
            v_node = root.find('.//{*}AccountingSupplierParty')
            if v_node is not None:
                info["empresa"] = v_node.findtext('.//{*}RegistrationName') or v_node.findtext('.//{*}Name') or "N/A"
                info["nit_empresa"] = v_node.findtext('.//{*}CompanyID') or "N/A"

            # 2. Datos del Comprador
            c_node = root.find('.//{*}AccountingCustomerParty')
            if c_node is not None:
                info["comprador_nombre"] = c_node.findtext('.//{*}RegistrationName') or c_node.findtext('.//{*}Name') or "Persona Natural"
                info["comprador_id"] = c_node.findtext('.//{*}CompanyID') or "N/A"

            # 3. Datos Generales y Totales
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try:
                        v = float(txt)
                        if v > info["total"]: info["total"] = v
                    except: pass
                if tag == 'ID' and txt and not txt.startswith('http') and len(txt) < 40:
                    info["id"] = txt
                if tag == 'Prefix' and txt:
                    info["prefijo"] = txt
                if tag == 'IssueDate' and txt:
                    info["fecha"] = txt

            # 4. Productos
            for line in root.findall('.//{*}InvoiceLine'):
                try:
                    desc = line.findtext('.//{*}Item/{*}Description') or "Sin descripción"
                    pre = float(line.findtext('.//{*}Price/{*}PriceAmount') or 0.0)
                    iva = float(line.findtext('.//{*}TaxTotal/{*}TaxAmount') or 0.0)
                    items.append({"Descripcion": desc, "Precio": pre, "IVA": iva})
                except: continue

            # 5. Recursividad para AttachedDocuments (Ocultos)
            if not items or info["total"] == 0:
                for nodo in root.iter():
                    contenido = (nodo.text or "").strip()
                    if "<?xml" in contenido or "<Invoice" in contenido:
                        inf_rec, it_rec = motor_supremo(contenido)
                        if it_rec: return inf_rec, it_rec
            
            return info, items

        res_gral, lista_prod = motor_supremo(raw_content)

        if res_gral and (res_gral["total"] > 0 or lista_prod):
            num_factura = f"{res_gral['prefijo']} {res_gral['id']}".strip()
            
            # --- INTERFAZ ---
            st.markdown(f'<p class="company-header">{res_gral["empresa"]}</p>', unsafe_allow_html=True)
            st.caption(f"NIT Vendedor: {res_gral['nit_empresa']}")
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                st.markdown(f'<p class="user-header">👤 Comprador: {res_gral["comprador_nombre"]}</p>', unsafe_allow_html=True)
                st.write(f"**Cédula/NIT:** {res_gral['comprador_id']}")
            
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Facturado", f"${res_gral['total']:,.2f}")
            with col_b:
                st.write("**Factura Nro:**")
                st.subheader(num_factura)
            with col_c:
                st.write("**Fecha:**")
                st.subheader(res_gral['fecha'])
            
            if lista_prod:
                st.subheader("📋 Detalle de Compra")
                st.table(pd.DataFrame(lista_prod).style.format({"Precio": "${:,.2f}", "IVA": "${:,.2f}"}))
            
            # PDF
            pdf_data = {
                "Empresa": res_gral["empresa"],
                "NIT Vendedor": res_gral["nit_empresa"],
                "Comprador": res_gral["comprador_nombre"],
                "ID Comprador": res_gral["comprador_id"],
                "Factura Nro": num_factura,
                "Fecha": res_gral["fecha"],
                "Total": f"${res_gral['total']:,.2f} COP"
            }
            pdf_out = generar_pdf(pdf_data, lista_prod)
            st.download_button("📥 Descargar Soporte PDF", data=bytes(pdf_out), file_name=f"Factura_{num_factura}.pdf")
        else:
            st.error("No se pudo extraer la información del archivo.")

    except Exception as e:
        st.error(f"Error detectado: {e}")
