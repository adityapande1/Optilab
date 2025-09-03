import streamlit as st
import markdown
from streamlit.components.v1 import html

def run():

    # Load Markdown file
    with open("./docs/metrics.md", "r", encoding="utf-8") as f:
        md_text = f.read()


    # Convert Markdown to HTML with syntax highlighting
    html_content = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "codehilite"]
    )

    # GitHub-like styling + GitHub’s own code theme
    styled_html = f"""
    <link rel="stylesheet" 
        href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css">
    <link rel="stylesheet" 
        href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>

    <article class="markdown-body" style="padding: 2rem; width: 100%; box-sizing: border-box;">
    {html_content}
    </article>
    """

    html(styled_html, height=800, scrolling=True)