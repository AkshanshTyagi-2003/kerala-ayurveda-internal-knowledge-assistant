import streamlit as st
from src.rag_engine import KeralaAyurvedaRAG

st.set_page_config(
    page_title="Kerala Ayurveda Internal Assistant",
    page_icon="🌿",
    layout="centered"
)

st.title("🌿 Kerala Ayurveda – Internal Knowledge Assistant")
st.caption(
    "Grounded answers from internal Kerala Ayurveda content. "
    "This tool provides educational, non-medical information with citations."
)

rag = KeralaAyurvedaRAG()

query = st.text_input(
    "Ask a question about Ayurveda, products, or clinic programs:",
    placeholder="e.g. What are the benefits and precautions of Ashwagandha Stress Balance Tablets?"
)

if query:
    with st.spinner("Searching internal knowledge base..."):
        response = rag.answer_user_query(query)

    st.subheader("Answer")

    # --- CASE 1: Fallback / safety response ---
    if "answer" in response:
        st.markdown(response["answer"])

    # --- CASE 2: Grounded answer prompt ---
    elif "answer_prompt" in response:
        st.markdown(
            "This draft is generated strictly from internal content and follows Kerala Ayurveda tone and safety guidelines."
        )
        st.code(response["answer_prompt"], language="text")

        if response.get("citations"):
            st.subheader("Sources")
            for c in response["citations"]:
                st.markdown(f"- **{c['doc_id']}** : {c['section_id']}")

    st.divider()
    st.caption(
        "⚠️ This tool is for internal informational use only. "
        "It does not provide medical advice, diagnosis, or treatment."
    )
