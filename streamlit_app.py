import streamlit as st
import pandas as pd
from gtts import gTTS
import io
import requests
import urllib.parse
import unicodedata
from datetime import datetime
from functools import lru_cache

st.set_page_config(
    page_title="HSK Flashcard AI",
    page_icon="🇨🇳",
    layout="centered",
    initial_sidebar_state="expanded",
)

HSK_LEVELS = ["1", "2", "3", "4", "5", "6", "7-9"]


@st.cache_data
def get_default_vocab():
    return pd.DataFrame([
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
        {"simplified": "悖论", "pinyin": "bèilùn", "meaning": "ความขัดแย้งในตัวเอง", "hsk_level": "7-9"},
        {"simplified": "范畴", "pinyin": "fànchóu", "meaning": "ขอบเขต/ประเภท", "hsk_level": "7-9"},
        {"simplified": "辩证", "pinyin": "biànzhèng", "meaning": "วิภาษวิธี", "hsk_level": "7-9"},
        {"simplified": "意识形态", "pinyin": "yìshí xíngtài", "meaning": "อุดมการณ์", "hsk_level": "7-9"},
        {"simplified": "颠覆", "pinyin": "diānfù", "meaning": "ล้มล้าง/พลิกผัน", "hsk_level": "7-9"},
    ])


@st.cache_data
def load_vocab():
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
        for skip in [0, 1]:
            try:
                if p.suffix.lower() in (".xlsx", ".xls"):
                    df_raw = pd.read_excel(p, skiprows=skip)
                else:
                    try:
                        df_raw = pd.read_csv(p, skiprows=skip)
                    except Exception:
                        df_raw = pd.read_csv(p, skiprows=skip, encoding="utf-8", engine="python")
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
    s = str(level).strip()
    if s in ("7", "8", "9", "7-9", "7-9级"):
        return "7-9"
    return s


def strip_tones(text):
    if text is None:
        return ""
    text = str(text).replace("ü", "u").replace("Ü", "U")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


@lru_cache(maxsize=512)
def free_translate_cached(text, source="zh-CN", target="th"):
    """Cached translation to avoid repeated API calls"""
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source}|{target}"}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        translated = data.get("responseData", {}).get("translatedText")
        if translated:
            return translated
        return None
    except Exception as e:
        return None


def free_translate(text, source="zh-CN", target="th"):
    return free_translate_cached(text, source, target)


def get_hsk_color(level):
    level_str = str(level)
    color_map = {
        "1": {"bg": "#4CAF50", "fg": "#ffffff", "gradient": "135deg, #4CAF50 0%, #45a049 100%", "light": "#e8f5e9"},
        "2": {"bg": "#8BC34A", "fg": "#ffffff", "gradient": "135deg, #8BC34A 0%, #7CB342 100%", "light": "#f1f8e9"},
        "3": {"bg": "#FFC107", "fg": "#333333", "gradient": "135deg, #FFC107 0%, #FFB300 100%", "light": "#fff8e1"},
        "4": {"bg": "#FF9800", "fg": "#ffffff", "gradient": "135deg, #FF9800 0%, #F57C00 100%", "light": "#fff3e0"},
        "5": {"bg": "#FF5722", "fg": "#ffffff", "gradient": "135deg, #FF5722 0%, #E64A19 100%", "light": "#fbe9e7"},
        "6": {"bg": "#9C27B0", "fg": "#ffffff", "gradient": "135deg, #9C27B0 0%, #7B1FA2 100%", "light": "#f3e5f5"},
        "7-9": {"bg": "#FFD700", "fg": "#333333", "gradient": "135deg, #FFD700 0%, #FFA000 100%", "light": "#fffde7"},
    }
    return color_map.get(level_str, {"bg": "#667eea", "fg": "#ffffff", "gradient": "135deg, #667eea 0%, #764ba2 100%", "light": "#ede7f6"})


# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Flip card ── */
.flip-toggle-checkbox { position:absolute; opacity:0; width:0; height:0; pointer-events:none; }
.flip-card {
    background-color:transparent; width:100%; height:360px;
    perspective:1000px; margin:16px 0; display:block; cursor:pointer;
}
.flip-card-inner {
    position:relative; width:100%; height:100%; text-align:center;
    transition:transform 0.6s; transform-style:preserve-3d;
}
.flip-card.flipped .flip-card-inner,
.flip-toggle-checkbox:checked + .flip-card .flip-card-inner { transform:rotateY(180deg); }
.flip-card-front, .flip-card-back {
    position:absolute; width:100%; height:100%; backface-visibility:hidden;
    display:flex; align-items:center; justify-content:center;
    font-size:48px; font-weight:bold; border-radius:20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.flip-card-front { color:white; }
.flip-card-back {
    color:white; transform:rotateY(180deg);
    flex-direction:column; justify-content:space-around; padding:20px;
}
.pinyin-text { font-size:32px; margin-bottom:12px; }
.meaning-text { font-size:26px; }
.click-hint { font-size:13px; opacity:0.75; margin-top:8px; }
..flip-card-front .id-badge {
    position:absolute; top:12px; left:14px;
    padding:5px 12px; border-radius:20px; font-size:12px;
    font-weight:700; font-family:monospace; color:white;
    background:rgba(0,0,0,0.22); z-index:10;
}
.flip-card-front .hsk-badge {
    position:absolute; top:12px; right:14px;
    padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700;
    color:white; background:rgba(0,0,0,0.22); z-index:10; letter-spacing:0.5px;
}
.flip-card-back .id-badge {
    position:absolute; top:12px; right:14px;
    padding:5px 12px; border-radius:20px; font-size:12px;
    font-weight:700; font-family:monospace; color:white;
    background:rgba(0,0,0,0.22); z-index:10;
}
.flip-card-back .hsk-badge {
    position:absolute; top:12px; left:14px;
    padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700;
    color:white; background:rgba(0,0,0,0.22); z-index:10; letter-spacing:0.5px;
}
.flip-card-front .id-badge { left:14px; }
.flip-card-front .hsk-badge { right:14px; }
.flip-card-back .id-badge { right:14px; }
.flip-card-back .hsk-badge { left:14px; }

/* ── Level pills in sidebar ── */
.lvl-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 8px 0 16px 0;
}
.lvl-pill {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    padding: 10px 6px 8px 6px;
    cursor: pointer;
    user-select: none;
    border: 2.5px solid transparent;
    transition: transform 0.12s, box-shadow 0.12s, opacity 0.15s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.13);
    text-decoration: none;
}
.lvl-pill:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.18); }
.lvl-pill-num { font-size: 20px; font-weight: 800; line-height: 1; }
.lvl-pill-label { font-size: 10px; font-weight: 600; opacity: 0.85; margin-top: 3px; letter-spacing: 0.3px; }
.lvl-pill-count { font-size: 10px; opacity: 0.7; margin-top: 1px; }
.lvl-pill-off { opacity: 0.3; filter: grayscale(60%); }
.lvl-pill-nodataoff { opacity: 0.18; filter: grayscale(80%); cursor: not-allowed; }

/* ── Action buttons ── */
.st-key-remember_btn button {
    font-size:22px !important; font-weight:800 !important;
    padding:1.1rem 0.5rem !important; border-radius:14px !important;
    background-color:rgba(76,175,80,0.15) !important;
    border:2px solid #4CAF50 !important; color:#2e7d32 !important;
}
.st-key-forget_btn button {
    font-size:22px !important; font-weight:800 !important;
    padding:1.1rem 0.5rem !important; border-radius:14px !important;
    background-color:rgba(244,67,54,0.12) !important;
    border:2px solid #e57373 !important; color:#c62828 !important;
}

/* ── Audio toggle button ── */
.st-key-audio_toggle_btn button {
    border-radius: 20px !important;
    font-weight: 700 !important;
}

/* ── AI panel toggle ── */
.st-key-ai_panel_toggle button {
    border-radius: 20px !important;
    font-weight: 700 !important;
}

