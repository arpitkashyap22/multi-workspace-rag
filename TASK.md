# Project Implementation Tracker

## Phase 1: Storage, Auth & Database Layer
- [x] Implement `storage.py` using `boto3` for Neon Object Storage
- [x] Implement `db.py` with Neon Auth REST wrappers and workspace SQL queries
- [x] Test signup, login, and default workspace creation

## Phase 2: Ingestion & Tenancy-Scoped RAG
- [ ] Implement `rag.py`: SHA-256 idempotency check, chunking (500 chars), Gemini `text-embedding-004`
- [ ] Enforce SQL-level scoped vector search (`WHERE workspace_id = %s`)
- [ ] Test context citations and "I don't know" fallback

## Phase 3: Tool Calling Engine
- [ ] Implement `tools.py`: `save_task` (DB write) and `send_discord_alert` (Webhook)
- [ ] Set up Pydantic argument validation and logging to `tool_logs`
- [ ] Integrate multi-turn tool calling loop with Gemini 1.5 Flash

## Phase 4: Streamlit UI
- [ ] Build Auth screen (Login/Signup toggle)
- [ ] Build Sidebar: User status, Workspace Switcher, and Create Workspace input
- [ ] Tab 1 (Chat): Message history, tool execution spinners (`st.status`), source citations
- [ ] Tab 2 (Documents): File uploader + preview fetched from Neon Object Storage
- [ ] Tab 3 (Dashboard): Live data tables for `workspace_tasks` and `tool_logs`

## Phase 5: Verification & Deployment
- [ ] Isolation Test: Check cross-workspace leakage between 2 workspaces
- [ ] Deploy to Streamlit Community Cloud with all secrets configured
- [ ] Complete `AI_NOTES.md` and `README.md`