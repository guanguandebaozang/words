import streamlit as st
from PIL import Image, ImageDraw
import json
import hashlib

st.set_page_config(page_title="🏫校园实景热点点读学英语", layout="wide")

# 哈希加密工具
def get_pwd_hash(raw_str):
    clean_str = raw_str.strip()
    return hashlib.sha256(clean_str.encode("utf-8")).hexdigest()

# 读取云端Secrets
try:
    ADMIN_USER = st.secrets["admin_user"]
    ADMIN_HASH = st.secrets["admin_hash"]
except Exception as e:
    st.error("读取后台密钥失败，请检查Streamlit Secrets配置！")
    st.stop()

# 会话状态初始化
if "image_pool" not in st.session_state:
    # 存储所有图片：{图片名称: {"img":原图对象, "hotspots":热点数组}}
    st.session_state.image_pool = {}
if "current_img_name" not in st.session_state:
    st.session_state.current_img_name = ""
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "visit"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "admin_name" not in st.session_state:
    st.session_state.admin_name = ""

# 页面顶部切换
st.title("🏫 校园实景热点点读英语学习平台")
st.divider()
col_switch1, col_switch2 = st.columns([1, 4])
with col_switch1:
    page_choose = st.radio("页面入口", ["学生学习页", "管理员后台"])
st.session_state.view_mode = "visit" if page_choose == "学生学习页" else "admin"

# 图片下拉选择器（全局共用）
img_name_list = list(st.session_state.image_pool.keys())
selected_img = ""
if img_name_list:
    selected_img = st.selectbox("选择场景图片", img_name_list)
    st.session_state.current_img_name = selected_img

