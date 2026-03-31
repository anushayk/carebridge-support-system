"""
ui/app.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from dotenv import load_dotenv

from agents.graph import run_graph

load_dotenv()

# --- Page config -------------------------------------------------------------

st.set_page_config(
    page_title="CareBridge",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Theme CSS ---------------------------------------------------------------

st.markdown("""
<style>
/* Hide Streamlit top toolbar (deploy button, three-dot menu) */
[data-testid="stToolbar"]          { display: none !important; }
[data-testid="stDecoration"]       { display: none !important; }
#MainMenu                          { display: none !important; }
footer                             { display: none !important; }

/* Main background — pale yellow */
[data-testid="stAppViewContainer"] { background-color: #fffdf5; }
[data-testid="stMain"]             { background-color: #fffdf5; }
.main .block-container             { background-color: #fffdf5; }

/* Top header bar — pale yellow */
[data-testid="stHeader"]           { background-color: #fffdf5 !important; }

/* Bottom chat input bar — pale yellow */
[data-testid="stBottom"]           { background-color: #fffdf5 !important; }
[data-testid="stBottom"] > div     { background-color: #fffdf5 !important; }

/* Sidebar */
[data-testid="stSidebar"]          { background-color: #fff3f7; border-right: 0.5px solid #f4c0d1; }

/* Chat input — override all nested wrappers */
[data-testid="stChatInput"] { background-color: #fff9fb !important; border: none !important; border-radius: 24px !important; overflow: hidden !important; }
[data-testid="stChatInput"] > div { background-color: #fff9fb !important; border: none !important; border-radius: 24px !important; }
[data-testid="stChatInput"] textarea { background-color: #fff9fb !important; color: #2c2c2a !important; border: none !important; box-shadow: none !important; }
[data-testid="stChatInput"] textarea:focus { box-shadow: none !important; border: none !important; }
[data-testid="stChatInputContainer"] { background-color: #fffdf5 !important; padding: 8px 0 !important; }
[data-testid="stChatInputContainer"] > div { background-color: #fff9fb !important; border: 0.5px solid #f4c0d1 !important; border-radius: 24px !important; box-shadow: none !important; }
[data-testid="stChatInputContainer"] > div:focus-within { border-color: #d4537e !important; box-shadow: none !important; }

/* Dark mode */
@media (prefers-color-scheme: dark) {
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main .block-container,
    [data-testid="stHeader"],
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div             { background-color: #1e1c1a !important; }
    [data-testid="stSidebar"]                  { background-color: #2a2028 !important; border-right: 0.5px solid #4a3848 !important; }
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInputContainer"] > div { background-color: #2a2028 !important; border-color: #4a3848 !important; }
    [data-testid="stChatInput"] textarea       { color: #e8e6e0 !important; }
    [data-testid="stChatMessage"]              { background: #221f1a !important; border-color: #3a3530 !important; }
    .chat-header                               { color: #e8e6e0 !important; }
    .chat-subheader                            { color: #5f5e5a !important; }
    .source-pill                               { background: #2c2c2a !important; color: #b4b2a9 !important; }
    .badge-sql                                 { background: #412402 !important; color: #fac775 !important; }
    .badge-rag                                 { background: #4b1528 !important; color: #f4c0d1 !important; }
    .badge-both                                { background: #04342c !important; color: #9fe1cb !important; }
}

.sidebar-brand   { font-size: 16px; font-weight: 700; color: #d4537e; margin-bottom: 2px; }
.sidebar-sub     { font-size: 12px; color: #ed93b1; margin-bottom: 0; }
.section-label   { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #d4537e; margin: 0 0 8px 0; }
.badge           { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 4px; }
.badge-sql       { background: #faeeda; color: #854f0b; }
.badge-rag       { background: #fbeaf0; color: #993556; }
.badge-both      { background: #e1f5ee; color: #0f6e56; }
.source-pill     { display: inline-block; background: #f1efe8; color: #5f5e5a; font-size: 11px; padding: 2px 7px; border-radius: 4px; margin-right: 4px; margin-top: 4px; }
.chat-header     { font-size: 22px; font-weight: 700; color: #2c2c2a; margin-bottom: 2px; }
.chat-subheader  { font-size: 13px; color: #888780; margin-bottom: 24px; }

.stButton > button       { background-color: #fbeaf0 !important; border: 0.5px solid #f4c0d1 !important; color: #d4537e !important; font-weight: 600 !important; border-radius: 8px !important; }
.stButton > button:hover { background-color: #f4c0d1 !important; }

[data-testid="stChatMessage"] { border-radius: 12px !important; border: 0.5px solid #faeeda !important; background: #fffdf5 !important; }
</style>
""", unsafe_allow_html=True)

# --- Session state -----------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_starters" not in st.session_state:
    st.session_state.show_starters = True

# --- Sidebar -----------------------------------------------------------------

with st.sidebar:
    st.markdown('<p class="sidebar-brand">Support Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-sub">Apple customer support</p>', unsafe_allow_html=True)

    st.divider()

    st.markdown('<p class="section-label">Upload policy PDF</p>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        label="policy_upload",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        if st.button("Index document"):
            with st.spinner("Indexing..."):
                try:
                    from langchain_community.document_loaders import PyPDFLoader
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                    from langchain_openai import OpenAIEmbeddings
                    from langchain_chroma import Chroma

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    loader = PyPDFLoader(tmp_path)
                    docs   = loader.load()
                    for doc in docs:
                        doc.metadata["source_file"] = uploaded_file.name

                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000, chunk_overlap=150
                    )
                    chunks = splitter.split_documents(docs)

                    embeddings = OpenAIEmbeddings(
                        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
                    )
                    vectorstore = Chroma(
                        collection_name="apple_policies",
                        embedding_function=embeddings,
                        persist_directory=os.getenv("CHROMA_DIR", "data/chroma_db"),
                    )
                    vectorstore.add_documents(chunks)
                    os.unlink(tmp_path)
                    st.success(f"Indexed {len(chunks)} chunks from {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Failed to index: {e}")

    st.divider()

    st.markdown('<p class="section-label">Routing guide</p>', unsafe_allow_html=True)
    st.markdown("""
<div style="display:flex;flex-direction:column;gap:8px;">
  <div style="display:flex;align-items:center;gap:8px;">
    <span class="badge badge-sql">SQL</span>
    <span style="font-size:12px;color:#888780;">Customer &amp; ticket data</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span class="badge badge-rag">RAG</span>
    <span style="font-size:12px;color:#888780;">Apple policy documents</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span class="badge badge-both">BOTH</span>
    <span style="font-size:12px;color:#888780;">Combined queries</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.show_starters = True
        st.rerun()

# --- Main area ---------------------------------------------------------------

st.markdown('<p class="chat-header">CareBridge</p>', unsafe_allow_html=True)
st.markdown('<p class="chat-subheader">Ask about any customer or policy</p>', unsafe_allow_html=True)

STARTERS = [
    "Give me a profile of customer Brandon Davis",
    "What does AppleCare cover for accidental damage?",
    "List all open critical priority tickets",
    "Does Jason Morris qualify for a refund on his open ticket?",
]

if st.session_state.show_starters:
    st.markdown("**Try asking...**")
    cols = st.columns(2)
    for i, prompt in enumerate(STARTERS):
        with cols[i % 2]:
            if st.button(prompt, key=f"starter_{i}", use_container_width=True):
                st.session_state.show_starters = False
                st.session_state["pending_query"] = prompt
                st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("route"):
            route        = message["route"]
            badge_cls    = f"badge-{route.lower()}"
            sources_html = "".join(
                f'<span class="source-pill">{s}</span>'
                for s in message.get("sources", [])
            )
            st.markdown(
                f'<span class="badge {badge_cls}">{route.upper()}</span>{sources_html}',
                unsafe_allow_html=True,
            )

query = st.chat_input("Ask a question...")

if "pending_query" in st.session_state:
    query = st.session_state.pop("pending_query")

if query:
    if st.session_state.show_starters:
        st.session_state.show_starters = False
        st.session_state["pending_query"] = query
        st.rerun()
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result  = run_graph(query)
                answer  = result.get("answer", "No answer returned.")
                route   = result.get("route", "unknown")
                sources = result.get("sources", [])
            except Exception as e:
                answer  = f"Something went wrong: {e}"
                route   = "error"
                sources = []

        st.markdown(answer)
        badge_cls    = f"badge-{route.lower()}" if route in ("sql", "rag", "both") else ""
        sources_html = "".join(f'<span class="source-pill">{s}</span>' for s in sources)
        st.markdown(
            f'<span class="badge {badge_cls}">{route.upper()}</span>{sources_html}',
            unsafe_allow_html=True,
        )

    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "route":   route,
        "sources": sources,
    })
