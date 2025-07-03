import streamlit as st
import requests
from docx import Document
from io import BytesIO
import json
import time
import re # Added for more robust cleaning

# Configuration
API_URL = "https://bagwkqqw6a6i3e7p.us-east-1.aws.endpoints.huggingface.cloud"
# Ensure you have HF_TOKEN in your Streamlit secrets
HF_TOKEN = st.secrets["huggingface"]["api_key"]
headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Language mapping
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

# Style prompts (kept for UI but not used in the API call)
STYLE_PROMPTS = {
    "formal": "",
    "conversational": "Translate in a natural, conversational style as people speak in daily life. Avoid overly formal or literary language.",
    "casual": "Translate in a casual, friendly tone using common everyday words that people use in normal conversation.",
    "simple": "Use simple, easy-to-understand words that are commonly used in everyday speech."
}

# --- FIX 1: Correct the preprocessing function ---
def preprocess_text(text, style="conversational"):
    """
    Prepares text for the translation model.
    FIX: Style instructions are no longer prepended. The NLLB model is a direct
    translation model and does not interpret natural language style prompts.
    Instead, it often translates the prompt itself, leading to the error you saw.
    Translation style is primarily influenced by the model's training data and
    parameters like 'temperature'.
    """
    return text.strip()

def translate_text(text, source_lang, target_lang, style="conversational", max_retries=3):
    """Translate text with retry logic and style enhancement"""
    if not text.strip():
        return text

    # The text is no longer modified with style instructions.
    processed_text = preprocess_text(text, style)

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

            if isinstance(result, list) and len(result) > 0:
                translation = result[0].get("translation_text", "")
                # --- FIX 3: Pass original text to the new cleaning function ---
                # Pass the original `text` for more accurate cleaning.
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

    return "[ERROR] Translation failed"

# --- FIX 2: Implement a more robust cleaning function ---
def clean_translation(translation, original_text):
    """
    Cleans the raw output from the translation model.
    FIX: This function no longer tries to remove the English prompt from the
    translated text. Instead, it removes common artifacts like the model
    echoing the original input or adding boilerplate labels.
    """
    if not translation:
        return ""

    cleaned = translation.strip()

    # 1. Remove the original text if the model echoes it at the beginning.
    # This is safer than a simple .replace().
    if cleaned.startswith(original_text):
        cleaned = cleaned[len(original_text):].strip()

    # 2. Use regex to remove common prefixes/labels (e.g., "Translation:", "hin_Deva:")
    # that the model might add. This is more flexible than a fixed list.
    cleaned = re.sub(r'^[A-Za-z_]+\s*:\s*', '', cleaned)

    # 3. Final normalization of whitespace to ensure clean output.
    cleaned = " ".join(cleaned.split())

    return cleaned

def extract_text_from_docx(uploaded_file):
    """Extract text from docx file with better structure preservation"""
    doc = Document(uploaded_file)
    content = []
    
    for element in doc.element.body:
        if element.tag.endswith('p'):
            para_text = ""
            for run in element.itertext():
                para_text += run
            if para_text.strip():
                content.append(("paragraph", para_text.strip()))
        elif element.tag.endswith('tbl'):
            # This logic can be expanded to handle table text extraction if needed
            content.append(("table", "[Table content - manual review needed]"))
    
    return content

# Streamlit UI
st.set_page_config(
    page_title="Document Translator",
    page_icon="🌐",
    layout="wide"
)

# Initialize session state
if 'translating' not in st.session_state:
    st.session_state.translating = False
if 'translated_paragraphs' not in st.session_state:
    st.session_state.translated_paragraphs = []
if 'current_paragraph' not in st.session_state:
    st.session_state.current_paragraph = 0
if 'translation_in_progress' not in st.session_state:
    st.session_state.translation_in_progress = False

st.title("Indian Language Document Translator")
st.write("Translate Word documents between Indian languages using Meta's NLLB-200 model")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Settings")
    uploaded_file = st.file_uploader("Choose a Word document", type=["docx"])
    source = st.selectbox("From Language", list(INDIC_LANGS.keys()), index=0)
    target = st.selectbox("To Language", list(INDIC_LANGS.keys()), index=1)
    style = st.selectbox("Translation Style", ["conversational", "casual", "simple", "formal"], index=0)
    
with col2:
    st.subheader("Translation")
    
    if uploaded_file is not None:
        try:
            content = extract_text_from_docx(uploaded_file)
            paragraphs = [item[1] for item in content if item[0] == "paragraph"]
            
            if not paragraphs:
                st.warning("No text content found in the document.")
                st.stop()
            
            # Use a separate key for the button to prevent state issues
            start_button = st.button("Start Translation", key="start_translating")

            if start_button and not st.session_state.translating:
                st.session_state.translating = True
                st.session_state.translated_paragraphs = [""] * len(paragraphs)
                st.session_state.current_paragraph = 0
                st.session_state.translation_in_progress = True
                st.rerun()

            # Display translations
            edited_translations = st.session_state.translated_paragraphs[:]
            
            if paragraphs:
                st.info(f"Found {len(paragraphs)} paragraphs. Please review each translation.")
            
            for i, paragraph in enumerate(paragraphs):
                st.markdown(f"**Original Paragraph {i+1}:**")
                st.write(paragraph)
                
                # Use the stored list for edited values
                edited_translations[i] = st.text_area(
                    f"Translation {i+1}:",
                    value=st.session_state.translated_paragraphs[i],
                    height=100,
                    key=f"trans_{i}",
                    placeholder="Translation will appear here..."
                )
                st.markdown("---")
            
            # After the loop, update the session state with the edited values
            st.session_state.translated_paragraphs = edited_translations

            # Translation process
            if st.session_state.translating and st.session_state.current_paragraph < len(paragraphs):
                current_idx = st.session_state.current_paragraph
                
                progress = (current_idx + 1) / len(paragraphs)
                st.progress(progress, text=f"Translating paragraph {current_idx + 1} of {len(paragraphs)}")

                translation = translate_text(
                    paragraphs[current_idx],
                    INDIC_LANGS[source],
                    INDIC_LANGS[target],
                    style
                )
                
                st.session_state.translated_paragraphs[current_idx] = translation
                st.session_state.current_paragraph += 1
                
                if st.session_state.current_paragraph >= len(paragraphs):
                    st.session_state.translating = False
                    st.session_state.translation_in_progress = False
                    st.success("Translation completed!")
                
                time.sleep(0.5) # Small delay to allow UI to update
                st.rerun()
            
            # Download button
            if not st.session_state.translation_in_progress and any(st.session_state.translated_paragraphs):
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
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            # Reset state on error
            st.session_state.translating = False
            st.session_state.translation_in_progress = False

    else:
        st.info("Please upload a Word document to begin translation.")

# Footer
st.markdown("---")
st.markdown(
    """
    **Tips for better translations:**
    - While style options are available, the underlying model may produce formal language.
    - Always review and edit translations for accuracy and context.
    - For highly technical or specific domains, manual editing is recommended.
    """
)
