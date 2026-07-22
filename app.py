import streamlit as st
from PIL import Image, ImageDraw
import json
import base64
from io import BytesIO
import os

# ====================== 固定路径：读取当前目录 data_backup.json ======================
DATA_FILE = "data_backup.json"

# 页面配置
st.set_page_config(page_title="英语点读学生端", layout="wide")

# base64 转图片
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

# 加载本地JSON数据
def load_all_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ====================== 初始化 ======================
data = load_all_data()

st.title("📖 英语情景智能点读")
st.divider()

# 无文件提示
if data is None:
    st.error("❌ 未找到 data_backup.json，请将文件与学生端脚本放在同一文件夹！")
    st.stop()

img_list = list(data.keys())
if not img_list:
    st.warning("暂无场景图片数据")
    st.stop()

# 场景选择
select_scene = st.selectbox("请选择学习场景", img_list)
scene_data = data[select_scene]
img = b64_to_img(scene_data["img_b64"])
hotspots = scene_data["hotspots"]

if not img:
    st.error("图片加载失败")
    st.stop()

# 绘制热点框
draw_img = img.copy()
draw = ImageDraw.Draw(draw_img)
for item in hotspots:
    x1, y1, x2, y2 = item["box"]
    draw.rectangle([x1, y1, x2, y2], outline="#4285F4", width=4)

# 展示图片
st.image(draw_img, use_column_width=True)
st.divider()

# 点读词汇列表
st.subheader("📝 本场景单词列表")
if len(hotspots) == 0:
    st.info("该场景暂无单词标注")
else:
    for idx, word in enumerate(hotspots):
        with st.expander(f"第{idx+1}个单词：{word['word']}"):
            st.markdown(f"**单词：** {word['word']}")
            st.markdown(f"**音标：** {word['phonetic']}")
            st.markdown(f"**释义：** {word['cn']}")
            st.markdown(f"**例句：** {word['sentence']}")
            
            # 浏览器朗读
            read_text = f"{word['word']}  {word['cn']}"
            st.components.v1.html(
                f"""
                <script>
                function read(){{
                    let u = new SpeechSynthesisUtterance("{read_text}");
                    u.lang = "zh-CN";
                    speechSynthesis.speak(u);
                }}
                </script>
                <button onclick="read()" style="padding:6px 20px;font-size:15px;background:#2196F3;color:white;border:none;border-radius:6px;">🔊 点击朗读</button>
                """,
                height=40
            )

st.divider()
st.caption("✅ 离线可用 | 仅需同目录 data_backup.json")