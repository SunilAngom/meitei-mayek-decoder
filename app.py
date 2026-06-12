import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import html as html_mod
import re
import io
import olefile
import fitz  # PyMuPDF
from collections import Counter

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

FILE_PAT = re.compile(r"[A-Za-z]:\\|\.tif|\.pmd|\.doc|\.jpg|\.png|\.TIF", re.IGNORECASE)

def extract_pmd_text(file_bytes, mapping):
    try:
        import io
        ole = olefile.OleFileIO(io.BytesIO(file_bytes))
        streams = ole.listdir()
        stream_name = next(("/".join(e) for e in streams if e[-1] == "PageMaker"), None)
        data = ole.openstream(stream_name).read() if stream_name else file_bytes
        ole.close()
    except Exception:
        data = file_bytes

    valid = set(mapping.keys())
    segments = []
    offset = 0
    for seg in data.split(b"\x00"):
        seg_len = len(seg) + 1
        try:
            s = seg.decode("windows-1252", errors="ignore").strip()
            p = re.sub(r"[^\x20-\x7e]", "", s)
            if (len(p) >= 10
                    and not FILE_PAT.search(p)
                    and any(c in p for c in ("[", "\\", "_"))):
                non_sp = [c for c in p if c not in (" ", "\t", "`")]
                if len(non_sp) >= 8:
                    sr = p.count(" ") / len(p)
                    if 0.08 <= sr <= 0.45:
                        tf = Counter(non_sp).most_common(1)[0][1] / len(non_sp)
                        dr = sum(c.isdigit() for c in non_sp) / len(non_sp)
                        if tf <= 0.65 and dr <= 0.5:
                            sc = sum(1 for c in non_sp if c in valid) / len(non_sp)
                            if sc >= 0.82:
                                clean = p.replace("``", "\n").replace("`", "").strip()
                                segments.append((offset, clean))
        except Exception:
            pass
        offset += seg_len
    return "\n\n".join(t for _, t in segments)

def pdf_viewer(file_bytes, height=700):
    """Render all PDF pages as images and show in a scrollable dark workspace."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_b64 = []
    scale = fitz.Matrix(1.8, 1.8)  # 1.8× zoom for crisp display
    for page in doc:
        pix = page.get_pixmap(matrix=scale, alpha=False)
        img_bytes = pix.tobytes("png")
        pages_b64.append(base64.b64encode(img_bytes).decode("ascii"))
    doc.close()

    imgs_js = "[" + ",".join(f'"{b}"' for b in pages_b64) + "]"
    total   = len(pages_b64)

    components.html(f"""<!DOCTYPE html>
<html>
<head>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;font-family:sans-serif}}
body{{background:#464646;display:flex;flex-direction:column}}

#toolbar{{
    background:#2c2c2c;border-bottom:1px solid #111;
    padding:5px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0;
}}
.title{{color:#ddd;font-size:12px;font-weight:600;flex:1}}
.nav-btn{{background:#3a3a3a;color:#ccc;border:none;padding:3px 10px;
          border-radius:3px;cursor:pointer;font-size:12px;}}
.nav-btn:hover{{background:#555}}
.nav-btn:disabled{{opacity:.35;cursor:default}}
#page-info{{color:#aaa;font-size:12px;min-width:60px;text-align:center}}
#zoom-out,#zoom-in{{background:#3a3a3a;color:#ccc;border:none;width:26px;height:26px;
                    border-radius:3px;cursor:pointer;font-size:15px;line-height:1}}
#zoom-out:hover,#zoom-in:hover{{background:#555}}

#workspace{{
    flex:1;overflow:auto;padding:20px;
    display:flex;justify-content:center;align-items:flex-start;
    scrollbar-width:thin;scrollbar-color:#666 #3a3a3a;
}}
#workspace::-webkit-scrollbar{{width:9px;height:9px;background:#3a3a3a}}
#workspace::-webkit-scrollbar-thumb{{background:#666;border-radius:4px}}

#page-wrap{{display:inline-block}}
#page-img{{
    display:block;
    box-shadow:0 4px 24px rgba(0,0,0,.7);
    transition:width .15s ease;
    max-width:none;
}}
</style>
</head>
<body>
<div id="toolbar">
  <span class="title">📰 Wayel Kati</span>
  <button class="nav-btn" id="btn-prev" onclick="changePage(-1)" disabled>&#8592; Prev</button>
  <span id="page-info">1 / {total}</span>
  <button class="nav-btn" id="btn-next" onclick="changePage(1)" {'disabled' if total<=1 else ''}>Next &#8594;</button>
  <button id="zoom-out" onclick="zoom(-0.15)" title="Zoom out">&#8722;</button>
  <button id="zoom-in"  onclick="zoom(+0.15)" title="Zoom in">&#43;</button>
