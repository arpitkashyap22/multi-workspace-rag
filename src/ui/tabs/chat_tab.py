"""
Chat Assistant Tab module.
Renders workspace-scoped conversational AI interface with autonomous tool execution
and grounded document citations.
"""

import streamlit as st
from src.agents.document_agent import DocumentAssistantAgent


def render_chat_tab(active_ws_id: str, active_ws_name: str) -> None:
    """
    Renders the Document Assistant chat interface for the active workspace.

    Args:
        active_ws_id: UUID of the current active workspace.
        active_ws_name: Display name of the active workspace.
    """
    # Initialize workspace chat history in session state
    if "chat_histories" not in st.session_state:
        st.session_state.chat_histories = {}

    if active_ws_id not in st.session_state.chat_histories:
        st.session_state.chat_histories[active_ws_id] = [
            {
                "role": "assistant",
                "content": f"Hello! I am your AI assistant for **{active_ws_name}**. Ask me questions about documents in this workspace, or ask me to record action items or send alerts.",
                "sources": [],
            }
        ]

    chat_messages = st.session_state.chat_histories[active_ws_id]

    # Render Chat History
    for msg in chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("📚 Source Citations", expanded=False):
                    for src in msg["sources"]:
                        st.markdown(f"- `{src}`")

    # Chat Input
    user_query = st.chat_input(f"Ask about documents in {active_ws_name}...")

    if user_query:
        # Append User Message
        chat_messages.append({"role": "user", "content": user_query, "sources": []})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            try:
                doc_agent = DocumentAssistantAgent()
            except ValueError as val_err:
                warning_msg = (
                    f"⚠️ **Configuration Notice:** {val_err}\n\n"
                    "Please set `GEMINI_API_KEY` in `.streamlit/secrets.toml` or as an environment variable to enable the Document Assistant Agent."
                )
                st.warning(warning_msg)
                chat_messages.append({"role": "assistant", "content": warning_msg, "sources": []})
                doc_agent = None

            if doc_agent:
                try:
                    with st.spinner(f"Document Assistant Agent is analyzing {active_ws_name}..."):
                        agent_resp = doc_agent.run(
                            workspace_id=active_ws_id,
                            query=user_query,
                            chat_history=chat_messages,
                        )

                    # Display any tool calls executed by the agent
                    for event in agent_resp.tool_events:
                        status_label = "✅ Tool finished" if event.status == "complete" else "❌ Tool failed"
                        with st.status(f"⚡ Executed tool `{event.tool_name}` — {status_label}", expanded=False):
                            st.write(f"**Arguments:** `{event.tool_args}`")
                            st.write(f"**Tool Output:** {event.tool_output}")

                    # Display Assistant Answer
                    st.markdown(agent_resp.answer)

                    # Display Sources if available
                    if agent_resp.sources:
                        with st.expander("📚 Source Citations (Active Workspace)", expanded=False):
                            for src in agent_resp.sources:
                                st.markdown(f"- 📄 `{src}`")

                    # Record message in history
                    chat_messages.append(
                        {
                            "role": "assistant",
                            "content": agent_resp.answer,
                            "sources": agent_resp.sources,
                        }
                    )

                except Exception as err:
                    err_msg = f"An error occurred while generating response: {err}"
                    st.error(err_msg)
                    chat_messages.append({"role": "assistant", "content": err_msg, "sources": []})
