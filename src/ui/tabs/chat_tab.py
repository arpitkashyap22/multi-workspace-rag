"""
Chat Assistant Tab module.
Renders Gemini-inspired conversational AI interface with persistent multi-turn chat threads,
rich prompt cards, collapsible thought process, grounded source chips, and tool execution.
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
    Renders the Gemini-styled Document Assistant chat interface for the active workspace.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    current_user = st.session_state.get("user", {})
    user_email = current_user.get("email", "")
    user_name = user_email.split("@")[0].capitalize() if user_email else "there"

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

    # 2. Sleek Gemini Top Navigation Bar
    col_brand, col_sel, col_new, col_del = st.columns([1.6, 2.8, 1.2, 0.6])
    with col_brand:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; height: 100%; padding-top: 4px;">
                <span style="font-size: 1.25rem;">✨</span>
                <span style="font-weight: 700; font-size: 1.05rem; background: linear-gradient(90deg, #8ab4f8, #c58af9); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Gemini Assistant</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

    st.markdown("<hr style='margin: 0.4rem 0 1.25rem 0; border: none; border-top: 1px solid rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # 3. Retrieve persistent message history for current thread
    messages = repository.get_conversation_messages(current_conv_id)

    # Render Gemini Hero Welcome & Suggestion Cards if thread is empty
    chosen_prompt: str | None = None
    if not messages:
        st.markdown(
            f"""
            <div style="margin: 1.5rem 0 2rem 0;">
                <div class="gemini-greeting">Hello, {user_name}</div>
                <div class="gemini-subheading">How can I help with {active_ws_name} today?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Gemini-style 4 prompt suggestion cards in 2x2 grid
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("### 📄 **Summarize Documents**")
                st.caption("Extract key findings, core takeaways, and high-level summaries from all workspace files.")
                if st.button("Summarize Workspace →", key="card_prompt_1", width="stretch"):
                    chosen_prompt = "Please provide an executive summary of all uploaded documents in this workspace."

            with st.container(border=True):
                st.markdown("### 📌 **Extract Action Items**")
                st.caption("Identify deliverables or follow-ups and automatically record them as workspace tasks.")
                if st.button("Extract Tasks →", key="card_prompt_3", width="stretch"):
                    chosen_prompt = "Identify the key action items and deliverables in this workspace, and save them as tasks."

        with c2:
            with st.container(border=True):
                st.markdown("### 🔍 **Deep Q&A & Citations**")
                st.caption("Ask specific domain questions with exact page and filename source citations.")
                if st.button("Explore Details →", key="card_prompt_2", width="stretch"):
                    chosen_prompt = "What are the most critical specifications, requirements, and findings in this workspace?"

            with st.container(border=True):
                st.markdown("### 📢 **Broadcast Team Alert**")
                st.caption("Compose an operational status notice and dispatch it directly to Discord.")
                if st.button("Broadcast Alert →", key="card_prompt_4", width="stretch"):
                    chosen_prompt = "Send an operational alert to Discord that workspace review is in progress."

        st.html("<div style='height: 100px; width: 100%;'></div>")

    else:
        # Render Chat History (Gemini Style)
        for msg in messages:
            is_user = (msg["role"] == "user")
            avatar_icon = ":material/account_circle:" if is_user else "✨"

            with st.chat_message(msg["role"], avatar=avatar_icon):
                st.markdown(msg["content"])

                # Grounded Citations (Gemini Chip Style)
                sources = msg.get("sources")
                if sources:
                    chips_html = "".join([f'<span class="gemini-source-chip">📄 {src}</span>' for src in sources])
                    st.markdown(
                        f"""
                        <div style="margin-top: 10px;">
                            <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #80868b; margin-bottom: 4px;">Grounded Sources</div>
                            <div>{chips_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # 4. Render bottom spacer and auto-scroll anchor so messages don't get hidden behind the pinned input bar
    if messages:
        st.html(
            """
            <div id="chat-bottom-anchor" style="height: 120px; width: 100%; clear: both;"></div>
            <div id="chat-scroll-container">
                <button id="gemini-scroll-btn" class="gemini-scroll-btn" title="Scroll to bottom" aria-label="Scroll to bottom">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </button>
            </div>
            <script>
            (function() {
                function findScrollContainer() {
                    return document.querySelector('[data-testid="stMain"]') || document.querySelector('section.main') || document.documentElement;
                }

                function doScrollToBottom(smooth = true) {
                    const anchor = document.getElementById("chat-bottom-anchor");
                    if (anchor) {
                        anchor.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" });
                    }
                    const container = findScrollContainer();
                    if (container) {
                        container.scrollTo({ top: container.scrollHeight, behavior: smooth ? "smooth" : "auto" });
                    }
                    window.scrollTo({ top: document.body.scrollHeight, behavior: smooth ? "smooth" : "auto" });
                }

                window.__geminiDoScroll = doScrollToBottom;

                // Perform smooth scroll to bottom after layout settles
                requestAnimationFrame(() => doScrollToBottom(true));
                setTimeout(() => doScrollToBottom(true), 80);
                setTimeout(() => doScrollToBottom(true), 250);

                const btn = document.getElementById("gemini-scroll-btn");
                const container = findScrollContainer();
                let userScrolledUp = false;

                function checkScroll() {
                    const anchor = document.getElementById("chat-bottom-anchor");
                    if (!anchor || !btn) return;
                    const scrollDist = container.scrollHeight - container.scrollTop - container.clientHeight;
                    if (scrollDist > 140) {
                        userScrolledUp = true;
                        btn.style.display = "flex";
                    } else {
                        userScrolledUp = false;
                        btn.style.display = "none";
                    }
                }

                if (btn) {
                    btn.onclick = function(e) {
                        e.preventDefault();
                        userScrolledUp = false;
                        doScrollToBottom(true);
                        btn.style.display = "none";
                    };
                }

                if (container && !container.__hasChatScroll) {
                    container.__hasChatScroll = true;
                    container.addEventListener("scroll", checkScroll, { passive: true });
                }
                window.addEventListener("scroll", checkScroll, { passive: true });

                // MutationObserver for auto-scrolling when new messages or thought steps are added
                const mainEl = document.querySelector('[data-testid="stMain"]') || document.body;
                if (mainEl && !window.__geminiChatObserver) {
                    window.__geminiChatObserver = new MutationObserver(function() {
                        const anchor = document.getElementById("chat-bottom-anchor");
                        if (!anchor) return;
                        if (!userScrolledUp) {
                            doScrollToBottom(true);
                        }
                    });
                    window.__geminiChatObserver.observe(mainEl, {
                        childList: true,
                        subtree: true
                    });
                }
            })();
            </script>
            """,
            unsafe_allow_javascript=True,
        )

    # 5. Fixed Gemini Chat Input (Pinned to viewport bottom)
    with st.bottom:
        input_query = st.chat_input(
            f"Ask Gemini about {active_ws_name}...",
            submit_mode="disable",
            key="gemini_chat_input",
        )
    user_query = chosen_prompt or input_query

    if user_query:
        # 1. Mount screen freeze overlay to block UI interactions while generating solution
        freeze_overlay = st.empty()
        freeze_overlay.spinner("Generating solution...")


        # Trigger immediate scroll to bottom when a query is submitted
        st.html(
            """
            <script>
            if (window.__geminiDoScroll) {
                window.__geminiDoScroll(true);
            }
            </script>
            """,
            unsafe_allow_javascript=True,
        )

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
        with st.chat_message("user", avatar=":material/account_circle:"):
            st.markdown(user_query)

        # Run assistant agent with multi-turn conversation memory
        with st.chat_message("assistant", avatar="✨"):
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
                    # Gemini Thought Process (Compact collapsible cognition container)
                    with st.status(":material/cognition: Thought process", expanded=True) as status_box:
                        st.caption(f"Searching semantic vector index for `{active_ws_name}`...")
                        agent_resp = doc_agent.run(
                            workspace_id=active_ws_id,
                            query=user_query,
                            chat_history=messages,
                        )

                        # Display Tool Executions in Thought Process
                        if agent_resp.tool_events:
                            for event in agent_resp.tool_events:
                                status_label = "✅ Complete" if event.status == "complete" else "❌ Failed"
                                st.markdown(f"**Tool Invocation:** `{event.tool_name}` — {status_label}")
                                st.caption(f"Arguments: `{event.tool_args}`")
                                if event.tool_output:
                                    st.caption(f"Output: `{event.tool_output}`")
                        else:
                            st.write("Retrieved grounded context chunks and generated structured response.")

                        status_box.update(label="Thought process complete", state="complete", expanded=False)

                    # Display Assistant Answer
                    st.markdown(agent_resp.answer)

                    # Grounded Source Chips
                    if agent_resp.sources:
                        chips_html = "".join([f'<span class="gemini-source-chip">📄 {src}</span>' for src in agent_resp.sources])
                        st.markdown(
                            f"""
                            <div style="margin-top: 10px;">
                                <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #80868b; margin-bottom: 4px;">Grounded Sources</div>
                                <div>{chips_html}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

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

        # Clear freeze overlay before refreshing page
        freeze_overlay.empty()

        # Trigger scroll to bottom for the newly completed answer before rerun
        st.html(
            """
            <script>
            if (window.__geminiDoScroll) {
                window.__geminiDoScroll(true);
            }
            </script>
            """,
            unsafe_allow_javascript=True,
        )
        st.rerun()
