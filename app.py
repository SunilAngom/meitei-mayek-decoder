import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import html as html_mod

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


def pdf_viewer(file_bytes, height=720):
    b64 = base64.b64encode(file_bytes).decode("ascii")
    components.html(f"""<!DOCTYPE html>
<html>
<head>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:#525659;display:flex;flex-direction:column;overflow:hidden}}
#toolbar{{
  background:#3a3a3a;padding:6px 10px;display:flex;align-items:center;
  gap:8px;flex-shrink:0;border-bottom:1px solid #222;
}}
#toolbar button{{
  background:#555;color:#eee;border:none;border-radius:4px;
  padding:3px 10px;cursor:pointer;font-size:15px;font-weight:bold;
}}
#toolbar button:hover{{background:#777}}
#zoom-label{{color:#ddd;font-family:sans-serif;font-size:13px;min-width:44px;text-align:center}}
#scroll{{flex:1;overflow-y:scroll;overflow-x:auto;padding:10px}}
#viewer{{display:flex;flex-direction:column;align-items:center}}
.page-wrap{{position:relative;margin-bottom:10px;box-shadow:0 2px 10px rgba(0,0,0,.6)}}
.page-wrap canvas{{display:block}}
.textLayer{{
  position:absolute;left:0;top:0;right:0;bottom:0;
  overflow:hidden;opacity:0.25;line-height:1;
  -webkit-text-size-adjust:none;text-size-adjust:none;
}}
.textLayer span{{
  color:transparent;position:absolute;white-space:pre;
  cursor:text;transform-origin:0% 0%;
}}
.textLayer span::selection{{background:rgba(0,100,255,0.35)}}
#msg{{color:#ccc;font-family:sans-serif;font-size:13px;padding:30px;text-align:center}}
</style>
</head>
<body>
<div id="toolbar">
  <button onclick="zoom(-0.2)">−</button>
  <span id="zoom-label">140%</span>
  <button onclick="zoom(+0.2)">+</button>
</div>
<div id="scroll">
  <div id="msg">Loading PDF…</div>
  <div id="viewer"></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
document.getElementById('scroll').addEventListener('wheel',function(e){{
  e.stopPropagation();
  this.scrollTop+=e.deltaY;
}},{{passive:false}});
var b64="{b64}";
var bin=atob(b64),arr=new Uint8Array(bin.length);
for(var i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
var pdfDoc=null, scale=1.4;
pdfjsLib.getDocument({{data:arr}}).promise.then(function(pdf){{
  pdfDoc=pdf;
  document.getElementById('msg').style.display='none';
  renderAll();
}}).catch(function(e){{
  document.getElementById('msg').textContent='Could not load PDF: '+e.message;
}});
function renderAll(){{
  var v=document.getElementById('viewer');
  v.innerHTML='';
  document.getElementById('zoom-label').textContent=Math.round(scale*100)+'%';
  function render(n){{
    pdfDoc.getPage(n).then(function(page){{
      var vp=page.getViewport({{scale:scale}});
      var wrap=document.createElement('div');
      wrap.className='page-wrap';
      wrap.style.width=vp.width+'px';
      wrap.style.height=vp.height+'px';
      v.appendChild(wrap);
      var c=document.createElement('canvas');
      c.width=vp.width; c.height=vp.height;
      wrap.appendChild(c);
      page.render({{canvasContext:c.getContext('2d'),viewport:vp}}).promise.then(function(){{
        page.getTextContent().then(function(tc){{
          var tl=document.createElement('div');
          tl.className='textLayer';
          wrap.appendChild(tl);
          try{{pdfjsLib.renderTextLayer({{textContentSource:tc,container:tl,viewport:vp,textDivs:[]}});}}catch(e){{}}
        }});
        if(n<pdfDoc.numPages) render(n+1);
      }});
    }});
  }}
  render(1);
}}
function zoom(delta){{
  scale=Math.min(4, Math.max(0.4, scale+delta));
  renderAll();
}}
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
    ("pdf_bytes",None), ("pdf_uploader_key",0),
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
            st.session_state.pdf_uploader_key += 1
            st.rerun()

    pdf_up = st.file_uploader(
        "Open a PDF file", type=["pdf"],
        key=f"pdf_uploader_{st.session_state.pdf_uploader_key}"
    )
    if pdf_up is not None:
        st.session_state.pdf_bytes = pdf_up.read()

    if st.session_state.pdf_bytes:
        pdf_viewer(st.session_state.pdf_bytes, height=720)
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
