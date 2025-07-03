import streamlit as st
import requests
from docx import Document

# Load Hugging Face API key from secrets
API_TOKEN = st.secrets["huggingface"]["api_key"]

# App title
st.title("🌐 Translate Text File using Meta's NLLB")

# File upload
uploaded_file = st.file_uploader("Upload a .txt file", type=["txt"])

# Language selection
source_lang = st.selectbox("Source Language (ISO)", ["eng", "hin", "fra", "deu", "spa"])
target_lang = st.selectbox("Target Language (ISO)", ["hin", "eng", "fra", "deu", "spa"])

# When file is uploaded
if uploaded_file is not None:
    text = uploaded_file.read().decode("utf-8")

    if st.button("Translate"):
        with st.spinner("Translating..."):
            # Meta's NLLB-200 API
            API_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
            headers = {"Authorization": f"Bearer {API_TOKEN}"}
            payload = {
                "inputs": text,
                "parameters": {
                    "src_lang": source_lang,
                    "tgt_lang": target_lang
                }
            }

            response = requests.post(API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                translated_text = response.json()[0]["translation_text"]

                # Create Word Document
                doc = Document()
                doc.add_heading("Translated Output", 0)
                doc.add_paragraph(translated_text)

                output_file = "translated_output.docx"
                doc.save(output_file)

                with open(output_file, "rb") as f:
                    st.success("✅ Translation completed!")
                    st.download_button(
                        label="Download Translated Word File",
                        data=f,
                        file_name="translated_output.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            else:
                st.error("❌ Error in translation. Try again later.")
