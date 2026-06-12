import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import requests
import urllib.parse
import unicodedata

st.set_page_config(
    page_title="HSK Flashcard AI",
    page_icon="🇨🇳",
    layout="centered",
    initial_sidebar_state="expanded",  # โชว์แถบด้านซ้าย — กดลูกศร « ที่มุมบนซ้ายเพื่อซ่อน/เปิดได้ตลอด
)

# ลำดับเลเวล HSK ทั้งหมดที่รองรับ (HSK 3.0 รวม 7-9 เป็นระดับเดียว)
HSK_LEVELS = ["1", "2", "3", "4", "5", "6", "7-9"]


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
        {"simplified": "体育", "pinyin": "tǐyù", "meaning": "กีฬา", "hsk_level": "3"},
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
        {"simplified": "能源", "pinyin": "néngyuán", "meaning": "พลังงาน", "hsk_level": "4"},
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
        {"simplified": "信念", "pinyin": "xìnniàn", "meaning": "ศรัทธา", "hsk_level": "6"},
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
        # HSK Level 7-9 (HSK 3.0)
        {"simplified": "悖论", "pinyin": "bèilùn", "meaning": "ความขัดแย้งในตัวเอง", "hsk_level": "7-9"},
        {"simplified": "范畴", "pinyin": "fànchóu", "meaning": "ขอบเขต/ประเภท", "hsk_level": "7-9"},
        {"simplified": "辩证", "pinyin": "biànzhèng", "meaning": "วิภาษวิธี", "hsk_level": "7-9"},
        {"simplified": "意识形态", "pinyin": "yìshí xíngtài", "meaning": "อุดมการณ์", "hsk_level": "7-9"},
        {"simplified": "颠覆", "pinyin": "diānfù", "meaning": "ล้มล้าง/พลิกผัน", "hsk_level": "7-9"},
    ])


@st.cache_data
def load_vocab():
    """โหลดไฟล์คำศัพท์ที่แนบมากับโปรเจกต์ (ถ้ามี) — รองรับทั้ง .csv และ .xlsx
    และทั้งคอลัมน์ชุดเก่า (simplified/pinyin/meaning/hsk_level)
    และชุดใหม่ (id, level, word, pinyin, pos_zh, pos_en, trans_en, trans_th)"""
    from pathlib import Path
    base = Path(__file__).parent
    search_dirs = [base, Path.cwd()]
    candidates = []
    for d in search_dirs:
        candidates += [
            d / "hsk_vocab - zh-th.csv",
            d / "hsk_vocab - zh-th.xlsx",
            d / "hsk_vocab.csv",
            d / "hsk_vocab.xlsx",
        ]

    for p in candidates:
        if not p.exists():
            continue
        try:
            if p.suffix.lower() in (".xlsx", ".xls"):
                df_raw = pd.read_excel(p)
            else:
                try:
                    df_raw = pd.read_csv(p)
                except Exception:
                    df_raw = pd.read_csv(p, encoding="utf-8", engine="python")
        except Exception:
            continue

        mapped = map_vocab_columns(df_raw)
        if mapped is not None:
            return mapped
        if {"simplified", "pinyin", "meaning", "hsk_level"}.issubset(df_raw.columns):
            return df_raw

    return None


def speak_word(text):
    tts = gTTS(text, lang='zh-cn')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp


def normalize_level(level):
    """รวมเลเวล 7,8,9 (หรือรูปแบบอื่น ๆ ของ HSK 3.0) ให้เป็นกลุ่ม '7-9'"""
    s = str(level).strip()
    if s in ("7", "8", "9", "7-9", "7-9级"):
        return "7-9"
    return s


