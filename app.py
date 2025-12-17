import streamlit as st
import sys
import os

st.set_page_config(
    page_title="Kerala Ayurveda Internal Assistant",
    page_icon="🌿",
    layout="centered"
)

# ----------------- DEBUG INFO -----------------

st.sidebar.write("Python version:", sys.version)
st.sidebar.write("Current directory:", os.getcwd())
st.sidebar.write(
    "Files in src/:",
    os.listdir("src") if os.path.exists("src") else "src not found"
)

try:
    from src.rag_engine import KeralaAyurvedaRAG  # Import from rag_engine.py
    st.sidebar.success("✅ Import successful")
except Exception as e:
    st.sidebar.error(f"❌ Import error: {e}")
    st.stop()

# ----------------- UI -----------------

st.title("🌿 Kerala Ayurveda – Internal Knowledge Assistant")
st.caption(
    "Grounded answers from internal Kerala Ayurveda content. "
    "This tool provides educational, non-medical information with citations."
)

# ----------------- LOAD RAG -----------------

@st.cache_resource  # ADDED: Cache RAG initialization for better performance
def load_rag():
    """Initialize RAG system once and cache it."""
    return KeralaAyurvedaRAG()

try:
    rag = load_rag()
    st.sidebar.success("✅ RAG system initialized")
except Exception as e:
    st.sidebar.error(f"❌ Error loading RAG system: {e}")
    st.stop()

# ----------------- QUERY -----------------

query = st.text_input(
    "Ask a question about Ayurveda, products, or clinic programs:",
    placeholder="e.g. What does Ayurveda mean by Vata, Pitta, and Kapha?"
)

if query:
    with st.spinner("Searching internal knowledge base..."):
        try:
            response = rag.answer_user_query(query)

            st.subheader("Answer")
            st.markdown(response["answer"])

            # Show citations if available
            if response.get("citations"):
                with st.expander("📚 View Citations"):
                    for i, citation in enumerate(response["citations"], 1):
                        st.write(f"**{i}.** {citation['doc_id']} → {citation['section_id']}")

            st.divider()
            st.caption(
                "⚠️ This tool is for internal informational use only. "
                "It does not provide medical advice, diagnosis, or treatment."
            )

        except Exception as e:
            st.error(f"❌ Error processing query: {e}")
            st.exception(e)  # Show full traceback for debugging