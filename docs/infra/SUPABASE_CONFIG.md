# ✅ Supabase Configuration Added

Your Supabase credentials have been added to the project.

## 📁 Configuration Files

### 1. **Backend (Python FastAPI)** — `graph/.env`
```env
# Neo4j Configuration
GRAPH_NEO4J_URI=neo4j://127.0.0.1:7687
GRAPH_NEO4J_USER=neo4j
GRAPH_NEO4J_PASSWORD=kshayik1
GRAPH_NEO4J_DATABASE=datahack-graphdb

# Supabase Configuration
SUPABASE_URL=https://nzofdwwcouzfpacapvmz.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. **Frontend (Next.js)** — `ui/.env.local`
```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://nzofdwwcouzfpacapvmz.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Graph API
GRAPH_API_URL=http://localhost:8001
```

## 📦 Dependencies

### Python (Backend)
Added to `graph/requirements.txt`:
```
supabase>=2.0.0
```

**Install:**
```bash
cd graph
pip install -r requirements.txt
```

### JavaScript (Frontend)
Already in `ui/package.json`:
```json
"@supabase/supabase-js": "^2.103.0"
```

**Install:**
```bash
cd ui
npm install
```

## 🔧 Usage

### Python (FastAPI Server)

```python
import os
from supabase import create_client, Client

# Load from environment
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

# Create client
supabase: Client = create_client(supabase_url, supabase_key)

# Query example
response = supabase.table("companies").select("*").execute()
```

### TypeScript (Next.js UI)

The UI already uses Supabase via `ui/src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

## ✅ What's Configured

- ✅ Supabase URL: `https://nzofdwwcouzfpacapvmz.supabase.co`
- ✅ Service Role Key (backend)
- ✅ Anon Key (frontend)
- ✅ Python library added to requirements
- ✅ JavaScript library already installed
- ✅ Environment variables set for both frontend and backend

## 🚀 Next Steps

1. **Install Python dependencies:**
   ```bash
   cd graph
   pip install -r requirements.txt
   ```

2. **Restart the FastAPI server** (if running):
   ```bash
   pkill -f "python.*api.py"
   ./start_graph_api.sh
   ```

3. **Restart Next.js dev server** (if running):
   ```bash
   # In the ui/ directory
   npm run dev
   ```

## 🔐 Security Notes

- ✅ `.env` files are gitignored (credentials won't be committed)
- ✅ Service Role Key is only in backend (not exposed to browser)
- ✅ Anon Key is safe to use in frontend (has RLS protection)

## 📊 Your Supabase Instance

- **URL**: https://nzofdwwcouzfpacapvmz.supabase.co
- **Project**: nzofdwwcouzfpacapvmz
- **Region**: (check your Supabase dashboard)

You can access your Supabase dashboard at:
https://supabase.com/dashboard/project/nzofdwwcouzfpacapvmz

---

**All set! Your Supabase credentials are configured for both the FastAPI backend and Next.js frontend.**
