import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

# Configuración de la página
st.set_page_config(page_title="Visor Factura Pro", layout="wide")

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'REPRESENTACIÓN GRÁFICA DE FACTURA ELECTRÓNICA', 0, 1, 'C')
        self.ln(5)

def generar_pdf(datos, items):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    
    # Datos de cabecera
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f" FACTURA NRO: {datos['folio']}", ln=True, fill=True)
    pdf.ln(2)
    pdf.cell(0, 8, f"Fecha de Emisión: {datos['fecha']}", ln=True)
    pdf.cell(0, 8, f"Emisor: {datos['emisor']}", ln=True)
    pdf.cell(0, 8, f"Receptor: {datos['receptor']}", ln=True)
    pdf.ln(10)
    
    # Tabla de productos
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(110, 10, " Descripción", 1, 0, 'L', True)
    pdf.cell(25, 10, " Cant", 1, 0, 'C', True)
    pdf.cell(50, 10, " Valor Unit.", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", size=10)
    for item in items:
        pdf.cell(110, 10, str(item['Producto'])[:55], 1)
        pdf.cell(25, 10, str(item['Cant']), 1, 0, 'C')
        pdf.cell(50, 10, f"{item['Precio']}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL A PAGAR: {datos['total']}  ", 0, 1, 'R')
    
    return pdf.output()

st.title("📄 Visor de Facturas DIAN (Servientrega)")
st.info("Sube tu archivo XML para generar la representación en PDF.")

# Namespaces estándar
NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#'
}

archivo = st.file_uploader("Seleccionar archivo XML", type="xml")

if archivo:
    try:
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # 1. Intentar extraer datos básicos (búsqueda flexible)
        def buscar(xpath):
            nodo = root.find(xpath, NS)
            if nodo is None: # Si no lo halla con NS, busca por nombre simple
                nodo = root.find(f".//*[local-name()='{xpath.split(':')[-1]}']")
            return nodo.text if nodo is not None else "No encontrado"

        folio = buscar(".//cbc:ParentDocumentID")
        if folio == "No encontrado": folio = buscar(".//cbc:ID")
            
        fecha = buscar(".//cbc:IssueDate")
        emisor = buscar(".//cac:SenderParty//cbc:RegistrationName")
        receptor = buscar(".//cac:ReceiverParty//cbc:RegistrationName")
        
        # 2. Intentar hallar el Total (buscamos PayableAmount en todo el XML)
        total_nodo = root.find(".//*[local-name()='PayableAmount']")
        total_final = f"${float(total_nodo.text):,.2f} COP" if total_nodo is not None else "Consultar Original"

        # 3. Intentar extraer productos
        items = []
        lineas = root.findall(".//*[local-name()='InvoiceLine']")
        
        if not lineas:
            # Si es un AttachedDocument vacío, creamos una línea resumen
            items.append({
                "Producto": "Servicio de transporte / Mensajería (Ver detalle en XML)",
                "Cant": "1",
                "Precio": total_final
            })
        else:
            for line in lineas:
                desc = line.find(".//*[local-name()='Description']").text
                cant = line.find(".//*[local-name()='InvoicedQuantity']").text if line.find(".//*[local-name()='InvoicedQuantity']") is not None else "1"
                pre = line.find(".//*[local-name()='PriceAmount']").text if line.find(".//*[local-name()='PriceAmount']") is not None else "0"
                items.append({
                    "Producto": desc,
                    "Cant": cant,
                    "Precio": f"${float(pre):,.2f}"
                })

        # Mostrar resumen en la App
        st.success(f"Factura {folio} procesada")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Detectado", total_final)
        with col2:
            # Generar PDF y botón
            pdf_bytes = generar_pdf({
                "folio": folio, "fecha": fecha, "emisor": emisor, 
                "receptor": receptor, "total": total_final
            }, items)
            
            st.download_button(
                label="📥 Descargar Factura PDF",
                data=bytes(pdf_bytes),
                file_name=f"Factura_{folio}.pdf",
                mime="application/pdf"
            )

        st.subheader("Detalle de productos")
        st.dataframe(pd.DataFrame(items), use_container_width=True)

    except Exception as e:
        st.error(f"No se pudo leer el detalle: {e}")
        st.warning("Nota: Algunos archivos 'AttachedDocument' no contienen el detalle de precios, solo la validación.")
