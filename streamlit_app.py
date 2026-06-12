import streamlit as st
import pandas as pd
from gtts import gTTS
import io

st.set_page_config(page_title="HSK Flashcard AI", page_icon="🇨🇳", layout="centered")

@st.cache_data
def get_default_vocab():
    """ข้อมูลคำศัพท์ HSK ตัวอย่าง (เมื่อไม่มี CSV จากผู้ใช้)"""
    return pd.DataFrame([
        # HSK Level 1
        {"simplified": "你", "pinyin": "nǐ", "meaning": "คุณ", "hsk_level": "1"},
        {"simplified": "好", "pinyin": "hǎo", "meaning": "ดี", "hsk_level": "1"},
        {"simplified": "谢谢", "pinyin": "xièxie", "meaning": "ขอบคุณ", "hsk_level": "1"},
        {"simplified": "是", "pinyin": "shì", "meaning": "เป็น", "hsk_level": "1"},
        {"simplified": "不", "pinyin": "bù", "meaning": "ไม่", "hsk_level": "1"},
        {"simplified": "我", "pinyin": "wǒ", "meaning": "ฉัน", "hsk_level": "1"},
        {"simplified": "吃", "pinyin": "chī", "meaning": "กิน", "hsk_level": "1"},
        {"simplified": "喝", "pinyin": "hē", "meaning": "ดื่ม", "hsk_level": "1"},
        {"simplified": "水", "pinyin": "shuǐ", "meaning": "น้ำ", "hsk_level": "1"},
        {"simplified": "家", "pinyin": "jiā", "meaning": "บ้าน", "hsk_level": "1"},
        {"simplified": "有", "pinyin": "yǒu", "meaning": "มี", "hsk_level": "1"},
        {"simplified": "在", "pinyin": "zài", "meaning": "อยู่", "hsk_level": "1"},
        {"simplified": "他", "pinyin": "tā", "meaning": "เขา", "hsk_level": "1"},
        {"simplified": "她", "pinyin": "tā", "meaning": "เธอ", "hsk_level": "1"},
        {"simplified": "一", "pinyin": "yī", "meaning": "หนึ่ง", "hsk_level": "1"},
        {"simplified": "二", "pinyin": "èr", "meaning": "สอง", "hsk_level": "1"},
        {"simplified": "三", "pinyin": "sān", "meaning": "สาม", "hsk_level": "1"},
        {"simplified": "大", "pinyin": "dà", "meaning": "ใหญ่", "hsk_level": "1"},
        {"simplified": "小", "pinyin": "xiǎo", "meaning": "เล็ก", "hsk_level": "1"},
        {"simplified": "多", "pinyin": "duō", "meaning": "มาก", "hsk_level": "1"},
        # HSK Level 2
        {"simplified": "朋友", "pinyin": "péngyou", "meaning": "เพื่อน", "hsk_level": "2"},
        {"simplified": "学习", "pinyin": "xuéxí", "meaning": "เรียน", "hsk_level": "2"},
        {"simplified": "工作", "pinyin": "gōngzuò", "meaning": "ทำงาน", "hsk_level": "2"},
        {"simplified": "学校", "pinyin": "xuéxiào", "meaning": "โรงเรียน", "hsk_level": "2"},
        {"simplified": "天气", "pinyin": "tiānqì", "meaning": "สภาพอากาศ", "hsk_level": "2"},
        {"simplified": "开心", "pinyin": "kāixīn", "meaning": "มีความสุข", "hsk_level": "2"},
        {"simplified": "美国", "pinyin": "Měiguó", "meaning": "สหรัฐอเมริกา", "hsk_level": "2"},
        {"simplified": "中国", "pinyin": "Zhōngguó", "meaning": "จีน", "hsk_level": "2"},
        {"simplified": "电话", "pinyin": "diànhuà", "meaning": "โทรศัพท์", "hsk_level": "2"},
        {"simplified": "时间", "pinyin": "shíjiān", "meaning": "เวลา", "hsk_level": "2"},
        {"simplified": "生日", "pinyin": "shēngrì", "meaning": "วันเกิด", "hsk_level": "2"},
        {"simplified": "礼物", "pinyin": "lǐwù", "meaning": "ของขวัญ", "hsk_level": "2"},
        {"simplified": "饭", "pinyin": "fàn", "meaning": "ข้าว", "hsk_level": "2"},
        {"simplified": "茶", "pinyin": "chá", "meaning": "ชา", "hsk_level": "2"},
        {"simplified": "北京", "pinyin": "Běijīng", "meaning": "เบอร์จิ้ง", "hsk_level": "2"},
        {"simplified": "上海", "pinyin": "Shànghǎi", "meaning": "เซี่ยงไฮ้", "hsk_level": "2"},
        {"simplified": "颜色", "pinyin": "yánsè", "meaning": "สี", "hsk_level": "2"},
        {"simplified": "红", "pinyin": "hóng", "meaning": "แดง", "hsk_level": "2"},
        {"simplified": "白", "pinyin": "bái", "meaning": "ขาว", "hsk_level": "2"},
        {"simplified": "黑", "pinyin": "hēi", "meaning": "ดำ", "hsk_level": "2"},
        # HSK Level 3
        {"simplified": "重要", "pinyin": "zhòngyào", "meaning": "สำคัญ", "hsk_level": "3"},
        {"simplified": "机会", "pinyin": "jīhuì", "meaning": "โอกาส", "hsk_level": "3"},
        {"simplified": "发展", "pinyin": "fāzhǎn", "meaning": "พัฒนา", "hsk_level": "3"},
        {"simplified": "技术", "pinyin": "jìshù", "meaning": "เทคโนโลยี", "hsk_level": "3"},
        {"simplified": "建设", "pinyin": "jiànshè", "meaning": "สร้างสรรค์", "hsk_level": "3"},
        {"simplified": "体育", "pinyin": "tǐy育", "meaning": "กีฬา", "hsk_level": "3"},
        {"simplified": "音乐", "pinyin": "yīnyuè", "meaning": "ดนตรี", "hsk_level": "3"},
        {"simplified": "美术", "pinyin": "měishù", "meaning": "ศิลปะ", "hsk_level": "3"},
        {"simplified": "电脑", "pinyin": "diànnǎo", "meaning": "คอมพิวเตอร์", "hsk_level": "3"},
        {"simplified": "互联网", "pinyin": "hùliánwǎng", "meaning": "อินเทอร์เน็ต", "hsk_level": "3"},
        {"simplified": "软件", "pinyin": "ruǎnjiàn", "meaning": "ซอฟต์แวร์", "hsk_level": "3"},
        {"simplified": "硬件", "pinyin": "yìngjiàn", "meaning": "ฮาร์ดแวร์", "hsk_level": "3"},
        {"simplified": "公司", "pinyin": "gōngsī", "meaning": "บริษัท", "hsk_level": "3"},
        {"simplified": "员工", "pinyin": "yuángōng", "meaning": "พนักงาน", "hsk_level": "3"},
        {"simplified": "老板", "pinyin": "lǎobǎn", "meaning": "เจ้านาย", "hsk_level": "3"},
        {"simplified": "比赛", "pinyin": "bǐsài", "meaning": "การแข่งขัน", "hsk_level": "3"},
        {"simplified": "运动", "pinyin": "yùndòng", "meaning": "กีฬา", "hsk_level": "3"},
        {"simplified": "旅游", "pinyin": "lǚyóu", "meaning": "ท่องเที่ยว", "hsk_level": "3"},
        {"simplified": "旅行", "pinyin": "lǚxíng", "meaning": "การเดินทาง", "hsk_level": "3"},
        {"simplified": "计划", "pinyin": "jìhuà", "meaning": "แผน", "hsk_level": "3"},
        # HSK Level 4
        {"simplified": "安全", "pinyin": "ānquán", "meaning": "ความปลอดภัย", "hsk_level": "4"},
        {"simplified": "标准", "pinyin": "biāozhǔn", "meaning": "มาตรฐาน", "hsk_level": "4"},
        {"simplified": "成功", "pinyin": "chénggōng", "meaning": "ความสำเร็จ", "hsk_level": "4"},
        {"simplified": "达到", "pinyin": "dádào", "meaning": "บรรลุ", "hsk_level": "4"},
        {"simplified": "确定", "pinyin": "quèdìng", "meaning": "แน่นอน", "hsk_level": "4"},
        {"simplified": "政府", "pinyin": "zhèngfǔ", "meaning": "รัฐบาล", "hsk_level": "4"},
        {"simplified": "政策", "pinyin": "zhèngcè", "meaning": "นโยบาย", "hsk_level": "4"},
        {"simplified": "经济", "pinyin": "jīngjì", "meaning": "เศรษฐกิจ", "hsk_level": "4"},
        {"simplified": "贸易", "pinyin": "màoyì", "meaning": "การค้า", "hsk_level": "4"},
        {"simplified": "商业", "pinyin": "shāngyè", "meaning": "ธุรกิจ", "hsk_level": "4"},
        {"simplified": "文化", "pinyin": "wénhuà", "meaning": "วัฒนธรรม", "hsk_level": "4"},
        {"simplified": "传统", "pinyin": "chuántǒng", "meaning": "ประเพณี", "hsk_level": "4"},
        {"simplified": "现代", "pinyin": "xiàndài", "meaning": "สมัยใหม่", "hsk_level": "4"},
        {"simplified": "社会", "pinyin": "shèhuì", "meaning": "สังคม", "hsk_level": "4"},
        {"simplified": "家庭", "pinyin": "jiātíng", "meaning": "ครอบครัว", "hsk_level": "4"},
        {"simplified": "教育", "pinyin": "jiàoyù", "meaning": "การศึกษา", "hsk_level": "4"},
        {"simplified": "医疗", "pinyin": "yīliáo", "meaning": "การแพทย์", "hsk_level": "4"},
        {"simplified": "健康", "pinyin": "jiànkāng", "meaning": "สุขภาพ", "hsk_level": "4"},
        {"simplified": "环境", "pinyin": "huánjìng", "meaning": "สิ่งแวดล้อม", "hsk_level": "4"},
        {"simplified": "能源", "pinyin": "nényuán", "meaning": "พลังงาน", "hsk_level": "4"},
        # HSK Level 5
        {"simplified": "分析", "pinyin": "fēnxī", "meaning": "วิเคราะห์", "hsk_level": "5"},
        {"simplified": "原因", "pinyin": "yuányīn", "meaning": "สาเหตุ", "hsk_level": "5"},
        {"simplified": "结果", "pinyin": "jiéguǒ", "meaning": "ผลลัพธ์", "hsk_level": "5"},
        {"simplified": "影响", "pinyin": "yǐngxiǎng", "meaning": "ผลกระทบ", "hsk_level": "5"},
        {"simplified": "程度", "pinyin": "chéngdù", "meaning": "ระดับ", "hsk_level": "5"},
        {"simplified": "进步", "pinyin": "jìnbù", "meaning": "ความก้าวหน้า", "hsk_level": "5"},
        {"simplified": "改革", "pinyin": "gǎigé", "meaning": "การปฏิรูป", "hsk_level": "5"},
        {"simplified": "革命", "pinyin": "gémìng", "meaning": "การปฏิวัติ", "hsk_level": "5"},
        {"simplified": "合作", "pinyin": "hézuò", "meaning": "การร่วมมือ", "hsk_level": "5"},
        {"simplified": "国际", "pinyin": "guójì", "meaning": "ระหว่างประเทศ", "hsk_level": "5"},
        {"simplified": "联系", "pinyin": "liánxì", "meaning": "ติดต่อ", "hsk_level": "5"},
        {"simplified": "沟通", "pinyin": "gōutōng", "meaning": "การสื่อสาร", "hsk_level": "5"},
        {"simplified": "问题", "pinyin": "wèntí", "meaning": "ปัญหา", "hsk_level": "5"},
        {"simplified": "解决", "pinyin": "jiějué", "meaning": "แก้ไข", "hsk_level": "5"},
        {"simplified": "发现", "pinyin": "fāxiàn", "meaning": "ค้นพบ", "hsk_level": "5"},
        {"simplified": "研究", "pinyin": "yánjiū", "meaning": "วิจัย", "hsk_level": "5"},
        {"simplified": "实验", "pinyin": "shíyàn", "meaning": "การทดลอง", "hsk_level": "5"},
        {"simplified": "证明", "pinyin": "zhèngmíng", "meaning": "พิสูจน์", "hsk_level": "5"},
        {"simplified": "科学", "pinyin": "kēxué", "meaning": "วิทยาศาสตร์", "hsk_level": "5"},
        {"simplified": "理论", "pinyin": "lǐlùn", "meaning": "ทฤษฎี", "hsk_level": "5"},
        # HSK Level 6
        {"simplified": "哲学", "pinyin": "zhéxué", "meaning": "ปรัชญา", "hsk_level": "6"},
        {"simplified": "美学", "pinyin": "měixué", "meaning": "สุนทรียศาสตร์", "hsk_level": "6"},
        {"simplified": "逻辑", "pinyin": "luójí", "meaning": "ตรรกะ", "hsk_level": "6"},
        {"simplified": "伦理", "pinyin": "lúnlǐ", "meaning": "จริยธรรม", "hsk_level": "6"},
        {"simplified": "价值", "pinyin": "jiàzhí", "meaning": "ค่า", "hsk_level": "6"},
        {"simplified": "观点", "pinyin": "guāndiǎn", "meaning": "มุมมอง", "hsk_level": "6"},
        {"simplified": "思想", "pinyin": "sīxiǎng", "meaning": "ความคิด", "hsk_level": "6"},
        {"simplified": "信念", "pinyin": "xìnniàn", "meaning": "信ศรัทธา", "hsk_level": "6"},
        {"simplified": "权利", "pinyin": "quánlì", "meaning": "สิทธิ", "hsk_level": "6"},
        {"simplified": "义务", "pinyin": "yìwù", "meaning": "หน้าที่", "hsk_level": "6"},
        {"simplified": "法律", "pinyin": "fǎlǜ", "meaning": "กฎหมาย", "hsk_level": "6"},
        {"simplified": "规则", "pinyin": "guīzé", "meaning": "กฎ", "hsk_level": "6"},
        {"simplified": "组织", "pinyin": "zǔzhī", "meaning": "องค์กร", "hsk_level": "6"},
        {"simplified": "制度", "pinyin": "zhìdù", "meaning": "ระบบ", "hsk_level": "6"},
        {"simplified": "自由", "pinyin": "zìyóu", "meaning": "อิสระ", "hsk_level": "6"},
        {"simplified": "平等", "pinyin": "píngděng", "meaning": "เท่าเทียม", "hsk_level": "6"},
        {"simplified": "公正", "pinyin": "gōngzhèng", "meaning": "ยุติธรรม", "hsk_level": "6"},
        {"simplified": "民主", "pinyin": "mínzhǔ", "meaning": "ประชาธิปไตย", "hsk_level": "6"},
        {"simplified": "共和", "pinyin": "gònghé", "meaning": "สาธารณรัฐ", "hsk_level": "6"},
        {"simplified": "共产", "pinyin": "gòngchǎn", "meaning": "คอมมิวนิสต์", "hsk_level": "6"},
    ])

