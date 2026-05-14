import os
import json
import pandas as pd
from PyPDF2 import PdfReader
from openai import OpenAI
from supabase import create_client, Client

# ==========================================
# CONFIG & CREDENTIALS
# ==========================================
SUPABASE_URL = "https://nzofdwwcouzfpacapvmz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56b2Zkd3djb3V6ZnBhY2Fwdm16Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTg5NDE5OCwiZXhwIjoyMDkxNDcwMTk4fQ.YB0xsa4EOKjK0O3Vtgi23ffVdU3yAeEzPeW503Tqi4I"

TARGET_COMPANY_ID = "EIH"
ROOT_FOLDER = "../Raw Data Extraction/EIH_Limited"

# ==========================================
# CLIENTS
# ==========================================
llm_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1 -> READ & CHUNK
# ==========================================
def extract_text(filepath):
    ext = filepath.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            for page in PdfReader(filepath).pages: text += page.extract_text() + "\n"
        elif ext == 'csv': text = pd.read_csv(filepath).to_string()
        elif ext == 'txt': text = open(filepath, 'r', encoding='utf-8').read()
    except Exception as e: print(f"[-] Read fail {filepath}: {e}")
    return text

def chunk_text(text, chunk_size=1500): # SMALL CHUNK FOR SMALL BRAIN
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# ==========================================
# 2 -> LOCAL LLM EXTRACTION
# ==========================================
def analyze_chunk(chunk, filename):
    prompt = """Extract facts, metrics, guidance, risks.
RULES:
1 -> Output ONLY JSON array of objects.
2 -> Each object MUST have 'target_table' and 'data'.
3 -> target_table = 'financials', 'guidance_claims', 'risk_flags', 'credit_ratings', or 'raw_data'.
Example: [{"target_table": "financials", "data": {"metric": "revenue", "value": 500}}]"""
    try:
        response = llm_client.chat.completions.create(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Doc: {filename}\nText:\n{chunk}"}
            ],
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        
        # fix json if model wrap in dict
        if isinstance(parsed, dict) and 'data' in parsed and isinstance(parsed['data'], list): return parsed['data']
        elif isinstance(parsed, list): return parsed
        return []
    except Exception as e:
        print(f"[-] LLM fail {filename}: {e}")
        return []

# ==========================================
# 3 -> CLEAN & PUSH TO DB
# ==========================================
def sanitize_insert(items, filename):
    if not items: return
    for item in items:
        table = item.get("target_table")
        data = item.get("data", {})

        # Force keys
        data["company_id"] = TARGET_COMPANY_ID
        data["source_document"] = filename

        # Fix Not-Null constraints
        if table == 'credit_ratings': data['rating_agency'] = data.get('rating_agency') or 'Unknown'
        elif table == 'financials':
            data['metric'] = data.get('metric') or 'Unknown'
            data['period'] = data.get('period') or 'Unknown'
        elif table == 'guidance_claims':
            data['metric_type'] = data.get('metric_type') or 'Unknown'
            data['verbatim_quote'] = data.get('verbatim_quote') or 'Missing'
        elif table == 'risk_flags':
            data['description'] = data.get('description') or 'Missing'
            valid = ['debt', 'governance', 'operational', 'regulatory', 'auditor', 'supply_overhang', 'margin_compression', 'management_mismatch', 'key_person']
            if data.get('category') not in valid: data['category'] = 'operational'

        # Push to Supabase
        valid_tables = ['financials', 'guidance_claims', 'risk_flags', 'credit_ratings', 'raw_data']
        if table in valid_tables:
            try:
                supabase.table(table).insert(data).execute()
                print(f"[+] Insert OK -> {table}")
            except Exception as e: 
                print(f"[-] Insert fail -> {table}: {e}")

# ==========================================
# 4 -> MAIN ENGINE
# ==========================================
def run():
    print(f"🚀 Start Local Qwen -> {TARGET_COMPANY_ID}")
    for root, dirs, files in os.walk(ROOT_FOLDER):
        if 'Annual_Reports' in root: continue # Skip big books
        for file in files:
            if file.endswith(('.pdf', '.csv', '.txt')):
                path = os.path.join(root, file)
                print(f"\n📂 File -> {file}")
                
                text = extract_text(path)
                if not text.strip(): continue
                
                chunks = chunk_text(text)
                print(f"   -> {len(chunks)} chunks")
                
                for i, chunk in enumerate(chunks):
                    print(f"   -> LLM eat chunk {i+1}/{len(chunks)}")
                    items = analyze_chunk(chunk, file)
                    sanitize_insert(items, file)

if __name__ == "__main__":
    run()