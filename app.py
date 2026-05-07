import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Lector Factura DIAN", page_icon="🇨🇴")

st.title("🇨🇴 Visor de AttachedDocument (DIAN)")
st.markdown("Extrae información de archivos XML de facturación electrónica en Colombia.")

# Definición de Namespaces estándar de la DIAN / UBL 2.1
NS = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    'ds': 'http://www.w3.org/2000/09/xmldsig#',
    'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
    'none': 'urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2'
}

uploaded_file = st.file_uploader("Sube tu archivo XML", type="xml")

if uploaded_file:
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()

        # 1. Información General del Contenedor
        document_id = root.find("cbc:ID", NS).text if root.find("cbc:ID", NS) is not None else "N/A"
        issue_date = root.find("cbc:IssueDate", NS).text if root.find("cbc:IssueDate", NS) is not None else "N/A"

        # 2. Extraer el Emisor (Sender)
        sender_name = root.find(".//cac:SenderParty//cbc:RegistrationName", NS)
        sender_nit = root.find(".//cac:SenderParty//cbc:CompanyID", NS)

        # 3. Extraer el Receptor (Receiver)
        receiver_name = root.find(".//cac:ReceiverParty//cbc:RegistrationName", NS)
        receiver_nit = root.find(".//cac:ReceiverParty//cbc:CompanyID", NS)

        # Mostrar Resultados en Streamlit
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Datos de Envío")
            st.write(f"**Folio:** {document_id}")
            st.write(f"**Fecha Emisión:** {issue_date}")
        
        with col2:
            st.subheader("Entidades")
            st.success(f"**Emisor:** {sender_name.text if sender_name is not None else 'No hallado'}")
            st.info(f"**Receptor:** {receiver_name.text if receiver_name is not None else 'No hallado'}")

        # 4. Sección técnica para desarrolladores
        with st.expander("Ver XML estructurado"):
            xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
            st.code(xml_str, language='xml')

    except Exception as e:
        st.error(f"Error al procesar: {e}")
        st.info("Asegúrate de que es un archivo AttachedDocument válido de la DIAN.")