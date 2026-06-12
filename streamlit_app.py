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

# CSS สำหรับ Flip Card
flip_card_css = """
<style>
.flip-card {
    background-color: transparent;
    width: 100%;
    height: 400px;
    perspective: 1000px;
    margin: 20px 0;
}

.flip-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;
    transition: transform 0.6s;
    transform-style: preserve-3d;
}

.flip-card.flipped .flip-card-inner {
    transform: rotateY(180deg);
}

.flip-card-front, .flip-card-back {
    position: absolute;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    font-weight: bold;
    border-radius: 15px;
    cursor: pointer;
}

.flip-card-front {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.flip-card-back {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
    transform: rotateY(180deg);
    flex-direction: column;
    justify-content: space-around;
    padding: 20px;
}

.pinyin-text {
    font-size: 32px;
    margin-bottom: 20px;
}

.meaning-text {
    font-size: 28px;
}

.click-hint {
    font-size: 14px;
    opacity: 0.8;
    margin-top: 10px;
}

.hsk-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    padding: 8px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    color: white;
    z-index: 10;
}

.hsk-level-1 { background-color: #4CAF50; }
.hsk-level-2 { background-color: #8BC34A; }
.hsk-level-3 { background-color: #FFC107; color: #333; }
.hsk-level-4 { background-color: #FF9800; }
.hsk-level-5 { background-color: #FF5722; }
.hsk-level-6 { background-color: #9C27B0; }
.hsk-level-7-9 { background-color: #FFD700; color: #333; }
</style>
"""

def get_hsk_color(level):
    """ส่งคืนสีตามระดับ HSK"""
    level_str = str(level)
    color_map = {
        "1": {"bg": "#4CAF50", "fg": "#ffffff", "gradient": "135deg, #4CAF50 0%, #45a049 100%"},
        "2": {"bg": "#8BC34A", "fg": "#ffffff", "gradient": "135deg, #8BC34A 0%, #7CB342 100%"},
        "3": {"bg": "#FFC107", "fg": "#333333", "gradient": "135deg, #FFC107 0%, #FFB300 100%"},
        "4": {"bg": "#FF9800", "fg": "#ffffff", "gradient": "135deg, #FF9800 0%, #F57C00 100%"},
        "5": {"bg": "#FF5722", "fg": "#ffffff", "gradient": "135deg, #FF5722 0%, #E64A19 100%"},
        "6": {"bg": "#9C27B0", "fg": "#ffffff", "gradient": "135deg, #9C27B0 0%, #7B1FA2 100%"},
        "7-9": {"bg": "#FFD700", "fg": "#333333", "gradient": "135deg, #FFD700 0%, #FFC700 100%"},
    }
    return color_map.get(level_str, {"bg": "#667eea", "fg": "#ffffff", "gradient": "135deg, #667eea 0%, #764ba2 100%"})

st.markdown(flip_card_css, unsafe_allow_html=True)

st.title("🇨🇳 HSK Flashcard Intelligence")

st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV (คอลัมน์: word, pinyin, trans_th, level)", type=["csv"])
if uploaded is not None:
    try:
        df_raw = pd.read_csv(uploaded)
    except Exception:
        try:
            uploaded.seek(0)
            df_raw = pd.read_csv(uploaded, encoding='utf-8', engine='python')
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ CSV ได้: {e}")
            st.stop()
    # ปรับคอลัมน์ให้ตรงกับรูปแบบที่คาดหวัง
    if 'word' in df_raw.columns and 'trans_th' in df_raw.columns and 'level' in df_raw.columns:
        df = df_raw[['word', 'pinyin', 'trans_th', 'level']].copy()
        df.columns = ['simplified', 'pinyin', 'meaning', 'hsk_level']
    else:
        st.error(f"⚠️ CSV ต้องมีคอลัมน์: word, pinyin, trans_th, level")
        st.stop()
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

# เรียงลำดับ HSK Level อย่างถูกต้อง (รองรับ 1,2,3...6,7-9)
def parse_level(level_str):
    """ดึงตัวเลขแรกจาก level string (เช่น '7-9' -> 7, '3' -> 3)"""
    try:
        return float(level_str.split('-')[0])
    except:
        return float('inf')

