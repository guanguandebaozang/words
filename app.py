import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os

# 线下更新数据文件
DATA_FILE = "data_backup.json"

st.set_page_config(page_title="英语情景点读-学生端", layout="wide")

def b64_to_img(b64_str):
    if not b64 or not isinstance(b64_str, str):
        return None
    try:
        raw_bytes = base64.b64decode(b64_str)
        buf = BytesIO(raw_bytes)
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

# 标准示例数据（兜底专用）
def get_demo_data():
    w, h = 800, 600
    demo_img = Image.new("RGB", (w, h), color=(240, 248, 255))
    demo_hotspots = [
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
            "hotspots": demo_hotspots
        }
    }

# 加载并过滤损坏图片
def load_scene_data():
    demo_pool = get_demo_data()
    if not os.path.exists(DATA_FILE):
        return demo_pool
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        valid_data = {}
        for name, item in raw.items():
            b64_txt = item.get("img_b64", "")
            img_obj = b64_to_img(b64_txt)
            if img_obj:
                valid_data[name] = {
                    "img": img_obj,
                    "hotspots": item.get("hotspots", [])
                }
        if len(valid_data) == 0:
            return demo_pool
        return valid_data
    except Exception:
        return demo_pool

# 加载全部有效场景
scene_pool = load_scene_data()
demo_full = get_demo_data()
demo_item = demo_full["demo_test.jpg"]

st.title("沉浸式英语情景点读")
st.divider()

img_names = list(scene_pool.keys())
select_name = st.selectbox("选择学习场景", img_names)
current_item = scene_pool[select_name]

# 【关键修复】不用直接["img"]，使用get安全获取
origin_img = current_item.get("img")
hotspot_list = current_item.get("hotspots", [])

# 图片损坏则强制使用示例
if origin_img is None:
    st.error("当前图片数据损坏，自动切换至调试示例图，请运维更新data_backup.json文件")
    origin_img = demo_item.get("img")
    hotspot_list = demo_item.get("hotspots", [])

# 渲染图片
orig_w, orig_h = origin_img.size
buf = BytesIO()
origin_img.save(buf, format="JPEG", quality=80)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
buf.close()
hot_json = json.dumps(hotspot_list, ensure_ascii=False)

html_code = f"""
<script>
function speakWord(text) {{
    speechSynthesis.cancel();
    let u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.95;
    speechSynthesis.speak(u);
}}
function speakSentence(text) {{
    speechSynthesis.cancel();
    let u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.9;
    speechSynthesis.speak(u);
}}
window.onload = function(){{
    const hotList = {hot_json};
    const container = document.getElementById("scene-container");
    const imgEl = document.getElementById("scene-img");
    const scaleX = imgEl.offsetWidth / {orig_w};
    const scaleY = imgEl.offsetHeight / {orig_h};
    hotList.forEach(item=>{{
        let [x1,y1,x2,y2] = item.box;
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.left = (x1*scaleX)+'px';
        div.style.top = (y1*scaleY)+'px';
        div.style.width = ((x2-x1)*scaleX)+'px';
        div.style.height = ((y2-y1)*scaleY)+'px';
        div.style.background = 'rgba(255,255,0,0.06)';
        div.style.border = '1px solid rgba(255,180,0,0.5)';
        div.style.cursor = 'pointer';
        div.style.zIndex = 10;
        div.title = item.word + " 【" + item.cn + "】";
        div.onclick = ()=>speakWord(item.word);
        container.appendChild(div);
    }});
}}
</script>
<div id="scene-container" style="position:relative;width:100%;">
<img id="scene-img" src="data:image/jpeg;base64,{img_b64}" style="width:100%;display:block;">
</div>
"""
st.components.v1.html(html_code, height=int(orig_h * 0.72))

# 词汇区域
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

    b1, b2 = st.columns(2)
    with b1:
        st.button("🔊朗读单词", on_click=lambda: st.markdown(f'<script>speakWord("{w_text}")</script>', unsafe_allow_html=True))
    with b2:
        st.button("🔊朗读例句", on_click=lambda: st.markdown(f'<script>speakSentence("{s_text}")</script>', unsafe_allow_html=True))

st.divider()
st.info("更新说明：线下生成完整data_backup.json，替换仓库文件后重新部署即可修复图片损坏问题。")