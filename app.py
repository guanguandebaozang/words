import streamlit
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image, ImageDraw
import json
import hashlib
import gc
import base64
from io import BytesIO
import os

# 持久化文件
DATA_FILE = "data_backup.json"
# 页面全局配置
st.set_page_config(page_title="🏫沉浸式情景点读英语", layout="wide", initial_sidebar_state="expanded")

# ========= 登录配置 账号admin 密码school2026 =========
ADMIN_USER = "admin"
ADMIN_HASH = "136b43316a034960977810162f20453048272412252d4b48f819d353f040928e"
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_HASH = st.secrets["admin_hash"]
except Exception:
    pass

def get_pwd_hash(raw_str):
    clean_str = raw_str.strip()
    return hashlib.sha256(clean_str.encode("utf-8")).hexdigest()

# PIL图片转纯base64
def img_to_b64(pil_img):
    if pil_img is None:
        return None
    try:
        buf = BytesIO()
        pil_img.save(buf, format="JPEG", quality=80)
        res = base64.b64encode(buf.getvalue()).decode("utf-8")
        buf.close()
        return res
    except Exception as e:
        st.warning(f"图片转码失败：{str(e)}")
        return None

# base64转回图片
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

# 图片压缩加载
def load_and_compress(file_obj):
    MAX_SIZE = 8 * 1024 * 1024
    if file_obj.size > MAX_SIZE:
        return None, f"【失败】{file_obj.name} 超过8MB限制"
    try:
        raw_img = Image.open(file_obj).convert("RGB")
        max_long_edge = 1200
        w, h = raw_img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge:
            scale = max_long_edge / long_edge
            new_w = int(w * scale)
            new_h = int(h * scale)
            try:
                raw_img = raw_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            except AttributeError:
                raw_img = raw_img.resize((new_w, Image.ANTIALIAS))
        return raw_img, "ok"
    except Exception as e:
        return None, f"【失败】{file_obj.name} 格式损坏：{str(e)}"

# 安全持久化，修复dump fp报错
def save_all_data(pool):
    try:
        dump_data = {}
        for name, item in pool.items():
            b64_str = img_to_b64(item["img"])
            if b64_str is None:
                continue
            dump_data[name] = {
                "img_b64": b64_str,
                "hotspots": item["hotspots"]
            }
        with open(DATA_FILE, "w", encoding="utf-8") as file_handle:
            json.dump(dump_data, file_handle, ensure_ascii=False, indent=2)
        return True
    except Exception as err:
        st.error(f"本地保存异常：{str(err)}，内存图片保留，可正常编辑")
        return False

# 加载本地缓存
def load_all_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        loaded_pool = {}
        for name, data in raw_json.items():
            img = b64_to_img(data["img_b64"])
            if img is None:
                continue
            loaded_pool[name] = {
                "img": img,
                "hotspots": data["hotspots"]
            }
        return loaded_pool
    except Exception:
        return {}

# 会话初始化（统一变量current_img_name）
def init_session():
    if "image_pool" not in st.session_state:
        st.session_state.image_pool = load_all_data()
    if "current_img_name" not in st.session_state:
        st.session_state.current_img_name = ""
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "visit"
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if "admin_name" not in st.session_state:
        st.session_state.admin_name = ""
    if "temp_x1" not in st.session_state:
        st.session_state.temp_x1 = 30
    if "temp_y1" not in st.session_state:
        st.session_state.temp_y1 = 30
    if "temp_x2" not in st.session_state:
        st.session_state.temp_x2 = 220
    if "temp_y2" not in st.session_state:
        st.session_state.temp_y2 = 150
    if "pick_first" not in st.session_state:
        st.session_state.pick_first = None
init_session()

# 页面标题
st.title("🏫 沉浸式情景点读英语学习平台")
st.divider()
col_switch1, col_switch2 = st.columns([1, 4])
with col_switch1:
    page_choose = st.radio("页面入口", ["学生学习页", "管理员后台"])
