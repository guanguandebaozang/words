import streamlit as st
from PIL import Image, ImageDraw
import json
import streamlit_authenticator as stauth

# 页面基础配置
st.set_page_config(page_title="🏫校园场景点读学英语", layout="wide")

# 从secrets读取加密账号配置
auth_config = st.secrets["credentials"]
authenticator = stauth.Authenticate(auth_config, "school_campus_app", "auth_cookie_key", cookie_expiry_days=30)

# 登录校验
login_name, auth_status, username = authenticator.login("管理员登录", "main")

# 会话状态初始化
if "bg_img" not in st.session_state:
    st.session_state.bg_img = None
if "draw_canvas" not in st.session_state:
    st.session_state.draw_canvas = None
if "hotspot_list" not in st.session_state:
    st.session_state.hotspot_list = []
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "visit"

# 页面标题与模式切换
st.title("🏫 校园实景图 热点点读英语学习平台")
st.divider()

mode_col1, mode_col2 = st.columns([1, 4])
with mode_col1:
    mode_select = st.radio("页面入口", ["学生学习页", "管理员后台"])

if mode_select == "学生学习页":
    st.session_state.view_mode = "visit"
else:
    st.session_state.view_mode = "admin"

# ====================== 学生学习页（前端JS朗读，无后端语音依赖） ======================
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区")
    st.info("仅查看单词、网页语音朗读，无编辑权限")

    if st.session_state.bg_img is None:
        st.warning("管理员尚未上传校园场景图片与单词热点，请稍后再来！")
    else:
        st.image(st.session_state.draw_canvas, caption="校园全景（红色方框为单词学习热点）", use_column_width=True)

        if len(st.session_state.hotspot_list) == 0:
            st.warning("管理员还未添加任何校园单词")
        else:
            st.subheader("选择校园物品学习单词")
            hot_idx = st.radio("物品列表",
                               options=range(len(st.session_state.hotspot_list)),
                               format_func=lambda i: st.session_state.hotspot_list[i]["word"])
            data = st.session_state.hotspot_list[hot_idx]

            st.markdown(f"# {data['word']}")
            st.markdown(f"音标：/{data['phonetic']}/")
            st.markdown(f"释义：{data['cn']}")
            st.markdown(f"例句：{data['sentence']}")

            # 前端语音朗读JS
            word_js = f"""
            <script>
                function speakWord() {{
                    let utter = new SpeechSynthesisUtterance("{data['word']}");
                    utter.lang = "en-US";
                    speechSynthesis.speak(utter);
                }}
                function speakSentence() {{
                    let utter = new SpeechSynthesisUtterance("{data['sentence']}");
                    utter.lang = "en-US";
                    speechSynthesis.speak(utter);
                }}
            </script>
            """
            st.components.v1.html(word_js, height=0)

            b1, b2 = st.columns(2)
            with b1:
                st.button("🔊 朗读单词", on_click=lambda: st.components.v1.html("<script>speakWord()</script>", height=0))
            with b2:
                st.button("🔊 朗读例句", on_click=lambda: st.components.v1.html("<script>speakSentence()</script>", height=0))

# ====================== 管理员后台（加密密码登录，无明文密码） ======================
else:
    st.subheader("🔐 管理员配置后台")
    # 未登录 / 登录失败
    if auth_status is False:
        st.error("账号密码错误，请重新登录")
    elif auth_status is None:
        st.info("请输入管理员账号密码登录后台")
    # 登录成功
    elif auth_status:
        st.success(f"欢迎管理员 {login_name}，可编辑校园单词热点")
        authenticator.logout("退出登录", "sidebar")

        # 侧边栏编辑区
        with st.sidebar:
            st.header("1. 上传校园场景图")
            upload_img = st.file_uploader("上传校园图片 jpg/png", type=["jpg", "png", "jpeg"])
            if upload_img:
                st.session_state.bg_img = Image.open(upload_img).convert("RGB")
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
                st.session_state.hotspot_list = []
                st.success("图片加载完成，开始配置热点")

            st.divider()
            st.header("2. 设置热点框坐标")
            if st.session_state.bg_img:
                w, h = st.session_state.bg_img.size
                c1, c2 = st.columns(2)
                with c1:
                    x1 = st.number_input("左上角X", min_value=0, max_value=w, value=30)
                    y1 = st.number_input("左上角Y", min_value=0, max_value=h, value=30)
                with c2:
                    x2 = st.number_input("右下角X", min_value=0, max_value=w, value=120)
                    y2 = st.number_input("右下角Y", min_value=0, max_value=h, value=120)

            st.divider()
            st.header("3. 单词信息录入")
            word = st.text_input("英文单词")
            phonetic = st.text_input("国际音标")
            cn_trans = st.text_input("中文释义")
            sentence = st.text_input("校园例句")

            st.divider()
            st.header("4. 操作按钮")
            save_hot = st.button("✅ 保存当前热点")
            clear_all_hot = st.button("🗑️ 清空全部热点")

        # 保存热点逻辑
        if save_hot and st.session_state.bg_img:
            if not word or not cn_trans:
                st.warning("单词和中文释义不能为空！")
            else:
                hot_data = {
                    "box": [x1, y1, x2, y2],
                    "word": word,
                    "phonetic": phonetic,
                    "cn": cn_trans,
                    "sentence": sentence
                }
                st.session_state.hotspot_list.append(hot_data)
                draw = ImageDraw.Draw(st.session_state.draw_canvas)
                draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
                st.success(f"热点【{word}】添加成功！")

        if clear_all_hot:
            st.session_state.hotspot_list = []
            if st.session_state.bg_img:
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
            st.rerun()

        # 主画面预览
        col_img, col_opt = st.columns([3, 1])
        with col_img:
            if st.session_state.draw_canvas:
                st.image(st.session_state.draw_canvas, caption="编辑预览图（红色为热点框）", use_column_width=True)
            else:
                st.info("请左侧上传校园图片")

        # 热点删除管理
        with col_opt:
            st.subheader("热点管理")
            if len(st.session_state.hotspot_list) == 0:
                st.info("暂无热点")
            else:
                del_idx = st.radio("选择删除", range(len(st.session_state.hotspot_list)),
                                   format_func=lambda i: st.session_state.hotspot_list[i]["word"])
                if st.button("删除该热点"):
                    st.session_state.hotspot_list.pop(del_idx)
                    st.session_state.draw_canvas = st.session_state.bg_img.copy()
                    draw = ImageDraw.Draw(st.session_state.draw_canvas)
                    for item in st.session_state.hotspot_list:
                        draw.rectangle(item["box"], outline="red", width=3)
                    st.rerun()

        # 导入导出配置
        st.divider()
        st.subheader("单词配置保存/导入")
        if len(st.session_state.hotspot_list) > 0:
            json_str = json.dumps(st.session_state.hotspot_list, ensure_ascii=False, indent=2)
            st.download_button("💾 导出单词配置文件", data=json_str,
                               file_name="school_word_config.json", mime="application/json")

        upload_config = st.file_uploader("📂 导入已保存的配置json", type=["json"])
        if upload_config:
            import_data = json.load(upload_config)
            st.session_state.hotspot_list = import_data
            if st.session_state.bg_img:
                st.session_state.draw_canvas = st.session_state.bg_img.copy()
                draw = ImageDraw.Draw(st.session_state.draw_canvas)
                for item in st.session_state.hotspot_list:
                    draw.rectangle(item["box"], outline="red", width=3)
            st.success("配置导入完成！切换学生页即可分享学习")
    else:
        st.stop()

# 校园词汇模板
with st.expander("📚 校园高频英语词汇模板（管理员复制使用）"):
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