available_levels = sorted(df['hsk_level'].astype(str).unique(), key=parse_level)
selected_levels = st.sidebar.multiselect("เลือกเลเวล HSK:", options=available_levels, default=available_levels)

# Display colored HSK level badges
if selected_levels:
    st.sidebar.markdown("**📊 เลเวลที่เลือก:**")
    badges_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;">'
    for level in sorted(selected_levels, key=parse_level):
        color_info = get_hsk_color(level)
        badges_html += f'''<span style="
            background: linear-gradient({color_info['gradient']});
            color: {color_info['fg']};
            padding: 8px 14px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            Level {level} ✓
        </span>'''
    badges_html += '</div>'
    st.sidebar.markdown(badges_html, unsafe_allow_html=True)

if selected_levels:
    filtered_df = df[df['hsk_level'].astype(str).isin(selected_levels)]
else:
    filtered_df = df.copy()

tab1, tab2 = st.tabs(["🎴 Flashcard (สุ่มทาย)", "📖 คำศัพท์ทั้งหมด (List)"])

with tab1:
    if not filtered_df.empty:
        # Initialize session state
        if 'current_word' not in st.session_state or st.session_state.current_word_level not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
        
        # Always ensure these exist
        if 'card_flipped' not in st.session_state:
            st.session_state.card_flipped = False
        if 'audio_played' not in st.session_state:
            st.session_state.audio_played = False
        
        # Initialize memory stats
        if 'remembered' not in st.session_state:
            st.session_state.remembered = []
        if 'forgotten' not in st.session_state:
            st.session_state.forgotten = []
        if 'last_feedback' not in st.session_state:
            st.session_state.last_feedback = None
        
        # Auto-play audio on page load
        if not st.session_state.audio_played:
            audio_fp = speak_word(st.session_state.current_word['simplified'])
            st.session_state.audio_played = True
        
        col_left, col_right = st.columns([0.7, 0.3], gap="large")
        
        with col_left:
            st.subheader("🎴 Flashcard")
            
            # Flip Card Element
            card_id = "flip-card"
            flipped_class = "flipped" if st.session_state.get('card_flipped', False) else ""
            
            # Get color based on HSK level
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])
            
            # Create a placeholder and update it based on flip state
            flip_placeholder = st.empty()
            
            with flip_placeholder.container():
                flip_card_html = f"""
                <div class="{card_id} {flipped_class}" style="cursor: default; position: relative;">
                    <div class="flip-card-inner">
                        <div class="flip-card-front" style="background: linear-gradient({colors['gradient']}); color: {colors['fg']};">
                            <div class="hsk-badge hsk-level-{st.session_state.current_word['hsk_level']}">
                                HSK {st.session_state.current_word['hsk_level']}
                            </div>
                            <div>
                                {st.session_state.current_word['simplified']}
                                <div class="click-hint">กดปุ่มด้านล่าง</div>
                            </div>
                        </div>
                        <div class="flip-card-back" style="background: linear-gradient({colors['gradient']}); color: {colors['fg']};">
                            <div class="hsk-badge hsk-level-{st.session_state.current_word['hsk_level']}">
                                HSK {st.session_state.current_word['hsk_level']}
                            </div>
                            <div class="pinyin-text">{st.session_state.current_word['pinyin']}</div>
                            <div class="meaning-text">{st.session_state.current_word['meaning']}</div>
                            <div class="click-hint">กดปุ่มด้านล่าง</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(flip_card_html, unsafe_allow_html=True)
            
            # Feedback section - จำได้/ไม่ได้ อยู่ด้านบน
            st.markdown("---")
            col_feedback1, col_feedback2 = st.columns(2)
            
            with col_feedback1:
                if st.button("✅ จำได้", use_container_width=True, key="remembered_btn", help="สีเขียว = จำได้"):
                    word_simplified = st.session_state.current_word['simplified']
                    if word_simplified not in st.session_state.remembered:
                        st.session_state.remembered.append(word_simplified)
                    if word_simplified in st.session_state.forgotten:
                        st.session_state.forgotten.remove(word_simplified)
                    st.session_state.last_feedback = "remembered"
                    st.session_state.current_word = filtered_df.sample().iloc[0]
                    st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                    st.session_state.card_flipped = False
                    st.session_state.audio_played = False
                    st.rerun()
            
            with col_feedback2:
                if st.button("❌ จำไม่ได้", use_container_width=True, key="forgotten_btn", help="สีแดง = จำไม่ได้"):
                    word_simplified = st.session_state.current_word['simplified']
                    if word_simplified not in st.session_state.forgotten:
                        st.session_state.forgotten.append(word_simplified)
                    if word_simplified in st.session_state.remembered:
                        st.session_state.remembered.remove(word_simplified)
                    st.session_state.last_feedback = "forgotten"
                    st.session_state.current_word = filtered_df.sample().iloc[0]
                    st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                    st.session_state.card_flipped = False
                    st.session_state.audio_played = False
                    st.rerun()
            
            st.markdown("---")
            
            # Flip card button
            if st.button("👁️ เปิดดูคำแปล", use_container_width=True):
                st.session_state.card_flipped = not st.session_state.card_flipped
                st.rerun()
            
            st.markdown("---")
            
            # Display stats - สถิติอยู่ด้านล่าง
            total_played = len(st.session_state.remembered) + len(st.session_state.forgotten)
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                st.metric("📊 เล่นไปแล้ว", total_played)
            
            with col_stat2:
                st.metric("✅ จำได้", len(st.session_state.remembered), delta_color="off")
            
            with col_stat3:
                st.metric("❌ จำไม่ได้", len(st.session_state.forgotten), delta_color="off")
        
        with col_right:
            # Get colors for current card
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])
            
            st.subheader("⚡ ควบคุม")
            
            # Control buttons - ด้านขวา
            st.markdown("---")
            
            col_right_btn1, col_right_btn2, col_right_btn3 = st.columns(3)
            
            with col_right_btn1:
                if st.button("✅ จำได้", use_container_width=True, key="right_remembered_btn"):
                    word_simplified = st.session_state.current_word['simplified']
                    if word_simplified not in st.session_state.remembered:
                        st.session_state.remembered.append(word_simplified)
                    if word_simplified in st.session_state.forgotten:
                        st.session_state.forgotten.remove(word_simplified)
                    st.session_state.current_word = filtered_df.sample().iloc[0]
                    st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                    st.session_state.card_flipped = False
                    st.session_state.audio_played = False
                    st.rerun()
            
            with col_right_btn2:
                if st.button("❌ ไม่ได้", use_container_width=True, key="right_forgotten_btn"):
                    word_simplified = st.session_state.current_word['simplified']
                    if word_simplified not in st.session_state.forgotten:
                        st.session_state.forgotten.append(word_simplified)
                    if word_simplified in st.session_state.remembered:
                        st.session_state.remembered.remove(word_simplified)
                    st.session_state.current_word = filtered_df.sample().iloc[0]
                    st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                    st.session_state.card_flipped = False
                    st.session_state.audio_played = False
                    st.rerun()
            
            with col_right_btn3:
                if st.button("⏭️ ข้าม", use_container_width=True, key="skip_btn"):
                    st.session_state.current_word = filtered_df.sample().iloc[0]
                    st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
                    st.session_state.card_flipped = False
                    st.session_state.audio_played = False
                    st.session_state.last_feedback = None
                    st.rerun()
            
            st.markdown("---")
            
            # Play sound button
            if st.button("🔊 เล่นเสียงอีก", use_container_width=True):
                audio_fp = speak_word(st.session_state.current_word['simplified'])
                # Use autoplay audio element
                audio_base64 = audio_fp.getvalue()
                import base64
                b64_audio = base64.b64encode(audio_base64).decode()
                st.markdown(f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mpeg">
                </audio>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.write("**💡 ข้อมูลคำศัพท์:**")
            st.markdown(f"""
            - 🇨🇳 คำจีน: {st.session_state.current_word['simplified']}
            - 📖 พินอิน: {st.session_state.current_word['pinyin']}
            - 🇹🇭 ความหมาย: {st.session_state.current_word['meaning']}
            """)

with tab2:
    if not filtered_df.empty:
        st.dataframe(filtered_df[['simplified', 'pinyin', 'meaning', 'hsk_level']], use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ ดาวน์โหลด CSV", data=csv, file_name='hsk_filtered.csv', mime='text/csv')