import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os

DATA_FILE = "data_backup.json"
st.set_page_config(page_title="英语点读学生端", layout="wide")

def b64_to_img(b64_str):
    if not b64_str:
        return None
    try:
        buf = BytesIO(base64.b64decode(b64_str))
        img = Image.open(buf).convert("RGB")
        buf.close()
        return img
    except Exception:
        return None

def load_all_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

data = load_all_data()

st.title("📖 英语情景智能点读")
st.divider()

if data is None:
    st.error("❌ 未找到 data_backup.json，请将文件与学生端脚本放在同一文件夹！")
    st.stop()

img_list = list(data.keys())
if not img_list:
    st.warning("暂无场景图片数据")
    st.stop()

select_scene = st.selectbox("请选择学习场景", img_list)
scene_data = data[select_scene]
img = b64_to_img(scene_data["img_b64"])
hotspots = scene_data["hotspots"]

if not img:
    st.error("图片加载失败")
    st.stop()

orig_w, orig_h = img.size
buf = BytesIO()
img.save(buf, format="JPEG", quality=80)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
buf.close()
hot_json = json.dumps(hotspots, ensure_ascii=False)

html_code = f"""
<style>
    .word-tip {{
        position: fixed;
        background: rgba(0,0,0,0.75);
        color: #fff;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 20px;
        z-index: 2000;
        display: none;
        pointer-events:none;
        transform: translate(16px,16px);
    }}
    .modal-mask {{
        position: fixed;
        inset:0;
        background:rgba(0,0,0,0.55);
        z-index:3000;
        display:none;
    }}
    .word-card {{
        position: fixed;
        left:50%;
        top:50%;
        transform:translate(-50%,-50%);
        background:rgba(255,255,255,0.55);
        backdrop-filter: blur(6px);
        padding:32px;
        border-radius:12px;
        min-width:360px;
        text-align:center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }}
</style>
<div class="word-tip" id="tipBox"></div>
<div class="modal-mask" id="maskBox">
    <div class="word-card" id="cardBox">
        <h2 id="cardWord"></h2>
        <p id="cardPhon" style="font-size:18px;color:#555;margin:4px 0;"></p>
        <p id="cardCn" style="font-size:16px;color:#666;margin:4px 0;"></p>
        <p id="cardSent" style="font-size:16px;color:#444;margin:12px 0;"></p>
        <div style="margin-top:20px;">
            <button id="readWordBtn" style="padding:8px 16px;margin:0 6px;">🔊朗读单词</button>
            <button id="closeModalBtn" style="padding:8px 16px;margin:0 6px;">关闭</button>
        </div>
    </div>
</div>

<div id="scene-container" style="position:relative;width:100%;">
<img id="scene-img" src="data:image/jpeg;base64,{img_b64}" style="width:100%;display:block;">
</div>

<script>
const hotList = {hot_json};
const container = document.getElementById("scene-container");
const imgEl = document.getElementById("scene-img");
const tipBox = document.getElementById("tipBox");
const maskBox = document.getElementById("maskBox");
const cardBox = document.getElementById("cardBox");
const cardWord = document.getElementById("cardWord");
const cardPhon = document.getElementById("cardPhon");
const cardCn = document.getElementById("cardCn");
const cardSent = document.getElementById("cardSent");
const readWordBtn = document.getElementById("readWordBtn");
const closeModalBtn = document.getElementById("closeModalBtn");

let currentHot = null;
let voiceUS = null;

// 优先加载纯正美式发音
function loadVoice(){{
    const voices = speechSynthesis.getVoices();
    // 优先 en-US 美式女声
    voiceUS = voices.find(v => v.lang === "en-US" && v.name.toLowerCase().includes("female"));
    if(!voiceUS) voiceUS = voices.find(v => v.lang === "en-US");
}}
speechSynthesis.onvoiceschanged = loadVoice;
loadVoice();

function speakWord(text){{
    speechSynthesis.cancel();
    let u = new SpeechSynthesisUtterance(text);
    if(voiceUS) u.voice = voiceUS;
    u.lang = "en-US";
    u.rate = 0.90;
    u.pitch = 1.0;
    speechSynthesis.speak(u);
}}

function buildHotAreas(){{
    const scaleX = imgEl.offsetWidth / {orig_w};
    const scaleY = imgEl.offsetHeight / {orig_h};
    hotList.forEach((item,idx)=>{{
        let [x1,y1,x2,y2] = item.box;
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.left = (x1*scaleX)+'px';
        div.style.top = (y1*scaleY)+'px';
        div.style.width = ((x2-x1)*scaleX)+'px';
        div.style.height = ((y2-y1)*scaleY)+'px';
        div.style.background = 'transparent';
        div.style.zIndex = 10;

        div.onmouseover = ()=>{{
            tipBox.innerText = item.word;
            tipBox.style.display = "block";
            currentHot = item;
        }}
        div.onmouseout = ()=>{{
            tipBox.style.display = "none";
        }}
        div.onmousemove = (e)=>{{
            tipBox.style.left = e.clientX + "px";
            tipBox.style.top = e.clientY + "px";
        }}
        div.onclick = ()=>{{
            currentHot = item;
            cardWord.innerText = item.word;
            cardPhon.innerText = item.phonetic;
            cardCn.innerText = item.cn;
            cardSent.innerText = item.sentence;
            maskBox.style.display = "block";
        }}
        container.appendChild(div);
    }})
}}

closeModalBtn.onclick = ()=>{{
    maskBox.style.display = "none";
}}
maskBox.onclick = (e)=>{{
    if(e.target === maskBox) maskBox.style.display = "none";
}}
readWordBtn.onclick = ()=>{{
    if(currentHot) speakWord(currentHot.word);
}}

imgEl.onload = buildHotAreas;
window.addEventListener('resize', ()=>{{
    container.querySelectorAll('div[style*="z-index:10"]').forEach(d=>d.remove());
    setTimeout(buildHotAreas,100);
}})
</script>
"""
st.components.v1.html(html_code, height=int(orig_h * 0.78))

