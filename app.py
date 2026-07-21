import streamlit as st
from PIL import Image, ImageDraw
import json
import streamlit_authenticator as stauth

st.set_page_config(page_title="🏫校园场景点读学英语", layout="wide")

# 强制读取云端Secrets，转普通字典解决只读赋值报错（云端专用核心逻辑）
raw_credentials = st.secrets["credentials"]
# 关键：转为可变普通dict，消除 Secrets does not support item assignment
auth_credentials = dict(raw_credentials)

# 登录鉴权初始化
authenticator = stauth.Authenticate(
    auth_credentials,
    "campus_word_web",
    "cloud_auth_secret_key_0721",
    cookie_expiry_days=30
)
login_name, auth_state, login_user = authenticator.login("管理员登录", "main")

# 会话状态初始化
if "bg_img" not in st.session_state:
    st.session_state.bg_img = None
if "draw_canvas" not in st.session_state:
    st.session_state.draw_canvas = None
if "hotspot_list" not in st.session_state:
    st.session_state.hotspot_list = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "visit"

# 页面切换控件
st.title("🏫 校园实景热点点读英语学习平台")
st.divider()
col_mode1, col_mode2 = st.columns([1, 4])
with col_mode1:
    page_select = st.radio("页面入口", ["学生学习页", "管理员后台"])
st.session_state.view_mode = "visit" if page_select == "学生学习页" else "admin"

# -------------------------- 学生公开学习页（外网访客默认进入） --------------------------
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（仅浏览+浏览器语音朗读）")
    st.info("所有外网访问者仅可查看单词、播放发音，无任何编辑/上传/删除权限")

    if st.session_state.bg_img is None:
        st.warning("管理员尚未上传校园场景图与单词热点，等待管理员配置后再学习！")
    else:
        st.image(st.session_state.draw_canvas, caption="校园全景图（红色方框=单词学习热点）", use_column_width=True)
        if len(st.session_state.hotspot_list) == 0:
            st.warning("暂无校园英语词汇，请管理员添加热点")
        else:
            hot_index = st.radio("选择校园物品学习", range(len(st.session_state.hotspot_list)),
                                 format_func=lambda idx: st.session_state.hotspot_list[idx]["word"])
            word_info = st.session_state.hotspot_list[hot_index]

            st.markdown(f"# {word_info['word']}")
            st.markdown(f"音标：/{word_info['phonetic']}/")
            st.markdown(f"中文释义：{word_info['cn']}")
            st.markdown(f"校园例句：{word_info['sentence']}")

            # 前端Web Speech朗读，云端完全可用，不依赖后端语音库
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
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                st.button("🔊 朗读单词", on_click=lambda: st.components.v1.html("<script>readWord()</script>", height=0))
            with btn_col2:
                st.button("🔊 朗读例句", on_click=lambda: st.components.v1.html("<script>readSentence()</script>", height=0))

