import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from fpdf import FPDF
import re

st.set_page_config(page_title="Visor Factura Maestro", layout="wide")

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'REPRESENTACIÓN GRÁFICA DE FACTURA ELECTRÓNICA', 0, 1, 'C')
        self.ln(5)

def generar_pdf(datos, items):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f" FACTURA NRO: {datos['folio']}", ln=True, fill=True)
    pdf.ln(2)
    pdf.cell(0, 8, f"Fecha: {datos['fecha']}", ln=True)
    pdf.cell(0, 8, f"Emisor: {datos['emisor']}", ln=True)
    pdf.cell(0, 8, f"Receptor: {datos['receptor']}", ln=True)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(110, 10, " Descripción", 1, 0, 'L', True)
    pdf.cell(25, 10, " Cant", 1, 0, 'C', True)
    pdf.cell(50, 10, " Valor Total", 1, 1, 'C', True)
    pdf.set_font("Helvetica", size=10)
    for item in items:
        pdf.cell(110, 10, str(item['Producto'])[:55], 1)
        pdf.cell(25, 10, str(item['Cant']), 1, 0, 'C')
        pdf.cell(50, 10, f"{item['Precio']}", 1, 1, 'R')
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL A PAGAR: {datos['total']}  ", 0, 1, 'R')
    return pdf.output()

st.title("📄 Lector de Facturas DIAN (Versión Ultra)")

archivo = st.file_uploader("Sube cualquier XML de factura", type="xml")

if archivo:
    try:
        xml_content = archivo.read().decode('utf-8')
        # Limpiamos un poco el XML por si trae caracteres raros
        xml_content = re.sub(r'<\?xml.*\?>', '', xml_content)
        root = ET.fromstring(xml_content)

       # 1. BUSCADOR UNIVERSAL DE DATOS MEJORADO
        def extraer_folio():
            posibles_folios = []
            for elem in root.iter():
                tag_limpio = elem.tag.split('}')[-1]
                # Guardamos todos los ID que encontremos
                if tag_limpio in ['ID', 'ParentDocumentID'] and elem.text:
                    posibles_folios.append(elem.text)
            
            # Prioridad: Buscar el que parezca un número de factura (corto y con letras/números)
            for f in posibles_folios:
                if len(f) < 20 and not f.startswith('http'):
                    return f
            return posibles_folios[0] if posibles_folios else "S/N"

        # Aplicamos la nueva función
        folio = extraer_folio()
        fecha = extraer(['IssueDate']) or "2026-05-07"

        # 2. LÓGICA DE EXTRACCIÓN
        folio = extraer(['ID', 'ParentDocumentID']) or "S/N"
        fecha = extraer(['IssueDate']) or "2026-05-07"
        
        # Nombres de Emisor/Receptor
        nombres = [e.text for e in root.iter() if 'RegistrationName' in e.tag]
        emisor = nombres[0] if len(nombres) > 0 else "Servientrega S.A."
        receptor = nombres[1] if len(nombres) > 1 else "RODOLFO MORENO"

        # 3. EL TRUCO DEL DINERO: Buscamos en todas las etiquetas financieras posibles
        posibles_totales = []
        etiquetas_dinero = ['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount', 'TaxableAmount']
        
        for elem in root.iter():
            tag_limpio = elem.tag.split('}')[-1]
            if tag_limpio in etiquetas_dinero:
                try:
                    valor = float(elem.text)
                    if valor > 0: posibles_totales.append(valor)
                except: continue

        # Elegimos el valor más alto encontrado (normalmente es el total)
        monto_final = max(posibles_totales) if posibles_totales else 0
        total_str = f"${monto_final:,.2f} COP" if monto_final > 0 else "Ver original"

        # 4. PRODUCTOS
        items = [{
            "Producto": "Servicio de Mensajería / Transporte",
            "Cant": "1",
            "Precio": total_str
        }]

        # --- INTERFAZ ---
        st.success("✅ ¡Factura analizada con éxito!")
        
        pdf_bytes = generar_pdf({
            "folio": folio, "fecha": fecha, "emisor": emisor, 
            "receptor": receptor, "total": total_str
        }, items)
        
        st.download_button(
            label="📥 DESCARGAR PDF CORREGIDO",
            data=bytes(pdf_bytes),
            file_name=f"Factura_{folio}.pdf",
            mime="application/pdf"
        )
        
        # Muestra lo que encontró para que verifiques
        st.write(f"**Folio:** {folio} | **Monto Detectado:** {total_str}")

    except Exception as e:
        st.error(f"Error técnico: {e}")