st.divider()
st.subheader("📚 本场景单词列表")
if len(hotspots) == 0:
    st.info("该场景暂无标注词汇")
else:
    hot_idx = st.radio(
        "选择词汇查看",
        range(len(hotspots)),
        format_func=lambda i: hotspots[i]["word"]
    )
    word_info = hotspots[hot_idx]
    w_text = word_info["word"]
    s_text = word_info["sentence"]

    st.markdown(f"# {word_info['word']}")
    st.markdown(f"音标：/{word_info['phonetic']}/")
    st.markdown(f"中文释义：{word_info['cn']}")
    st.markdown(f"例句：{word_info['sentence']}")

    read_js = f"""
    <script>
    let listVoice = null;
    function loadListVoice(){{
        const vs = speechSynthesis.getVoices();
        listVoice = vs.find(v => v.lang === "en-US" && v.name.toLowerCase().includes("female"));
        if(!listVoice) listVoice = vs.find(v => v.lang === "en-US");
    }}
    speechSynthesis.onvoiceschanged = loadListVoice;
    loadListVoice();

    function playAudio(){{
        speechSynthesis.cancel();
        let u1 = new SpeechSynthesisUtterance("{w_text}");
        if(listVoice) u1.voice = listVoice;
        u1.lang="en-US";
        u1.rate=0.90;
        u1.pitch=1.0;
        speechSynthesis.speak(u1);
        u1.onend = ()=>{{
            setTimeout(()=>{{
                let u2 = new SpeechSynthesisUtterance("{s_text}");
                if(listVoice) u2.voice = listVoice;
                u2.lang="en-US";
                u2.rate=0.90;
                u2.pitch=1.0;
                speechSynthesis.speak(u2);
            }},300);
        }}
    }}
    </script>
    <button onclick="playAudio()" style="padding:8px 20px;font-size:16px;background:#2563eb;color:white;border:none;border-radius:6px;">🔊朗读单词+例句</button>
    """
    st.components.v1.html(read_js, height=50)

st.divider()
st.caption("运行说明：将 data_backup.json 和 student.py 放在同一文件夹，启动即可加载场景")