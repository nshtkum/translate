import streamlit as st
import requests
from docx import Document
from io import BytesIO
import json

# Hugging Face Endpoint Config
API_URL = "https://bagwkqqw6a6i3e7p.us-east-1.aws.endpoints.huggingface.cloud"
HF_TOKEN = st.secrets["huggingface"]["api_key"]  # ✅ FIXED LINE

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# UI
st.title("MB Translate Word File (.docx) using Meta AI")
st.caption("Supports only Indian languages via Meta's `nllb-200` model")

uploaded_file = st.file_uploader("Upload a Word (.docx) file", type=["docx"])

INDIC_LANGS = {
    "English": "eng_Latn",
    "Hindi": "hin_Deva",
    "Marathi": "mar_Deva",
    "Bengali": "ben_Beng",
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
    "Gujarati": "guj_Gujr",
    "Kannada": "kan_Knda",
    "Malayalam": "mal_Mlym",
    "Punjabi": "pan_Guru",
    "Urdu": "urd_Arab",
    "Odia": "ory_Orya"
}

source = st.selectbox("Source Language", list(INDIC_LANGS.keys()), index=0)
target = st.selectbox("Target Language", list(INDIC_LANGS.keys()), index=1)

if uploaded_file:
    doc = Document(uploaded_file)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    st.markdown("### ✍️ Translate & Edit")
    translated_paragraphs = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Translating paragraph {i+1}/{len(paragraphs)}..."):
            payload = {
                "inputs": para,
                "parameters": {
                    "src_lang": INDIC_LANGS[source],
                    "tgt_lang": INDIC_LANGS[target]
                }
            }
            try:
                res = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=30)
                result = res.json()
                translation = result[0]["translation_text"]
            except Exception as e:
                translation = f"[ERROR] {str(e)}"

        edited = st.text_area(f"Para {i+1}", value=translation, height=100)
        translated_paragraphs.append(edited)

    if st.button("📥 Download Translated Word File"):
        final_doc = Document()
        for p in translated_paragraphs:
            final_doc.add_paragraph(p)

        buffer = BytesIO()
        final_doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="Download .docx",
            data=buffer,
            file_name="translated_output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