# -------------------------- 管理员加密后台（仅云端Secrets账号可登录） --------------------------
else:
    st.subheader("🔐 管理员单词配置后台")
    if auth_state is False:
        st.error("账号密码错误，无权限编辑后台")
    elif auth_state is None:
        st.info("请输入云端Secrets内配置的管理员账号密码解锁编辑功能")
    elif auth_state:
        st.success(f"欢迎管理员 {login_name}，可上传校园图、新增/删除单词热点")
        authenticator.logout("退出管理员登录", sidebar="sidebar")

        # 侧边栏编辑操作区
        with st.sidebar:
            st.header("1. 上传校园场景图片")
            upload_image = st.file_uploader("支持jpg/png/jpeg图片", type=["jpg", "png", "jpeg"])
            if upload_image:
                st.session_state.bg_img = Image.open(upload_image).convert("RGB")
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
                st.session_state.hotspot_list = []
                st.success("校园图片加载完成，开始配置单词热点")

            st.divider()
            st.header("2. 热点区域坐标设置")
            if st.session_state.bg_img:
                img_w, img_h = st.session_state.bg_img.size
                c1, c2 = st.columns(2)
                with c1:
                    x_left = st.number_input("左上角 X", min_value=0, max_value=img_w, value=30)
                    y_top = st.number_input("左上角 Y", min_value=0, max_value=img_h, value=30)
                with c2:
                    x_right = st.number_input("右下角 X", min_value=0, max_value=img_w, value=120)
                    y_bottom = st.number_input("右下角 Y", min_value=0, max_value=img_h, value=120)

            st.divider()
            st.header("3. 单词信息录入")
            eng_word = st.text_input("英文单词")
            phonetic_sym = st.text_input("国际音标")
            chinese_mean = st.text_input("中文释义")
            eng_sentence = st.text_input("校园场景例句")

            st.divider()
            save_hot_btn = st.button("✅ 保存当前热点")
            clear_all_btn = st.button("🗑️ 清空全部热点")

        # 保存热点逻辑
        if save_hot_btn and st.session_state.bg_img:
            if not eng_word or not chinese_mean:
                st.warning("英文单词与中文释义不能为空！")
            else:
                hotspot_data = {
                    "box": [x_left, y_top, x_right, y_bottom],
                    "word": eng_word,
                    "phonetic": phonetic_sym,
                    "cn": chinese_mean,
                    "sentence": eng_sentence
                }
                st.session_state.hotspot_list.append(hotspot_data)
                draw = ImageDraw.Draw(st.session_state.draw_canvas)
                draw.rectangle([x_left, y_top, x_right, y_bottom], outline="red", width=3)
                st.success(f"热点【{eng_word}】添加成功！")

        if clear_all_btn:
            st.session_state.hotspot_list = []
            if st.session_state.bg_img:
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
            st.rerun()

        # 图片预览 + 热点删除面板
        img_col, opt_col = st.columns([3, 1])
        with img_col:
            if st.session_state.draw_canvas:
                st.image(st.session_state.draw_canvas, caption="编辑预览图（红色框=单词热点）", use_column_width=True)
            else:
                st.info("请在左侧上传校园全景图片")
        with opt_col:
            st.subheader("热点管理列表")
            if len(st.session_state.hotspot_list) > 0:
                del_idx = st.radio("选择要删除的单词", range(len(st.session_state.hotspot_list)),
                                   format_func=lambda i: st.session_state.hotspot_list[i]["word"])
                if st.button("删除该热点"):
                    st.session_state.hotspot_list.pop(del_idx)
                    st.session_state.draw_canvas = st.session_state.bg_img.copy()
                    draw = ImageDraw.Draw(st.session_state.draw_canvas)
                    for item in st.session_state.hotspot_list:
                        draw.rectangle(item["box"], outline="red", width=3)
                    st.rerun()

        # 单词配置导入导出（云端重启数据丢失，务必导出备份）
        st.divider()
        st.subheader("单词库配置保存/导入")
        if len(st.session_state.hotspot_list) > 0:
            json_data = json.dumps(st.session_state.hotspot_list, ensure_ascii=False, indent=2)
            st.download_button("💾 导出单词配置JSON", data=json_data, file_name="school_word_config.json")
        json_upload = st.file_uploader("📂 导入本地备份JSON", type="json")
        if json_upload:
            load_config = json.load(json_upload)
            st.session_state.hotspot_list = load_config
            if st.session_state.bg_img:
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
                draw = ImageDraw.Draw(st.session_state.draw_canvas)
                for item in st.session_state.hotspot_list:
                    draw.rectangle(item["box"], outline="red", width=3)
            st.success("单词配置导入完成，切换学生页即可对外分享学习")
    else:
        st.stop()

# 校园高频词汇模板（管理员复制快速录入）
with st.expander("📚 校园英语词汇模板（直接复制填写）"):
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
11. garden /ˈɡɑːdn/ 花坛
12. office /ˈɒfɪs/ 教师办公室
""")