# ========== 游客学生页面（免登录） ==========
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（游客无需登录）")
    st.info("仅浏览单词、浏览器语音朗读，无任何编辑上传权限")

    if not img_name_list:
        st.warning("管理员尚未上传校园场景图片，请稍后再来！")
    else:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        hotspot_list = current_data["hotspots"]

        # 绘制当前图片所有热点红框
        canvas = origin_img.copy()
        draw = ImageDraw.Draw(canvas)
        for item in hotspot_list:
            bx1, by1, bx2, by2 = item["box"]
            draw.rectangle([bx1, by1, bx2, by2], outline="red", width=4)

        st.image(canvas, caption="校园全景（红色粗框=单词学习热点）", use_column_width=True)

        if len(hotspot_list) == 0:
            st.warning("该图片暂未录入校园英语词汇")
        else:
            hot_idx = st.radio("选择校园物品学习", range(len(hotspot_list)),
                               format_func=lambda i: hotspot_list[i]["word"])
            word_info = hotspot_list[hot_idx]

            st.markdown(f"# {word_info['word']}")
            st.markdown(f"音标：/{word_info['phonetic']}/")
            st.markdown(f"中文释义：{word_info['cn']}")
            st.markdown(f"校园例句：{word_info['sentence']}")

            # 前端Web Speech朗读JS
            speak_js = f"""
            <script>
                function readWord() {{
                    let voice = new SpeechSynthesisUtterance("{word_info['word']}");
                    voice.lang = "en-US";
                    speechSynthesis.speak(voice);
                }}
                function readSentence() {{
                    let voice = new SpeechSynthesisUtterance("{word_info['sentence']}");
                    voice.lang = "en-US";
                    speechSynthesis.speak(voice);
                }}
            </script>
            """
            st.components.v1.html(speak_js, height=0)
            b1, b2 = st.columns(2)
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
                input_user = username_input.strip()
                input_hash = get_pwd_hash(password_input)
                if input_user != ADMIN_USER:
                    st.error("用户名不正确")
                elif input_hash == ADMIN_HASH:
                    st.session_state.is_admin = True
                    st.session_state.admin_name = "校园管理员"
                    st.rerun()
                else:
                    st.error("密码错误，请重新输入")
        st.stop()

    st.subheader("🔐 管理员单词配置后台")
    st.success(f"欢迎管理员 {st.session_state.admin_name}")
    if st.button("退出登录"):
        st.session_state.is_admin = False
        st.session_state.admin_name = ""
        st.rerun()

    # 侧边编辑区
    with st.sidebar:
        st.header("1. 批量上传场景图片")
        upload_imgs = st.file_uploader("支持jpg/png/jpeg，可多选批量上传", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if upload_imgs:
            for file in upload_imgs:
                if file.name not in st.session_state.image_pool:
                    img = Image.open(file).convert("RGB")
                    st.session_state.image_pool[file.name] = {
                        "img": img,
                        "hotspots": []
                    }
            st.success("图片上传完成，上方下拉框切换图片")
            st.rerun()

        st.divider()
        if img_name_list and selected_img:
            current_data = st.session_state.image_pool[selected_img]
            w, h = current_data["img"].size
            st.header("2. 热点坐标设置（X1<X2，Y1<Y2）")
            c1, c2 = st.columns(2)
            with c1:
                x1 = st.number_input("左上角 X", min_value=0, max_value=w, value=30)
                y1 = st.number_input("左上角 Y", min_value=0, max_value=h, value=30)
            with c2:
                x2 = st.number_input("右下角 X", min_value=0, max_value=w, value=220)
                y2 = st.number_input("右下角 Y", min_value=0, max_value=h, value=150)

            st.divider()
            st.header("3. 单词信息录入")
            eng_word = st.text_input("英文单词")
            phonetic = st.text_input("国际音标")
            cn_mean = st.text_input("中文释义")
            sentence = st.text_input("校园例句")

            st.divider()
            st.header("4. 操作按钮")
            save_btn = st.button("✅ 保存当前热点")
            clear_all_btn = st.button("🗑️ 清空本图全部热点")
            del_img_btn = st.button("🗑️ 删除当前这张图片")

            # 保存热点逻辑
            if save_btn:
                if not eng_word or not cn_mean:
                    st.warning("英文单词和中文释义不可为空！")
                else:
                    hot_data = {
                        "box": [x1, y1, x2, y2],
                        "word": eng_word,
                        "phonetic": phonetic,
                        "cn": cn_mean,
                        "sentence": sentence
                    }
                    st.session_state.image_pool[selected_img]["hotspots"].append(hot_data)
                    st.success(f"热点【{eng_word}】添加成功！")
                    st.rerun()

            # 清空当前图片热点
            if clear_all_btn:
                st.session_state.image_pool[selected_img]["hotspots"] = []
                st.rerun()

            # 删除当前图片
            if del_img_btn:
                del st.session_state.image_pool[selected_img]
                st.rerun()
        else:
            st.info("请先上传图片再配置热点")

    # 主区域图片预览 + 热点删除面板
    if img_name_list and selected_img:
        current_data = st.session_state.image_pool[selected_img]
        origin_img = current_data["img"]
        hotspot_list = current_data["hotspots"]

        canvas = origin_img.copy()
        draw = ImageDraw.Draw(canvas)
        for item in hotspot_list:
            bx1, by1, bx2, by2 = item["box"]
            draw.rectangle([bx1, by1, bx2, by2], outline="red", width=4)

        img_col, opt_col = st.columns([3, 1])
        with img_col:
            st.image(canvas, caption=f"编辑预览图：{selected_img}（红色粗框=单词热点）", use_column_width=True)
        with opt_col:
            st.subheader("当前图片热点管理")
            if len(hotspot_list) > 0:
                del_idx = st.radio("选择删除单词", range(len(hotspot_list)),
                                   format_func=lambda i: hotspot_list[i]["word"])
                if st.button("删除该热点"):
                    st.session_state.image_pool[selected_img]["hotspots"].pop(del_idx)
                    st.rerun()

    # 全局多图配置导入导出
    st.divider()
    st.subheader("全套图片+单词库备份/恢复")
    # 导出：仅导出可序列化数据（图片无法序列化，仅保存热点与图片名称）
    export_data = {}
    for name, data in st.session_state.image_pool.items():
        export_data[name] = {"hotspots": data["hotspots"]}
    json_dump = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.download_button("💾 导出全部热点配置JSON", data=json_dump, file_name="all_hotspots_backup.json")

    json_upload = st.file_uploader("📂 导入热点备份JSON（需提前上传对应图片）", type="json")
    if json_upload:
        load_data = json.load(json_upload)
        match_count = 0
        for img_name, hotspots in load_data.items():
            if img_name in st.session_state.image_pool:
                st.session_state.image_pool[img_name]["hotspots"] = hotspots["hotspots"]
                match_count += 1
        st.success(f"匹配到{match_count}张图片，热点恢复完成！切换图片查看")
        st.rerun()