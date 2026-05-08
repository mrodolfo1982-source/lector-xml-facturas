import streamlit as st
import xml.etree.ElementTree as ET
from fpdf import FPDF

# Configuración de página con estilo CSS para evitar cortes de texto
st.set_page_config(page_title="Lector DIAN Pro", page_icon="🦖")
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .company-name { font-size: 28px; color: #1E88E5; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

def generar_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Soporte de Facturacion Digital", ln=True, align="C")
    pdf.ln(10)
    for campo, valor in datos.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(50, 10, f"{campo}:", 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"{valor}", 0, ln=True)
    return pdf.output(dest='S')

st.title("🦖 Lector Universal (Modo Godzilla)")
st.info("Sube cualquier XML de Colombia (Arturo Calle, Adidas, Éxito, etc.)")

archivo = st.file_uploader("", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_godzilla(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except:
                return None

            data = {"id": None, "comercio": None, "fecha": None, "total": 0.0}
            nombres_prohibidos = ["DIAN", "DIRECCION DE IMPUESTOS", "UNIDAD ESPECIAL"]

            for nodo in root.iter():
                tag_name = nodo.tag.split('}')[-1]
                content = (nodo.text or "").strip()

                if tag_name in ['PayableAmount', 'TaxInclusiveAmount'] and content:
                    try:
                        val = float(content)
                        if val > data["total"]: data["total"] = val
                    except: pass
                
                if tag_name == 'ID' and content and len(content) < 40 and not content.startswith('http'):
                    data["id"] = content

                if tag_name in ['RegistrationName', 'Name'] and len(content) > 3:
                    if not any(p in content.upper() for p in nombres_prohibidos):
                        if not data["comercio"] or len(content) > len(data["comercio"]):
                            data["comercio"] = content

                if tag_name == 'IssueDate' and content:
                    data["fecha"] = content

                # Recursividad para AttachedDocuments
                if any(x in content for x in ["<?xml", "<Invoice", "<AttachedDocument"]):
                    interno = motor_godzilla(content)
                    if interno:
                        if interno["total"] > data["total"]: data["total"] = interno["total"]
                        if interno["id"]: data["id"] = interno["id"]
                        if interno["comercio"] and not any(p in interno["comercio"].upper() for p in nombres_prohibidos):
                            data["comercio"] = interno["comercio"]
                        if interno["fecha"]: data["fecha"] = interno["fecha"]
            return data

    except Exception as e:
        st.error(f"Error: {e}")

    res = motor_godzilla(raw_content)

    if res and res["total"] > 0:
        st.success("¡Factura devorada con éxito!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Monto Total", f"${res['total']:,.2f}")
            st.write(f"**Fecha:** {res['fecha']}")
        with col2:
            st.markdown(f"**Vendedor:**")
            st.markdown(f'<p class="company-name">{res["comercio"]}</p>', unsafe_allow_html=True)
            st.write(f"**Folio:** {res['id']}")

        datos_pdf = {
            "Comercio": res["comercio"],
            "Factura Nro": res["id"],
            "Fecha": res["fecha"],
            "Monto Total": f"${res['total']:,.2f} COP"
        }
        
        pdf_bytes = generar_pdf(datos_pdf)
        st.download_button("📥 Descargar Soporte PDF", data=bytes(pdf_bytes), file_name=f"Factura_{res['id']}.pdf")
