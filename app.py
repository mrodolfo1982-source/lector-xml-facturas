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
    
    # Cabecera con fondo gris claro
    pdf.set_fill_color(240, 240, 240)
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
        # Limitar descripción para que no se salga de la celda
        desc = str(item['Producto'])[:55]
        pdf.cell(110, 10, desc, 1)
        pdf.cell(25, 10, str(item['Cant']), 1, 0, 'C')
        pdf.cell(50, 10, f"{item['Precio']}", 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"TOTAL A PAGAR: {datos['total']}  ", 0, 1, 'R')
    return pdf.output()

st.title("📄 Visor de Facturas DIAN (Modo Detective)")
st.markdown("Este visor busca montos ocultos en archivos de Servientrega y otros proveedores.")

archivo = st.file_uploader("Sube tu archivo XML", type="xml")

if archivo:
    try:
        xml_data = archivo.read()
        root = ET.fromstring(xml_data)

        # FUNCIÓN DETECTIVE: Busca cualquier etiqueta que contenga una palabra clave
        def buscar_profundo(lista_keywords):
            for elem in root.iter():
                for key in lista_keywords:
                    if key.lower() in elem.tag.lower() and elem.text:
                        return elem.text
            return None

        # 1. Buscar Folio/ID
        folio = buscar_profundo(['ParentDocumentID', 'ID']) or "S/N"
        
        # 2. Buscar Fecha
        fecha = buscar_profundo(['IssueDate']) or "N/A"
        
        # 3. Buscar Nombres (Emisor y Receptor)
        nombres = [elem.text for elem in root.iter() if 'RegistrationName' in elem.tag]
        emisor = nombres[0] if len(nombres) > 0 else "Servientrega S.A."
        receptor = nombres[1] if len(nombres) > 1 else "RODOLFO MORENO"
        
        # 4. Buscar Total (Intentamos varias etiquetas comunes en Colombia)
        total_val = buscar_profundo(['PayableAmount', 'TaxInclusiveAmount', 'LineExtensionAmount'])
        if total_val:
            try:
                total_final = f"${float(total_val):,.2f} COP"
            except:
                total_final = f"{total_val} COP"
        else:
            total_final = "Consultar soporte físico"

        # 5. Buscar Productos
        items = []
        encontro_lineas = False
        for line in root.iter():
            if 'InvoiceLine' in line.tag or 'CreditNoteLine' in line.tag:
                encontro_lineas = True
                desc = "Descripción no hallada"
                for sub in line.iter():
                    if 'Description' in sub.tag:
                        desc = sub.text
                items.append({
                    "Producto": desc,
                    "Cant": "1",
                    "Precio": total_final
                })

        if not encontro_lineas:
            items.append({
                "Producto": "Servicio registrado en AttachedDocument (Ver XML)",
                "Cant": "1",
                "Precio": total_final
            })

        # --- INTERFAZ ---
        st.success(f"✅ Factura {folio} procesada con éxito")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Monto Detectado", total_final)
            st.write(f"**Emisor:** {emisor}")
            st.write(f"**Receptor:** {receptor}")
        
        with col2:
            # Generar PDF
            pdf_bytes = generar_pdf({
                "folio": folio, "fecha": fecha, "emisor": emisor, 
                "receptor": receptor, "total": total_final
            }, items)
            
            st.download_button(
                label="📥 Descargar Representación PDF",
                data=bytes(pdf_bytes),
                file_name=f"Factura_{folio}.pdf",
                mime="application/pdf"
            )

        st.subheader("Detalle de la Operación")
        st.table(pd.DataFrame(items))

        # OPCIONAL: Ver el XML crudo por si quieres investigar más (útil para tu aprendizaje de datos)
        with st.expander("Ver contenido técnico del XML (Modo Programador)"):
            st.code(xml_data.decode('utf-8'), language='xml')

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