</div>
<div id="workspace">
  <div id="page-wrap">
    <img id="page-img" src="" alt="page">
  </div>
</div>
<script>
var pages={imgs_js};
var cur=0, scale=1.0;
var baseW=680;

function render(){{
  var img=document.getElementById('page-img');
  img.onload=function(){{
    img.style.width=(baseW*scale)+'px';
  }};
  img.src='data:image/png;base64,'+pages[cur];
  document.getElementById('page-info').textContent=(cur+1)+' / '+pages.length;
  document.getElementById('btn-prev').disabled=(cur===0);
  document.getElementById('btn-next').disabled=(cur===pages.length-1);
}}

function changePage(d){{
  cur=Math.max(0,Math.min(pages.length-1,cur+d));
  document.getElementById('workspace').scrollTo(0,0);
  render();
}}

function zoom(d){{
  scale=Math.max(0.4,Math.min(3.0,scale+d));
  var img=document.getElementById('page-img');
  img.style.width=(baseW*scale)+'px';
}}

render();
</script>
</body>
</html>""", height=height, scrolling=False)


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

def indesign_viewer(title, raw_text, decoded_text, height=640):
    raw_safe     = html_mod.escape(raw_text).replace("\n", "<br>")
    decoded_safe = html_mod.escape(decoded_text).replace("\n", "<br>")
    b64_raw = base64.b64encode(raw_text.encode("utf-8")).decode("ascii")
    b64_dec = base64.b64encode(decoded_text.encode("utf-8")).decode("ascii")
    title_safe = html_mod.escape(title)

    components.html(f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Meetei+Mayek&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden}}
body{{font-family:'Inter',sans-serif;background:#464646;display:flex;flex-direction:column}}

#toolbar{{
    background:#2c2c2c;border-bottom:1px solid #111;
    padding:5px 12px;display:flex;align-items:center;gap:8px;flex-shrink:0;
}}
.doc-name{{color:#ddd;font-size:12px;font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tbtn{{background:#3a3a3a;color:#bbb;border:none;padding:3px 10px;border-radius:3px;cursor:pointer;font-size:11px;}}
.tbtn.active{{background:#0078d4;color:#fff}}
.tbtn:hover:not(.active){{background:#505050}}
#cpybtn{{background:#d9534f;color:#fff;border:none;padding:3px 12px;border-radius:3px;cursor:pointer;font-size:11px;font-weight:600}}
#cpybtn:hover{{background:#b52b27}}

#workspace{{flex:1;overflow-y:auto;padding:20px 12px;scrollbar-width:thin;scrollbar-color:#666 #3a3a3a}}
#workspace::-webkit-scrollbar{{width:8px;background:#3a3a3a}}
#workspace::-webkit-scrollbar-thumb{{background:#666;border-radius:4px}}

.page{{background:#fff;width:100%;max-width:600px;margin:0 auto 20px;
       padding:40px 44px;box-shadow:0 3px 16px rgba(0,0,0,.55);min-height:500px;position:relative}}
.page-content{{font-family:'Noto Sans Meetei Mayek',serif;font-size:16px;line-height:2.1;color:#111;word-wrap:break-word;white-space:pre-wrap}}
.page-content.raw{{font-family:'Courier New',monospace;font-size:13px;line-height:1.8;color:#222}}
.pg-num{{position:absolute;bottom:14px;right:20px;font-size:10px;color:#bbb;font-family:'Inter',sans-serif}}
</style>
</head>
<body>
<div id="toolbar">
  <span class="doc-name">📄 {title_safe}</span>
  <button class="tbtn active" id="btnd" onclick="show('decoded')">Meitei Mayek</button>
  <button class="tbtn" id="btnr" onclick="show('raw')">Raw Code</button>
  <button id="cpybtn" onclick="copy()">Copy</button>
</div>
<div id="workspace">
  <div class="page">
    <div class="page-content" id="pdec">{decoded_safe}</div>
    <div class="page-content raw" id="praw" style="display:none">{raw_safe}</div>
    <div class="pg-num">© Sunil Angom</div>
  </div>
</div>
<script>
var cur='decoded';
var d={{decoded:'{b64_dec}',raw:'{b64_raw}'}};
function show(t){{
  cur=t;
  document.getElementById('pdec').style.display=t==='decoded'?'':'none';
  document.getElementById('praw').style.display=t==='raw'?'':'none';
  document.getElementById('btnd').className='tbtn'+(t==='decoded'?' active':'');
  document.getElementById('btnr').className='tbtn'+(t==='raw'?' active':'');
}}
function copy(){{
  var b=Uint8Array.from(atob(d[cur]),function(c){{return c.charCodeAt(0)}});
  navigator.clipboard.writeText(new TextDecoder().decode(b)).then(function(){{
    var btn=document.getElementById('cpybtn');
    btn.textContent='Copied!';btn.style.background='#21c354';
    setTimeout(function(){{btn.textContent='Copy';btn.style.background='#d9534f';}},1500);
  }});
}}
</script>
</body>
</html>""", height=height, scrolling=False)

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
    ("pmd_raw",""), ("pmd_decoded",""), ("pmd_name",""), ("pmd_uploader_key",0),
    ("pdf_bytes",None), ("pdf_name",""), ("pdf_uploader_key",0),
    ("left_view","pmd"),   # "pmd" or "pdf"
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════  SIDE-BY-SIDE  ═══════════════════════════════
left, right = st.columns([6, 4])

