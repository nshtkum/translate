import streamlit as st
import requests
from docx import Document
from docx.shared import Pt
from io import BytesIO

# Load token
API_TOKEN = st.secrets["huggingface"]["api_key"]
API_URL = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

st.title("📄 Word File Translator (Meta AI)")

uploaded_file = st.file_uploader("Upload a Word (.docx) file", type=["docx"])

source_lang = st.selectbox("Source Language (ISO)", ["eng", "hin", "fra", "deu", "spa"])
target_lang = st.selectbox("Target Language (ISO)", ["hin", "eng", "fra", "deu", "spa"])

def translate(text, src, tgt):
    payload = {
        "inputs": text,
        "parameters": {"src_lang": src, "tgt_lang": tgt}
    }
    try:
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()[0]["translation_text"]
    except Exception as e:
        return "[Translation failed]"

if uploaded_file and st.button("Translate and Download"):
    with st.spinner("Translating... Please wait"):
        original_doc = Document(uploaded_file)
        translated_doc = Document()

        for para in original_doc.paragraphs:
            text = para.text.strip()
            if not text:
                translated_doc.add_paragraph("")
                continue

            translated_text = translate(text, source_lang, target_lang)

            new_para = translated_doc.add_paragraph()
            run = new_para.add_run(translated_text)

            # Copy formatting from original run
            if para.runs:
                original_run = para.runs[0]
                run.bold = original_run.bold
                run.italic = original_run.italic
                run.font.size = original_run.font.size or Pt(12)
                run.font.name = original_run.font.name or "Arial"

        # Save in memory
        output = BytesIO()
        translated_doc.save(output)
        output.seek(0)

        st.success("✅ Translation completed!")
        st.download_button(
            label="Download Translated File",
            data=output,
            file_name="translated_output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
