import streamlit as st
from PIL import Image, ImageDraw
import json
import hashlib

st.set_page_config(page_title="🏫校园场景点读学英语", layout="wide")

# SHA256加密函数，自动去除输入首尾空格
def get_pwd_hash(raw_str):
    clean_str = raw_str.strip()
    return hashlib.sha256(clean_str.encode("utf-8")).hexdigest()

# 【关键：直接读取独立secrets字符串，不嵌套字典】
ADMIN_USER = st.secrets["admin_user"]
ADMIN_HASH = st.secrets["admin_hash"]

# 会话初始化
if "bg_img" not in st.session_state:
    st.session_state.bg_img = None
if "draw_canvas" not in st.session_state:
    st.session_state.draw_canvas = None
if "hotspot_list" not in st.session_state:
    st.session_state.hotspot_list = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "visit"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "admin_name" not in st.session_state:
    st.session_state.admin_name = ""

# 页面切换（游客默认打开，无需登录）
st.title("🏫 校园实景热点点读英语学习平台")
st.divider()
col_switch1, col_switch2 = st.columns([1, 4])
with col_switch1:
    page_choose = st.radio("页面入口", ["学生学习页", "管理员后台"])
st.session_state.view_mode = "visit" if page_choose == "学生学习页" else "admin"

# ========== 游客学生页面（完全免登录，外网直接访问） ==========
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（游客无需登录）")
    st.info("仅浏览单词、浏览器语音朗读，无任何编辑上传权限")

    if st.session_state.bg_img is None:
        st.warning("管理员尚未上传校园场景图片与单词热点，请稍后再来！")
    else:
        st.image(st.session_state.draw_canvas, caption="校园全景（红色方框=单词学习热点）", use_column_width=True)
        if len(st.session_state.hotspot_list) == 0:
            st.warning("管理员暂未录入校园英语词汇")
        else:
            hot_idx = st.radio("选择校园物品学习", range(len(st.session_state.hotspot_list)),
                               format_func=lambda i: st.session_state.hotspot_list[i]["word"])
            word_info = st.session_state.hotspot_list[hot_idx]

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

# ========== 管理员后台（仅切换才显示登录框） ==========
else:
    if not st.session_state.is_admin:
        st.subheader("🔐 管理员登录验证")
        with st.form("login_form"):
            username_input = st.text_input("用户名")
            password_input = st.text_input("密码", type="password")
            submit_btn = st.form_submit_button("登录")
            if submit_btn:
                # 自动清理空格再比对
                input_user = username_input.strip()
                input_hash = get_pwd_hash(password_input)
                if input_user != ADMIN_USER:
                    st.error("用户名不正确")
                elif input_hash == ADMIN_HASH:
                    st.session_state.is_admin = True
                    st.session_state.admin_name = "校园管理员"
                    st.rerun()
                else:
                    st.error("密码错误，请重新输入（注意不要带空格）")
        st.stop()

    # 登录成功编辑后台
    st.subheader("🔐 管理员单词配置后台")
    st.success(f"欢迎管理员 {st.session_state.admin_name}")
    if st.button("退出登录"):
        st.session_state.is_admin = False
        st.rerun()

    # 侧边编辑区
    with st.sidebar:
        st.header("1. 上传校园场景图片")
        upload_img = st.file_uploader("支持jpg/png/jpeg", type=["jpg", "png", "jpeg"])
        if upload_img:
            st.session_state.bg_img = Image.open(upload_img).convert("RGB")
            st.session_state.draw_canvas = st.session_state.bg_img.copy()
            st.session_state.hotspot_list = []
            st.success("图片加载完成，可配置单词热点")

        st.divider()
        st.header("2. 热点坐标设置")
        if st.session_state.bg_img:
            w, h = st.session_state.bg_img.size
            c1, c2 = st.columns(2)
            with c1:
                x1 = st.number_input("左上角 X", min_value=0, max_value=w, value=30)
                y1 = st.number_input("左上角 Y", min_value=0, max_value=h, value=30)
            with c2:
                x2 = st.number_input("右下角 X", min_value=0, max_value=w, value=120)
                y2 = st.number_input("右下角 Y", min_value=0, max_value=h, value=120)

        st.divider()
        st.header("3. 单词信息录入")
        eng_word = st.text_input("英文单词")
        phonetic = st.text_input("国际音标")
        cn_mean = st.text_input("中文释义")
        sentence = st.text_input("校园例句")

        st.divider()
        save_btn = st.button("✅ 保存当前热点")
        clear_all_btn = st.button("🗑️ 清空全部热点")

    # 保存热点逻辑
    if save_btn and st.session_state.bg_img:
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
            st.session_state.hotspot_list.append(hot_data)
            draw = ImageDraw.Draw(st.session_state.draw_canvas)
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            st.success(f"热点【{eng_word}】添加成功")

    if clear_all_btn:
        st.session_state.hotspot_list = []
        if st.session_state.bg_img:
            st.session_state.draw_canvas = st.session_state.bg_img.copy()
        st.rerun()

    # 图片预览 + 删除面板
    img_col, opt_col = st.columns([3, 1])
    with img_col:
        if st.session_state.draw_canvas:
            st.image(st.session_state.draw_canvas, caption="编辑预览图（红色框=单词热点）", use_column_width=True)
        else:
            st.info("请在左侧上传校园图片")
    with opt_col:
        st.subheader("热点管理列表")
        if len(st.session_state.hotspot_list) > 0:
            del_idx = st.radio("选择删除单词", range(len(st.session_state.hotspot_list)),
                               format_func=lambda i: st.session_state.hotspot_list[i]["word"])
            if st.button("删除该热点"):
                st.session_state.hotspot_list.pop(del_idx)
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
                draw = ImageDraw.Draw(st.session_state.draw_canvas)
                for item in st.session_state.hotspot_list:
                    draw.rectangle(item["box"], outline="red", width=3)
                st.rerun()

    # 单词配置导入导出
    st.divider()
    st.subheader("单词库保存/导入")
    if len(st.session_state.hotspot_list) > 0:
        json_dump = json.dumps(st.session_state.hotspot_list, ensure_ascii=False, indent=2)
        st.download_button("💾 导出单词配置JSON", data=json_dump, file_name="school_word_config.json")
    json_upload = st.file_uploader("📂 导入本地备份JSON", type="json")
    if json_upload:
        load_data = json.load(json_upload)
        st.session_state.hotspot_list = load_data
        if st.session_state.bg_img:
            st.session_state.draw_canvas = st.session_state.bg_img.copy()
            draw = ImageDraw.Draw(st.session_state.draw_canvas)
            for item in st.session_state.draw_canvas:
                draw.rectangle(item["box"], outline="red", width=3)
        st.success("单词配置导入完成！切换学生页即可分享学习")

# 校园高频词汇模板
with st.expander("📚 校园英语词汇模板（管理员复制）"):
    st.markdown("""
1. classroom /ˈklɑːsruːm/ 教室 We have English in this classroom.
2. playground /ˈpleɪɡraʊnd/ 操场 Students run on the playground.
3. library /ˈlaɪbrəri/ 图书馆 I read books in this library.
4. teaching building 教学楼
5. flag /flæɡ/ 国旗
6. basketball court 篮球场
7. cafeteria /ˌkæfəˈtɪəriə/ 食堂
8. tree /triː/ 大树
9. bench /bentʃ/ 长椅
10. school bus 校车
""")