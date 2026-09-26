Markdown
# 🛡️ Multi-Workspace Document Assistant (RAG & Tool Calling)

A production-grade, multi-tenant AI Document Assistant web application built with **Streamlit**, **Neon Serverless PostgreSQL** (with `pgvector`), **Neon S3-Compatible Object Storage**, **Neon Auth**, and **Google Gemini** orchestrated via **LangChain**.

---

## 🌐 Live Application & Demo Credentials

- **Live Deployed URL:** [https://multi-workspace-rag-dkh7qfsnyimypcfmv7fg7g.streamlit.app/](https://multi-workspace-rag-dkh7qfsnyimypcfmv7fg7g.streamlit.app/)
- **Demo Account for Evaluators:**
  - **Email:** `deflected-patient42@bravealias.com`
  - **Password:** `password123`

---

## 📌 Table of Contents
1. [Overview & Core Architecture](#-overview--core-architecture)
2. [How It Solves the Core Requirements](#-how-it-solves-the-core-requirements)
3. [Architecture Diagram](#-architecture-diagram)
4. [Environment Variables & Configuration](#-environment-variables--configuration)
5. [Local Setup Guide](#-local-setup-guide)
6. [Database Schema Setup](#-database-schema-setup)
7. [Deployment Guide](#-deployment-guide)
8. [Testing & Tenancy Verification Guide](#-testing--tenancy-verification-guide)

---

## 🚀 Overview & Core Architecture

The **Multi-Workspace Document Assistant** provides isolated digital workspaces where users can upload reference documents, query them through an AI assistant, and autonomously trigger actionable side-effect tools.

Every tenant and workspace shares **a single PostgreSQL database and one vector store table**, proving strict multi-tenancy isolation at the query layer without physical data fragmentation.

### 🌟 Core Capabilities
- **🔐 Multi-Tenant Authentication:** Sign-in and sign-up backed by Neon Auth REST API, with automated seeding of an initial workspace on creation.
- **📁 Workspace Switcher & Lifecycle Management:** Switch active workspaces dynamically via the sidebar. Creating or deleting workspaces maintains atomic cascading lifecycle boundaries.
- **📄 Idempotent Document Ingestion:** Supports `.pdf`, `.txt`, and `.md` uploads. Each upload computes a **SHA-256 hash** validated against a `(workspace_id, file_hash)` unique constraint in PostgreSQL to prevent duplicate vectorization.
- **☁️ Object Storage Persistence:** Uploaded document binaries are partitioned in Neon S3-compatible Object Storage under `workspaces/{workspace_id}/{filename}` and can be previewed or downloaded directly from the UI.
- **🧠 Tenancy-Scoped Semantic RAG:** Text chunks are split using LangChain's `RecursiveCharacterTextSplitter` (500 chars, 50 overlap), embedded via Google's `text-embedding-004` (768 dimensions), and stored in PostgreSQL (`langchain_pg_embedding`). Similarity retrieval applies a database-level metadata filter: `{"workspace_id": active_workspace_id}`.
- **🛡️ Anti-Hallucination & Injection Resistance:** The assistant cites sources by filename and explicitly replies: *"I do not have enough information in this workspace to answer that."* if the context lacks the answer. Retrieved chunks are enclosed in passive data delimiters to resist prompt hijacking.
- **⚡ Autonomous Tool Calling (2 Tools):**
  - `save_task`: Mutates internal workspace state by inserting actionable tasks with priority into `workspace_tasks`.
  - `send_discord_alert`: Executes external side-effect notifications via an outbound webhook.
  - Failures are intercepted safely, logged to `tool_logs`, and returned to the LLM without crashing the app.
- **📊 Real-Time Dashboard & Audit Logs:** A dedicated tab displaying active workspace tasks, document rosters, and a live tool-execution log.

---

## 🎯 How It Solves the Core Requirements

| Requirement | Implementation Detail | Tenancy & Safety Mechanism |
|---|---|---|
| **Single Shared Vector Store** | PostgreSQL + `pgvector` via `langchain-postgres` (`langchain_pg_embedding`) | Every chunk across all users and workspaces lives in one collection. |
| **Strict Tenancy Isolation** | Vector search runs with `filter={"workspace_id": active_workspace_id}` | Filter is executed inside PostgreSQL's vector index query, never post-filtered in memory. |
| **Grounded Citations & "I Don't Know"** | Strict system prompt guardrail | System prompt forces citation of filenames and commands exact refusal string when facts are absent. |
| **Idempotent Ingestion** | SHA-256 hash check before embedding | Re-uploading identical files within a workspace skips duplicate chunk generation. |
| **Tool Calling Loop** | LangChain Tool Calling with Gemini Flash | Pydantic schema validation + database logging into `tool_logs` on execution. |
| **Zero-Card Free Tier** | Streamlit Cloud + Neon Postgres + Gemini API + Neon S3 | Completely deployed and hosted with zero credit card requirements. |

---

## 🗺️ Architecture Diagram

```
flowchart TD
    User([User Browser]) <--> UI[Streamlit Frontend (app.py)]
    
    subgraph Identity & Workspaces
        UI <--> AuthAPI[Neon Auth REST API]
        UI <--> WSRepo[(PostgreSQL: users, workspaces)]
    end

    subgraph Ingestion Pipeline
        UI --> Parser[Text & PDF Parser]
        Parser --> HashCheck{SHA-256 Idempotency Check}
        HashCheck -->|New File| S3Storage[Neon Object Storage S3]
        HashCheck -->|New File| Splitter[RecursiveCharacterTextSplitter]
        Splitter --> EmbedModel[Gemini text-embedding-004]
        EmbedModel --> PGVector[(PostgreSQL: langchain_pg_embedding)]
    end

    subgraph Retrieval & Agent Loop
        UI <--> Agent[LangChain Agent - Gemini Flash]
        Agent <-->|Scoped by workspace_id| PGVector
        Agent --> Tool1[Tool: save_task] --> TaskDB[(PostgreSQL: workspace_tasks)]
        Agent --> Tool2[Tool: send_discord_alert] --> Discord[External Discord Webhook]
        Tool1 -.-> AuditLog[(PostgreSQL: tool_logs)]
        Tool2 -.-> AuditLog[(PostgreSQL: tool_logs)]
    end
```

---

## 🔑 Environment Variables & Configuration
The application reads configuration from local environment files (.env) or Streamlit secrets (.streamlit/secrets.toml).

A template is provided below:

```toml
# PostgreSQL Connection (Use Direct or Pooled SSL connection)
DATABASE_URL = "postgresql://user:password@ep-...neon.tech/neondb?sslmode=require"
DATABASE_URL_POOLED = "postgresql://user:password@ep-...-pooler.neon.tech/neondb?sslmode=require"

# Neon Auth REST API Base Endpoint
NEON_AUTH_BASE_URL = "[https://ep-...neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth](https://ep-...neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth)"

# Neon Object Storage (S3 Compatible API)
AWS_ENDPOINT_URL_S3 = "[https://br-...storage.c-4.ap-southeast-1.aws.neon.tech](https://br-...storage.c-4.ap-southeast-1.aws.neon.tech)"
AWS_ACCESS_KEY_ID = "nak_live_..."
AWS_SECRET_ACCESS_KEY = "nsk_live_..."
AWS_REGION = "ap-southeast-1"
S3_BUCKET = "uploads"

# Google Gemini API
GEMINI_API_KEY = "AIzaSy..."
GEMINI_CHAT_MODEL = "gemini-2.5-flash"
GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"

# External Webhooks (Tool 2)
DISCORD_WEBHOOK_URL = "[https://discord.com/api/webhooks/](https://discord.com/api/webhooks/)..."
```
---

## 💻 Local Setup Guide
1. Prerequisites
- Python >= 3.11 (tested up to 3.13)
- Git
- Neon PostgreSQL database instance with vector extension enabled
- Google Gemini API key (Google AI Studio)

2. Clone and Setup Environment
 ```Bash
### Clone the repository
git clone [https://github.com/arpitkashyap22/multi-workspace-rag.git](https://github.com/arpitkashyap22/multi-workspace-rag.git)
cd multi-workspace-rag

### Create virtual environment using uv or standard venv

uv venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
# Alternatively: pip install -r requirements.txt
```
3. Configure Secrets
Create .streamlit/secrets.toml or .env in the root folder with the variables listed above.

4. Run the Local Streamlit App
Bash
streamlit run app.py
Open your browser at http://localhost:8501.

## 🗄️ Database Schema Setup
Run the following migration in your Neon SQL Console before starting:

```SQL
-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document metadata table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    blob_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_workspace_file_hash UNIQUE (workspace_id, file_hash)
);

-- 4. Tasks table (Created by save_task tool)
CREATE TABLE IF NOT EXISTS workspace_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tool audit execution logs
CREATE TABLE IF NOT EXISTS tool_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    arguments JSONB,
    status TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Note: The vector store table (langchain_pg_embedding) is provisioned
-- automatically by langchain-postgres when initialized.
```

---

## 🚀 Deployment Guide
Deploying to Streamlit Community Cloud (Zero-Cost Setup)
Push your repository to GitHub:

```Bash
git add .
git commit -m "feat: complete multi-workspace assistant"
git push origin main
```
Navigate to share.streamlit.io and click New App.

Point to your repository, select branch main, and specify app.py as the entrypoint.

Under Advanced Settings > Secrets, paste the exact contents of your .streamlit/secrets.toml.

Click Deploy!. Streamlit Cloud will run the container with automated persistent hosting.

---

## 🧪 Evaluator & Testing Instructions

### 1. Test Credentials
- **Live URL:** https://multi-workspace-rag-dkh7qfsnyimypcfmv7fg7g.streamlit.app/
- **Email:** `deflected-patient42@bravealias.com`
- **Password:** `password123`

---

### 2. Step-by-Step Tenancy Isolation Test
This test confirms that documents uploaded in one workspace cannot be retrieved or cited in another workspace.

1. **Log in** using the credentials above.
2. In the sidebar, select or create **Workspace A** (e.g., `"Engineering"`).
3. In the **Documents** tab, upload a text file with distinct content:
   > *"The secret internal staging access token is ALPHA-SECRET-9021."*
4. In the **Assistant** tab, ask:
   > *"What is the staging access token?"*
   - **Expected Result:** Assistant answers `ALPHA-SECRET-9021` with a citation to your file.
5. In the sidebar, switch to **Workspace B** (e.g., `"General"` or create `"Marketing"`).
6. Ask the identical question:
   > *"What is the staging access token?"*
   - **Expected Result:** The assistant responds:
     *"I do not have enough information in this workspace to answer that."*
   - **Verdict:** Isolation holds at the vector query level.

---

### 3. Step-by-Step Tool Calling Test
1. **Tool 1 (`save_task`):**
   - In chat, prompt: `"Please save a high priority task to review deployment logs before Friday."`
   - **Expected Result:** Live status indicator shows `save_task` running. The new task appears in the **Dashboard & Audit Logs** tab under Workspace Tasks.
2. **Tool 2 (`send_discord_alert`):**
   - In chat, prompt: `"Send an alert to the team that maintenance starts at midnight."`
   - **Expected Result:** Assistant confirms dispatch, and the execution is logged with status `SUCCESS` in the Tool Logs table.