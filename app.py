import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector DIAN Pro", page_icon="🦖", layout="wide")

def generar_pdf(datos_gral, productos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Soporte de Facturacion Detallado", ln=True, align="C")
    pdf.ln(5)
    
    # Encabezado
    pdf.set_font("Arial", "B", 11)
    for k, v in datos_gral.items():
        pdf.cell(40, 7, f"{k}:", 0)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"{v}", 0, ln=True)
        pdf.set_font("Arial", "B", 11)
    
    pdf.ln(10)
    # Tabla de productos
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(100, 10, "Producto", 1, 0, 'C', True)
    pdf.cell(45, 10, "Precio Base", 1, 0, 'C', True)
    pdf.cell(45, 10, "IVA", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 9)
    for p in productos:
        pdf.cell(100, 8, p['Descripcion'][:50], 1)
        pdf.cell(45, 8, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(45, 8, f"${p['IVA']:,.2f}", 1, 1, 'R')
        
    return pdf.output(dest='S')

st.title("🦖 Godzilla XML: Lector de Detalles")
archivo = st.file_uploader("Sube el XML para ver el desglose", type="xml")

if archivo:
    try:
        raw = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_detallado(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            root = ET.fromstring(xml_text)
            
            info = {"id": "N/A", "comercio": "N/A", "fecha": "N/A", "total": 0.0}
            items = []
            
            # --- 1. Buscar Datos Generales ---
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try: val = float(txt); info["total"] = max(info["total"], val)
                    except: pass
                if tag == 'ID' and txt and len(txt) < 40 and not txt.startswith('http'):
                    info["id"] = txt
                if tag in ['RegistrationName', 'Name'] and len(txt) > 3:
                    if "DIAN" not in txt.upper(): info["comercio"] = txt
                if tag == 'IssueDate' and txt: info["fecha"] = txt

            # --- 2. Buscar Productos (InvoiceLine) ---
            # Buscamos en el XML principal y en los internos si existen
            for line in root.findall('.//{*}InvoiceLine'):
                desc = line.findtext('.//{*}Item/{*}Description') or "Sin descripción"
                precio = line.findtext('.//{*}Price/{*}PriceAmount') or "0"
                # El IVA suele estar en TaxTotal dentro de la línea
                iva = line.findtext('.//{*}TaxTotal/{*}TaxAmount') or "0"
                
                items.append({
                    "Descripcion": desc,
                    "Precio": float(precio),
                    "IVA": float(iva)
                })

            # Si no encontró items, podría ser un AttachedDocument, buscamos recursivo
            if not items:
                desc_interna = root.findtext('.//{*}Description')
                if desc_interna and "<?xml" in desc_interna:
                    return motor_detallado(desc_interna)
            
            return info, items

        res_gral, lista_prod = motor_detallado(raw)

        if res_gral:
            st.success(f"Factura de **{res_gral['comercio']}** leída.")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Total Facturado", f"${res_gral['total']:,.2f}")
                st.write(f"**Nro:** {res_gral['id']}")
            
            with col2:
                st.subheader("Desglose de Productos")
                df = pd.DataFrame(lista_prod)
                # Formatear números para la tabla
                df_show = df.copy()
                df_show['Precio'] = df_show['Precio'].apply(lambda x: f"${x:,.2f}")
                df_show['IVA'] = df_show['IVA'].apply(lambda x: f"${x:,.2f}")
                st.table(df_show)

            # PDF
            datos_pdf = {
                "Comercio": res_gral["comercio"],
                "Factura": res_gral["id"],
                "Total": f"${res_gral['total']:,.2f}"
            }
            pdf_bytes = generar_pdf(datos_pdf, lista_prod)
            st.download_button("📥 Descargar PDF Detallado", data=bytes(pdf_bytes), file_name="Factura_Detallada.pdf")

    except Exception as e:
        st.error(f"Hubo un problema: {e}")
