import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector DIAN Pro", page_icon="🦖", layout="wide")

def generar_pdf(datos_gral, productos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Soporte de Facturacion Digital", ln=True, align="C")
    pdf.ln(5)
    for k, v in datos_gral.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(45, 7, f"{k}:", 0)
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
        pdf.cell(90, 8, str(p['Descripcion'])[:50], 1)
        pdf.cell(50, 8, f"${p['Precio']:,.2f}", 1, 0, 'R')
        pdf.cell(50, 8, f"${p['IVA']:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S')

st.title("🦖 Godzilla Detallado: Versión Final")
st.markdown("---")

archivo = st.file_uploader("Sube cualquier factura XML de Colombia", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_definitivo(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except: return None, []

            info = {"id": "N/A", "empresa": "No encontrada", "fecha": "N/A", "total": 0.0}
            items = []
            prohibidos = ["DIAN", "DIRECCION DE IMPUESTOS", "UNIDAD ESPECIAL"]

            # 1. Escaneo de Datos Generales
            for nodo in root.iter():
                tag = nodo.tag.split('}')[-1]
                txt = (nodo.text or "").strip()
                
                if tag in ['PayableAmount', 'TaxInclusiveAmount'] and txt:
                    try: 
                        v = float(txt)
                        if v > info["total"]: info["total"] = v
                    except: pass
                
                if tag == 'ID' and txt and len(txt) < 40 and not txt.startswith('http'):
                    info["id"] = txt

                if tag == 'RegistrationName' and len(txt) > 3:
                    if not any(p in txt.upper() for p in prohibidos):
                        info["empresa"] = txt

                if tag == 'IssueDate' and txt:
                    info["fecha"] = txt

            # 2. Escaneo de Productos (InvoiceLine)
            lineas = root.findall('.//{*}InvoiceLine')
            for line in lineas:
                # Búsqueda segura de cada campo
                d_node = line.find('.//{*}Item/{*}Description')
                p_node = line.find('.//{*}Price/{*}PriceAmount')
                i_node = line.find('.//{*}TaxTotal/{*}TaxAmount')
                
                try:
                    desc = d_node.text.strip() if d_node is not None else "Producto sin nombre"
                    pre = float(p_node.text) if p_node is not None else 0.0
                    iva = float(i_node.text) if i_node is not None else 0.0
                    items.append({"Descripcion": desc, "Precio": pre, "IVA": iva})
                except:
                    continue

            # 3. RECURSIVIDAD (Para archivos tipo 'AttachedDocument')
            if not items or info["total"] == 0:
                for nodo in root.iter():
                    contenido = (nodo.text or "").strip()
                    if "<?xml" in contenido or "<Invoice" in contenido:
                        i_f, i_i = motor_definitivo(contenido)
                        if i_f and i_f["total"] > 0: return i_f, i_i
            
            return info, items

        res_gral, lista_prod = motor_definitivo(raw_content)

        if res_gral and res_gral["total"] > 0:
            st.success(f"✅ Factura de **{res_gral['empresa']}** procesada.")
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.metric("Total", f"${res_gral['total']:,.2f}")
                st.write(f"**Folio:** {res_gral['id']}")
                st.write(f"**Fecha:** {res_gral['fecha']}")
            
            with c2:
                st.subheader("Contenido de la Factura")
                if lista_prod:
                    df = pd.DataFrame(lista_prod)
                    st.dataframe(df.style.format({"Precio": "${:,.2f}", "IVA": "${:,.2f}"}))
                else:
                    st.info("Esta factura no detalla productos individuales en el XML.")

            pdf_bytes = generar_pdf({"Empresa": res_gral["empresa"], "ID": res_gral["id"], "Total": f"${res_gral['total']:,.2f}"}, lista_prod)
            st.download_button("📥 Descargar Soporte PDF", data=bytes(pdf_bytes), file_name=f"Factura_{res_gral['id']}.pdf")
        else:
            st.error("No se pudo extraer la información. Asegúrate de que es un XML válido de la DIAN.")

    except Exception as e:
        st.error(f"Error crítico: {e}")
