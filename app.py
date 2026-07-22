import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os

# 线下更新专用数据文件
DATA_FILE = "data_backup.json"

# 页面基础配置
st.set_page_config(page_title="英语情景点读-学生端", layout="wide")

# base64转图片（增加异常捕获，损坏直接返回None）
def b64_to_img(b64_str):
    if not b64_str or not isinstance(b64_str, str):
        return None
    try:
        raw_bytes = base64.b64decode(b64_str)
        buf = BytesIO(raw_bytes)
        img = Image.open(buf).convert("RGB")
        buf.close()
        return img
    except Exception:
        return None

# 图片转base64
def img_to_b64(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=80)
    res = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()
    return res

# 内置标准调试示例（永远可用兜底图）
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

# 加载数据：过滤损坏图片，只保留正常图片
def load_scene_data():
    demo = get_demo_data()
    if not os.path.exists(DATA_FILE):
        return demo
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        valid_pool = {}
        for img_name, data in raw_json.items():
            b64_text = data.get("img_b64", "")
            img = b64_to_img(b64_text)
            if img is not None:
                valid_pool[img_name] = {
                    "img": img,
                    "hotspots": data.get("hotspots", [])
                }
        # 如果所有图片全部损坏，返回示例
        if len(valid_pool) == 0:
            return demo
        return valid_pool
    except Exception:
        return demo

# 加载有效场景数据
scene_pool = load_scene_data()

# 页面标题
st.title("沉浸式英语情景点读")
st.divider()

img_name_list = list(scene_pool.keys())
select_img = st.selectbox("选择学习场景", img_name_list)
scene_info = scene_pool[select_img]

# 安全读取图片与热点
origin_img = scene_info.get("img")
hotspot_list = scene_info.get("hotspots", [])

# 图片损坏兜底切换示例
if origin_img is None:
    st.error("当前图片数据损坏，自动切换至调试示例图，请运维更新data_backup.json文件")
    # 强制使用示例图
    demo_pool = get_demo_data()
    scene_info = demo_pool["demo_test.jpg"]
    origin_img = scene_info["img"]
    hotspot_list = scene_info["hotspots"]

orig_w, orig_h = origin_img.size

# 渲染图片base64
buf = BytesIO()
origin_img.save(buf, format="JPEG", quality=80)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
buf.close()
hot_json = json.dumps(hotspot_list, ensure_ascii=False)

# 前端朗读悬浮层HTML
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

# 单词朗读区域
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

# 底部更新说明（无网页上传功能）
st.divider()
st.info("更新说明：线下使用管理端导出完整data_backup.json，替换项目仓库内同名文件后重新部署应用即可修复损坏图片。")