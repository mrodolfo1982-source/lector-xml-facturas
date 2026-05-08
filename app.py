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
            # Limpieza inicial para asegurar que empiece en un tag
            xml_text = xml_text[xml_text.find('<'):] if '<' in xml_text else xml_text
            try:
                root = ET.fromstring(xml_text)
            except:
                return None

            data = {"id": None, "comercio": None, "fecha": None, "total": 0.0}
            
            # Lista de etiquetas que la DIAN usa para el TOTAL
            tags_dinero = ['PayableAmount', 'TaxInclusiveAmount', 'LegalMonetaryTotal']
            
            for nodo in root.iter():
                # Quitamos el Namespace (el texto entre llaves {})
                tag_name = nodo.tag.split('}')[-1]
                content = (nodo.text or "").strip()

                # 1. Buscar el TOTAL (compara con varias opciones legales)
                if any(t == tag_name for t in tags_dinero) and content:
                    try:
                        val = float(content)
                        # Nos quedamos con el valor más alto encontrado (el total final)
                        if val > data["total"]: data["total"] = val
                    except: pass
                
                # 2. Buscar ID (Folio de la factura)
                if tag_name == 'ID' and content:
                    if len(content) > 3 and not content.startswith('http'):
                        # Preferimos IDs con letras (prefijos de factura)
                        if not data["id"] or any(c.isalpha() for c in content):
                            data["id"] = content

                # 3. Buscar Nombre del Comercio (Emisor)
                if tag_name in ['RegistrationName', 'Name'] and len(content) > 3:
                    # Filtramos nombres muy genéricos o vacíos
                    if not data["comercio"] or (len(content) > len(data["comercio"])):
                        data["comercio"] = content

                # 4. Buscar Fecha
                if tag_name in ['IssueDate', 'Date'] and content and not data["fecha"]:
                    data["fecha"] = content

                # 5. RECURSIVIDAD: Si hay contenido XML o Invoice dentro de un tag
                if "<?xml" in content or "<Invoice" in content or "<AttachedDocument" in content:
                    interno = motor_universal(content)
                    if interno:
                        if interno["total"] > data["total"]: data["total"] = interno["total"]
                        if interno["id"] and (not data["id"] or any(c.isalpha() for c in interno["id"])):
                            data["id"] = interno["id"]
                        if interno["comercio"]: data["comercio"] = interno["comercio"]
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
            
            # Formato scannable
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Monto Total", resumen["Total a Pagar"])
            with col2:
                st.metric("Número de Factura", resumen["Factura Nro"])
            
            st.write(f"**Vendedor:** {resumen['Empresa']}")
            st.write(f"**Fecha:** {resumen['Fecha Emision']}")

            # Botón de PDF
            pdf_bytes = generar_pdf(resumen)
            st.download_button("📥 Generar Soporte PDF", data=bytes(pdf_bytes), file_name=f"Resumen_{resultado['id']}.pdf")
        else:
            st.warning("⚠️ Se leyó el archivo pero no se encontró un monto superior a $0. ¿Es este un XML de factura?")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
