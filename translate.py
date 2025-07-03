import streamlit as st
import requests
from docx import Document
from docx.shared import Pt
from io import BytesIO
import time

# API config
API_URL = "https://bagwkqqw6a6i3e7p.us-east-1.aws.endpoints.huggingface.cloud"
API_TOKEN = st.secrets["huggingface"]["api_key"]
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

st.title("📄 Translate Word File (.docx) with Meta NLLB (Private Endpoint)")

uploaded_file = st.file_uploader("Upload a Word (.docx) file", type=["docx"])
source_lang = st.selectbox("Source Language", ["eng", "hin", "fra", "deu", "spa"])
target_lang = st.selectbox("Target Language", ["hin", "eng", "fra", "deu", "spa"])

def translate(text, src, tgt, max_retries=3, delay=2):
    payload = {
        "inputs": text,
        "parameters": {"src_lang": src, "tgt_lang": tgt}
    }
    for attempt in range(max_retries):
        try:
            r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            if r.status_code == 200:
                return r.json()[0]["translation_text"]
            else:
                st.error(f"Error {r.status_code}: {r.text}")
                break
        except Exception as e:
            st.warning(f"Retry {attempt+1}: {e}")
            time.sleep(delay)
    return "[Translation failed]"

if uploaded_file and st.button("Translate and Download"):
    with st.spinner("Translating document..."):
        original = Document(uploaded_file)
        translated_doc = Document()

        for para in original.paragraphs:
            text = para.text.strip()
            trans_para = translated_doc.add_paragraph()
            if text:
                translated_text = translate(text, source_lang, target_lang)
                run = trans_para.add_run(translated_text)
                if para.runs:
                    r0 = para.runs[0]
                    run.bold = r0.bold
                    run.italic = r0.italic
                    run.font.size = r0.font.size or Pt(12)
                    run.font.name = r0.font.name or "Arial"
            else:
                trans_para.add_run("")

        output = BytesIO()
        translated_doc.save(output)
        output.seek(0)

        st.success("✅ Translation complete!")
        st.download_button(
            label="⬇️ Download Translated .docx",
            data=output,
            file_name="translated_output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
