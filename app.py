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


def pdf_viewer(file_bytes, height=680):
    b64 = base64.b64encode(file_bytes).decode("ascii")
    components.html(f"""<!DOCTYPE html>
<html>
<head>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:#525659;display:flex;flex-direction:column;overflow:hidden}}
#toolbar{{
  background:#3a3a3a;padding:6px 12px;display:flex;align-items:center;
  gap:8px;flex-shrink:0;border-bottom:1px solid #222;
}}
#toolbar button{{
  background:#555;color:#eee;border:none;border-radius:4px;
  padding:4px 14px;cursor:pointer;font-size:16px;font-weight:bold;line-height:1;
}}
#toolbar button:hover{{background:#888}}
#zoom-label{{color:#ddd;font-family:sans-serif;font-size:13px;min-width:48px;text-align:center}}
#scroll{{flex:1;overflow:auto;padding:12px}}
#viewer{{display:flex;flex-direction:column;align-items:center;min-width:fit-content}}
.page-wrap{{position:relative;margin-bottom:12px;background:#fff;box-shadow:0 3px 14px rgba(0,0,0,.7)}}
.page-wrap canvas{{display:block}}
.textLayer{{
  position:absolute;left:0;top:0;right:0;bottom:0;
  overflow:hidden;line-height:1;text-align:initial;
  -webkit-text-size-adjust:none;text-size-adjust:none;
}}
.textLayer span,.textLayer br{{
  color:transparent;position:absolute;white-space:pre;
  cursor:text;transform-origin:0% 0%;
  -webkit-user-select:text;user-select:text;
}}
.textLayer ::selection{{background:rgba(0,120,255,0.35);color:transparent}}
#msg{{color:#ccc;font:13px sans-serif;padding:30px;text-align:center}}
</style>
</head>
<body>
<div id="toolbar">
  <button onclick="zoom(-0.25)">−</button>
  <span id="zoom-label">…</span>
  <button onclick="zoom(+0.25)">+</button>
  <button onclick="fitWidth()" style="font-size:12px;padding:4px 10px">Fit</button>
</div>
<div id="scroll">
  <div id="msg">Loading PDF…</div>
  <div id="viewer"></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
var scr=document.getElementById('scroll');
scr.addEventListener('wheel',function(e){{e.stopPropagation();scr.scrollTop+=e.deltaY;}},{{passive:false}});
var DPR=Math.max(window.devicePixelRatio||1,2);
var b64="{b64}";
var bin=atob(b64),arr=new Uint8Array(bin.length);
for(var i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
var pdfDoc=null,scale=1.0;
pdfjsLib.getDocument({{data:arr}}).promise.then(function(pdf){{
  pdfDoc=pdf;
  document.getElementById('msg').style.display='none';
  pdfDoc.getPage(1).then(function(page){{
    var nativeW=page.getViewport({{scale:1}}).width;
    scale=Math.max(1.2,(scr.clientWidth-24)/nativeW);
    renderAll();
  }});
}}).catch(function(e){{
  document.getElementById('msg').textContent='Error: '+e.message;
}});
function renderAll(){{
  document.getElementById('viewer').innerHTML='';
  document.getElementById('zoom-label').textContent=Math.round(scale*100)+'%';
  renderPage(1);
}}
function renderPage(n){{
  pdfDoc.getPage(n).then(function(page){{
    var vpCSS=page.getViewport({{scale:scale}});
    var vpHD=page.getViewport({{scale:scale*DPR}});
    var wrap=document.createElement('div');
    wrap.className='page-wrap';
    wrap.style.width=vpCSS.width+'px';
    wrap.style.height=vpCSS.height+'px';
    document.getElementById('viewer').appendChild(wrap);
    var c=document.createElement('canvas');
    c.width=vpHD.width; c.height=vpHD.height;
    c.style.width=vpCSS.width+'px'; c.style.height=vpCSS.height+'px';
    wrap.appendChild(c);
    var ctx=c.getContext('2d');
    ctx.imageSmoothingEnabled=true;
    ctx.imageSmoothingQuality='high';
    page.render({{canvasContext:ctx,viewport:vpHD}}).promise.then(function(){{
      page.getTextContent().then(function(tc){{
        var tl=document.createElement('div');
        tl.className='textLayer';
        wrap.appendChild(tl);
        pdfjsLib.renderTextLayer({{textContent:tc,container:tl,viewport:vpCSS,textDivs:[]}});
      }});
      if(n<pdfDoc.numPages) renderPage(n+1);
    }});
  }});
}}
function zoom(d){{scale=Math.min(5,Math.max(0.3,scale+d));renderAll();}}
function fitWidth(){{
  if(!pdfDoc)return;
  pdfDoc.getPage(1).then(function(page){{
    scale=Math.max(0.5,(scr.clientWidth-24)/page.getViewport({{scale:1}}).width);
    renderAll();
  }});
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
    ("col_split",6), ("pdf_minimized",False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ═══════════════════════════  TOOLBAR  ════════════════════════════════════
tb1, tb2, tb3, tb4 = st.columns([1, 3, 1, 1])
with tb1:
    if not st.session_state.pdf_minimized:
        if st.button("◀  PDF wider", use_container_width=True, key="col_left"):
            st.session_state.col_split = min(8, st.session_state.col_split + 1)
            st.rerun()
with tb2:
    if not st.session_state.pdf_minimized:
        pct = st.session_state.col_split * 10
        st.markdown(
            f"<div style='text-align:center;font-size:12px;color:#888;padding-top:6px'>"
            f"PDF {pct}%  ·  Decoder {100-pct}%</div>",
            unsafe_allow_html=True,
        )
with tb3:
    if not st.session_state.pdf_minimized:
        if st.button("Decoder wider  ▶", use_container_width=True, key="col_right"):
            st.session_state.col_split = max(2, st.session_state.col_split - 1)
            st.rerun()
with tb4:
    min_label = "▼ Show PDF" if st.session_state.pdf_minimized else "▲ Hide PDF"
    if st.button(min_label, use_container_width=True, key="btn_pdf_min"):
        st.session_state.pdf_minimized = not st.session_state.pdf_minimized
        st.rerun()

# ═══════════════════════════  LAYOUT  ═════════════════════════════════════
if st.session_state.pdf_minimized:
    left  = None
    right = st.container()
else:
    _cols = st.columns([st.session_state.col_split, 10 - st.session_state.col_split])
    left, right = _cols[0], _cols[1]

# ── LEFT: PDF Viewer (hidden when minimized) ───────────────────────────────
if left is not None:
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
            pdf_viewer(st.session_state.pdf_bytes, height=680)
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
