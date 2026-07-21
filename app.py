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

# ========= Secrets安全读取 =========
ADMIN_USER = "admin"
ADMIN_HASH = "6261f86b819e46d4027239f8c6d72505078f824137a40842d8d37711718d5461"
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
                raw_img = raw_img.resize((new_w, new_h), Image.ANTIALIAS)
        return raw_img, "ok"
    except Exception as e:
        return None, f"【失败】{file_obj.name} 格式损坏：{str(e)}"

# 【修复】安全持久化，完整捕获文件+json异常
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
        # 分开定义文件句柄，杜绝参数缺失
        f = open(DATA_FILE, "w", encoding="utf-8")
        json.dump(dump_data, f, ensure_ascii=False, indent=2)
        f.close()
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

# 会话初始化
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
# 自动匹配选中图片
selected_img = st.session_state.current_img_name
if img_name_list:
    if selected_img in img_name_list:
        idx = img_name_list.index(selected_img)
    else:
        idx = 0
    selected_img = st.selectbox(f"选择场景图片（共{len(img_name_list)}张）", img_name_list, index=idx)
    st.session_state.current_img_name = selected_img

# ========== 学生页面（无红框，原图正常展示） ==========
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（游客无需登录）")
    st.info("仅浏览单词、浏览器语音朗读")
    if not img_name_list:
        st.warning("管理员尚未上传情景图片，请稍后再来！")
    else:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        hotspot_list = current_data["hotspots"]
        # 学生纯原图无红框
        st.image(origin_img, caption="情景", use_column_width=True)
        if len(hotspot_list) == 0:
            st.warning("暂无情景词汇")
        else:
            hot_idx = st.radio("选择物品学习", range(len(hotspot_list)), format_func=lambda i: hotspot_list[i]["word"])
            word_info = hotspot_list[hot_idx]
            st.markdown(f"# {word_info['word']}")
            st.markdown(f"音标：/{word_info['phonetic']}/")
            st.markdown(f"中文释义：{word_info['cn']}")
            st.markdown(f"校园例句：{word_info['sentence']}")
            speak_js = f"""
            <script>
            function readWord(){{let v=new SpeechSynthesisUtterance("{word_info['word']}");v.lang="en-US";speechSynthesis.speak(v);}}
            function readSentence(){{let v=new SpeechSynthesisUtterance("{word_info['sentence']}");v.lang="en-US";speechSynthesis.speak(v);}}
            </script>
            """
            st.components.v1.html(speak_js, height=0)
            b1,b2 = st.columns(2)
            with b1:
                st.button("🔊 朗读单词", on_click=lambda: st.components.v1.html("<script>readWord()</script>", height=0))
            with b2:
                st.button("🔊 朗读例句", on_click=lambda: st.components.v1.html("<script>readSentence()</script>", height=0))

