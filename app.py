import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

st.set_page_config(page_title="Lector Universal de Facturas", page_icon="🧾")

def generar_pdf(datos_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Facturacion", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for campo, valor in datos_dict.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(70, 10, f"{campo}:", border=0)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"{str(valor)}", border=0, ln=True)
    return pdf.output(dest='S')

st.title("🧾 Extractor Universal de XML (DIAN)")
st.write("Sube cualquier factura electrónica en formato XML para extraer su información real.")

archivo = st.file_uploader("Arrastra tu archivo XML aquí", type="xml")

if archivo:
    try:
        contenido_crudo = archivo.read().decode("utf-8", errors="ignore")
        
        # --- MOTOR DE BÚSQUEDA UNIVERSAL ---
        def extraer_datos_recursivo(texto_xml):
            try:
                root = ET.fromstring(texto_xml)
            except:
                return None

            res = {"id": None, "emisor": None, "fecha": None, "total": 0.0}
            
            # Etiquetas prioritarias según estándar UBL 2.1 (DIAN)
            tags_total = ['PayableAmount', 'TaxInclusiveAmount', 'LegalMonetaryTotal']
            tags_id = ['ID', 'ParentDocumentID']
            tags_emisor = ['RegistrationName', 'Name']
            
            for e in root.iter():
                tag = e.tag.split('}')[-1]
                
                # 1. Buscar Totales (el mayor valor suele ser el PayableAmount)
                if any(t == tag for t in tags_total) and e.text:
                    try:
                        val = float(e.text)
                        if val > res["total"]: res["total"] = val
                    except: pass
                
                # 2. Buscar ID de Factura (evitando basura técnica)
                if tag in tags_id and e.text:
                    txt = e.text.strip()
                    if not txt.startswith('http') and txt != "0" and len(txt) > 3:
                        if not res["id"]: res["id"] = txt

                # 3. Buscar Emisor
                if tag in tags_emisor and e.text and res["emisor"] is None:
                    if len(e.text.strip()) > 3: res["emisor"] = e.text.strip()

                # 4. Buscar Fecha
                if tag == 'IssueDate' and e.text:
                    res["fecha"] = e.text

                # --- EL TRUCO PARA ADIDAS Y OTROS: XML ANIDADO ---
                # Si encontramos un bloque que parece otro XML (CDATA), lo procesamos
                if e.text and "<?xml" in e.text:
                    datos_internos = extraer_datos_recursivo(e.text.strip())
                    if datos_internos:
                        if datos_internos["total"] > res["total"]: res["total"] = datos_internos["total"]
                        if datos_internos["id"]: res["id"] = datos_internos["id"]
                        if datos_internos["emisor"]: res["emisor"] = datos_internos["emisor"]
            
            return res

        # Ejecutar el extractor
        resultado = extraer_datos_recursivo(contenido_crudo)

        if resultado:
            # Diccionario limpio para mostrar y para el PDF
            resumen = {
                "Factura Nro": resultado["id"] if resultado["id"] else "No detectado",
                "Comercio": resultado["emisor"] if resultado["emisor"] else "No detectado",
                "Fecha": resultado["fecha"] if resultado["fecha"] else "No detectada",
                "Monto Total": f"${resultado['total']:,.2f}",
                "Moneda": "COP"
            }

            # --- INTERFAZ ---
            st.success("✅ Información extraída con éxito")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", resumen["Monto Total"])
                st.write(f"**Emisor:** {resumen['Comercio']}")
            with col2:
                st.metric("Nro. Factura", resumen["Factura Nro"])
                st.write(f"**Fecha:** {resumen['Fecha']}")

            st.table(pd.DataFrame(list(resumen.items()), columns=["Campo", "Valor Detectado"]))

            # --- PDF ---
            pdf_raw = generar_pdf(resumen)
            st.download_button(
                label="📥 Descargar Soporte PDF",
                data=bytes(pdf_raw) if isinstance(pdf_raw, (bytearray, bytes)) else pdf_raw,
                file_name=f"Factura_{resumen['Factura Nro']}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No se pudo encontrar una estructura de factura válida en el archivo.")

    except Exception as e:
        st.error(f"Error crítico de lectura: {e}")
