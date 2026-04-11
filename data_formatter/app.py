import os, json
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader
import docx # for .docx
from openai import OpenAI
from supabase import create_client, Client

# ==========================================
# CONFIG
# ==========================================
SUPABASE_URL = "https://nzofdwwcouzfpacapvmz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56b2Zkd3djb3V6ZnBhY2Fwdm16Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTg5NDE5OCwiZXhwIjoyMDkxNDcwMTk4fQ.YB0xsa4EOKjK0O3Vtgi23ffVdU3yAeEzPeW503Tqi4I"

TARGET_COMPANY = "EIH"
ROOT_FOLDER = "../Raw Data Extraction/EIH_Limited"

llm_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1 -> EXTRACT
# ==========================================
def read_text(path):
    ext = path.lower().split('.')[-1]
    txt = ""
    try:
        if ext == 'pdf':
            for p in PdfReader(path).pages: txt += p.extract_text() + "\n"
        elif ext == 'csv': txt = pd.read_csv(path).to_string()
        elif ext == 'txt': txt = open(path, 'r', encoding='utf-8').read()
        elif ext == 'docx': 
            doc = docx.Document(path)
            txt = "\n".join([p.text for p in doc.paragraphs])
    except Exception as e: return f"Error: {e}"
    return txt

def chunk_text(text, size=3000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# ==========================================
# 2 -> LLM
# ==========================================
def ask_llm(chunk, filename):
    prompt = """Extract facts, metrics, guidance, risks.
RULES:
1 -> Output ONLY JSON array of objects.
2 -> Keys must be: target_table, data.
3 -> target_table = 'financials', 'guidance_claims', 'risk_flags', 'credit_ratings', or 'raw_data'."""
    try:
        res = llm_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Doc: {filename}\nText:\n{chunk}"}
            ],
            response_format={"type": "json_object"}
        )
        raw = res.choices[0].message.content
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and 'data' in parsed and isinstance(parsed['data'], list): return raw, parsed['data']
        elif isinstance(parsed, list): return raw, parsed
        return raw, []
    except Exception as e:
        return str(e), []

# ==========================================
# 3 -> SANITIZE (NO PUSH TO DB YET - JUST SHOW)
# ==========================================
def clean_data(items, filename):
    clean = []
    if not items: return clean
    for i in items:
        table = i.get("target_table")
        d = i.get("data", {})
        d["company_id"] = TARGET_COMPANY
        d["source_document"] = filename
        
        if table == 'credit_ratings': d['rating_agency'] = d.get('rating_agency') or 'Unknown'
        elif table == 'financials':
            d['metric'] = d.get('metric') or 'Unknown'
            d['period'] = d.get('period') or 'Unknown'
        elif table == 'risk_flags':
            d['description'] = d.get('description') or 'Missing'
            if d.get('category') not in ['debt', 'governance', 'operational', 'regulatory', 'auditor', 'supply_overhang', 'margin_compression']: 
                d['category'] = 'operational'
        clean.append({"table": table, "data": d})
    return clean

# ==========================================
# FRONTEND UI (STREAMLIT)
# ==========================================
st.set_page_config(layout="wide")
st.title("🦣 Caveman Data Pipeline Visualizer")

if st.button("🚀 Start Engine"):
    for root, dirs, files in os.walk(ROOT_FOLDER):
        if 'Annual_Reports' in root: continue
        
        for f in files:
            if f.endswith(('.pdf', '.csv', '.txt', '.docx')):
                path = os.path.join(root, f)
                
                with st.expander(f"📁 {f}", expanded=True):
                    txt = read_text(path)
                    if not txt.strip(): 
                        st.warning("Empty file.")
                        continue
                        
                    chunks = chunk_text(txt)
                    st.info(f"Chunks -> {len(chunks)}")
                    
                    for i, c in enumerate(chunks):
                        st.markdown(f"### Chunk {i+1}")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.caption("Raw Text in")
                            st.code(c[:500] + "...[TRUNCATED]", language="text")
                            
                        with col2:
                            st.caption("LLM Raw JSON out")
                            raw_str, parsed_items = ask_llm(c, f)
                            st.code(raw_str, language="json")
                            
                        with col3:
                            st.caption("Clean DB Ready Data")
                            clean_items = clean_data(parsed_items, f)
                            st.json(clean_items)
                            
                            # UNCOMMENT TO ACTUALLY PUSH TO SUPABASE
                            for item in clean_items:
                                supabase.table(item['table']).insert(item['data']).execute()