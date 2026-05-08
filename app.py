import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector Universal DIAN", page_icon="🇨🇴")

def generar_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Facturacion Electronica", ln=True, align="C")
    pdf.ln(10)
    for campo, valor in datos.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(60, 10, f"{campo}:", 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"{valor}", 0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Lector de Facturas Integral")
st.info("Compatible con Adidas (XML anidado) y Servientrega (AttachedDocument)")

archivo = st.file_uploader("Sube tu archivo XML", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def minero_de_datos(xml_text):
            # Limpiar posibles espacios antes del tag de apertura
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except:
                return None

            data = {"id": None, "comercio": None, "fecha": None, "total": 0.0}
            
            for nodo in root.iter():
                tag_name = nodo.tag.split('}')[-1]
                content = (nodo.text or "").strip()

                # 1. Buscar el TOTAL (PayableAmount es el estándar de oro)
                if tag_name == 'PayableAmount' and content:
                    try:
                        val = float(content)
                        if val > data["total"]: data["total"] = val
                    except: pass
                
                # 2. Buscar ID de factura (Priorizamos los que tienen letras como C546...)
                if tag_name == 'ID' and content:
                    if len(content) > 4 and not content.startswith('http'):
                        if not data["id"] or any(c.isalpha() for c in content):
                            data["id"] = content

                # 3. Buscar Nombre del Comercio
                if tag_name in ['RegistrationName', 'Name'] and len(content) > 3:
                    if not data["comercio"] or "S.A" in content.upper():
                        data["comercio"] = content

                # 4. Buscar Fecha
                if tag_name == 'IssueDate' and content and not data["fecha"]:
                    data["fecha"] = content

                # --- EL TRUCO RECURSIVO ---
                # Si encontramos un bloque XML oculto (como en Adidas o Servientrega)
                if "<?xml" in content or "<Invoice" in content or "<ApplicationResponse" in content:
                    interno = minero_de_datos(content)
                    if interno:
                        if interno["total"] > data["total"]: data["total"] = interno["total"]
                        if interno["id"] and (not data["id"] or any(c.isalpha() for c in interno["id"])):
                            data["id"] = interno["id"]
                        if interno["comercio"]: data["comercio"] = interno["comercio"]
                        if interno["fecha"]: data["fecha"] = interno["fecha"]
            
            return data

        resultado = minero_de_datos(raw_content)

        if resultado and resultado["total"] > 0:
            resumen = {
                "Factura Nro": resultado["id"],
                "Empresa": resultado["comercio"],
                "Fecha Emision": resultado["fecha"],
                "Total a Pagar": f"${resultado['total']:,.2f}",
                "Moneda": "COP"
            }

            # Mostrar resultados
            st.success("¡Factura procesada!")
            c1, c2 = st.columns(2)
            c1.metric("Monto", resumen["Total a Pagar"])
            c2.metric("Factura", resumen["Factura Nro"])
            
            st.table(pd.DataFrame(list(resumen.items()), columns=["Concepto", "Dato"]))

            # Descarga
            pdf_out = generar_pdf(resumen)
            st.download_button("📥 Descargar PDF", data=bytes(pdf_out), file_name=f"Factura_{resultado['id']}.pdf")
        else:
            st.error("No se pudo extraer el monto. Verifica que el XML sea una factura válida.")

    except Exception as e:
        st.error(f"Error técnico: {e}")