# ========== 管理员后台 ==========
else:
    if not st.session_state.is_admin:
        st.subheader("🔐 管理员登录验证")
        with st.form("login_form"):
            username_input = st.text_input("用户名")
            password_input = st.text_input("密码", type="password")
            submit_btn = st.form_submit_button("登录")
            if submit_btn:
                input_user = username_input.strip() if username_input else ""
                input_pwd = password_input.strip()
                input_hash = get_pwd_hash(input_pwd)
                if input_user != ADMIN_USER:
                    st.error("用户名不正确")
                elif input_hash == ADMIN_HASH:
                    st.session_state.is_admin = True
                    st.session_state.admin_name = "校园管理员"
                    st.rerun()
                else:
                    st.error("密码错误，请重新输入")
        st.stop()

    st.subheader("🔐 管理员后台")
    st.success(f"欢迎 {st.session_state.admin_name}")
    if st.button("退出登录"):
        st.session_state.is_admin = False
        st.session_state.admin_name = ""
        st.rerun()

    with st.sidebar:
        st.header("1. 批量上传图片")
        st.info(f"当前图片总数：{len(img_name_list)} | 单次≤8张，单张≤8MB")
        upload_imgs = st.file_uploader("支持jpg/png/jpeg，可多选", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key="img_upload_key_fix")
        if upload_imgs:
            if len(upload_imgs) > 8:
                st.error("单次最多8张！")
            else:
                progress_bar = st.progress(0)
                total = len(upload_imgs)
                success_count = 0
                new_upload_name = ""
                fail_list = []
                for idx, file in enumerate(upload_imgs):
                    progress_bar.progress((idx+1)/total, text=f"处理：{file.name}")
                    img, msg = load_and_compress(file)
                    if img is None:
                        fail_list.append(msg)
                        continue
                    # 同名只替换图片，保留热点
                    if file.name in st.session_state.image_pool:
                        st.session_state.image_pool[file.name]["img"] = img
                        st.info(f"{file.name}：已更新图片，原有热点保留")
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
                    st.success(f"成功处理{success_count}张，自动切换至最新图片！")
                    st.rerun()
                else:
                    st.info("无图片处理")

        st.divider()
        st.header("2. 热点坐标【实时预览】")
        temp_x1 = st.session_state.temp_x1
        temp_y1 = st.session_state.temp_y1
        temp_x2 = st.session_state.temp_x2
        temp_y2 = st.session_state.temp_y2
        valid_temp_box = False
        if len(img_name_list) > 0:
            current_data = st.session_state.image_pool[selected_img]
            w, h = current_data["img"].size
            c1,c2 = st.columns(2)
            with c1:
                st.session_state.temp_x1 = st.number_input("左上角 X", min_value=0, max_value=w, value=temp_x1, key="tx1")
                st.session_state.temp_y1 = st.number_input("左上角 Y", min_value=0, max_value=h, value=temp_y1, key="ty1")
            with c2:
                st.session_state.temp_x2 = st.number_input("右下角 X", min_value=0, max_value=w, value=temp_x2, key="tx2")
                st.session_state.temp_y2 = st.number_input("右下角 Y", min_value=0, max_value=h, value=temp_y2, key="ty2")
            tx1,ty1,tx2,ty2 = st.session_state.temp_x1, st.session_state.temp_y1, st.session_state.temp_x2, st.session_state.temp_y2
            if tx1 < tx2 and ty1 < ty2:
                valid_temp_box = True
                st.success("坐标合法，浅红框实时预览")
            else:
                st.error("左上数值必须小于右下")
            st.divider()
            st.subheader("3. 单词录入")
            eng_word = st.text_input("英文单词", key="word_in")
            phonetic = st.text_input("国际音标", key="phon_in")
            cn_mean = st.text_input("中文释义", key="cn_in")
            sentence = st.text_input("例句", key="sent_in")
            st.divider()
            st.subheader("4. 操作按钮")
            save_btn = st.button("✅ 保存热点")
            clear_all_btn = st.button("🗑️ 清空本图全部热点")
            del_img_btn = st.button("🗑️ 删除当前图片")
            if save_btn:
                if eng_word and cn_mean and valid_temp_box:
                    hot_data = {"box":[tx1,ty1,tx2,ty2],"word":eng_word,"phonetic":phonetic,"cn":cn_mean,"sentence":sentence}
                    st.session_state.image_pool[selected_img]["hotspots"].append(hot_data)
                    save_all_data(st.session_state.image_pool)
                    st.success(f"【{eng_word}】保存成功")
                    st.rerun()
                else:
                    st.warning("英文/释义不能为空或坐标非法")
            if clear_all_btn:
                st.session_state.image_pool[selected_img]["hotspots"] = []
                save_all_data(st.session_state.image_pool)
                st.rerun()
            if del_img_btn:
                del st.session_state.image_pool[selected_img]
                save_all_data(st.session_state.image_pool)
                st.rerun()

    # 管理员预览画布
    if img_name_list and selected_img and selected_img in st.session_state.image_pool:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        hotspot_list = current_data["hotspots"]
        tx1,ty1,tx2,ty2 = st.session_state.temp_x1, st.session_state.temp_y1, st.session_state.temp_x2, st.session_state.temp_y2
        valid_temp_box = tx1 < tx2 and ty1 < ty2
        canvas = origin_img.copy()
        draw = ImageDraw.Draw(canvas)
        # 已保存粗红框
        for item in hotspot_list:
            bx1,by1,bx2,by2 = item["box"]
            if bx1 < bx2 and by1 < by2:
                draw.rectangle([bx1,by1,bx2,by2], outline="#ff0000", width=6)
        # 预览浅红框
        if valid_temp_box:
            draw.rectangle([tx1, ty1, tx2, ty2], outline="#ff8888", width=2)
        img_col, opt_col = st.columns([3,1])
        with img_col:
            val = streamlit_image_coordinates(canvas, key="coord_picker", use_column_width=True)
            st.caption("粗红=已保存 | 浅红=实时预览｜点击两点框选")
            if val is not None:
                xc = round(val["x"])
                yc = round(val["y"])
                if st.session_state.pick_first is None:
                    st.session_state.pick_first = (xc, yc)
                    st.info(f"已拾取左上({xc},{yc})，再点右下角")
                else:
                    x1,y1 = st.session_state.pick_first
                    st.session_state.temp_x1 = min(x1,xc)
                    st.session_state.temp_y1 = min(y1,yc)
                    st.session_state.temp_x2 = max(x1,xc)
                    st.session_state.temp_y2 = max(y1,yc)
                    st.session_state.pick_first = None
                    st.rerun()
            if st.button("🔄 重置坐标拾取"):
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
                st.info("暂无热点可删除")
    else:
        st.info("请上传并选择图片后预览")

    # 热点导入导出
    st.divider()
    st.subheader("热点备份/恢复")
    export_data = {}
    for name, data in st.session_state.image_pool.items():
        export_data[name] = {"hotspots": data["hotspots"]}
    json_dump = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.download_button("💾 导出全部热点JSON", data=json_dump, file_name="all_hotspots_backup.json")
    json_upload = st.file_uploader("📂 导入备份JSON", type="json", key="json_upload_fix")
    if json_upload:
        load_data = json.load(json_upload)
        match_count = 0
        for img_name, hotspots in load_data.items():
            if img_name in st.session_state.image_pool:
                st.session_state.image_pool[img_name]["hotspots"] = hotspots
                match_count += 1
        save_all_data(st.session_state.image_pool)
        st.success(f"匹配{match_count}张图片热点恢复完成")
        st.rerun()