def strip_tones(text):
    """ตัดวรรณยุกต์/เครื่องหมายกำกับเสียงออกจากพินอิน เช่น nǐ hǎo -> ni hao
    และแปลง ü -> u เพื่อให้ค้นหาแบบไม่ต้องพิมพ์วรรณยุกต์ได้"""
    if text is None:
        return ""
    text = str(text).replace("ü", "u").replace("Ü", "U")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def free_translate(text, source="zh-CN", target="th"):
    """แปลคำศัพท์แบบฟรี ไม่ต้องใช้ API Key (MyMemory Translation API)"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source}|{target}"}
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        translated = data.get("responseData", {}).get("translatedText")
        if translated:
            return translated
        return None
    except Exception:
        return None


def get_hsk_color(level):
    """ส่งคืนสีตามระดับ HSK — ใช้ร่วมกันทั้ง flashcard และตัวเลือกเลเวล"""
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


# ─── CSS ──────────────────────────────────────────────────────────────────────
flip_card_css = """
<style>
.flip-toggle-checkbox {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    pointer-events: none;
}
.flip-card {
    background-color: transparent;
    width: 100%;
    height: 360px;
    perspective: 1000px;
    margin: 16px 0;
    display: block;
    cursor: pointer;
}
.flip-card-inner {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;
    transition: transform 0.6s;
    transform-style: preserve-3d;
}
.flip-card.flipped .flip-card-inner { transform: rotateY(180deg); }
.flip-toggle-checkbox:checked + .flip-card .flip-card-inner { transform: rotateY(180deg); }
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
}
.flip-card-front { color: white; }
.flip-card-back {
    color: white;
    transform: rotateY(180deg);
    flex-direction: column;
    justify-content: space-around;
    padding: 20px;
}
.pinyin-text { font-size: 32px; margin-bottom: 12px; }
.meaning-text { font-size: 26px; }
.click-hint { font-size: 13px; opacity: 0.8; margin-top: 8px; }
.hsk-badge {
    position: absolute;
    top: 10px;
    right: 10px;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    color: white;
    background: rgba(0,0,0,0.18);
    z-index: 10;
}
.id-badge {
    position: absolute;
    top: 10px;
    left: 10px;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    font-family: monospace;
    color: white;
    background: rgba(0,0,0,0.18);
    z-index: 10;
}

/* ── Level selector pills (ใช้สีเดียวกับ flashcard) ── */
.level-pill-label {
    display: block;
    text-align: center;
    border-radius: 10px;
    padding: 8px 4px;
    font-weight: bold;
    font-size: 13px;
    cursor: pointer;
    user-select: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    transition: transform 0.1s, opacity 0.15s;
}
.level-pill-label:hover { transform: translateY(-1px); }
.level-pill-dim { opacity: 0.32; filter: grayscale(40%); }

/* ปรับ checkbox ของ Streamlit ให้เป็น "ปุ่มสีตามเลเวล" */
div[data-testid="stSidebar"] .level-toggle div[data-testid="stCheckbox"] {
    margin-bottom: 6px;
}
div[data-testid="stSidebar"] .level-toggle div[data-testid="stCheckbox"] label {
    width: 100%;
    border-radius: 10px;
    padding: 6px 10px;
    font-weight: bold;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}

