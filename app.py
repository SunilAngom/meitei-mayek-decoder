import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import html as html_mod
import fitz  # PyMuPDF

st.set_page_config(
    page_title="Meitei Mayek Decoder",
    page_icon="🔤",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Meetei+Mayek&display=swap');

/* tighten default Streamlit padding for wide layout */
.block-container { padding-top: 1.2rem !important; padding-bottom: 0.5rem !important; }

.meitei-output {
    font-family: 'Noto Sans Meetei Mayek', serif;
    font-size: 20px;
    line-height: 2;
    padding: 14px;
    border: 1px solid #ccc;
    border-radius: 8px;
    min-height: 180px;
    white-space: pre-wrap;
    word-wrap: break-word;
    background: #fafafa;
    color: #111;
}

/* vertical divider between columns */
div[data-testid="column"]:first-child {
    border-right: 1px solid #e0e0e0;
    padding-right: 1.5rem;
}
div[data-testid="column"]:last-child {
    padding-left: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────

def load_mapping():
    try:
        return json.loads(st.secrets["MAPPING_JSON"])
    except Exception as e:
        st.error(f"Secrets error: {e}")
        return {}

def decode_text(text, mapping):
    return "\n".join(
        "".join(mapping.get(ch, ch) for ch in line)
        for line in text.split("\n")
    )


def render_pdf_pages(file_bytes, dpi=150):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_b64 = base64.b64encode(pix.tobytes("png")).decode()
        text = page.get_text("text")
        pages.append({"img": img_b64, "text": text})
    doc.close()
    return pages


def show_pdf_pages(pages, height=700):
    imgs = "".join(
        f'<img src="data:image/png;base64,{p["img"]}" '
        f'style="display:block;width:100%;margin-bottom:10px;'
        f'box-shadow:0 3px 14px rgba(0,0,0,.7)">'
        for p in pages
    )
    components.html(f"""<!DOCTYPE html>
<html><head><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:#525659;overflow:auto}}
#v{{padding:10px}}
</style></head>
<body><div id="v">{imgs}</div></body>
</html>""", height=height, scrolling=True)


def copy_btn_html(b64_str, key):
    return f"""
    <button id="cb_{key}"
        onclick="
            var b=Uint8Array.from(atob('{b64_str}'),function(c){{return c.charCodeAt(0)}});
            var t=new TextDecoder().decode(b);
            navigator.clipboard.writeText(t).then(function(){{
                var btn=document.getElementById('cb_{key}');
                btn.textContent='Copied!';btn.style.background='#21c354';
                setTimeout(function(){{btn.textContent='Copy';btn.style.background='#d9534f';}},1500);
            }});
        "
        style="background:#d9534f;color:#fff;border:none;padding:6px 18px;
               border-radius:5px;cursor:pointer;font-size:13px;font-weight:500;">
        Copy
    </button>"""

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## Meitei Mayek Decoder")
st.caption("Maintained and developed by **Sunil Angom**")
st.divider()

mapping = load_mapping()
if not mapping:
    st.error("Mapping not loaded — check secrets.toml")
    st.stop()

for key, default in [
    ("output",""), ("input_key",0),
    ("pdf_bytes",None), ("pdf_pages",None), ("pdf_uploader_key",0),
    ("col_split", 6),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════  COLUMN RESIZE BAR  ══════════════════════════
r1, r2, r3 = st.columns([1, 4, 1])
with r1:
    if st.button("◀  PDF wider", use_container_width=True, key="col_left"):
        st.session_state.col_split = min(8, st.session_state.col_split + 1)
        st.rerun()
with r2:
    pct = st.session_state.col_split * 10
    st.markdown(
        f"<div style='text-align:center;font-size:12px;color:#888;padding-top:6px'>"
        f"PDF {pct}%  ·  Decoder {100-pct}%</div>",
        unsafe_allow_html=True,
    )
with r3:
    if st.button("Decoder wider  ▶", use_container_width=True, key="col_right"):
        st.session_state.col_split = max(2, st.session_state.col_split - 1)
        st.rerun()

# ═══════════════════════════  SIDE-BY-SIDE  ═══════════════════════════════
left, right = st.columns([st.session_state.col_split, 10 - st.session_state.col_split])

# ── LEFT: PDF Viewer ───────────────────────────────────────────────────────
with left:
    hA, hB = st.columns([4, 1])
    with hA:
        st.markdown("### PDF Viewer")
    with hB:
        if st.button("Clear", key="btn_pdf_clear", use_container_width=True):
            st.session_state.pdf_bytes        = None
            st.session_state.pdf_pages        = None
            st.session_state.pdf_uploader_key += 1
            st.rerun()

    pdf_up = st.file_uploader(
        "Open a PDF file", type=["pdf"],
        key=f"pdf_uploader_{st.session_state.pdf_uploader_key}"
    )
    if pdf_up is not None:
        new_bytes = pdf_up.read()
        if new_bytes != st.session_state.pdf_bytes:
            st.session_state.pdf_bytes = new_bytes
            st.session_state.pdf_pages = None

    if st.session_state.pdf_bytes:
        if st.session_state.pdf_pages is None:
            with st.spinner("Rendering PDF…"):
                st.session_state.pdf_pages = render_pdf_pages(st.session_state.pdf_bytes)

        show_pdf_pages(st.session_state.pdf_pages, height=680)

        all_text = "\n\n".join(p["text"] for p in st.session_state.pdf_pages)
        with st.expander("📋 Copy text from PDF"):
            st.text_area(
                "Select all (Ctrl+A) then copy (Ctrl+C):",
                value=all_text, height=180,
                key="pdf_text_area",
            )
    else:
        st.markdown(
            '<div style="background:#464646;height:380px;border-radius:6px;'
            'display:flex;align-items:center;justify-content:center;'
            'color:#aaa;font-size:14px;">Upload a PDF to view it here</div>',
            unsafe_allow_html=True,
        )

# ── RIGHT: Decoder ─────────────────────────────────────────────────────────
with right:
    st.markdown("### Decoder")
    input_text = st.text_area(
        "Enter decode code:",
        placeholder="Type or paste decode code here...",
        height=220,
        key=f"input_area_{st.session_state.input_key}"
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Decode", type="primary", use_container_width=True, key="btn_decode"):
            if input_text.strip():
                st.session_state.output = decode_text(input_text, mapping)
            else:
                st.session_state.output = ""
                st.warning("Please enter some decode code text.")
    with c2:
        if st.button("Clear", use_container_width=True, key="btn_clear"):
            st.session_state.output = ""
            st.session_state.input_key += 1
            st.rerun()

    st.markdown("**Meitei Mayek Output:**")
    if st.session_state.output:
        safe = html_mod.escape(st.session_state.output).replace("\n", "<br>")
        st.markdown(f'<div class="meitei-output">{safe}</div>', unsafe_allow_html=True)
        b64 = base64.b64encode(st.session_state.output.encode("utf-8")).decode("ascii")
        components.html(copy_btn_html(b64, "dec"), height=46)
    else:
        st.markdown(
            '<div class="meitei-output" style="color:#aaa;font-family:sans-serif;'
            'font-size:14px;">Output will appear here...</div>',
            unsafe_allow_html=True,
        )

st.divider()
st.caption("© Sunil Angom · Meitei Mayek Decoder")
