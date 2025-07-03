import streamlit as st
import requests
from docx import Document
from docx.shared import Pt
from io import BytesIO
import time

# Load API token from secrets
API_TOKEN = st.secrets["huggingface"]["api_key"]

# Replace this with your Hosted Inference Endpoint URL
API_URL = "https://<your-endpoint>.eu-west-1.aws.endpoints.huggingface.cloud/facebook--nllb-200-distilled-600M"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# UI
st.title("🌍 Translate Word (.docx) File using Meta AI (NLLB-200)")
uploaded_file = st.file_uploader("Upload a Word (.docx) file", type=["docx"])

source_lang = st.selectbox("From Language (ISO code)", ["eng", "hin", "fra", "deu", "spa"])
target_lang = st.selectbox("To Language (ISO code)", ["hin", "eng", "fra", "deu", "spa"])

# Translation function with retry
def translate(text, src, tgt, max_retries=3, delay=2):
    payload = {
        "inputs": text,
        "parameters": {"src_lang": src, "tgt_lang": tgt}
    }
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()[0]["translation_text"]
            elif response.status_code == 503:
                time.sleep(delay)
            else:
                st.warning(f"API Error {response.status_code}: {response.text}")
                break
        except Exception as e:
            st.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    return "[Translation failed]"

# When user clicks translate
if uploaded_file and st.button("Translate and Download"):
    with st.spinner("Translating... Please wait"):
        original_doc = Document(uploaded_file)
        translated_doc = Document()

        for para in original_doc.paragraphs:
            text = para.text.strip()
            translated_para = translated_doc.add_paragraph()

            if text:
                translated_text = translate(text, source_lang, target_lang)
                run = translated_para.add_run(translated_text)

                # Preserve basic formatting
                if para.runs:
                    orig_run = para.runs[0]
                    run.bold = orig_run.bold
                    run.italic = orig_run.italic
                    run.font.size = orig_run.font.size or Pt(12)
                    run.font.name = orig_run.font.name or "Arial"
            else:
                translated_para.add_run("")

        output = BytesIO()
        translated_doc.save(output)
        output.seek(0)

        st.success("✅ Translation complete!")
        st.download_button(
            label="⬇️ Download Translated .docx File",
            data=output,
            file_name="translated_output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