/* ปุ่ม จำได้ / จำไม่ได้ ให้ใหญ่และกดง่ายขึ้น */
.st-key-remember_btn button, .st-key-forget_btn button {
    font-size: 22px !important;
    font-weight: 800 !important;
    padding: 1.1rem 0.5rem !important;
    border-radius: 14px !important;
}
.st-key-remember_btn button {
    background-color: rgba(76,175,80,0.15) !important;
    border: 2px solid #4CAF50 !important;
    color: #2e7d32 !important;
}
.st-key-forget_btn button {
    background-color: rgba(244,67,54,0.12) !important;
    border: 2px solid #e57373 !important;
    color: #c62828 !important;
}
</style>
"""
st.markdown(flip_card_css, unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🇨🇳 HSK Flashcard Intelligence")


# ─── Sidebar: data source ──────────────────────────────────────────────────────
st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader(
    "อัปโหลดไฟล์คำศัพท์ (CSV หรือ Excel .xlsx)",
    type=["csv", "xlsx", "xls"],
    help="รองรับคอลัมน์ชุดเก่า: word, pinyin, trans_th, level\n"
         "หรือชุดใหม่: id, level, word, pinyin, pos_zh, pos_en, trans_en, trans_th",
)


def map_vocab_columns(df_raw: pd.DataFrame) -> pd.DataFrame:
    """แปลงคอลัมน์จากไฟล์ผู้ใช้ (ชุดเก่า/ใหม่) ให้เป็นรูปแบบภายในของแอป"""
    cols = set(df_raw.columns)

    # ชุดใหม่: id, level, word, pinyin, pos_zh, pos_en, trans_en, trans_th
    if {"word", "trans_th", "level"}.issubset(cols):
        out = pd.DataFrame()
        out["id"] = df_raw["id"] if "id" in cols else range(1, len(df_raw) + 1)
        out["simplified"] = df_raw["word"]
        out["pinyin"] = df_raw["pinyin"] if "pinyin" in cols else ""
        out["meaning"] = df_raw["trans_th"]
        out["hsk_level"] = df_raw["level"]
        if "pos_th" in cols:
            out["pos"] = df_raw["pos_th"]
        elif "pos_en" in cols:
            out["pos"] = df_raw["pos_en"]
        return out

    return None


if uploaded is not None:
    try:
        if uploaded.name.lower().endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(uploaded)
        else:
            try:
                df_raw = pd.read_csv(uploaded)
            except Exception:
                uploaded.seek(0)
                df_raw = pd.read_csv(uploaded, encoding="utf-8", engine="python")
    except Exception as e:
        st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")
        st.stop()

    mapped = map_vocab_columns(df_raw)
    if mapped is not None:
        df = mapped
    else:
        st.error("⚠️ ไฟล์ต้องมีคอลัมน์อย่างน้อย: word, pinyin, trans_th, level (หรือ id, level, word, pinyin, ... trans_th)")
        st.stop()
else:
    df = load_vocab()
    if df is None:
        df = get_default_vocab()
        st.sidebar.info("📚 ใช้ข้อมูลตัวอย่าง HSK สำหรับสาธารณะ — สามารถอัปโหลดไฟล์ CSV/Excel ของคุณเองได้")

if "id" not in df.columns:
    df = df.reset_index(drop=True)
    df["id"] = df.index + 1

if df.empty:
    st.error("ไฟล์ CSV ว่างเปล่า — ตรวจสอบว่ายังมีแถวข้อมูลและคอลัมน์ที่ถูกต้อง")
    st.stop()

# รวมเลเวล 7/8/9 ให้เป็น "7-9" เพื่อให้ตรงกับชุดตัวเลือกมาตรฐาน
df['hsk_level'] = df['hsk_level'].apply(normalize_level)

query = st.sidebar.text_input(
    "🔍 ค้นหา (เลขที่ / คำจีน / พินอิน / คำแปล / เลเวล HSK)",
    placeholder="เช่น 12, ni hao, ขอบคุณ, hsk 3",
    help="พินอินไม่ต้องพิมพ์วรรณยุกต์ก็หาเจอ เช่น พิมพ์ 'ni' จะเจอ 'nǐ'",
)
if query:
    q = query.strip()
    q_toneless = strip_tones(q)

    pinyin_toneless = df['pinyin'].apply(strip_tones)
    id_str = df['id'].astype(str)
    hsk_str = "hsk" + df['hsk_level'].astype(str).str.lower()

    mask = (
        df['simplified'].astype(str).str.contains(q, case=False, na=False, regex=False)
        | df['pinyin'].astype(str).str.contains(q, case=False, na=False, regex=False)
        | pinyin_toneless.str.contains(q_toneless, na=False, regex=False)
        | df['meaning'].astype(str).str.contains(q, case=False, na=False, regex=False)
        | df['hsk_level'].astype(str).str.contains(q, case=False, na=False, regex=False)
        | (id_str == q)
        | hsk_str.str.contains(q_toneless.replace(" ", ""), na=False, regex=False)
    )
    df = df[mask]
    st.sidebar.caption(f"พบ {len(df)} คำ ที่ตรงกับ \"{query}\"")


# ─── Sidebar: level selector (สีตรงกับ flashcard, ครบ 1-6 และ 7-9) ────────────
st.sidebar.markdown("**📊 เลือกเลเวล HSK:**")

if "level_filter" not in st.session_state:
    st.session_state.level_filter = {lvl: True for lvl in HSK_LEVELS}

levels_with_data = set(df['hsk_level'].astype(str).unique())

# inject inline style ให้แต่ละ checkbox มีสีตาม HSK level ของมัน (เรียงตาม HSK_LEVELS)
level_css = ""
for i, lvl in enumerate(HSK_LEVELS, start=1):
    c = get_hsk_color(lvl)
    level_css += f"""
    div[data-testid="stSidebar"] .level-toggle:nth-of-type({i}) div[data-testid="stCheckbox"] label {{
        background: linear-gradient({c['gradient']});
    }}
    div[data-testid="stSidebar"] .level-toggle:nth-of-type({i}) div[data-testid="stCheckbox"] label p {{
        color: {c['fg']} !important;
    }}
    """
st.markdown(f"<style>{level_css}</style>", unsafe_allow_html=True)

for lvl in HSK_LEVELS:
    has_data = lvl in levels_with_data
    label = f"HSK {lvl}" + ("" if has_data else " (ไม่มีคำในชุดนี้)")
    st.sidebar.markdown('<div class="level-toggle">', unsafe_allow_html=True)
    st.session_state.level_filter[lvl] = st.sidebar.checkbox(
        label,
        value=st.session_state.level_filter.get(lvl, True),
        key=f"lvl_chk_{lvl}",
        disabled=not has_data,
    )
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

selected_levels = [lvl for lvl in HSK_LEVELS if st.session_state.level_filter.get(lvl) and lvl in levels_with_data]

if selected_levels:
    filtered_df = df[df['hsk_level'].astype(str).isin(selected_levels)]
else:
    filtered_df = df.iloc[0:0]  # ไม่เลือกเลย = ไม่มีคำให้สุ่ม


# ─── AI translate helper (เก็บไว้บนสุดเพื่อให้เรียกใช้ได้จากทุกที่) ────────────
def get_ai_explanation(question):
    """ลำดับความสำคัญ: ChatGPT (ถ้ามี API Key) -> แปลฟรี MyMemory -> ลิงก์เปิด ChatGPT"""
    try:
        from openai import OpenAI
        api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
    except Exception:
        api_key = None

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "คุณคือครูสอนภาษาจีนที่มีความเชี่ยวชาญ สามารถอธิบายคำศัพท์และวิธีใช้อย่างชัดเจน"},
                    {"role": "user", "content": question},
                ],
            )
            return ("chatgpt", response.choices[0].message.content)
        except Exception as e:
            return ("error", f"❌ เกิดข้อผิดพลาดกับ ChatGPT: {e}")

    return (None, None)


tab1, tab2 = st.tabs(["🎴 Flashcard (สุ่มทาย)", "📖 คำศัพท์ทั้งหมด (List)"])

with tab1:
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำศัพท์ในเลเวลที่เลือก — กรุณาเลือกเลเวล HSK อย่างน้อย 1 ระดับทางด้านซ้าย")
    else:
        # Initialize session state
        if 'current_word' not in st.session_state or st.session_state.current_word_level not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])

        if 'card_flipped' not in st.session_state:
            st.session_state.card_flipped = False
        if 'audio_played' not in st.session_state:
            st.session_state.audio_played = False
        if 'remembered' not in st.session_state:
            st.session_state.remembered = []
        if 'forgotten' not in st.session_state:
            st.session_state.forgotten = []
        if 'ai_response' not in st.session_state:
            st.session_state.ai_response = None
        if 'ai_response_word' not in st.session_state:
            st.session_state.ai_response_word = None

        def next_word(feedback=None):
            word = st.session_state.current_word['simplified']
            if feedback == "remembered":
                if word not in st.session_state.remembered:
                    st.session_state.remembered.append(word)
                if word in st.session_state.forgotten:
                    st.session_state.forgotten.remove(word)
            elif feedback == "forgotten":
                if word not in st.session_state.forgotten:
                    st.session_state.forgotten.append(word)
                if word in st.session_state.remembered:
                    st.session_state.remembered.remove(word)
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
            st.session_state.card_flipped = False
            st.session_state.audio_played = False
            st.session_state.reveal_side = False
            st.session_state.ai_response = None
            st.session_state.ai_response_word = None

        # Auto-play audio on first load of a word
        if not st.session_state.audio_played:
            audio_fp = speak_word(st.session_state.current_word['simplified'])
            st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
            st.session_state.audio_played = True

        col_left, col_right = st.columns([0.6, 0.4], gap="large")

        with col_left:
            flipped_class = "flipped" if st.session_state.card_flipped else ""
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])

            flip_card_html = f"""
            <input type="checkbox" id="flip-toggle" class="flip-toggle-checkbox">
            <label for="flip-toggle" class="flip-card {flipped_class}">
                <div class="flip-card-inner">
                    <div class="flip-card-front" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word['id']}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div>
                            {st.session_state.current_word['simplified']}
                            <div class="click-hint">แตะที่การ์ดเพื่อเปิดคำตอบ</div>
                        </div>
                    </div>
                    <div class="flip-card-back" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word['id']}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div class="pinyin-text">{st.session_state.current_word['pinyin']}</div>
                        <div class="meaning-text">{st.session_state.current_word['meaning']}</div>
                        <div class="click-hint">แตะที่การ์ดเพื่อพลิกกลับ</div>
                    </div>
                </div>
            </label>
            """
            st.markdown(flip_card_html, unsafe_allow_html=True)

            # ── ปุ่มควบคุมหลัก ──
            r1, r2 = st.columns(2)
            with r1:
                if st.button("✅ จำได้", use_container_width=True, key="remember_btn"):
                    next_word("remembered")
                    st.rerun()
            with r2:
                if st.button("❌ จำไม่ได้", use_container_width=True, key="forget_btn"):
                    next_word("forgotten")
                    st.rerun()

            b1, b2 = st.columns(2)
            with b1:
                if st.button("🔊 ฟังเสียงอีก", use_container_width=True, key="replay_audio_btn"):
                    audio_fp = speak_word(st.session_state.current_word['simplified'])
                    st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
            with b2:
                if st.button("⏭️ ข้ามคำนี้", use_container_width=True, key="skip_btn"):
                    next_word(None)
                    st.rerun()

            st.markdown("---")
            total_played = len(st.session_state.remembered) + len(st.session_state.forgotten)
            s1, s2, s3 = st.columns(3)
            with s1:
                st.metric("📊 เล่นไปแล้ว", total_played)
            with s2:
                st.metric("✅ จำได้", len(st.session_state.remembered))
            with s3:
                st.metric("❌ จำไม่ได้", len(st.session_state.forgotten))

        with col_right:
            st.subheader("🤖 ผู้ช่วย AI")

            if 'reveal_side' not in st.session_state:
                st.session_state.reveal_side = False

            head_col, toggle_col = st.columns([0.7, 0.3])
            with head_col:
                st.markdown("**คำปัจจุบัน:**")
            with toggle_col:
                btn_label = "🙈 ซ่อน" if st.session_state.reveal_side else "👁️ แสดงเฉลย"
                if st.button(btn_label, use_container_width=True, key="toggle_reveal_btn"):
                    st.session_state.reveal_side = not st.session_state.reveal_side
                    st.rerun()

            if st.session_state.reveal_side:
                pinyin_display = st.session_state.current_word['pinyin']
                meaning_display = st.session_state.current_word['meaning']
            else:
                pinyin_display = "*" * max(len(str(st.session_state.current_word['pinyin'])), 4)
                meaning_display = "*" * max(len(str(st.session_state.current_word['meaning'])), 4)

            st.markdown(f"""
            - 🇨🇳 {st.session_state.current_word['simplified']}
            - 📖 {pinyin_display}
            - 🇹🇭 {meaning_display}
            """)

            default_q = (
                f"อธิบายความหมายและวิธีใช้คำว่า {st.session_state.current_word['simplified']} "
                f"({st.session_state.current_word['pinyin']}) ในภาษาจีน พร้อมยกตัวอย่างประโยค"
            )
            question = st.text_area("เขียนคำถาม:", value=default_q, height=80, key="ai_question_input")

            a1, a2 = st.columns(2)
            with a1:
                if st.button("🆓 แปล/อธิบายฟรี", use_container_width=True, key="free_ai_btn"):
                    source_text = st.session_state.current_word['simplified']
                    with st.spinner("กำลังแปล..."):
                        translated = free_translate(source_text, "zh-CN", "th")
                    if translated:
                        st.session_state.ai_response = (
                            f"**แปลฟรี (MyMemory):** {translated}\n\n"
                            f"_หมายเหตุ: เป็นการแปลคำต่อคำแบบพื้นฐาน อาจไม่ครอบคลุมทุกบริบทการใช้งาน_"
                        )
                    else:
                        st.session_state.ai_response = "⚠️ แปลฟรีไม่สำเร็จ ลองใหม่อีกครั้ง หรือใช้ลิงก์เปิด ChatGPT ด้านล่าง"
                    st.session_state.ai_response_word = st.session_state.current_word['simplified']

            with a2:
                if st.button("🧠 ขอ AI อธิบายเต็ม", use_container_width=True, key="full_ai_btn"):
                    kind, content = get_ai_explanation(question)
                    if kind == "chatgpt":
                        st.session_state.ai_response = f"**ChatGPT:**\n\n{content}"
                    elif kind == "error":
                        st.session_state.ai_response = content
                    else:
                        st.session_state.ai_response = (
                            "ℹ️ ไม่พบ OpenAI API Key ใน Secrets — ใช้ปุ่ม **🆓 แปล/อธิบายฟรี** "
                            "แทนได้ทันที หรือเพิ่ม `OPENAI_API_KEY` ใน Settings → Secrets "
                            "เพื่อใช้ AI อธิบายเต็มรูปแบบ"
                        )
                    st.session_state.ai_response_word = st.session_state.current_word['simplified']

            encoded_q = urllib.parse.quote(question)
            st.markdown(f"[🔗 เปิดคำถามนี้ใน ChatGPT](https://chat.openai.com/?q={encoded_q})")

            if st.session_state.ai_response and st.session_state.ai_response_word == st.session_state.current_word['simplified']:
                st.markdown("---")
                st.markdown(st.session_state.ai_response)

with tab2:
    if not filtered_df.empty:
        display_cols = ['id', 'simplified', 'pinyin', 'meaning', 'hsk_level']
        if 'pos' in filtered_df.columns:
            display_cols.append('pos')
        st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)
        csv = filtered_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ ดาวน์โหลด CSV", data=csv, file_name='hsk_filtered.csv', mime='text/csv')
    else:
        st.info("ไม่มีคำศัพท์ในเลเวลที่เลือก")