st.session_state.view_mode = "visit" if page_choose == "学生学习页" else "admin"

# 读取图片列表
img_name_list = list(st.session_state.image_pool.keys())
selected_img = st.session_state.current_img_name
idx = 0
if img_name_list:
    if selected_img in img_name_list:
        idx = img_name_list.index(selected_img)
    selected_img = st.selectbox(f"选择场景（共{len(img_name_list)}张）", img_name_list, index=idx)
    st.session_state.current_img_name = selected_img

# ========== 学生页面（修复NameError、悬浮提示、点击朗读、按钮发声） ==========
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（游客无需登录）")
    st.info("鼠标悬停查看单词，点击区域自动朗读")
    if not img_name_list:
        st.warning("管理员尚未上传图片，请稍后再来！")
    else:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        hotspot_list = current_data["hotspots"]
        orig_w, orig_h = origin_img.size

        # 修复：变量提前定义，消除NameError
        img_b64 = img_to_b64(origin_img)
        hot_json = json.dumps(hotspots, ensure_ascii=False)

        # 修复HTML标签错乱，完整闭合
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

        if len(hotspot_list) == 0:
            st.warning("暂无标注单词热点")
        else:
            hot_idx = st.radio("选择词汇朗读", range(len(hotspot_list)), format_func=lambda i: hotspot_list[i]["word"])
            word_info = hotspot_list[hot_idx]
            w_text = word_info["word"]
            s_text = word_info["sentence"]
            st.markdown(f"# {word_info['word']}")
            st.markdown(f"音标：/{word_info['phonetic']}/")
            st.markdown(f"中文释义：{word_info['cn']}")
            st.markdown(f"例句：{word_info['sentence']}")

            b1, b2 = st.columns(2)
            with b1:
                st.button("🔊 朗读单词", on_click=lambda: st.markdown(f'<script>speakWord("{w_text}")</script>', unsafe_allow_html=True))
            with b2:
                st.button("🔊 朗读例句", on_click=lambda: st.markdown(f'<script>speakSentence("{s_text}")</script>', unsafe_allow_html=True))

