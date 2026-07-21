import streamlit as st
from PIL import Image, ImageDraw
import json
import streamlit_authenticator

st.set_page_config(page_title="🏫校园场景点读学英语", layout="wide")

# 手动递归转换Secrets为标准字典，无递归栈溢出
def secret_to_std_dict(obj):
    if hasattr(obj, "items"):
        res = {}
        for k, v in obj.items():
            res[k] = secret_to_std_dict(v)
        return res
    return obj

# 强制读取云端Secrets（满足必须读取secret要求）
raw_secrets = st.secrets["credentials"]
auth_credentials = secret_to_std_dict(raw_secrets)

# 初始化鉴权，location改为unrendered，手动渲染登录框
authenticator = streamlit_authenticator.Authenticate(
    auth_credentials,
    "campus_word_web",
    "cloud_auth_secret_key_0721",
    cookie_expiry_days=30
)

# 关键修复：location="unrendered"，不自动渲染，手动创建登录组件
login_name, auth_state, login_user = authenticator.login(location="unrendered")

# 手动绘制登录表单（替代失效main参数）
if auth_state is None:
    st.subheader("🔐 管理员登录")
    with st.form("admin_login_form"):
        username_input = st.text_input("用户名")
        pwd_input = st.text_input("密码", type="password")
        submit = st.form_submit_button("登录验证")
        if submit:
            # 手动校验账号密码
            user_data = auth_credentials["usernames"].get(username_input)
            if user_data and streamlit_authenticator.Hasher.check_pwd(pwd_input, user_data["password"]):
                st.session_state["is_admin"] = True
                st.session_state["admin_name"] = user_data["name"]
                st.rerun()
            else:
                st.error("用户名或密码错误")

# 会话缓存初始化
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

# 页面标题与切换
st.title("🏫 校园实景热点点读英语学习平台")
st.divider()
col_mode1, col_mode2 = st.columns([1, 4])
with col_mode1:
    page_select = st.radio("页面入口", ["学生学习页", "管理员后台"])
st.session_state.view_mode = "visit" if page_select == "学生学习页" else "admin"

# ---------------------- 学生公开学习页（所有访客可访问） ----------------------
if st.session_state.view_mode == "visit":
    st.subheader("📖 学生学习专区（仅浏览+浏览器语音朗读）")
    st.info("外网访客仅可查看单词、播放发音，无任何编辑、上传权限")

    if st.session_state.bg_img is None:
        st.warning("管理员尚未上传校园场景图与单词热点，请稍后再来！")
    else:
        st.image(st.session_state.draw_canvas, caption="校园全景（红色方框=单词学习热点）", use_column_width=True)
        if len(st.session_state.hotspot_list) == 0:
            st.warning("暂无校园英语词汇")
        else:
            hot_idx = st.radio("选择校园物品学习", range(len(st.session_state.hotspot_list)),
                               format_func=lambda i: st.session_state.hotspot_list[i]["word"])
            word_info = st.session_state.hotspot_list[hot_idx]

            st.markdown(f"# {word_info['word']}")
            st.markdown(f"音标：/{word_info['phonetic']}/")
            st.markdown(f"中文释义：{word_info['cn']}")
            st.markdown(f"校园例句：{word_info['sentence']}")

            # 前端Web Speech朗读，云端通用
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
            btn1, btn2 = st.columns(2)
            with btn1:
                st.button("🔊 朗读单词", on_click=lambda: st.components.v1.html("<script>readWord()</script>", height=0))
            with btn2:
                st.button("🔊 朗读例句", on_click=lambda: st.components.v1.html("<script>readSentence()</script>", height=0))

# ---------------------- 管理员后台（必须登录解锁） ----------------------
else:
    if not st.session_state.is_admin:
        st.stop() # 未登录直接阻断页面
    st.subheader("🔐 管理员单词配置后台")
    st.success(f"欢迎管理员 {st.session_state.admin_name}")
    if st.button("退出登录"):
        st.session_state.is_admin = False
        st.session_state.admin_name = ""
        st.rerun()

    # 侧边栏编辑区
    with st.sidebar:
        st.header("1. 上传校园场景图片")
        upload_img = st.file_uploader("支持jpg/png/jpeg", type=["jpg", "png", "jpeg"])
        if upload_img:
            st.session_state.bg_img = Image.open(upload_img).convert("RGB")
            st.session_state.draw_canvas = st.session_state.bg_img.copy()
            st.session_state.hotspot_list = []
            st.success("校园图片加载完成，开始配置单词热点")

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
        st.header("4. 操作按钮")
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

    # 图片预览 + 热点删除面板
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

    # 单词配置导入导出（云端必备份）
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
            for item in st.session_state.hotspot_list:
                draw.rectangle(item["box"], outline="red", width=3)
        st.success("单词配置导入完成！切换学生页即可分享学习")

# 校园高频词汇模板
with st.expander("📚 校园英语词汇模板（管理员直接复制）"):
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