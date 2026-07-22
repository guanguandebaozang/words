import streamlit as st
import json
import base64
from io import BytesIO
from PIL import Image
import os

# 持久化数据文件
DATA_FILE = "data_backup.json"

# 页面基础配置
st.set_page_config(page_title="英语情景点读-学生端", layout="wide")

# base64转图片
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

# 图片转base64工具
def img_to_b64(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=80)
    res = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()
    return res

# 生成内置测试示例数据（无json时自动加载）
def get_demo_data():
    # 创建一张简易白色测试图
    w, h = 800, 600
    demo_img = Image.new("RGB", (w, h), color=(240, 248, 255))
    # 内置测试热点
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

# 加载本地场景数据，无文件自动加载示例
def load_scene_data():
    if not os.path.exists(DATA_FILE):
        return get_demo_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        scene_pool = {}
        for img_name, data in raw_json.items():
            img = b64_to_img(data["img_b64"])
            scene_pool[img_name] = {
                "img": img,
                "hotspots": data["hotspots"]
            }
        return scene_pool
    except Exception as e:
        st.warning(f"本地数据读取失败，自动加载示例：{str(e)}")
        return get_demo_data()

# 初始化加载
scene_pool = load_scene_data()

# 页面标题
st.title("沉浸式英语情景点读")
st.divider()

# 场景选择
img_name_list = list(scene_pool.keys())
select_img = st.selectbox("选择学习场景", img_name_list)
scene_info = scene_pool[select_img]
origin_img = scene_info["img"]
hotspot_list = scene_info["hotspots"]
orig_w, orig_h = origin_img.size

# 图片转base64渲染页面热点层
buf = BytesIO()
origin_img.save(buf, format="JPEG", quality=80)
img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
buf.close()
hot_json = json.dumps(hotspots, ensure_ascii=False)

# 前端朗读JS+悬浮热点
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

# 单词展示与朗读按钮
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

# =====================线下JSON上传更新模块=====================
st.divider()
st.subheader("【管理员专用】线下场景文件更新")
st.info("使用管理端导出的data_backup.json上传，一键更新全部图片与单词热点；若无文件程序自动加载demo_test示例图调试")
upload_json_file = st.file_uploader("上传data_backup.json", type="json")
if upload_json_file is not None:
    try:
        # 读取上传的JSON内容
        new_full_data = json.load(upload_json_file)
        # 覆盖本地持久化文件
        with open(DATA_FILE, "w", encoding="utf-8") as output_f:
            json.dump(new_full_data, output_f, ensure_ascii=False, indent=2)
        st.success("✅场景更新成功！刷新页面即可加载新内容")
    except Exception as err:
        st.error(f"文件上传失败，请检查JSON格式：{str(err)}")