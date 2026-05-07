import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF

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
    
    # Cabecera
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f" FACTURA NRO: {datos['folio']}", ln=True, fill=True)
    pdf.ln(2)
    pdf.cell(0, 8, f"Fecha de Emisión: {datos['fecha']}", ln=True)
    pdf.cell(0, 8, f"Emisor: {datos['emisor']}", ln=True)
    pdf.cell(0, 8, f"Receptor: {datos['receptor']}", ln=True)
    pdf.ln(10)
    
    # Tabla
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

archivo = st.file_uploader("Seleccionar archivo XML", type="xml")

if archivo:
    try:
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # Extracción ultra-simple sin predicados complejos
        def obtener_texto(tag_name):
            for elem in root.iter():
                if tag_name in elem.tag:
                    return elem.text
            return "No encontrado"

        # Buscamos datos clave
        folio = obtener_texto('ParentDocumentID')
        if folio == "No encontrado": folio = obtener_texto('ID')
        
        fecha = obtener_texto('IssueDate')
        # Para emisor y receptor buscamos el nombre registrado
        nombres = [elem.text for elem in root.iter() if 'RegistrationName' in elem.tag]
        emisor = nombres[0] if len(nombres) > 0 else "Servientrega S.A."
        receptor = nombres[1] if len(nombres) > 1 else "RODOLFO MORENO"
        
        # Total
        total_val = obtener_texto('PayableAmount')
        total_final = f"${float(total_val):,.2f} COP" if total_val != "No encontrado" else "Ver adjunto"

        # Productos
        items = []
        # Buscamos todas las líneas de la factura
        encontró_items = False
        for line in root.iter():
            if 'InvoiceLine' in line.tag or 'CreditNoteLine' in line.tag:
                encontró_items = True
                desc = "Descripción no hallada"
                for sub in line.iter():
                    if 'Description' in sub.tag: desc = sub.text
                items.append({
                    "Producto": desc,
                    "Cant": "1",
                    "Precio": total_final
                })

        if not encontró_items:
            items.append({
                "Producto": "Servicio de transporte / Mensajería (Detalle en XML)",
                "Cant": "1",
                "Precio": total_final
            })

        st.success(f"Factura {folio} procesada")
        
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

        st.subheader("Vista Previa de Datos")
        st.table(pd.DataFrame(items))

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