# ── LEFT: switcher between PDF viewer and PMD text viewer ──────────────────
with left:
    # ── header row: title + tab switcher + clear ──────────────────────────
    hA, hB, hC = st.columns([3, 2, 1])
    with hA:
        st.markdown("### Document Viewer")
    with hB:
        v = st.radio("View", ["PDF", "PMD Text"], horizontal=True,
                     key="view_switch", label_visibility="collapsed")
        st.session_state.left_view = "pdf" if v == "PDF" else "pmd"
    with hC:
        if st.button("Clear", key="btn_left_clear", use_container_width=True):
            st.session_state.pmd_raw          = ""
            st.session_state.pmd_decoded      = ""
            st.session_state.pmd_name         = ""
            st.session_state.pmd_uploader_key += 1
            st.session_state.pdf_bytes        = None
            st.session_state.pdf_name         = ""
            st.session_state.pdf_uploader_key += 1
            st.rerun()

    # ── PDF VIEW ─────────────────────────────────────────────────────────
    if st.session_state.left_view == "pdf":
        pdf_up = st.file_uploader(
            "Open a PDF file", type=["pdf"],
            key=f"pdf_uploader_{st.session_state.pdf_uploader_key}"
        )
        if pdf_up is not None:
            st.session_state.pdf_bytes = pdf_up.read()
            st.session_state.pdf_name  = pdf_up.name
            st.success(f"**{pdf_up.name}** — {len(st.session_state.pdf_bytes):,} bytes")

        if st.session_state.pdf_bytes:
            pdf_viewer(st.session_state.pdf_bytes, height=700)
        else:
            st.markdown(
                '<div style="background:#464646;height:340px;border-radius:6px;'
                'display:flex;align-items:center;justify-content:center;'
                'color:#aaa;font-size:14px;">Upload a PDF to view the newspaper here</div>',
                unsafe_allow_html=True,
            )

    # ── PMD TEXT VIEW ─────────────────────────────────────────────────────
    else:
        pmd_up = st.file_uploader(
            "Open a PageMaker (.pmd) file", type=["pmd"],
            key=f"pmd_uploader_{st.session_state.pmd_uploader_key}"
        )
        if pmd_up is not None:
            with st.spinner("Extracting text…"):
                fb  = pmd_up.read()
                raw = extract_pmd_text(fb, mapping)
            if raw.strip():
                st.session_state.pmd_raw     = raw
                st.session_state.pmd_decoded = decode_text(raw, mapping)
                st.session_state.pmd_name    = pmd_up.name
                st.success(f"**{pmd_up.name}** — {len(raw):,} chars extracted")
            else:
                st.warning("No decodable Meitei Mayek text found.")
                st.session_state.pmd_raw = st.session_state.pmd_decoded = ""

        if st.session_state.pmd_raw:
            indesign_viewer(
                title        = st.session_state.pmd_name,
                raw_text     = st.session_state.pmd_raw,
                decoded_text = st.session_state.pmd_decoded,
                height       = 700,
            )
        else:
            st.markdown(
                '<div style="background:#464646;height:340px;border-radius:6px;'
                'display:flex;align-items:center;justify-content:center;'
                'color:#aaa;font-size:14px;">Upload a PMD file to extract text</div>',
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
