import streamlit as st
import requests
from docx import Document
from io import BytesIO
import json
import time
import re

# --- Configuration ---
# Ensure you have HF_TOKEN in your Streamlit secrets
# The secrets.toml file should look like this:
# [huggingface]
# api_key = "hf_YOUR_HUGGINGFACE_TOKEN"

API_URL = "https://bagwkqqw6a6i3e7p.us-east-1.aws.endpoints.huggingface.cloud"
try:
    HF_TOKEN = st.secrets["huggingface"]["api_key"]
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
except (KeyError, FileNotFoundError):
    st.error("Hugging Face API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()


# --- Language and Style Definitions ---
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
    "Odia": "ory_Orya",
    "Assamese": "asm_Beng",
    "Nepali": "nep_Deva"
}

STYLE_PROMPTS = {
    "formal": "",
    "conversational": "Translate in a natural, conversational style.",
    "casual": "Translate in a casual, friendly tone.",
    "simple": "Use simple, easy-to-understand words."
}


# --- Core Functions ---

def preprocess_text(text):
    """
    Prepares text for the translation model. Style instructions are not prepended
    as the NLLB model does not use them and often translates the prompt itself.
    """
    return text.strip()

def clean_translation(translation, original_text):
    """
    Cleans the raw output from the translation model by removing artifacts
    like echoed input text or boilerplate labels.
    """
    if not translation:
        return ""

    cleaned = translation.strip()

    # Remove the original text if the model echoes it at the beginning
    if cleaned.startswith(original_text):
        cleaned = cleaned[len(original_text):].strip()

    # Use regex to remove common prefixes/labels (e.g., "Translation:")
    cleaned = re.sub(r'^[A-Za-z_]+\s*:\s*', '', cleaned)

    # Final normalization of whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned

def translate_text(text, source_lang, target_lang, max_retries=3):
    """Translate text using the API, with retry logic."""
    if not text.strip():
        return ""

    processed_text = preprocess_text(text)

    payload = {
        "inputs": processed_text,
        "parameters": {
            "src_lang": source_lang,
            "tgt_lang": target_lang,
            "max_length": 512,
            "temperature": 0.7,
            "do_sample": True
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=45
            )
            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and result:
                translation = result[0].get("translation_text", "")
                cleaned_translation = clean_translation(translation, text)
                return cleaned_translation
            else:
                return "[ERROR] Unexpected response format"

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return "[ERROR] Translation timeout"
        except requests.exceptions.RequestException as e:
            return f"[ERROR] Network error: {str(e)}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    return "[ERROR] Translation failed after multiple retries"

def extract_text_from_docx(uploaded_file):
    """
    Extracts text from a .docx file paragraph by paragraph using the reliable
    high-level python-docx API to prevent text duplication.
    """
    try:
        doc = Document(uploaded_file)
        content = []
        for para in doc.paragraphs:
            if para.text.strip():
                content.append(para.text.strip())
        return content
    except Exception as e:
        st.error(f"Could not read the document. It may be corrupted. Error: {e}", icon="📄")
        return []


# --- Streamlit UI ---
st.set_page_config(page_title="Document Translator", page_icon="🌐", layout="wide")

# Initialize session state
if 'translating' not in st.session_state:
    st.session_state.translating = False
if 'translated_paragraphs' not in st.session_state:
    st.session_state.translated_paragraphs = []
if 'current_paragraph' not in st.session_state:
    st.session_state.current_paragraph = 0

st.title("Indian Language Document Translator 🇮🇳")
st.write("Translate Word documents between Indian languages using Meta's NLLB-200 model.")

col1, col2 = st.columns([1, 2])

# --- Left Column (Settings) ---
with col1:
    st.subheader("Settings")
    uploaded_file = st.file_uploader("1. Choose a Word document", type=["docx"])
    source_lang_name = st.selectbox("2. From Language", list(INDIC_LANGS.keys()), index=0)
    target_lang_name = st.selectbox("3. To Language", list(INDIC_LANGS.keys()), index=1)
    # Style dropdown is kept for potential future use but does not affect the current model
    style = st.selectbox("Translation Style (Note: model may default to formal)", list(STYLE_PROMPTS.keys()), index=0)

# --- Right Column (Translation) ---
with col2:
    st.subheader("Translation")

    if uploaded_file:
        paragraphs = extract_text_from_docx(uploaded_file)

        if not paragraphs:
            st.warning("No text found in the document or the file could not be read.", icon="⚠️")
        else:
            st.info(f"Found {len(paragraphs)} paragraphs. Click below to start.", icon="💡")

            start_button = st.button("Start Translation", key="start_translating", type="primary")

            if start_button and not st.session_state.translating:
                st.session_state.translating = True
                st.session_state.translated_paragraphs = [""] * len(paragraphs)
                st.session_state.current_paragraph = 0
                st.rerun()

            # --- Translation Process Logic ---
            if st.session_state.translating:
                current_idx = st.session_state.current_paragraph
                if current_idx < len(paragraphs):
                    progress = (current_idx + 1) / len(paragraphs)
                    st.progress(progress, text=f"Translating paragraph {current_idx + 1} of {len(paragraphs)}...")

                    translation = translate_text(
                        paragraphs[current_idx],
                        INDIC_LANGS[source_lang_name],
                        INDIC_LANGS[target_lang_name]
                    )

                    st.session_state.translated_paragraphs[current_idx] = translation
                    st.session_state.current_paragraph += 1
                    time.sleep(0.5)  # Small delay for UI update
                    st.rerun()
                else:
                    st.session_state.translating = False
                    st.success("Translation complete! You can now review and download.", icon="✅")
                    st.rerun()

            # --- Display and Edit Results ---
            if st.session_state.translated_paragraphs:
                edited_translations = st.session_state.translated_paragraphs[:]

                for i, (original_para, translated_para) in enumerate(zip(paragraphs, st.session_state.translated_paragraphs)):
                    st.markdown(f"---")
                    st.markdown(f"**Original Paragraph {i+1}:**")
                    st.write(original_para)

                    edited_translations[i] = st.text_area(
                        f"**Translation {i+1}:**",
                        value=translated_para,
                        height=100,
                        key=f"trans_{i}"
                    )
                st.session_state.translated_paragraphs = edited_translations

                # --- Download Button ---
                if not st.session_state.translating:
                    final_doc = Document()
                    for translation in st.session_state.translated_paragraphs:
                        if translation.strip():
                            final_doc.add_paragraph(translation)

                    buffer = BytesIO()
                    final_doc.save(buffer)
                    buffer.seek(0)

                    st.download_button(
                        label="Download Translated Document",
                        data=buffer.getvalue(),
                        file_name=f"translated_{uploaded_file.name}",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary"
                    )

    else:
        st.info("Please upload a Word document to begin translation.")

# --- Footer ---
st.markdown("---")
st.markdown("Developed with Streamlit and Hugging Face.")