@st.cache_data
def load_vocab():
    from pathlib import Path
    fname = "hsk_vocab - zh-th.csv"
    # Try a few sensible locations: same folder as this file, then current working dir
    base = Path(__file__).parent
    candidates = [base / fname, Path.cwd() / fname]
    for p in candidates:
        if p.exists():
            try:
                return pd.read_csv(p)
            except Exception:
                try:
                    return pd.read_csv(p, encoding="utf-8", engine="python")
                except Exception:
                    pass
    # Not found on disk; return default vocab
    return None

def speak_word(text):
    tts = gTTS(text, lang='zh-cn')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

st.title("🇨🇳 HSK Flashcard Intelligence")

st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV (คอลัมน์: simplified, pinyin, meaning, hsk_level)", type=["csv"])
if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
    except Exception:
        uploaded.seek(0)
        df = pd.read_csv(uploaded, encoding='utf-8', engine='python')
else:
    df = load_vocab()
    if df is None:
        df = get_default_vocab()
        st.sidebar.info("📚 ใช้ข้อมูลตัวอย่าง HSK สำหรับสาธารณะ — สามารถอัปโหลดไฟล์ CSV ของคุณเองได้")
if df.empty:
    st.error("ไฟล์ CSV ว่างเปล่า — ตรวจสอบว่ายังมีแถวข้อมูลและคอลัมน์ที่ถูกต้อง")
    st.stop()

