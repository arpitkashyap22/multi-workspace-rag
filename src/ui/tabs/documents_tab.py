"""
Documents Tab module.
Renders document ingestion, object storage persistence, and file previews
scoped to the active workspace with support for .txt, .md, and .pdf documents.
"""

import streamlit as st
from src.database import repository
from src.services import rag, storage


def render_documents_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders the document management, upload, and inspection UI.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    st.markdown("### 📄 Workspace Documents")
    st.caption(f"Manage documents stored securely in Neon Object Storage for **{active_ws_name}**.")

    # Upload Section
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        col_up1, col_up2 = st.columns([3, 1])

        with col_up1:
            uploaded_file = st.file_uploader(
                "Upload a document (.txt, .md, or .pdf)",
                type=["txt", "md", "pdf"],
                help="Uploaded files (.txt, .md, .pdf) are hashed with SHA-256 for idempotency, uploaded to Neon Object Storage, and chunked with vector embeddings.",
            )

        with col_up2:
            st.markdown("<br>", unsafe_allow_html=True)
            upload_btn = st.button("📤 Ingest Document", use_container_width=True, type="primary")

        if upload_btn and uploaded_file is not None:
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name

            try:
                with st.spinner(f"Extracting content, uploading blob, & generating embeddings for '{filename}'..."):
                    ingest_res = rag.ingest_document(
                        workspace_id=active_ws_id,
                        filename=filename,
                        file_bytes=file_bytes,
                    )

                if ingest_res.already_exists:
                    st.info(f"ℹ️ **Already Ingested:** {ingest_res.message}")
                else:
                    st.success(f"✅ **Success:** {ingest_res.message}")
                    st.rerun()
            except Exception as err:
                st.error(f"❌ Ingestion failed for '{filename}': {err}")

        st.markdown("</div>", unsafe_allow_html=True)

    # Document List & Preview
    docs = repository.get_workspace_documents(active_ws_id)

    if not docs:
        st.info("No documents uploaded yet to this workspace. Upload a `.txt`, `.md`, or `.pdf` file above to begin!")
    else:
        st.markdown(f"**Total Documents:** {len(docs)}")
        for doc in docs:
            doc_id = doc["id"]
            filename = doc["filename"]
            blob_path = doc["blob_path"]
            created_at = doc.get("created_at")
            created_str = (
                created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                if hasattr(created_at, "strftime")
                else str(created_at)
            )

            is_pdf = filename.lower().endswith(".pdf")
            icon = "📕" if is_pdf else "📄"

            with st.expander(f"{icon} {filename} — (Uploaded: {created_str})", expanded=False):
                col_meta, col_actions = st.columns([3, 1])

                with col_meta:
                    st.markdown(f"**Storage Path:** `{blob_path}`")
                    st.markdown(f"**Document ID:** `{doc_id}`")
                    st.markdown(f"**Type:** `{'PDF Document' if is_pdf else 'Text Document'}`")

                try:
                    # Download original binary/text from Neon Object Storage
                    raw_bytes = storage.get_file_bytes_from_blob(blob_path)
                    mime_type = "application/pdf" if is_pdf else "text/plain"

                    with col_actions:
                        st.download_button(
                            label="⬇️ Download File",
                            data=raw_bytes,
                            file_name=filename,
                            mime=mime_type,
                            key=f"dl_{doc_id}",
                            use_container_width=True,
                        )

                    st.markdown("**Content Preview:**")
                    if is_pdf:
                        try:
                            preview_text = rag.extract_text_from_pdf(raw_bytes)
                        except Exception:
                            preview_text = "[PDF binary file - unable to extract text preview]"
                    else:
                        preview_text = raw_bytes.decode("utf-8", errors="replace")

                    st.text_area(
                        "Preview",
                        value=preview_text[:2000] + ("\n... [Truncated]" if len(preview_text) > 2000 else ""),
                        height=180,
                        disabled=True,
                        key=f"preview_{doc_id}",
                    )

                except Exception as blob_err:
                    st.error(f"Failed to fetch file from storage: {blob_err}")
