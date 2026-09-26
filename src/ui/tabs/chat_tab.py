"""
Chat Assistant Tab module.
Renders workspace-scoped conversational AI interface with persistent multi-turn chat history,
thread switching, autonomous tool execution, and grounded document citations.
"""

import streamlit as st
from src.database import repository
from src.agents.document_agent import DocumentAssistantAgent


@st.dialog("Delete Conversation Thread")
def confirm_delete_conversation_dialog(conversation_id: str, workspace_id: str, title: str) -> None:
    """
    Renders a confirmation modal before permanently deleting a chat conversation thread.
    """
    st.warning(f"⚠️ Are you sure you want to delete conversation **'{title}'**?")
    st.error(
        "**Permanent Deletion Warning:**\n\n"
        "This will permanently delete this conversation thread, its message history, "
        "and all associated citation records.\n\n"
        "**This action cannot be undone.**"
    )

    col_cancel, col_confirm = st.columns(2)
    with col_cancel:
        if st.button("Cancel", width="stretch", key=f"dlg_cancel_conv_{conversation_id}"):
            st.rerun()

    with col_confirm:
        if st.button("🚨 Yes, Delete Thread", type="primary", width="stretch", key=f"dlg_confirm_conv_{conversation_id}"):
            repository.delete_conversation(conversation_id=conversation_id, workspace_id=workspace_id)
            if st.session_state.get("active_conversation_id") == conversation_id:
                st.session_state.pop("active_conversation_id", None)
            st.toast(f"Deleted conversation '{title}'.", icon="🗑️")
            st.rerun()


def render_chat_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders the Document Assistant chat interface for the active workspace with persistent history.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    # 1. Fetch persistent conversations for active workspace
    conversations = repository.get_workspace_conversations(active_ws_id)
    if not conversations:
        new_conv = repository.create_conversation(active_ws_id, "New Chat")
        conversations = [new_conv]

    conv_map = {c["id"]: c for c in conversations}

    # Ensure valid active_conversation_id for this workspace
    if (
        "active_conversation_id" not in st.session_state
        or st.session_state.active_conversation_id not in conv_map
    ):
        st.session_state.active_conversation_id = conversations[0]["id"]

    current_conv = conv_map[st.session_state.active_conversation_id]
    current_conv_id = current_conv["id"]
    current_conv_title = current_conv["title"]

    # 2. Top Conversation Thread Control Bar
    st.markdown("### 💬 Conversational Assistant")
    st.caption(f"Persistent conversation threads scoped to **{active_ws_name}**.")

    col_sel, col_new, col_del = st.columns([3.5, 1.2, 0.8])
    with col_sel:
        def _format_conv(cid: str) -> str:
            c = conv_map.get(cid)
            if not c:
                return cid
            title = c["title"]
            return f"💬 {title}"

        selected_id = st.selectbox(
            "Select Conversation Thread",
            options=list(conv_map.keys()),
            format_func=_format_conv,
            index=list(conv_map.keys()).index(current_conv_id),
            label_visibility="collapsed",
            key="select_active_conv_dropdown",
        )
        if selected_id != current_conv_id:
            st.session_state.active_conversation_id = selected_id
            st.rerun()

    with col_new:
        if st.button("➕ New Chat", width="stretch", type="secondary", key="btn_create_new_chat"):
            created = repository.create_conversation(active_ws_id, "New Chat")
            st.session_state.active_conversation_id = created["id"]
            st.rerun()

    with col_del:
        if st.button("🗑️", width="stretch", type="secondary", key="btn_delete_curr_chat", help="Delete this conversation thread"):
            confirm_delete_conversation_dialog(
                conversation_id=current_conv_id,
                workspace_id=active_ws_id,
                title=current_conv_title,
            )

    st.markdown("<hr style='margin: 0.5rem 0 1rem 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # 3. Retrieve persistent message history for current thread
    messages = repository.get_conversation_messages(current_conv_id)

    # Render Welcome Message and suggestion chips if thread is empty
    chosen_prompt: str | None = None
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(
                f"Hello! I am your AI assistant for **{active_ws_name}**.\n\n"
                "Ask me anything about documents in this workspace, or ask me to record action items or broadcast alerts. "
                "All conversation history in this thread is persistently saved."
            )

        suggestions = [
            "📄 Summarize documents in this workspace",
            "📌 Save a high-priority review task",
            "📢 Send an alert to the team on Discord",
        ]
        chosen = st.pills("💡 Suggested actions:", suggestions, key=f"pills_{current_conv_id}")
        if chosen:
            chosen_prompt = chosen
    else:
        # Render Chat History
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander("📚 Source Citations", expanded=False):
                        for src in msg["sources"]:
                            st.markdown(f"- 📄 `{src}`")

    # 4. Chat Input & Response Generation
    input_query = st.chat_input(f"Message assistant in {active_ws_name}...", submit_mode="disable")
    user_query = chosen_prompt or input_query

    if user_query:
        # Save user message to database
        repository.save_chat_message(
            conversation_id=current_conv_id,
            role="user",
            content=user_query,
        )

        # Auto-update thread title from first user query
        if current_conv_title in ("New Chat", "Welcome Chat"):
            clean_title = user_query.strip().replace("\n", " ")
            short_title = clean_title[:45] + ("..." if len(clean_title) > 45 else "")
            repository.update_conversation_title(current_conv_id, short_title)

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_query)

        # Run assistant agent with multi-turn conversation memory
        with st.chat_message("assistant"):
            try:
                doc_agent = DocumentAssistantAgent()
            except ValueError as val_err:
                warning_msg = (
                    f"⚠️ **Configuration Notice:** {val_err}\n\n"
                    "Please set `GEMINI_API_KEY` in `.streamlit/secrets.toml` or as an environment variable to enable the Document Assistant Agent."
                )
                st.warning(warning_msg)
                repository.save_chat_message(
                    conversation_id=current_conv_id,
                    role="assistant",
                    content=warning_msg,
                )
                doc_agent = None

            if doc_agent:
                try:
                    with st.status(":shimmer[Thinking & searching workspace documents...]", type="compact") as status_box:
                        agent_resp = doc_agent.run(
                            workspace_id=active_ws_id,
                            query=user_query,
                            chat_history=messages,
                        )

                        # Display any tool calls executed by the agent inside the compact reasoning block
                        if agent_resp.tool_events:
                            for event in agent_resp.tool_events:
                                status_label = "✅ Complete" if event.status == "complete" else "❌ Failed"
                                st.markdown(f"**Tool:** `{event.tool_name}` — {status_label}")
                                st.caption(f"Arguments: `{event.tool_args}`")
                                if event.tool_output:
                                    st.caption(f"Output: `{event.tool_output}`")
                        else:
                            st.write("Retrieved workspace chunks and synthesized response.")

                        status_box.update(label="Grounded reasoning complete", state="complete")

                    # Display Assistant Answer
                    st.markdown(agent_resp.answer)

                    # Display Sources if available
                    if agent_resp.sources:
                        with st.expander("📚 Source Citations (Active Workspace)", expanded=False):
                            for src in agent_resp.sources:
                                st.markdown(f"- 📄 `{src}`")

                    # Persist assistant message and source citations to database
                    repository.save_chat_message(
                        conversation_id=current_conv_id,
                        role="assistant",
                        content=agent_resp.answer,
                        sources=agent_resp.sources,
                    )

                except Exception as err:
                    err_msg = f"An error occurred while generating response: {err}"
                    st.error(err_msg)
                    repository.save_chat_message(
                        conversation_id=current_conv_id,
                        role="assistant",
                        content=err_msg,
                    )

        st.rerun()
