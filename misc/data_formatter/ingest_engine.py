import os
import json
import time
import pandas as pd
from PyPDF2 import PdfReader
from openai import OpenAI  # <-- NEW: Import OpenAI
from supabase import create_client, Client

# ==========================================
# CONFIGURATION & CREDENTIALS
# ==========================================
FEATHERLESS_API_KEY = "rc_6bfc881d20932f68c74f2a1b50a8f1f309ea2bbcef7fb7d90c5cd203f91de560" # <-- Add your Featherless Key
SUPABASE_URL = "https://nzofdwwcouzfpacapvmz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im56b2Zkd3djb3V6ZnBhY2Fwdm16Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTg5NDE5OCwiZXhwIjoyMDkxNDcwMTk4fQ.YB0xsa4EOKjK0O3Vtgi23ffVdU3yAeEzPeW503Tqi4I"

TARGET_COMPANY_ID = "EIH"  
ROOT_FOLDER = "D:\Projects\datahack-the big leagues\Raw Data Extraction\EIH_Limited" 

# Initialize Clients
# <-- NEW: Initialize Featherless client using OpenAI library
llm_client = OpenAI(
    base_url="https://api.featherless.ai/v1",
    api_key=FEATHERLESS_API_KEY
)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1. FILE PARSING & CHUNKING
# ==========================================
def extract_text_from_file(filepath):
    """Extracts text based on file extension."""
    ext = filepath.lower().split('.')[-1]
    text = ""
    try:
        if ext == 'pdf':
            reader = PdfReader(filepath)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif ext == 'csv':
            df = pd.read_csv(filepath)
            text = df.to_string() # Convert tabular data to string for LLM
        elif ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print(f"[-] Error reading {filepath}: {e}")
    return text

def chunk_text(text, chunk_size=3500):
    """Splits text into manageable chunks for the LLM."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# ==========================================
# 2. LLM EXTRACTION (FEATHERLESS)
# ==========================================
def analyze_chunk_with_llm(chunk, filename):
    """Sends chunk to Featherless (Gemma 3) and forces strictly formatted JSON array."""
    system_prompt = """You are a ruthless equity research extraction agent. Extract facts, quantitative metrics, forward-looking guidance, risk flags, and credit ratings.
CRITICAL RULE 1: Ignore standard legal disclaimers and copyright notices.
CRITICAL RULE 2: You MUST output a JSON array of objects. Do NOT wrap the array in a 'data' key.
CRITICAL RULE 3: Every object MUST have a 'target_table' key (must be 'financials', 'guidance_claims', 'risk_flags', 'credit_ratings', or 'raw_data').
CRITICAL RULE 4: Every object MUST have a 'data' object containing the extracted details.
Example:
[
  {
    "target_table": "financials",
    "data": { "metric": "revenue", "value": 500, "unit": "INR Cr", "period": "FY24" }
  }
]"""

    try:
        # <-- NEW: Call Featherless API
        response = llm_client.chat.completions.create(
            model="google/gemma-3-27b-it",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Source Document: {filename}\n\nText to analyze:\n{chunk}"}
            ],
            response_format={"type": "json_object"}
        )
        raw_json = response.choices[0].message.content
        
        parsed = json.loads(raw_json)
        if isinstance(parsed, dict) and 'data' in parsed and isinstance(parsed['data'], list):
            return parsed['data'] 
        elif isinstance(parsed, list):
            return parsed
        else:
            return []
            
    except Exception as e:
        print(f"[-] LLM API or Parse Error on {filename}: {e}")
        return []

# ==========================================
# 3. DATA SANITIZATION & SUPABASE INSERT
# ==========================================
def sanitize_and_insert(extracted_items, filename):
    """Forces citations, fixes nulls, and pushes to Supabase."""
    if not extracted_items:
        return

    for item in extracted_items:
        target_table = item.get("target_table")
        row_data = item.get("data", {})

        # 1. FORCE FOREIGN KEYS & CITATIONS (Overrides LLM)
        row_data["company_id"] = TARGET_COMPANY_ID
        row_data["source_document"] = filename

        # 2. FIX 'NOT NULL' CONSTRAINTS
        if target_table == 'credit_ratings':
            row_data['rating_agency'] = row_data.get('rating_agency') or 'Unknown Agency'
        elif target_table == 'financials':
            row_data['metric'] = row_data.get('metric') or 'Unknown Metric'
            row_data['period'] = row_data.get('period') or 'Unknown Period'
        elif target_table == 'guidance_claims':
            row_data['metric_type'] = row_data.get('metric_type') or 'Unknown Metric'
            row_data['verbatim_quote'] = row_data.get('verbatim_quote') or 'Quote missing'
        elif target_table == 'risk_flags':
            row_data['description'] = row_data.get('description') or 'Description missing'
            valid_cats = ['debt', 'governance', 'operational', 'regulatory', 'auditor', 'supply_overhang', 'margin_compression', 'management_mismatch', 'key_person']
            if row_data.get('category') not in valid_cats:
                row_data['category'] = 'operational' # Fallback for CHECK constraint
        
        # 3. INSERT INTO SUPABASE
        valid_tables = ['financials', 'guidance_claims', 'risk_flags', 'credit_ratings', 'raw_data']
        if target_table in valid_tables:
            try:
                # Remove any keys that LLM hallucinated that aren't in your schema
                # (Supabase will throw an error if you pass a column that doesn't exist)
                response = supabase.table(target_table).insert(row_data).execute()
                print(f"[+] Inserted 1 row into {target_table} from {filename}")
            except Exception as e:
                print(f"[-] Supabase Insert Error ({target_table}): {e}")
                print(f"    Payload was: {row_data}")

# ==========================================
# 4. MAIN ORCHESTRATOR LOOP
# ==========================================
def run_pipeline():
    print(f"🚀 Starting Ingestion Pipeline for {TARGET_COMPANY_ID}...")
    
    for root, dirs, files in os.walk(ROOT_FOLDER):
        if 'Annual_Reports' in root:
            continue
            
        for file in files:
            if file.endswith(('.pdf', '.csv', '.txt')):
                filepath = os.path.join(root, file)
                print(f"\n📂 Processing: {file}...")
                
                text = extract_text_from_file(filepath)
                if not text.strip():
                    continue
                    
                chunks = chunk_text(text)
                print(f"   -> Split into {len(chunks)} chunks.")
                
                for idx, chunk in enumerate(chunks):
                    print(f"   -> Analyzing chunk {idx+1}/{len(chunks)} via Featherless Gemma 3...")
                    # <-- NEW: Call the updated function
                    extracted_items = analyze_chunk_with_llm(chunk, file) 
                    
                    sanitize_and_insert(extracted_items, file)
                    
                    # You can reduce this delay now since Featherless doesn't have Groq's strict free tier RPM limits
                    time.sleep(1.5) 

if __name__ == "__main__":
    run_pipeline()