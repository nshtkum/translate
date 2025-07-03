import streamlit as st
import requests
from docx import Document
from io import BytesIO
import json
import time

# Configuration
API_URL = "https://bagwkqqw6a6i3e7p.us-east-1.aws.endpoints.huggingface.cloud"
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

# Style prompts
STYLE_PROMPTS = {
    "formal": "",
    "conversational": "Translate in a natural, conversational style as people speak in daily life. Avoid overly formal or literary language.",
    "casual": "Translate in a casual, friendly tone using common everyday words that people use in normal conversation.",
    "simple": "Use simple, easy-to-understand words that are commonly used in everyday speech."
}

def preprocess_text(text, style="conversational"):
    if style != "formal" and text.strip():
        instruction = STYLE_PROMPTS[style]
        return f"{instruction}\n\nText to translate: {text}"
    return text

def translate_text(text, source_lang, target_lang, style="conversational", max_retries=3):
    if not text.strip():
        return text
    
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
                return clean_translation(translation, style)
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

def clean_translation(translation, style):
    if not translation:
        return translation
    
    for prompt in STYLE_PROMPTS.values():
        if prompt and prompt in translation:
            translation = translation.replace(prompt, "")
    
    prefixes_to_remove = [
        "Text to translate:",
        "Translation:",
        "Translated text:",
        "Output:"
    ]
    
    for prefix in prefixes_to_remove:
        if translation.startswith(prefix):
            translation = translation[len(prefix):].strip()
    
    return translation.strip()

def extract_text_from_docx(uploaded_file):
    doc = Document(uploaded_file)
    content = []
    
    for element in doc.element.body:
        if element.tag.endswith('p'):
            para_text = ""
            for run in element:
                if run.text:
                    para_text += run.text
            if para_text.strip():
                content.append(("paragraph", para_text.strip()))
        elif element.tag.endswith('tbl'):
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
    batch_size = st.slider("Batch Size", min_value=1, max_value=10, value=3)

with col2:
    st.subheader("Translation")
    
    if uploaded_file is not None:
        try:
            content = extract_text_from_docx(uploaded_file)
            paragraphs = [item[1] for item in content if item[0] == "paragraph"]
            
            if not paragraphs:
                st.warning("No text content found in the document.")
                st.stop()
            
            st.info(f"Found {len(paragraphs)} paragraphs to translate")
            
            # Translate button
            if st.button("Start Translation") and not st.session_state.translating:
                st.session_state.translating = True
                st.session_state.translated_paragraphs = []
                st.session_state.current_paragraph = 0
                st.session_state.translation_in_progress = True
                st.rerun()

            # Display translations
            edited_translations = []
            for i, paragraph in enumerate(paragraphs):
                st.markdown(f"**Original Paragraph {i+1}:**")
                st.write(paragraph)
                
                current_translation = st.session_state.translated_paragraphs[i] if i < len(st.session_state.translated_paragraphs) else ""
                
                if st.session_state.translating:
                    if i < st.session_state.current_paragraph:
                        status = "✅ Completed"
                    elif i == st.session_state.current_paragraph:
                        status = "⏳ Translating..."
                    else:
                        status = "⏸️ Pending"
                    st.caption(f"Status: {status}")
                
                edited_translation = st.text_area(
                    f"Translation {i+1}:",
                    value=current_translation,
                    height=100,
                    key=f"trans_{i}",
                    placeholder="Translation will appear here..."
                )
                
                edited_translations.append(edited_translation)
                st.markdown("---")
            
            # Translation process
            if st.session_state.translating and st.session_state.current_paragraph < len(paragraphs):
                current_idx = st.session_state.current_paragraph
                
                with st.container():
                    progress = current_idx / len(paragraphs)
                    st.progress(progress)
                    st.info(f"Translating paragraph {current_idx + 1} of {len(paragraphs)}")
                
                translation = translate_text(
                    paragraphs[current_idx], 
                    INDIC_LANGS[source], 
                    INDIC_LANGS[target],
                    style
                )
                
                if len(st.session_state.translated_paragraphs) <= current_idx:
                    st.session_state.translated_paragraphs.extend([""] * (current_idx + 1 - len(st.session_state.translated_paragraphs)))
                
                st.session_state.translated_paragraphs[current_idx] = translation
                st.session_state.current_paragraph += 1
                
                if st.session_state.current_paragraph < len(paragraphs):
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.translating = False
                    st.session_state.translation_in_progress = False
                    st.success("Translation completed!")
                    st.rerun()
                
            # Download button
            if len(st.session_state.translated_paragraphs) == len(paragraphs) and not st.session_state.translation_in_progress:
                if st.button("Download Translated Document", type="primary"):
                    final_doc = Document()
                    for translation in edited_translations:
                        if translation.strip():
                            final_doc.add_paragraph(translation)
                    
                    buffer = BytesIO()
                    final_doc.save(buffer)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="Download Word File",
                        data=buffer.getvalue(),
                        file_name=f"translated_{source}_to_{target}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
        
        except Exception as e:
            st.error(f"Error processing document: {str(e)}")
    else:
        st.info("Please upload a Word document to begin translation.")

# Footer
st.markdown("---")
st.markdown(
    """
    **Tips for better translations:**
    - Use 'conversational' or 'casual' style for natural everyday language
    - Review and edit translations for accuracy
    - Consider context when editing technical or domain-specific terms
    """
)
