import os
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from agent import run_stream
from agent.tools import list_files, read_file, zip_project

st.set_page_config(page_title="Coder Buddy", page_icon="🤖", layout="wide")

LANG = {".py": "python", ".js": "javascript", ".ts": "typescript", ".html": "html",
        ".css": "css", ".json": "json", ".md": "markdown", ".txt": "text",
        ".sh": "bash", ".yml": "yaml", ".yaml": "yaml", ".jsx": "jsx", ".tsx": "tsx"}
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
EXAMPLES = [
    "Build a calculator web app with add, subtract, multiply and divide buttons.",
    "Build a to-do list web app with local storage, filters and a dark theme.",
    "Build a tic tac toe game web application with colour difference",
]


def inline_assets(project_dir: str, html: str) -> str:
    """Inline local CSS/JS so index.html can be previewed inside Streamlit."""
    def css(m):
        body = read_file(project_dir, m.group(1))
        return f"<style>{body}</style>" if body else m.group(0)

    def js(m):
        body = read_file(project_dir, m.group(1))
        return f"<script>{body}</script>" if body else m.group(0)

    html = re.sub(r'<link[^>]+href=["\'](?!https?:)([^"\']+\.css)["\'][^>]*>', css, html)
    return re.sub(r'<script[^>]+src=["\'](?!https?:)([^"\']+\.js)["\'][^>]*>\s*</script>', js, html)


with st.sidebar:
    st.header("Settings")
    model = st.selectbox("Model", MODELS)
    custom = st.text_input("Custom model id (optional)")
    st.markdown("**Pipeline**\n\n1. 🧭 Planner\n2. 🏗️ Architect\n3. 💻 Coder (one file at a time)")

st.title("🤖 Coder Buddy: multi-agent coding assistant")
st.caption("Describe an app. A Planner, Architect and Coder agent build it file by file.")

if "prompt" not in st.session_state:
    st.session_state.prompt = EXAMPLES[0]
cols = st.columns(len(EXAMPLES))
for i, ex in enumerate(EXAMPLES):
    if cols[i].button(f"Example {i + 1}", use_container_width=True, help=ex):
        st.session_state.prompt = ex

prompt = st.text_area("What should I build?", key="prompt", height=100)

api_key = os.getenv("GROQ_API_KEY")

if st.button("🚀 Generate project", type="primary", disabled=not prompt.strip()):
    if not api_key:
        st.error("Add your Groq API key in the sidebar (or set GROQ_API_KEY).")
        st.stop()
    os.environ["GROQ_API_KEY"] = api_key
    chosen = custom.strip() or model

    result = {}
    with st.status("Agents are working...", expanded=True) as status:
        try:
            for node, update in run_stream(prompt, chosen):
                icon = {"planner": "🧭", "architect": "🏗️", "coder": "💻"}.get(node, "•")
                st.write(f"{icon} {update.get('status', node)}")
                result.update({k: v for k, v in update.items() if k in ("project_dir", "plan", "tasks")})
            status.update(label="Project generated ✅", state="complete")
            st.session_state.result = result
        except Exception as e:  # surface rate-limit / auth errors nicely
            status.update(label="Generation failed", state="error")
            st.exception(e)


res = st.session_state.get("result")
if res and res.get("project_dir"):
    pdir = res["project_dir"]
    files = list_files(pdir)
    st.subheader(f"📁 {res['plan']['name']}")
    st.write(res["plan"]["description"])

    left, right = st.columns([1, 3])
    with left:
        st.download_button("⬇️ Download .zip", zip_project(pdir),
                           file_name=f"{Path(pdir).name}.zip", mime="application/zip",
                           use_container_width=True)
        st.markdown("**Files**")
        for f in files:
            st.text(f)
        st.caption(f"Saved at `{pdir}`")
        st.markdown("**Run locally**")
        if "index.html" in files:
            st.caption("Open `index.html` in your browser.")
        elif "requirements.txt" in files:
            st.caption("`pip install -r requirements.txt`, then follow the README.")
        elif "package.json" in files:
            st.caption("`npm install && npm start`")

    with right:
        tabs = ["📄 Code", "🗺️ Plan & tasks"] + (["👀 Preview"] if "index.html" in files else [])
        t = st.tabs(tabs)
        with t[0]:
            pick = st.selectbox("File", files)
            st.code(read_file(pdir, pick), language=LANG.get(Path(pick).suffix, "text"), line_numbers=True)
        with t[1]:
            st.json(res["plan"], expanded=False)
            for task in res.get("tasks", []):
                st.markdown(f"**`{task['filepath']}`**: {task['task_description']}")
        if "index.html" in files:
            with t[2]:
                components.html(inline_assets(pdir, read_file(pdir, "index.html")),
                                height=650, scrolling=True)