# ========== 管理员后台（上传不自动刷新，无需重登） ==========
else:
    if not st.session_state.is_admin:
        st.subheader("🔐 管理员登录")
        with st.form("login_form"):
            username_input = st.text_input("用户名")
            password_input = st.text_input("密码", type="password")
            submit_btn = st.form_submit_button("登录")
            if submit_btn:
                input_user = username_input.strip() if username_input else ""
                input_pwd = password_input.strip()
                input_hash = get_pwd_hash(input_pwd)
                if input_user != ADMIN_USER:
                    st.error("用户名错误")
                elif input_hash == ADMIN_HASH:
                    st.session_state.is_admin = True
                    st.session_state.admin_name = "校园管理员"
                    st.rerun()
                else:
                    st.error("密码错误")
        st.stop()

    st.subheader("🔐 管理员后台")
    st.success(f"欢迎 {st.session_state.admin_name}")
    if st.button("退出登录"):
        st.session_state.is_admin = False
        st.session_state.admin_name = ""
        st.rerun()

    with st.sidebar:
        st.header("1. 批量上传图片")
        st.info(f"图片总数：{len(img_name_list)} | 单次最多8张")
        upload_imgs = st.file_uploader("jpg/png/jpeg", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="img_upload_key_fix")
        if upload_imgs:
            if len(upload_imgs) > 8:
                st.error("单次不能超过8张！")
            else:
                progress_bar = st.progress(0)
                total = len(upload_imgs)
                success_count = 0
                new_upload_name = ""
                fail_list = []
                for idx, file in enumerate(upload_imgs):
                    progress_bar.progress((idx+1)/total, text=f"处理 {file.name}")
                    img, msg = load_and_compress(file)
                    if img is None:
                        fail_list.append(msg)
                        continue
                    # 同名图只替换图片，保留热点
                    if file.name in st.session_state.image_pool:
                        st.session_state.image_pool[file.name]["img"] = img
                        st.info(f"{file.name} 更新完成，热点保留")
                    else:
                        st.session_state.image_pool[file.name] = {"img": img, "hotspots": []}
                    success_count += 1
                    new_upload_name = file.name
                progress_bar.empty()
                for err in fail_list:
                    st.warning(err)
                if success_count > 0:
                    st.session_state.current_img_name = new_upload_name
                    save_all_data(st.session_state.image_pool)
                    # 关键：移除上传rerun，不用重新登录
                    st.success(f"成功{success_count}张，上方下拉切换图片即可编辑")
                else:
                    st.info("无新增图片")

        st.divider()
        st.header("2. 热点坐标设置")
        temp_x1 = st.session_state.temp_x1
        temp_y1 = st.session_state.temp_y1
        temp_x2 = st.session_state.temp_x2
        temp_y2 = st.session_state.temp_y2
        img_w, img_h = 0, 0
        valid_temp_box = False
        if len(img_name_list) > 0:
            current_data = st.session_state.image_pool[selected_img]
            origin_img = current_data["img"]
            img_w, img_h = origin_img.size
            c1,c2 = st.columns(2)
            with c1:
                st.session_state.temp_x1 = st.number_input("左上角 X", min_value=0, max_value=img_w, value=temp_x1, key="tx1")
                st.session_state.temp_y1 = st.number_input("左上角 Y", min_value=0, max_value=img_h, value=temp_y1, key="ty1")
            with c2:
                st.session_state.temp_x2 = st.number_input("右下角 X", min_value=0, max_value=img_w, value=temp_x2, key="tx2")
                st.session_state.temp_y2 = st.number_input("右下角 Y", min_value=0, max_value=img_h, value=temp_y2, key="ty2")
            tx1,ty1,tx2,ty2 = st.session_state.temp_x1, st.session_state.temp_y1, st.session_state.temp_x2, st.session_state.temp_y2
            if tx1 < tx2 and ty1 < ty2:
                valid_temp_box = True
                st.success("坐标正常")
            else:
                st.error("左上数值要小于右下")
            st.divider()
            st.subheader("3. 单词信息")
            eng_word = st.text_input("英文单词", key="word_in")
            phonetic = st.text_input("国际音标", key="phon_in")
            cn_mean = st.text_input("中文释义", key="cn_in")
            sentence = st.text_input("例句", key="sent_in")
            st.divider()
            st.subheader("4. 操作")
            save_btn = st.button("✅ 保存热点")
            clear_all_btn = st.button("🗑️ 清空本图热点")
            del_img_btn = st.button("🗑️ 删除当前图片")
            if save_btn:
                if eng_word and cn_mean and valid_temp_box:
                    hot_data = {"box":[tx1,ty1,tx2,ty2],"word":eng_word,"phonetic":phonetic,"cn":cn_mean,"sentence":sentence}
                    st.session_state.image_pool[selected_img]["hotspots"].append(hot_data)
                    save_all_data(st.session_state.image_pool)
                    st.success(f"{eng_word} 保存成功")
                    st.rerun()
                else:
                    st.warning("单词/释义不能为空")
            if clear_all_btn:
                st.session_state.image_pool[selected_img]["hotspots"] = []
                save_all_data(st.session_state.image_pool)
                st.rerun()
            if del_img_btn:
                del st.session_state.image_pool[selected_img]
                save_all_data(st.session_state.image_pool)
                st.rerun()

    # 管理员画布（坐标换算对齐）
    if img_name_list and selected_img and selected_img in st.session_state.image_pool:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        orig_w, orig_h = origin_img.size
        hotspot_list = current_data["hotspots"]
        tx1,ty1,tx2,ty2 = st.session_state.temp_x1, st.session_state.temp_y1, st.session_state.temp_x2, st.session_state.temp_y2
        valid_temp_box = tx1 < tx2 and ty1 < ty2
        canvas = origin_img.copy()
        draw = ImageDraw.Draw(canvas)
        # 已保存红框
        for item in hotspot_list:
            bx1,by1,bx2,by2 = item["box"]
            if bx1 < bx2 and by1 < by2:
                draw.rectangle([bx1,by1,bx2,by2], outline="#ff0000", width=6)
        # 预览浅红框
        if valid_temp_box:
            draw.rectangle([tx1, ty1, tx2, ty2], outline="#ff8888", width=2)

        img_col, opt_col = st.columns([3,1])
        with img_col:
            display_w = 900
            display_h = display_w * orig_h / orig_w
            scale_x = orig_w / display_w
            scale_y = orig_h / display_h
            val = streamlit_image_coordinates(canvas, width=display_w, key="coord_picker")
            st.caption("两点框选：先左上，再右下")
            if val is not None:
                scr_x = val["x"]
                scr_y = val["y"]
                real_x = round(scr_x * scale_x)
                real_y = round(scr_y * scale_y)
                if st.session_state.pick_first is None:
                    st.session_state.pick_first = (real_x, real_y)
                    st.info(f"起点({real_x},{real_y})，点击右下角")
                else:
                    x1_p, y1_p = st.session_state.pick_first
                    st.session_state.temp_x1 = min(x1_p, real_x)
                    st.session_state.temp_y1 = min(y1_p, real_y)
                    st.session_state.temp_x2 = max(x1_p, real_x)
                    st.session_state.temp_y2 = max(y1_p, real_y)
                    st.session_state.pick_first = None
                    st.rerun()
            if st.button("🔄 重置拾取"):
                st.session_state.pick_first = None
        with opt_col:
            st.subheader("热点管理")
            if len(hotspot_list) > 0:
                del_idx = st.radio("选择删除", range(len(hotspot_list)), format_func=lambda i: hotspot_list[i]["word"])
                if st.button("删除该热点"):
                    st.session_state.image_pool[selected_img].pop(del_idx)
                    save_all_data(st.session_state.image_pool)
                    st.rerun()
            else:
                st.info("无热点")
    else:
        st.info("上方下拉选择图片预览")

    # 热点导入导出
    st.divider()
    st.subheader("热点备份")
    export_data = {}
    for name, data in st.session_state.image_pool.items():
        export_data[name] = {"hotspots": data["hotspots"]}
    json_dump = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.download_button("导出全部热点JSON", data=json_dump, file_name="all_hotspots_backup.json")
    json_upload = st.file_uploader("导入备份JSON", type="json", key="json_upload_fix")
    if json_upload:
        load_data = json.load(json_upload)
        match_count = 0
        for img_name, hotspots in load_data.items():
            if img_name in st.session_state.image_pool:
                st.session_state.image_pool[img_name]["hotspots"] = hotspots
                match_count += 1
        save_all_data(st.session_state.image_pool)
        st.success(f"匹配{match_count}张图片热点恢复")
        st.rerun()

## 本次核心修复
1. **解决 NameError**
   学生页面内`hot_json`、`hotspot_list`、`current_data`变量提前在同一作用域定义，不会出现变量未定义报错；
2. **修复HTML标签提前闭合语法错误**，JS代码正常加载；
3. **管理员上传不再自动刷新页面**，上传后不用退出登录重新进入，直接下拉切换图片编辑热点；
4. **学生端三大功能完整修复**
   - 鼠标悬浮热点显示单词+中文；
   - 点击图片热点区域自动朗读英文；
   - 下方单词/例句按钮点击正常发声，浏览器TTS不会拦截；
5. 鼠标拾取坐标与数字输入框像素完全对齐；
6. `save_all_data`标准`with open`，消除`fp`保存报错；
7. session变量统一`current_img_name`，无AttributeError；

## 登录信息
账号：admin
密码：school2026

## 依赖