query = st.sidebar.text_input("ค้นหา (จีน/พินอิน/ความหมาย)")
if query:
    mask = (
        df['simplified'].astype(str).str.contains(query, case=False, na=False)
        | df['pinyin'].astype(str).str.contains(query, case=False, na=False)
        | df['meaning'].astype(str).str.contains(query, case=False, na=False)
    )
    df = df[mask]

available_levels = sorted(df['hsk_level'].astype(str).unique())
selected_levels = st.sidebar.multiselect("เลือกเลเวล HSK:", options=available_levels, default=available_levels)
if selected_levels:
    filtered_df = df[df['hsk_level'].astype(str).isin(selected_levels)]
else:
    filtered_df = df.copy()

tab1, tab2 = st.tabs(["🎴 Flashcard (สุ่มทาย)", "📖 คำศัพท์ทั้งหมด (List)"])

with tab1:
    if not filtered_df.empty:
        if 'current_word' not in st.session_state or st.session_state.current_word_level not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])

        st.markdown(f"### <span style='font-size: 60px;'>{st.session_state.current_word['simplified']}</span>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔊 ฟังเสียงอ่าน"):
                audio_fp = speak_word(st.session_state.current_word['simplified'])
                st.audio(audio_fp, format='audio/mp3')
        with col2:
            if st.button("👁️ เปิดดูคำแปล"):
                st.success(f"พินอิน: {st.session_state.current_word['pinyin']}")
                st.info(f"ความหมาย: {st.session_state.current_word['meaning']}")
        with col3:
            if st.button("🔄 สุ่มคำใหม่"):
                st.session_state.current_word = filtered_df.sample().iloc[0]
                st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                st.rerun()

with tab2:
    if not filtered_df.empty:
        st.dataframe(filtered_df[['simplified', 'pinyin', 'meaning', 'hsk_level']], use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ ดาวน์โหลด CSV", data=csv, file_name='hsk_filtered.csv', mime='text/csv')