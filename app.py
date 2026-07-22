import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os

DATA_FILE = "data_backup.json"
st.set_page_config(page_title="英语情景点读-学生端", layout="wide")

def b64_to_img(b64_str):
    if not b64_str or not isinstance(b64_str, str):
        return None
    try:
        buf = BytesIO(base64.b64decode(b64_str))
        img = Image.open(buf).convert("RGB")
        buf.close()
        return img
    except Exception:
        return None

def img_to_b64(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=80)
    res = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()
    return res

# 内置调试示例（无json自动启用）
def get_demo_data():
    w, h = 800, 600
    demo_img = Image.new("RGB", (w, h), color=(240, 248, 255))
    hotspots = [
        {
            "box": [100, 100, 300, 300],
            "word": "book",
            "phonetic": "/bʊk/",
            "cn": "书本",
            "sentence": "This is a book."
        },
        {
            "box": [400, 200, 600, 400],
            "word": "pen",
            "phonetic": "/pen/",
            "cn": "钢笔",
            "sentence": "I have a pen."
        }
    ]
    return {
        "demo_test.jpg": {
            "img_b64": img_to_b64(demo_img),
            "hotspots": hotspots
        }
    }

def load_scene_data():
    demo = get_demo_data()
    if not os.path.exists(DATA_FILE):
        return demo
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        valid_pool = {}
        for name, data in raw_json.items():
            img = b64_to_img(data.get("img_b64", ""))
            if img:
                valid_pool[name] = {
                    "img": img,
                    "hotspots": data.get("hotspots", [])
                }
        if len(valid_pool) == 0:
            return demo
        return valid_pool
    except Exception:
        return demo

scene_pool = load_scene_data()

# 存储当前选中热点（点击弹出卡片）
if "active_hot" not in st.session_state:
    st.session_state.active_hot = None

st.title("沉浸式英语情景点读")
st.divider()

img_name_list = list(scene_pool.keys())
select_img = st.selectbox("选择学习场景", img_name_list)
scene_info = scene_pool[select_img]
origin_img = scene_info["img"]
hotspot_list = scene_info["hotspots"]
orig_w, orig_h = origin_img.size

# 图片base64
buf = BytesIO()
origin_img.save(buf, format="JPEG", quality=80)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
buf.close()
hot_json = json.dumps(hotspot_list, ensure_ascii=False)

# ========== 前端JS实现全部交互需求 ==========
html_code = f"""
<style>
    /* 右下角悬浮单词提示 */
    .word-tip {{
        position: fixed;
        right: 24px;
        bottom: 120px;
        background: rgba(0,0,0,0.75);
        color: #fff;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 20px;
        z-index: 2000;
        display: none;
        pointer-events:none;
    }}
    /* 单词弹窗遮罩 */
    .modal-mask {{
        position: fixed;
        inset:0;
        background:rgba(0,0,0,0.55);
        z-index:3000;
        display:none;
    }}
    /* 单词卡片 */
    .word-card {{
        position: fixed;
        left:50%;
        top:50%;
        transform:translate(-50%,-50%);
        background:#ffffff;
        padding:32px;
        border-radius:12px;
        min-width:360px;
        text-align:center;
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

// 朗读英文单词
function speakWord(text){{
    speechSynthesis.cancel();
    let u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.95;
    speechSynthesis.speak(u);
}}

// 生成透明热点区域
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
        div.style.background = 'transparent'; /* 完全透明，不显示方框 */
        div.style.zIndex = 10;

        // 鼠标悬浮：右下角显示单词小样
        div.onmouseover = ()=>{{
            tipBox.innerText = item.word;
            tipBox.style.display = "block";
            currentHot = item;
        }}
        div.onmouseout = ()=>{{
            tipBox.style.display = "none";
        }}
        // 点击热点：弹出单词卡片
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

// 关闭弹窗
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
    // 清空旧区域重新生成
    container.querySelectorAll('div[style*="z-index:10"]').forEach(d=>d.remove());
    setTimeout(buildHotAreas,100);
}})
</script>
"""
st.components.v1.html(html_code, height=int(orig_h * 0.78))

st.divider()
st.subheader("📚 本场景单词列表")
if len(hotspot_list) == 0:
    st.info("该场景暂无标注词汇")
else:
    hot_idx = st.radio("选择词汇查看", range(len(hotspot_list)), format_func=lambda i: hotspot_list[i]["word"])
    word_info = hotspot_list[hot_idx]
    w_text = word_info["word"]
    s_text = word_info["sentence"]

    st.markdown(f"# {word_info['word']}")
    st.markdown(f"音标：/{word_info['phonetic']}/")
    st.markdown(f"中文释义：{word_info['cn']}")
    st.markdown(f"例句：{word_info['sentence']}")

    # 列表朗读：只读【单词 + 例句】英文，不读中文
    read_js = f"""
    <script>
    function playAudio(){{
        speechSynthesis.cancel();
        let u1 = new SpeechSynthesisUtterance("{w_text}");
        u1.lang="en-US";
        u1.rate=0.95;
        speechSynthesis.speak(u1);
        u1.onend = ()=>{{
            let u2 = new SpeechSynthesisUtterance("{s_text}");
            u2.lang="en-US";
            u2.rate=0.9;
            speechSynthesis.speak(u2);
        }}
    }}
    </script>
    <button onclick="playAudio()" style="padding:8px 20px;font-size:16px;background:#2563eb;color:white;border:none;border-radius:6px;">🔊朗读单词+例句</button>
    """
    st.components.v1.html(read_js, height=50)

st.divider()
st.caption("运行说明：将 data_backup.json 和 student.py 放在同一文件夹，启动即可加载场景")