/* ── Sidebar section headers ── */
.sidebar-section-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #888;
    margin: 16px 0 6px 2px;
}
</style>
""", unsafe_allow_html=True)


# ─── Header ───────────────────────────────────────────────────────────────────
st.title("🇨🇳 HSK Flashcard Intelligence")


# ─── Sidebar: data source ──────────────────────────────────────────────────────
st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader(
    "อัปโหลดไฟล์คำศัพท์ (CSV หรือ Excel .xlsx)",
    type=["csv", "xlsx", "xls"],
    help="รองรับคอลัมน์: word, pinyin, trans_th, level",
)


def map_vocab_columns(df_raw):
    cols = set(df_raw.columns)
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
    df = None
    for skip in [0, 1]:
        try:
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                df_raw = pd.read_excel(uploaded, skiprows=skip)
            else:
                uploaded.seek(0)
                try:
                    df_raw = pd.read_csv(uploaded, skiprows=skip)
                except Exception:
                    uploaded.seek(0)
                    df_raw = pd.read_csv(uploaded, skiprows=skip, encoding="utf-8", engine="python")
        except Exception as e:
            continue
        mapped = map_vocab_columns(df_raw)
        if mapped is not None:
            df = mapped
            break
        if {"simplified", "pinyin", "meaning", "hsk_level"}.issubset(df_raw.columns):
            df = df_raw
            break
    if df is None:
        st.error("⚠️ ไม่พบคอลัมน์ที่รองรับ — ต้องมี: word, pinyin, trans_th, level (หรือ simplified, pinyin, meaning, hsk_level)")
        st.stop()
else:
    df = load_vocab()
    if df is None:
        df = get_default_vocab()
        st.sidebar.info("📚 ใช้ข้อมูลตัวอย่าง HSK — อัปโหลดไฟล์ CSV/Excel ของคุณได้")

if "id" not in df.columns:
    df = df.reset_index(drop=True)
    df["id"] = df.index + 1

if df.empty:
    st.error("ไฟล์ CSV ว่างเปล่า")
    st.stop()

df['hsk_level'] = df['hsk_level'].apply(normalize_level)

# ─── Sidebar: search ──────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">🔍 ค้นหาคำศัพท์</div>', unsafe_allow_html=True)
query = st.sidebar.text_input(
    "ค้นหา",
    placeholder="เช่น 12, ni hao, ขอบคุณ, hsk 3",
    label_visibility="collapsed",
    help="พินอินไม่ต้องพิมพ์วรรณยุกต์ก็หาเจอ",
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


# ─── Sidebar: level selector (pill grid) ─────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">📊 เลือกเลเวล HSK</div>', unsafe_allow_html=True)

if "level_filter" not in st.session_state:
    st.session_state.level_filter = {lvl: True for lvl in HSK_LEVELS}

levels_with_data = set(df['hsk_level'].astype(str).unique())
level_counts = df.groupby('hsk_level').size().to_dict()

cols_per_row = 2
rows = [HSK_LEVELS[i:i+cols_per_row] for i in range(0, len(HSK_LEVELS), cols_per_row)]

for row_lvls in rows:
    cols = st.sidebar.columns(len(row_lvls))
    for col, lvl in zip(cols, row_lvls):
        c = get_hsk_color(lvl)
        has_data = lvl in levels_with_data
        is_on = st.session_state.level_filter.get(lvl, True)
        count = level_counts.get(lvl, 0)

        if not has_data:
            extra_class = "lvl-pill-nodataoff"
        elif not is_on:
            extra_class = "lvl-pill-off"
        else:
            extra_class = ""

        border_style = f"border-color: {c['bg']};" if is_on and has_data else "border-color: transparent;"
        bg_style = f"background: linear-gradient({c['gradient']});" if is_on and has_data else f"background: {c['light']};"
        text_color = c['fg'] if is_on and has_data else "#666"
        label_text = "7–9" if lvl == "7-9" else lvl

        pill_label = f"HSK {label_text}"
        with col:
            st.markdown(f"""
            <div class="lvl-pill {extra_class}" style="{bg_style} {border_style} color:{text_color}; pointer-events:none;">
                <div class="lvl-pill-num">{label_text}</div>
                <div class="lvl-pill-label">HSK</div>
                <div class="lvl-pill-count">{count} คำ</div>
            </div>
            """, unsafe_allow_html=True)
            if has_data:
                new_val = st.checkbox(
                    pill_label,
                    value=is_on,
                    key=f"lvl_chk_{lvl}",
                    label_visibility="collapsed",
                )
                if new_val != st.session_state.level_filter.get(lvl):
                    st.session_state.level_filter[lvl] = new_val
                    st.rerun()
            else:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

selected_levels = [lvl for lvl in HSK_LEVELS if st.session_state.level_filter.get(lvl) and lvl in levels_with_data]

if selected_levels:
    filtered_df = df[df['hsk_level'].astype(str).isin(selected_levels)]
else:
    filtered_df = df.iloc[0:0]

# ─── Sidebar: settings ───────────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">⚙️ การตั้งค่า</div>', unsafe_allow_html=True)

if "audio_enabled" not in st.session_state:
    st.session_state.audio_enabled = True

audio_icon = "🔊" if st.session_state.audio_enabled else "🔇"
audio_label = f"{audio_icon} เสียงอัตโนมัติ: {'เปิด' if st.session_state.audio_enabled else 'ปิด'}"
if st.sidebar.button(audio_label, key="audio_toggle_btn", use_container_width=True):
    st.session_state.audio_enabled = not st.session_state.audio_enabled
    st.rerun()

if "ai_panel_open" not in st.session_state:
    st.session_state.ai_panel_open = True

ai_icon = "🤖" if st.session_state.ai_panel_open else "🤖"
ai_label = f"🤖 แผง AI: {'เปิด' if st.session_state.ai_panel_open else 'ปิด'}"
if st.sidebar.button(ai_label, key="ai_panel_toggle", use_container_width=True):
    st.session_state.ai_panel_open = not st.session_state.ai_panel_open
    st.rerun()


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎴 Flashcard (สุ่มทาย)", "📖 คำศัพท์ทั้งหมด (List)", "📋 ประวัติการเล่น"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำศัพท์ในเลเวลที่เลือก — กรุณาเลือกเลเวล HSK อย่างน้อย 1 ระดับทางด้านซ้าย")
    else:
        if 'current_word' not in st.session_state or st.session_state.get('current_word_level') not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])

        for key, default in [
            ('card_flipped', False),
            ('audio_played', False),
            ('remembered', []),
            ('forgotten', []),
            ('play_history', []),
            ('ai_response', None),
            ('ai_response_word', None),
            ('reveal_side', False),
        ]:
            if key not in st.session_state:
                st.session_state[key] = default

        def next_word(feedback=None):
            w = st.session_state.current_word
            word = w['simplified']
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
            
            if feedback in ("remembered", "forgotten"):
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.play_history.append({
                    "เวลา": timestamp,
                    "id": w['id'],
                    "คำจีน": word,
                    "พินอิน": w['pinyin'],
                    "คำแปล": w['meaning'],
                    "HSK": w['hsk_level'],
                    "ผล": "✅ จำได้" if feedback == "remembered" else "❌ จำไม่ได้",
                })
            
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
            st.session_state.card_flipped = False
            st.session_state.audio_played = False
            st.session_state.reveal_side = False
            st.session_state.ai_response = None
            st.session_state.ai_response_word = None

        # Auto-play audio only if enabled and not yet played for this word
        if st.session_state.audio_enabled and not st.session_state.audio_played:
            try:
                audio_fp = speak_word(st.session_state.current_word['simplified'])
                st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
                st.session_state.audio_played = True
            except Exception as e:
                st.caption("⚠️ ไม่สามารถเล่นเสียงอัตโนมัติได้ — กด 🔊 ฟังเสียง เพื่อเล่นด้วยตนเอง")

        # ── Layout ──
        if st.session_state.ai_panel_open:
            col_left, col_right = st.columns([0.6, 0.4], gap="large")
        else:
            col_left = st.container()
            col_right = None

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

            r1, r2 = st.columns(2)
            with r1:
                if st.button("✅ จำได้", use_container_width=True, key="remember_btn"):
                    next_word("remembered")
                    st.rerun()
            with r2:
                if st.button("❌ จำไม่ได้", use_container_width=True, key="forget_btn"):
                    next_word("forgotten")
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("🔊 ฟังเสียง", use_container_width=True, key="replay_audio_btn"):
                    try:
                        audio_fp = speak_word(st.session_state.current_word['simplified'])
                        st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
                    except Exception:
                        st.error("เสียงไม่พร้อม")
            with b2:
                if st.button("⏭️ ข้ามคำนี้", use_container_width=True, key="skip_btn"):
                    next_word(None)
                    st.rerun()
            with b3:
                audio_shortcut = "🔇 ปิดเสียง" if st.session_state.audio_enabled else "🔊 เปิดเสียง"
                if st.button(audio_shortcut, use_container_width=True, key="audio_toggle_card"):
                    st.session_state.audio_enabled = not st.session_state.audio_enabled
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

        # ── AI Panel ──
        if st.session_state.ai_panel_open and col_right is not None:
            with col_right:
                st.subheader("🤖 ผู้ช่วย AI")

                head_col, toggle_col = st.columns([0.7, 0.3])
                with head_col:
                    st.markdown("**คำปัจจุบัน:**")
                with toggle_col:
                    btn_label = "🙈 ซ่อน" if st.session_state.reveal_side else "👁️ เฉลย"
                    if st.button(btn_label, use_container_width=True, key="toggle_reveal_btn"):
                        st.session_state.reveal_side = not st.session_state.reveal_side
                        st.rerun()

                if st.session_state.reveal_side:
                    pinyin_display = st.session_state.current_word['pinyin']
                    meaning_display = st.session_state.current_word['meaning']
                else:
                    pinyin_display = "●" * max(len(str(st.session_state.current_word['pinyin'])), 4)
                    meaning_display = "●" * max(len(str(st.session_state.current_word['meaning'])), 4)

                st.markdown(f"""
                - 🇨🇳 {st.session_state.current_word['simplified']}
                - 📖 {pinyin_display}
                - 🇹🇭 {meaning_display}
                """)

                encoded_word = urllib.parse.quote(st.session_state.current_word['simplified'])
                encoded_q = urllib.parse.quote(
                    f"อธิบายความหมายและวิธีใช้คำว่า {st.session_state.current_word['simplified']} "
                    f"({st.session_state.current_word['pinyin']}) พร้อมยกตัวอย่างประโยค"
                )

                if st.button("🆓 แปลฟรี (MyMemory)", use_container_width=True, key="free_ai_btn"):
                    source_text = st.session_state.current_word['simplified']
                    with st.spinner("กำลังแปล..."):
                        translated = free_translate(source_text, "zh-CN", "th")
                    if translated:
                        st.session_state.ai_response = (
                            f"**แปลฟรี (MyMemory):** {translated}\n\n"
                            f"_หมายเหตุ: เป็นการแปลคำต่อคำแบบพื้นฐาน_"
                        )
                    else:
                        st.session_state.ai_response = "⚠️ แปลฟรีไม่สำเร็จ ลองใหม่อีกครั้ง"
                    st.session_state.ai_response_word = st.session_state.current_word['simplified']

                st.markdown(f"""
                🔗 เปิดใน: [ChatGPT](https://chat.openai.com/?q={encoded_q}) · [Google แปลภาษา](https://translate.google.com/?sl=zh-CN&tl=th&text={encoded_word}&op=translate)
                """)

                if (st.session_state.ai_response and
                        st.session_state.ai_response_word == st.session_state.current_word['simplified']):
                    st.markdown("---")
                    st.markdown(st.session_state.ai_response)

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🔍 ค้นหาคำศัพท์")

    if "list_search_val" not in st.session_state:
        st.session_state.list_search_val = ""
    
    if "tab2_page" not in st.session_state:
        st.session_state.tab2_page = 1

    def _on_search_change():
        st.session_state.list_search_val = st.session_state._list_search_box
        st.session_state.tab2_page = 1  # Reset page on search

    st.text_input(
        "พิมพ์เพื่อกรองทันที",
        placeholder="คำจีน / พินอิน / คำแปล / id / เลเวล...",
        label_visibility="collapsed",
        key="_list_search_box",
        value=st.session_state.list_search_val,
        on_change=_on_search_change,
    )
    list_search = st.session_state.list_search_val

    if not filtered_df.empty:
        display_df = filtered_df.copy()

        if list_search:
            q2 = list_search.strip()
            q2_toneless = strip_tones(q2)
            pinyin_toneless2 = display_df['pinyin'].apply(strip_tones)
            id_str2 = display_df['id'].astype(str)
            mask2 = (
                display_df['simplified'].astype(str).str.contains(q2, case=False, na=False, regex=False)
                | display_df['pinyin'].astype(str).str.contains(q2, case=False, na=False, regex=False)
                | pinyin_toneless2.str.contains(q2_toneless, na=False, regex=False)
                | display_df['meaning'].astype(str).str.contains(q2, case=False, na=False, regex=False)
                | display_df['hsk_level'].astype(str).str.contains(q2, case=False, na=False, regex=False)
                | id_str2.str.contains(q2, na=False, regex=False)
            )
            display_df = display_df[mask2]

        st.caption(f"พบ **{len(display_df)}** คำ จากทั้งหมด {len(filtered_df)} คำ")

        # ═══ PAGINATION ═══
        PAGE_SIZE = 100
        total_pages = (len(display_df) + PAGE_SIZE - 1) // PAGE_SIZE
        
        if st.session_state.tab2_page > total_pages and total_pages > 0:
            st.session_state.tab2_page = 1
        
        current_page = st.session_state.tab2_page if total_pages > 0 else 1
        start_idx = (current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        paginated_df = display_df.iloc[start_idx:end_idx]
        
        # Page navigation
        col_page1, col_page2, col_page3 = st.columns([0.2, 0.6, 0.2])
        with col_page1:
            if current_page > 1:
                if st.button("⬅️", use_container_width=True, key="prev_page"):
                    st.session_state.tab2_page -= 1
                    st.rerun()
            else:
                st.markdown("")
        with col_page2:
            if total_pages > 0:
                st.markdown(
                    f"<div style='text-align:center; padding:8px;'>"
                    f"<b>หน้า {current_page} / {total_pages}</b><br>"
                    f"<small>({start_idx + 1}–{min(end_idx, len(display_df))} จาก {len(display_df)} คำ)</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        with col_page3:
            if current_page < total_pages:
                if st.button("➡️", use_container_width=True, key="next_page"):
                    st.session_state.tab2_page += 1
                    st.rerun()
            else:
                st.markdown("")
        
        st.markdown("---")

        display_cols = ['id', 'simplified', 'pinyin', 'meaning', 'hsk_level']
        if 'pos' in paginated_df.columns:
            display_cols.append('pos')

        display_df_sel = paginated_df[display_cols].copy()
        display_df_sel.insert(0, "🔍 แปล", False)

        col_cfg = {
            "🔍 แปล":    st.column_config.CheckboxColumn("🔍 แปล", width=60),
            "id":        st.column_config.NumberColumn("#",        width=50),
            "simplified":st.column_config.TextColumn("คำจีน",     width=90),
            "pinyin":    st.column_config.TextColumn("พินอิน",    width=140),
            "meaning":   st.column_config.TextColumn("คำแปล (ไทย)", width="medium"),
            "hsk_level": st.column_config.TextColumn("HSK",       width=60),
        }
        if 'pos' in paginated_df.columns:
            col_cfg["pos"] = st.column_config.TextColumn("ชนิดคำ", width=100)

        edited = st.data_editor(
            display_df_sel,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            height=min(50 + len(display_df_sel) * 35, 600),
            key=f"tab2_data_editor_page_{current_page}",
        )

        selected_rows = edited[edited["🔍 แปล"] == True]

        csv = paginated_df[display_cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            f"⬇️ ดาวน์โหลด CSV (หน้า {current_page})",
            data=csv,
            file_name=f'hsk_filtered_p{current_page}.csv',
            mime='text/csv',
        )

        st.markdown("---")
        has_selected = len(selected_rows) > 0
        with st.expander("🤖 ตัวช่วยแปลคำศัพท์", expanded=has_selected):
            if "tab2_translate_result" not in st.session_state:
                st.session_state.tab2_translate_result = None
            if "tab2_translate_word" not in st.session_state:
                st.session_state.tab2_translate_word = ""

            if has_selected:
                st.markdown("**คำที่เลือกจากตาราง:**")
                for _, row in selected_rows.iterrows():
                    word = row['simplified']
                    pinyin = row['pinyin']
                    meaning = row['meaning']
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1:
                        st.markdown(f"**{word}** ({pinyin}) — {meaning}")
                    with c2:
                        if st.button(f"แปล {word}", key=f"sel_translate_{word}_{row['id']}"):
                            with st.spinner("กำลังแปล..."):
                                result = free_translate(word, "zh-CN", "th")
                            st.session_state.tab2_translate_result = result or "⚠️ แปลไม่สำเร็จ"
                            st.session_state.tab2_translate_word = word
                st.markdown("---")

            tr_col1, tr_col2 = st.columns([0.7, 0.3])
            with tr_col1:
                translate_input = st.text_input(
                    "หรือพิมพ์คำจีนเองที่นี่",
                    placeholder="เช่น 你好",
                    key="tab2_translate_input",
                )
            with tr_col2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                do_translate = st.button("🔍 แปล", use_container_width=True, key="tab2_translate_btn")

            if do_translate and translate_input.strip():
                with st.spinner("กำลังแปล..."):
                    result = free_translate(translate_input.strip(), "zh-CN", "th")
                st.session_state.tab2_translate_result = result or "⚠️ แปลไม่สำเร็จ"
                st.session_state.tab2_translate_word = translate_input.strip()

            if st.session_state.tab2_translate_result:
                word_disp = st.session_state.tab2_translate_word
                res_disp  = st.session_state.tab2_translate_result
                st.success(f"**{word_disp}** → {res_disp}")
                encoded_w = urllib.parse.quote(word_disp)
                encoded_q2 = urllib.parse.quote(f"อธิบายความหมายและวิธีใช้ {word_disp} พร้อมตัวอย่างประโยค")
                st.markdown(
                    f"🔗 เปิดใน: "
                    f"[Google แปลภาษา](https://translate.google.com/?sl=zh-CN&tl=th&text={encoded_w}&op=translate) · "
                    f"[ChatGPT](https://chat.openai.com/?q={encoded_q2})"
                )
    else:
        st.info("ไม่มีคำศัพท์ในเลเวลที่เลือก")

# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📋 ประวัติการเล่น Flashcard")

    history = st.session_state.get("play_history", [])

    if not history:
        st.info("ยังไม่มีประวัติ — กลับไปเล่น Flashcard แล้วกดจำได้/จำไม่ได้ก่อนนะครับ")
    else:
        hist_df = pd.DataFrame(history[::-1])

        total = len(hist_df)
        n_ok  = (hist_df["ผล"] == "✅ จำได้").sum()
        n_no  = (hist_df["ผล"] == "❌ จำไม่ได้").sum()
        pct   = int(n_ok / total * 100) if total else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 ทั้งหมด", total)
        m2.metric("✅ จำได้", n_ok)
        m3.metric("❌ จำไม่ได้", n_no)
        m4.metric("🎯 แม่นยำ", f"{pct}%")

        st.markdown("---")

        fc1, fc2 = st.columns(2)
        with fc1:
            filter_result = st.selectbox(
                "กรองตามผล",
                ["ทั้งหมด", "✅ จำได้", "❌ จำไม่ได้"],
                key="hist_filter_result",
            )
        with fc2:
            filter_hsk = st.multiselect(
                "กรองตาม HSK",
                options=sorted(hist_df["HSK"].unique()),
                default=[],
                placeholder="ทุกเลเวล",
                key="hist_filter_hsk",
            )

        disp = hist_df.copy()
        if filter_result != "ทั้งหมด":
            disp = disp[disp["ผล"] == filter_result]
        if filter_hsk:
            disp = disp[disp["HSK"].isin(filter_hsk)]

        st.caption(f"แสดง {len(disp)} รายการ")

        st.dataframe(
            disp,
            use_container_width=True,
            hide_index=True,
            column_config={
                "เวลา":   st.column_config.TextColumn("🕐 เวลา",   width=80),
                "id":     st.column_config.NumberColumn("#",        width=55),
                "คำจีน":  st.column_config.TextColumn("คำจีน",     width=80),
                "พินอิน": st.column_config.TextColumn("พินอิน",    width=130),
                "คำแปล":  st.column_config.TextColumn("คำแปล",     width="medium"),
                "HSK":    st.column_config.TextColumn("HSK",        width=55),
                "ผล":     st.column_config.TextColumn("ผล",         width=100),
            },
            height=min(60 + len(disp) * 35, 500),
        )

        st.markdown("---")
        cc1, cc2 = st.columns([0.3, 0.7])
        with cc1:
            if st.button("🗑️ ล้างประวัติทั้งหมด", key="clear_history_btn"):
                st.session_state.play_history = []
                st.rerun()
        with cc2:
            csv_h = pd.DataFrame(history).to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ ดาวน์โหลดประวัติ CSV",
                data=csv_h,
                file_name="hsk_history.csv",
                mime="text/csv",
                key="dl_history_btn",
            )