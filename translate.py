import streamlit as st
import requests
from docx import Document
from docx.shared import Pt
from io import BytesIO
import time

# API config
API_URL = "https://uu149rez6gw9ehej.eu-west-1.aws.endpoints.huggingface.cloud/facebook--nllb-200-distilled-600M"
API_TOKEN = st.secrets["huggingface"]["api_key"]
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

st.title("📄 Translate Word File (.docx) via Meta AI (Hosted Endpoint)")

uploaded_file = st.file_uploader("Upload a Word (.docx) file", type=["docx"])

source_lang = st.selectbox("Source Language", ["eng", "hin", "fra", "deu", "spa"])
target_lang = st.selectbox("Target Language", ["hin", "eng", "fra", "deu", "spa"])

# Translation with error logging
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
            elif response.status_code in [401, 403, 404]:
                st.error(f"Authorization or endpoint error: {response.status_code}\n{response.text}")
                break
            elif response.status_code == 503:
                st.warning("Model is loading... retrying.")
                time.sleep(delay)
            else:
                st.error(f"Unexpected error {response.status_code}: {response.text}")
                break
        except Exception as e:
            st.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    return "[Translation failed]"

if uploaded_file and st.button("Translate and Download"):
    with st.spinner("Translating paragraphs... please wait."):
        original = Document(uploaded_file)
        translated_doc = Document()

        for para in original.paragraphs:
            text = para.text.strip()
            target_para = translated_doc.add_paragraph()

            if text:
                translated = translate(text, source_lang, target_lang)
                run = target_para.add_run(translated)
                if para.runs:
                    orig_run = para.runs[0]
                    run.bold = orig_run.bold
                    run.italic = orig_run.italic
                    run.font.size = orig_run.font.size or Pt(12)
                    run.font.name = orig_run.font.name or "Arial"
            else:
                target_para.add_run("")

        # Output doc
        output = BytesIO()
        translated_doc.save(output)
        output.seek(0)

        st.success("✅ Done!")
        st.download_button(
            "⬇️ Download Translated File",
            data=output,
            file_name="translated_output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
