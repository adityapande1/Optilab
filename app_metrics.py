import streamlit as st

def run():

    # Read markdown file
    with open("./docs/metrics.md", "r") as f:
        md_content = f.read()

    # Display in Streamlit
    st.markdown(md_content, unsafe_allow_html=True)