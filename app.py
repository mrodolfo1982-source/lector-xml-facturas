import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

# Configuración de página
st.set_page_config(page_title="Lector Universal DIAN", page_icon="🧾")

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

st.title("🧾 Lector de Facturas Universal")
st.markdown("---")

archivo = st.file_uploader("Sube cualquier factura XML de Colombia", type="xml")

if archivo:
    try:
        raw_content = archivo.read().decode("utf-8", errors="ignore")
        
        def motor_universal(xml_text):
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except:
                return None

            data = {"id": None, "comercio": None, "fecha": None, "total": 0.0}
            
            # Filtro para ignorar a la DIAN como emisor
            nombres_prohibidos = ["DIAN", "DIRECCION DE IMPUESTOS", "UNIDAD ESPECIAL DIRECCION"]

            for nodo in root.iter():
                tag_name = nodo.tag.split('}')[-1]
                content = (nodo.text or "").strip()

                # 1. Buscar el TOTAL (PayableAmount es el estándar más fuerte)
                if tag_name in ['PayableAmount', 'TaxInclusiveAmount'] and content:
                    try:
                        val = float(content)
                        if val > data["total"]: data["total"] = val
                    except: pass
                
                # 2. Buscar ID (Folio) - Evitamos URLs
                if tag_name == 'ID' and content and len(content) < 30:
                    if not content.startswith('http'):
                        data["id"] = content

                # 3. Buscar Nombre del Comercio (Priorizando el que NO sea la DIAN)
                if tag_name in ['RegistrationName', 'Name'] and len(content) > 3:
                    es_dian = any(p in content.upper() for p in nombres_prohibidos)
                    if not es_dian:
                        # Si encontramos un nombre real, lo preferimos sobre cualquier otro
                        data["comercio"] = content
                    elif es_dian and not data["comercio"]:
                        # Solo ponemos DIAN si no hemos encontrado absolutamente nada más
                        data["comercio"] = content

                # 4. Fecha
                if tag_name == 'IssueDate' and content:
                    data["fecha"] = content

                # 5. RECURSIVIDAD
                if "<?xml" in content or "<Invoice" in content or "<AttachedDocument" in content:
                    interno = motor_universal(content)
                    if interno:
                        if interno["total"] > data["total"]: data["total"] = interno["total"]
                        if interno["id"]: data["id"] = interno["id"]
                        if interno["comercio"] and not any(p in interno["comercio"].upper() for p in nombres_prohibidos):
                            data["comercio"] = interno["comercio"]
                        if interno["fecha"]: data["fecha"] = interno["fecha"]
            
            return data

        resultado = motor_universal(raw_content)

        if resultado and resultado["total"] > 0:
            resumen = {
                "Factura Nro": resultado["id"],
                "Empresa": resultado["comercio"],
                "Fecha Emision": resultado["fecha"],
                "Total a Pagar": f"${resultado['total']:,.2f}",
                "Moneda": "COP"
            }

            st.success("✅ Datos extraídos correctamente")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Monto Total", resumen["Total a Pagar"])
            with col2:
                st.metric("Vendedor", resumen["Empresa"])
            
            st.write(f"**Folio:** {resumen['Factura Nro']}")
            st.write(f"**Fecha de Operación:** {resumen['Fecha Emision']}")

            pdf_bytes = generar_pdf(resumen)
            st.download_button("📥 Descargar Soporte PDF", data=bytes(pdf_bytes), file_name=f"Factura_{resultado['id']}.pdf")
        else:
            st.warning("⚠️ No se detectaron montos válidos. Verifica que el archivo sea un XML de factura electrónica.")

    except Exception as e:
        st.error(f"❌ Error técnico: {e}")
