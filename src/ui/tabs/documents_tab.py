"""
Documents Tab module.
Renders document ingestion, object storage persistence, file previews,
and safe document deletion with confirmation dialogs.
"""

import streamlit as st
from src.database import repository
from src.services import rag, storage


@st.cache_data(ttl="1h", max_entries=50, show_spinner=False)
def get_cached_file_bytes(blob_path: str) -> bytes:
    """Download and cache raw file bytes from Neon Object Storage."""
    return storage.get_file_bytes_from_blob(blob_path)


@st.cache_data(ttl="1h", max_entries=50, show_spinner=False)
def get_cached_document_preview(blob_path: str, is_pdf: bool) -> str:
    """Extract and cache preview text to avoid expensive re-parsing on every rerun."""
    try:
        raw_bytes = get_cached_file_bytes(blob_path)
        if is_pdf:
            return rag.extract_text_from_pdf(raw_bytes)
        return raw_bytes.decode("utf-8", errors="replace")
    except Exception as err:
        return f"[Unable to extract preview: {err}]"


@st.dialog("Delete Document Confirmation")
def confirm_delete_dialog(workspace_id: str, document_id: str, filename: str) -> None:
    """
    Renders a confirmation modal with explicit warnings before permanently deleting a document.
    """
    st.warning(f"⚠️ Are you sure you want to delete **{filename}** from this workspace?")
    st.error(
        "**Permanent Deletion Warning:**\n\n"
        "This action will permanently:\n"
        "• Remove the original file from Neon Object Storage\n"
        "• Delete all vector embeddings from PostgreSQL pgvector\n"
        "• Remove document metadata and citations from the Document Assistant\n\n"
        "**This action cannot be undone.**"
    )

    col_cancel, col_confirm = st.columns(2)
    with col_cancel:
        if st.button("Cancel", width="stretch", key=f"dlg_cancel_{document_id}"):
            st.rerun()

    with col_confirm:
        if st.button("🚨 Yes, Delete Permanently", type="primary", width="stretch", key=f"dlg_confirm_{document_id}"):
            with st.spinner(f"Deleting '{filename}' and associated vector embeddings..."):
                try:
                    res = rag.delete_document(workspace_id=workspace_id, document_id=document_id)
                    get_cached_file_bytes.clear()
                    get_cached_document_preview.clear()
                    st.toast(res.get("message", f"Deleted {filename}"), icon="🗑️")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to delete document: {err}")


def render_documents_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders the document management, upload, inspection, and deletion UI.

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
            upload_btn = st.button("📤 Ingest Document", width="stretch", type="primary")

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
                    get_cached_file_bytes.clear()
                    get_cached_document_preview.clear()
                    st.toast(f"Ingested '{filename}' ({ingest_res.chunk_count} chunks)", icon="✅")
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
                    raw_bytes = get_cached_file_bytes(blob_path)
                    mime_type = "application/pdf" if is_pdf else "text/plain"

                    with col_actions:
                        st.download_button(
                            label="⬇️ Download",
                            data=raw_bytes,
                            file_name=filename,
                            mime=mime_type,
                            key=f"dl_{doc_id}",
                            width="stretch",
                        )

                        if st.button(
                            "🗑️ Delete",
                            key=f"btn_del_{doc_id}",
                            width="stretch",
                            type="secondary",
                            help=f"Delete '{filename}', its storage blob, and its vector embeddings.",
                        ):
                            confirm_delete_dialog(
                                workspace_id=active_ws_id,
                                document_id=doc_id,
                                filename=filename,
                            )

                    preview_text = get_cached_document_preview(blob_path, is_pdf)
                    st.markdown("**Content Preview:**")
                    st.text_area(
                        "Preview",
                        value=preview_text[:2000] + ("\n... [Truncated]" if len(preview_text) > 2000 else ""),
                        height=180,
                        disabled=True,
                        key=f"preview_{doc_id}",
                    )

                except Exception as blob_err:
                    st.error(f"Failed to fetch file from storage: {blob_err}")
