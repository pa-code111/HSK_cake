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
        {"id": 1, "hsk_level": "1", "word": "你", "pinyin": "nǐ", "trans_th": "คุณ", "trans_en": "you", "pos_zh": "代", "pos_en": "pron.", "pos_th": "สรรพนาม"},
        {"id": 2, "hsk_level": "1", "word": "好", "pinyin": "hǎo", "trans_th": "ดี", "trans_en": "good", "pos_zh": "形", "pos_en": "adj.", "pos_th": "คุณศัพท์"},
        {"id": 3, "hsk_level": "1", "word": "谢谢", "pinyin": "xièxie", "trans_th": "ขอบคุณ", "trans_en": "thank you", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 4, "hsk_level": "1", "word": "是", "pinyin": "shì", "trans_th": "เป็น", "trans_en": "to be", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 5, "hsk_level": "1", "word": "不", "pinyin": "bù", "trans_th": "ไม่", "trans_en": "not", "pos_zh": "副", "pos_en": "adv.", "pos_th": "กริยาวิเศษณ์"},
        {"id": 6, "hsk_level": "1", "word": "我", "pinyin": "wǒ", "trans_th": "ฉัน", "trans_en": "I", "pos_zh": "代", "pos_en": "pron.", "pos_th": "สรรพนาม"},
        {"id": 7, "hsk_level": "1", "word": "吃", "pinyin": "chī", "trans_th": "กิน", "trans_en": "to eat", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 8, "hsk_level": "1", "word": "喝", "pinyin": "hē", "trans_th": "ดื่ม", "trans_en": "to drink", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 9, "hsk_level": "1", "word": "水", "pinyin": "shuǐ", "trans_th": "น้ำ", "trans_en": "water", "pos_zh": "名", "pos_en": "n.", "pos_th": "คำนาม"},
        {"id": 10, "hsk_level": "1", "word": "家", "pinyin": "jiā", "trans_th": "บ้าน", "trans_en": "home", "pos_zh": "名", "pos_en": "n.", "pos_th": "คำนาม"},
        {"id": 11, "hsk_level": "1", "word": "有", "pinyin": "yǒu", "trans_th": "มี", "trans_en": "to have", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 12, "hsk_level": "1", "word": "在", "pinyin": "zài", "trans_th": "อยู่", "trans_en": "at/in", "pos_zh": "动", "pos_en": "v.", "pos_th": "กริยา"},
        {"id": 13, "hsk_level": "1", "word": "他", "pinyin": "tā", "trans_th": "เขา", "trans_en": "he", "pos_zh": "代", "pos_en": "pron.", "pos_th": "สรรพนาม"},
        {"id": 14, "hsk_level": "1", "word": "她", "pinyin": "tā", "trans_th": "เธอ", "trans_en": "she", "pos_zh": "代", "pos_en": "pron.", "pos_th": "สรรพนาม"},
        {"id": 15, "hsk_level": "1", "word": "一", "pinyin": "yī", "trans_th": "หนึ่ง", "trans_en": "one", "pos_zh": "数", "pos_en": "num.", "pos_th": "ตัวเลข"},
        {"id": 16, "hsk_level": "1", "word": "二", "pinyin": "èr", "trans_th": "สอง", "trans_en": "two", "pos_zh": "数", "pos_en": "num.", "pos_th": "ตัวเลข"},
        {"id": 17, "hsk_level": "1", "word": "三", "pinyin": "sān", "trans_th": "สาม", "trans_en": "three", "pos_zh": "数", "pos_en": "num.", "pos_th": "ตัวเลข"},
        {"id": 18, "hsk_level": "1", "word": "大", "pinyin": "dà", "trans_th": "ใหญ่", "trans_en": "big", "pos_zh": "形", "pos_en": "adj.", "pos_th": "คุณศัพท์"},
        {"id": 19, "hsk_level": "1", "word": "小", "pinyin": "xiǎo", "trans_th": "เล็ก", "trans_en": "small", "pos_zh": "形", "pos_en": "adj.", "pos_th": "คุณศัพท์"},
        {"id": 20, "hsk_level": "1", "word": "多", "pinyin": "duō", "trans_th": "มาก", "trans_en": "many", "pos_zh": "形、副", "pos_en": "adj./adv.", "pos_th": "คุณศัพท์"},
    ])


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
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{source}|{target}"}
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        translated = data.get("responseData", {}).get("translatedText")
        return translated if translated else None
    except Exception:
        return None


def free_translate(text, source="zh-CN", target="th"):
    return free_translate_cached(text, source, target)


def get_google_translate_url(text, sl="zh-CN", tl="th"):
    return f"https://translate.google.com/?sl={sl}&tl={tl}&text={urllib.parse.quote(str(text))}&op=translate"


def get_chatgpt_translate_url(text):
    prompt = f"แปลคำจีนต่อไปนี้เป็นภาษาไทย พร้อมพินอิน ความหมาย และตัวอย่างประโยค: {text}"
    return f"https://chat.openai.com/?q={urllib.parse.quote(prompt)}"


def get_hsk_color(level):
    level_str = str(level)
    color_map = {
        "1": {"bg": "#4CAF50", "fg": "#ffffff", "gradient": "135deg, #4CAF50 0%, #45a049 100%"},
        "2": {"bg": "#8BC34A", "fg": "#ffffff", "gradient": "135deg, #8BC34A 0%, #7CB342 100%"},
        "3": {"bg": "#FFC107", "fg": "#333333", "gradient": "135deg, #FFC107 0%, #FFB300 100%"},
        "4": {"bg": "#FF9800", "fg": "#ffffff", "gradient": "135deg, #FF9800 0%, #F57C00 100%"},
        "5": {"bg": "#FF5722", "fg": "#ffffff", "gradient": "135deg, #FF5722 0%, #E64A19 100%"},
        "6": {"bg": "#9C27B0", "fg": "#ffffff", "gradient": "135deg, #9C27B0 0%, #7B1FA2 100%"},
        "7-9": {"bg": "#FFD700", "fg": "#333333", "gradient": "135deg, #FFD700 0%, #FFA000 100%"},
    }
    return color_map.get(level_str, {"bg": "#667eea", "fg": "#ffffff", "gradient": "135deg, #667eea 0%, #764ba2 100%"})


st.markdown("""
<style>
.flip-toggle-checkbox { position:absolute; opacity:0; width:0; height:0; pointer-events:none; }
.flip-card {
    background-color:transparent;
    width:100%;
    height:420px;
    perspective:1200px;
    margin:16px 0;
    display:block;
    cursor:pointer;
}
.flip-card-inner {
    position:relative;
    width:100%;
    height:100%;
    text-align:center;
    transition:transform 0.65s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    transform-style:preserve-3d;
}
.flip-card.flipped .flip-card-inner,
.flip-toggle-checkbox:checked + .flip-card .flip-card-inner {
    transform:rotateY(180deg);
}
.flip-card-front,
.flip-card-back {
    position:absolute;
    width:100%;
    height:100%;
    backface-visibility:hidden;
    -webkit-backface-visibility:hidden;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:48px;
    font-weight:bold;
    border-radius:24px;
    box-shadow:0 10px 40px rgba(0,0,0,0.25);
    padding:20px;
    box-sizing:border-box;
}
.flip-card-front {
    color:white;
    z-index:2;
}
.flip-card-back {
    color:white;
    transform:rotateY(180deg);
    flex-direction:column;
    justify-content:space-around;
    z-index:1;
}
.pinyin-text { font-size:36px; margin-bottom:12px; font-weight:700; }
.meaning-text { font-size:28px; font-weight:600; }
.click-hint { font-size:13px; opacity:0.75; margin-top:12px; font-weight:500; }
.hsk-badge { position:absolute; top:14px; padding:6px 14px; border-radius:22px; font-size:11px; font-weight:800; color:white; background:rgba(0,0,0,0.25); z-index:10; letter-spacing:0.5px; }
.id-badge { position:absolute; top:14px; padding:6px 14px; border-radius:22px; font-size:11px; font-weight:800; font-family:monospace; color:white; background:rgba(0,0,0,0.25); z-index:10; }
.flip-card-front .id-badge { left:14px; }
.flip-card-front .hsk-badge { right:14px; }
.flip-card-back .id-badge { right:14px; }
.flip-card-back .hsk-badge { left:14px; }
.st-key-remember_btn button { font-size:22px !important; font-weight:800 !important; padding:1.2rem 0.5rem !important; border-radius:14px !important; background-color:rgba(76,175,80,0.15) !important; border:2px solid #4CAF50 !important; color:#2e7d32 !important; line-height:1.2 !important; }
.st-key-forget_btn button { font-size:22px !important; font-weight:800 !important; padding:1.2rem 0.5rem !important; border-radius:14px !important; background-color:rgba(244,67,54,0.12) !important; border:2px solid #e57373 !important; color:#c62828 !important; line-height:1.2 !important; }
.sidebar-section-title { font-size: 12px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #888; margin: 16px 0 6px 2px; }
.translate-result-box {
    background: rgba(0,0,0,0.05);
    border-left: 3px solid #667eea;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 8px 0;
    font-size: 15px;
}
.vocab-search-highlight {
    background: #fff3cd;
    border-radius: 3px;
    padding: 1px 3px;
}
</style>
""", unsafe_allow_html=True)

st.title("🇨🇳 HSK Flashcard Intelligence")

# ─── Sidebar: data source ────────────────────────────────────────────────────
st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV/Excel", type=["csv", "xlsx", "xls"])

def map_vocab_columns(df_raw):
    cols = set(df_raw.columns)
    if {"word", "trans_th"}.issubset(cols) and ("level" in cols or "hsk_level" in cols):
        out = pd.DataFrame()
        out["id"] = df_raw["id"] if "id" in cols else range(1, len(df_raw) + 1)
        out["hsk_level"] = df_raw["level"] if "level" in cols else df_raw["hsk_level"] if "hsk_level" in cols else ""
        out["word"] = df_raw["word"]
        out["pinyin"] = df_raw["pinyin"] if "pinyin" in cols else ""
        out["trans_th"] = df_raw["trans_th"]
        out["trans_en"] = df_raw["trans_en"] if "trans_en" in cols else ""
        if "pos_en" in cols:
            out["pos_en"] = df_raw["pos_en"]
        if "pos_th" in cols:
            out["pos_th"] = df_raw["pos_th"]
        if "pos_zh" in cols:
            out["pos_zh"] = df_raw["pos_zh"]
        return out
    return None

if uploaded is not None:
    if "default_vocab_warned" in st.session_state:
        del st.session_state.default_vocab_warned
    df = None
    for skip in [1, 0, 2]:
        try:
            df_raw = pd.read_excel(uploaded, skiprows=skip) if uploaded.name.lower().endswith((".xlsx", ".xls")) else pd.read_csv(uploaded, skiprows=skip)
        except Exception:
            try:
                uploaded.seek(0)
                df_raw = pd.read_csv(uploaded, skiprows=skip, encoding="utf-8", engine="python")
            except Exception:
                continue
        mapped = map_vocab_columns(df_raw)
        if mapped is not None:
            df = mapped
            break
        if {"word", "pinyin", "trans_th"}.issubset(df_raw.columns) and ("level" in df_raw.columns or "hsk_level" in df_raw.columns):
            if "hsk_level" not in df_raw.columns and "level" in df_raw.columns:
                df_raw = df_raw.rename(columns={"level": "hsk_level"})
            df = df_raw
            break
    if df is None:
        st.error("⚠️ ไม่พบคอลัมน์ที่รองรับ (ต้องมี: word, trans_th, และ level/hsk_level)")
        st.stop()
else:
    df = get_default_vocab()
    if "default_vocab_warned" not in st.session_state:
        st.session_state.default_vocab_warned = True
        st.sidebar.warning(
            f"⚠️ **ใช้ข้อมูลตัวอย่าง {len(df)} คำ**\n\n"
            f"อัปโหลดไฟล์ CSV/Excel ของคุณเพื่อใช้ข้อมูลจำนวนมากขึ้น"
        )

if "id" not in df.columns:
    df = df.reset_index(drop=True)
    df["id"] = df.index + 1

if df.empty:
    st.error("ไฟล์ CSV ว่างเปล่า")
    st.stop()

df['hsk_level'] = df['hsk_level'].apply(normalize_level)

# ─── Initialize column mapping ────────────────────────────────────────────────
if "col_mapping" not in st.session_state:
    st.session_state.col_mapping = {
        "id": "id" if "id" in df.columns else None,
        "hsk_level": "hsk_level" if "hsk_level" in df.columns else "level" if "level" in df.columns else None,
        "word": "word" if "word" in df.columns else "simplified" if "simplified" in df.columns else None,
        "pos_en": "pos_en" if "pos_en" in df.columns else None,
        "pos_th": "pos_th" if "pos_th" in df.columns else None,
        "pos_zh": "pos_zh" if "pos_zh" in df.columns else None,
        "pinyin": "pinyin" if "pinyin" in df.columns else None,
        "trans_th": "trans_th" if "trans_th" in df.columns else "meaning" if "meaning" in df.columns else None,
        "trans_en": "trans_en" if "trans_en" in df.columns else None,
    }

if "col_display_toggle" not in st.session_state:
    st.session_state.col_display_toggle = {
        "id": True,
        "hsk_level": True,
        "word": True,
        "pinyin": True,
        "pos_en": True,
        "pos_th": False,
        "pos_zh": False,
        "trans_th": True,
        "trans_en": False,
    }

if "col_mapping_show" not in st.session_state:
    st.session_state.col_mapping_show = True

# ─── Sidebar: column mapping ────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">⚙️ การตั้งค่าคอลัมน์</div>', unsafe_allow_html=True)

with st.sidebar.expander("🔧 เลือกคอลัมน์จาก CSV", expanded=False):
    avail_cols = ["(ไม่ใช้)"] + sorted(df.columns.tolist())
    m = st.session_state.col_mapping
    
    new_id = st.selectbox("ID", avail_cols, index=avail_cols.index(m.get("id")) if m.get("id") in avail_cols else 0, key="sel_id")
    st.session_state.col_mapping["id"] = new_id if new_id != "(ไม่ใช้)" else None

    new_hsk = st.selectbox("HSK Level", avail_cols, index=avail_cols.index(m.get("hsk_level")) if m.get("hsk_level") in avail_cols else 0, key="sel_hsk")
    st.session_state.col_mapping["hsk_level"] = new_hsk if new_hsk != "(ไม่ใช้)" else None

    new_word = st.selectbox("คำจีน", avail_cols, index=avail_cols.index(m.get("word")) if m.get("word") in avail_cols else 0, key="sel_word")
    st.session_state.col_mapping["word"] = new_word if new_word != "(ไม่ใช้)" else None

    new_pos_en = st.selectbox("ชนิดคำ (EN)", avail_cols, index=avail_cols.index(m.get("pos_en")) if m.get("pos_en") in avail_cols else 0, key="sel_pos_en")
    st.session_state.col_mapping["pos_en"] = new_pos_en if new_pos_en != "(ไม่ใช้)" else None

    new_pos_th = st.selectbox("ชนิดคำ (TH)", avail_cols, index=avail_cols.index(m.get("pos_th")) if m.get("pos_th") in avail_cols else 0, key="sel_pos_th")
    st.session_state.col_mapping["pos_th"] = new_pos_th if new_pos_th != "(ไม่ใช้)" else None

    new_pos_zh = st.selectbox("ชนิดคำ (ZH)", avail_cols, index=avail_cols.index(m.get("pos_zh")) if m.get("pos_zh") in avail_cols else 0, key="sel_pos_zh")
    st.session_state.col_mapping["pos_zh"] = new_pos_zh if new_pos_zh != "(ไม่ใช้)" else None

    new_pin = st.selectbox("พินอิน", avail_cols, index=avail_cols.index(m.get("pinyin")) if m.get("pinyin") in avail_cols else 0, key="sel_pin")
    st.session_state.col_mapping["pinyin"] = new_pin if new_pin != "(ไม่ใช้)" else None

    new_trans_th = st.selectbox("แปลไทย", avail_cols, index=avail_cols.index(m.get("trans_th")) if m.get("trans_th") in avail_cols else 0, key="sel_trans_th")
    st.session_state.col_mapping["trans_th"] = new_trans_th if new_trans_th != "(ไม่ใช้)" else None

    new_trans_en = st.selectbox("แปลอังกฤษ", avail_cols, index=avail_cols.index(m.get("trans_en")) if m.get("trans_en") in avail_cols else 0, key="sel_trans_en")
    st.session_state.col_mapping["trans_en"] = new_trans_en if new_trans_en != "(ไม่ใช้)" else None

st.sidebar.markdown("**เลือกคอลัมน์ที่จะแสดง:**")

st.session_state.col_display_toggle["id"] = st.sidebar.checkbox("ID", st.session_state.col_display_toggle.get("id", True), key="tog_id")
st.session_state.col_display_toggle["hsk_level"] = st.sidebar.checkbox("HSK", st.session_state.col_display_toggle.get("hsk_level", True), key="tog_hsk")
st.session_state.col_display_toggle["word"] = st.sidebar.checkbox("คำจีน", st.session_state.col_display_toggle.get("word", True), key="tog_word")
st.session_state.col_display_toggle["pinyin"] = st.sidebar.checkbox("พินอิน", st.session_state.col_display_toggle.get("pinyin", True), key="tog_pin")
st.session_state.col_display_toggle["pos_en"] = st.sidebar.checkbox("ชนิดคำ (EN)", st.session_state.col_display_toggle.get("pos_en", True), key="tog_pos_en")
st.session_state.col_display_toggle["pos_th"] = st.sidebar.checkbox("ชนิดคำ (TH)", st.session_state.col_display_toggle.get("pos_th", False), key="tog_pos_th")
st.session_state.col_display_toggle["pos_zh"] = st.sidebar.checkbox("ชนิดคำ (ZH)", st.session_state.col_display_toggle.get("pos_zh", False), key="tog_pos_zh")
st.session_state.col_display_toggle["trans_th"] = st.sidebar.checkbox("แปลไทย", st.session_state.col_display_toggle.get("trans_th", True), key="tog_trans_th")
st.session_state.col_display_toggle["trans_en"] = st.sidebar.checkbox("แปลอังกฤษ", st.session_state.col_display_toggle.get("trans_en", False), key="tog_trans_en")

# ─── Get column names ─────────────────────────────────────────────────────────
word_col = st.session_state.col_mapping.get("word", "word")
pinyin_col = st.session_state.col_mapping.get("pinyin", "pinyin")
trans_th_col = st.session_state.col_mapping.get("trans_th", "trans_th")
id_col = st.session_state.col_mapping.get("id", "id")

# ─── Sidebar: search ──────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">🔍 ค้นหา</div>', unsafe_allow_html=True)
query = st.sidebar.text_input("ค้นหาในทุกคอลัมน์", placeholder="id / คำจีน / พินอิน / แปล", label_visibility="collapsed")

if query:
    q_toneless = strip_tones(query.strip())
    mask = pd.Series([False] * len(df))
    
    if st.session_state.col_display_toggle.get("id") and id_col:
        mask = mask | (df[id_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("word") and word_col:
        mask = mask | (df[word_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("pinyin") and pinyin_col:
        mask = mask | (df[pinyin_col].apply(strip_tones).str.contains(q_toneless, na=False, regex=False))
    if st.session_state.col_display_toggle.get("trans_th") and trans_th_col:
        mask = mask | (df[trans_th_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("trans_en") and st.session_state.col_mapping.get("trans_en"):
        trans_en_col = st.session_state.col_mapping["trans_en"]
        if trans_en_col in df.columns:
            mask = mask | (df[trans_en_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("pos_en") and st.session_state.col_mapping.get("pos_en"):
        pos_en_col = st.session_state.col_mapping["pos_en"]
        if pos_en_col in df.columns:
            mask = mask | (df[pos_en_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    
    df = df[mask]
    st.sidebar.caption(f"พบ {len(df)} คำ")

# ─── Sidebar: level selector ────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">📊 เลเวล HSK</div>', unsafe_allow_html=True)

if "level_filter" not in st.session_state:
    st.session_state.level_filter = {lvl: True for lvl in HSK_LEVELS}

levels_data = set(df['hsk_level'].unique())

for i, lvl in enumerate(HSK_LEVELS):
    has_data = lvl in levels_data
    if i % 2 == 0:
        c1, c2 = st.sidebar.columns(2)
    with (c1 if i % 2 == 0 else c2):
        if has_data:
            st.session_state.level_filter[lvl] = st.checkbox(f"HSK {lvl}", st.session_state.level_filter.get(lvl, True), key=f"lv_{lvl}")
        else:
            st.markdown(f"<span style='opacity:0.3;'>HSK {lvl}</span>", unsafe_allow_html=True)

selected_levels = [l for l in HSK_LEVELS if st.session_state.level_filter.get(l) and l in levels_data]
filtered_df = df[df['hsk_level'].isin(selected_levels)] if selected_levels else df.iloc[0:0]

# ─── Sidebar: settings ────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">⚙️ ตั้งค่า</div>', unsafe_allow_html=True)

if "audio_enabled" not in st.session_state:
    st.session_state.audio_enabled = True

audio_label = ("🔊 เสียงเปิด" if st.session_state.audio_enabled else "🔇 เสียงปิด")
if st.sidebar.button(audio_label, use_container_width=True, key="audio_sidebar_btn"):
    st.session_state.audio_enabled = not st.session_state.audio_enabled
    st.rerun()

if "ai_panel_open" not in st.session_state:
    st.session_state.ai_panel_open = True

ai_label = ("🤖 AI เปิด" if st.session_state.ai_panel_open else "🤖 AI ปิด")
if st.sidebar.button(ai_label, use_container_width=True, key="ai_sidebar_btn"):
    st.session_state.ai_panel_open = not st.session_state.ai_panel_open
    st.rerun()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎴 Flashcard", "📖 คำศัพท์", "📋 ประวัติ"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: FLASHCARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำในเลเวลที่เลือก")
    else:
        if 'current_word' not in st.session_state or st.session_state.get('current_word_level') not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])

        for k, v in [('card_flipped', False), ('audio_played', False), ('remembered', []), ('forgotten', []), ('play_history', []), ('ai_response', None), ('ai_response_word', None), ('reveal_side', False), ('last_word_id', None), ('show_translate_options', False), ('card_translate_result', None), ('card_translate_word', None)]:
            if k not in st.session_state:
                st.session_state[k] = v

        def next_word(feedback=None):
            w = st.session_state.current_word
            word = w[word_col] if word_col else w['word']
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
                    "id": w.get(id_col, w.get('id', '')),
                    "คำจีน": word,
                    "พินอิน": w.get(pinyin_col, w.get('pinyin', '')),
                    "คำแปล": w.get(trans_th_col, w.get('trans_th', '')),
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
            st.session_state.last_word_id = st.session_state.current_word.get('id')
            st.session_state.show_translate_options = False
            st.session_state.card_translate_result = None
            st.session_state.card_translate_word = None

        if st.session_state.audio_enabled and not st.session_state.audio_played:
            try:
                current_word_text = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']
                audio_fp = speak_word(current_word_text)
                st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
                st.session_state.audio_played = True
            except Exception:
                pass

        if st.session_state.ai_panel_open:
            col_left, col_right = st.columns([0.6, 0.4], gap="large")
        else:
            col_left = st.container()
            col_right = None

        with col_left:
            current_word_id = st.session_state.current_word.get('id')
            if st.session_state.last_word_id != current_word_id:
                st.session_state.card_flipped = False
                st.session_state.last_word_id = current_word_id
            
            flipped = "flipped" if st.session_state.card_flipped else ""
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])
            current_word_text = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']

            st.markdown(f"""
            <input type="checkbox" id="flip-toggle-{current_word_id}" class="flip-toggle-checkbox">
            <label for="flip-toggle-{current_word_id}" class="flip-card {flipped}">
                <div class="flip-card-inner">
                    <div class="flip-card-front" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word.get('id', '')}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div>{current_word_text}<div class="click-hint">แตะเพื่อเปิด</div></div>
                    </div>
                    <div class="flip-card-back" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word.get('id', '')}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div class="pinyin-text">{st.session_state.current_word.get(pinyin_col, st.session_state.current_word.get('pinyin', ''))}</div>
                        <div class="meaning-text">{st.session_state.current_word.get(trans_th_col, st.session_state.current_word.get('trans_th', ''))}</div>
                    </div>
                </div>
            </label>
            """, unsafe_allow_html=True)

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
                if st.button("🔊 ฟังเสียง", use_container_width=True, key="replay_btn"):
                    current_word_text = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']
                    audio_fp = speak_word(current_word_text)
                    st.audio(audio_fp.getvalue(), format="audio/mp3", autoplay=True)
            with b2:
                if st.button("⏭️ ข้าม", use_container_width=True, key="skip_btn"):
                    next_word(None)
                    st.rerun()
            with b3:
                audio_txt = "🔇 ปิด" if st.session_state.audio_enabled else "🔊 เปิด"
                if st.button(audio_txt, use_container_width=True, key="audio_card_btn"):
                    st.session_state.audio_enabled = not st.session_state.audio_enabled
                    st.rerun()

            st.divider()
            total = len(st.session_state.remembered) + len(st.session_state.forgotten)
            m1, m2, m3 = st.columns(3)
            m1.metric("📊 ทั้งหมด", total)
            m2.metric("✅ จำได้", len(st.session_state.remembered))
            m3.metric("❌ จำไม่ได้", len(st.session_state.forgotten))

        if st.session_state.ai_panel_open and col_right:
            with col_right:
                st.subheader("🤖 ผู้ช่วย")
                hc, tc = st.columns([0.7, 0.3])
                with hc:
                    st.markdown("**คำศัพท์:**")
                with tc:
                    lbl = "🙈 ซ่อน" if st.session_state.reveal_side else "👁️ เฉลย"
                    if st.button(lbl, use_container_width=True, key="reveal_btn"):
                        st.session_state.reveal_side = not st.session_state.reveal_side
                        st.rerun()

                current_word_text = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']
                pinyin_text = st.session_state.current_word.get(pinyin_col, st.session_state.current_word.get('pinyin', ''))
                meaning_text = st.session_state.current_word.get(trans_th_col, st.session_state.current_word.get('trans_th', ''))

                if st.session_state.reveal_side:
                    pin = pinyin_text
                    mean = meaning_text
                else:
                    pin = "●" * max(len(str(pinyin_text)), 4)
                    mean = "●" * max(len(str(meaning_text)), 4)

                st.markdown(f"- 🇨🇳 {current_word_text}\n- 📖 {pin}\n- 🇹🇭 {mean}")

                st.divider()
                # ── แปลคำ: MyMemory (ทำเลย) ──────────────────────────────
                st.markdown("**🔠 แปลคำนี้:**")
                
                if st.button("🤖 MyMemory (แปลทันที)", use_container_width=True, key="mymemory_card_btn"):
                    with st.spinner("กำลังแปล..."):
                        trans = free_translate(current_word_text, "zh-CN", "th")
                    if trans:
                        st.session_state.card_translate_result = f"**{current_word_text}** → {trans}"
                    else:
                        st.session_state.card_translate_result = "⚠️ แปลไม่ได้ ลองใช้ตัวอื่น"
                    st.session_state.card_translate_word = current_word_text
                    st.rerun()

                if st.session_state.card_translate_result and st.session_state.card_translate_word == current_word_text:
                    st.markdown(f'<div class="translate-result-box">{st.session_state.card_translate_result}</div>', unsafe_allow_html=True)

                # Google & GPT เปิด link ใหม่
                g_url = get_google_translate_url(current_word_text)
                gpt_url = get_chatgpt_translate_url(current_word_text)
                
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    st.link_button("🌍 Google", g_url, use_container_width=True)
                with btn_c2:
                    st.link_button("🧠 ChatGPT", gpt_url, use_container_width=True)

                if st.session_state.ai_response and st.session_state.ai_response_word == current_word_text:
                    st.divider()
                    st.markdown(st.session_state.ai_response)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: คำศัพท์ (พร้อม search + translate เลือกคำได้)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if not filtered_df.empty:
        # ── Search bar ในหน้าคำศัพท์ ─────────────────────────────────────────
        st.markdown("### 🔍 ค้นหาคำศัพท์")
        vocab_search_col1, vocab_search_col2 = st.columns([0.75, 0.25])
        with vocab_search_col1:
            vocab_query = st.text_input(
                "ค้นหา",
                placeholder="พิมพ์ id / คำจีน / pinyin (ไม่ต้องมีวรรณยุกต์) / แปล ...",
                label_visibility="collapsed",
                key="vocab_search_input"
            )
        with vocab_search_col2:
            vocab_search_clear = st.button("✕ ล้าง", use_container_width=True, key="vocab_search_clear")
            if vocab_search_clear:
                st.session_state.vocab_search_input = ""
                st.rerun()

        # กรองข้อมูลในหน้าคำศัพท์แยกจาก sidebar
        vocab_display_df = filtered_df.copy()
        
        if vocab_query and vocab_query.strip():
            vq = vocab_query.strip()
            vq_toneless = strip_tones(vq)
            vmask = pd.Series([False] * len(vocab_display_df), index=vocab_display_df.index)
            
            # ค้นหาทุก column ที่เปิดอยู่
            for col_key, actual_col in st.session_state.col_mapping.items():
                if actual_col and actual_col in vocab_display_df.columns:
                    if col_key == "pinyin":
                        # fuzzy pinyin ไม่ต้องมีวรรณยุกต์
                        vmask = vmask | (vocab_display_df[actual_col].apply(strip_tones).str.contains(vq_toneless, na=False, regex=False))
                    else:
                        vmask = vmask | (vocab_display_df[actual_col].astype(str).str.contains(vq, case=False, na=False, regex=False))
            
            vocab_display_df = vocab_display_df[vmask]
            st.caption(f"🔎 พบ **{len(vocab_display_df)}** คำ จาก {len(filtered_df)} คำทั้งหมด")
        else:
            st.caption(f"📚 แสดงทั้งหมด **{len(vocab_display_df)}** คำ")

        st.divider()

        # ── Pagination ───────────────────────────────────────────────────────
        items_per_page = 100
        total_items = len(vocab_display_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        if "vocab_page" not in st.session_state:
            st.session_state.vocab_page = 1

        # reset page เมื่อค้นหาใหม่
        if "last_vocab_query" not in st.session_state:
            st.session_state.last_vocab_query = ""
        if st.session_state.last_vocab_query != vocab_query:
            st.session_state.vocab_page = 1
            st.session_state.last_vocab_query = vocab_query

        if st.session_state.vocab_page > total_pages:
            st.session_state.vocab_page = total_pages
        if st.session_state.vocab_page < 1:
            st.session_state.vocab_page = 1

        if total_pages > 0 and total_items > 0:
            col_pg1, col_pg2, col_pg3, col_pg4, col_pg5 = st.columns([0.2, 0.2, 0.15, 0.2, 0.25])
            with col_pg1:
                if st.button("⬅️ ก่อนหน้า", use_container_width=True, key="prev_page"):
                    st.session_state.vocab_page = max(1, st.session_state.vocab_page - 1)
                    st.rerun()
            with col_pg2:
                if st.button("ถัดไป ➡️", use_container_width=True, key="next_page"):
                    st.session_state.vocab_page = min(total_pages, st.session_state.vocab_page + 1)
                    st.rerun()
            with col_pg3:
                page_input = st.number_input("หน้า", min_value=1, max_value=total_pages, value=st.session_state.vocab_page, key="page_input")
                if page_input != st.session_state.vocab_page:
                    st.session_state.vocab_page = page_input
                    st.rerun()
            with col_pg4:
                st.markdown(f"<div style='display:flex;align-items:center;height:100%;text-align:center;'><strong>{st.session_state.vocab_page} / {total_pages}</strong></div>", unsafe_allow_html=True)
            with col_pg5:
                st.markdown(f"<div style='display:flex;align-items:center;height:100%;text-align:right;'><small>รวม {total_items} คำ</small></div>", unsafe_allow_html=True)

            start_idx = (st.session_state.vocab_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_df = vocab_display_df.iloc[start_idx:end_idx]

            # columns ที่แสดง
            disp_cols = []
            col_order = ["id", "hsk_level", "word", "pinyin", "pos_en", "pos_th", "pos_zh", "trans_th", "trans_en"]
            for col_key in col_order:
                if st.session_state.col_display_toggle.get(col_key) and st.session_state.col_mapping.get(col_key):
                    disp_cols.append(st.session_state.col_mapping[col_key])
            show_cols = disp_cols if disp_cols else list(page_df.columns)
            
            st.dataframe(page_df[show_cols], use_container_width=True, hide_index=True)

            st.divider()

            # ── แปลคำที่เลือก ─────────────────────────────────────────────────
            st.markdown("### 🌐 แปลคำศัพท์")
            
            # เลือกคำจาก dropdown หรือพิมพ์เอง
            tr_input_col1, tr_input_col2 = st.columns([0.55, 0.45])
            
            with tr_input_col1:
                # ดึงคำจีนทั้งหมดในหน้า
                if word_col and word_col in page_df.columns:
                    word_options = ["(พิมพ์เอง)"] + page_df[word_col].dropna().astype(str).tolist()
                else:
                    word_options = ["(พิมพ์เอง)"]
                
                selected_word_option = st.selectbox(
                    "เลือกคำที่ต้องการแปล",
                    word_options,
                    key="vocab_translate_select"
                )
            
            with tr_input_col2:
                if selected_word_option == "(พิมพ์เอง)":
                    custom_word = st.text_input("พิมพ์คำจีน", placeholder="例: 你好", key="vocab_translate_custom", label_visibility="collapsed")
                    word_to_translate = custom_word.strip() if custom_word else ""
                else:
                    word_to_translate = selected_word_option
                    st.markdown(f"<div style='padding:8px 0; font-size:24px;'>{word_to_translate}</div>", unsafe_allow_html=True)

            if word_to_translate:
                tr_b1, tr_b2, tr_b3 = st.columns(3)
                
                with tr_b1:
                    if st.button("🤖 MyMemory", use_container_width=True, key="vocab_mymemory_btn"):
                        with st.spinner("กำลังแปล..."):
                            trans = free_translate(word_to_translate, "zh-CN", "th")
                        if trans:
                            st.session_state["vocab_translate_result"] = f"**{word_to_translate}** → {trans}"
                        else:
                            st.session_state["vocab_translate_result"] = "⚠️ แปลไม่ได้"
                        st.session_state["vocab_translate_target"] = word_to_translate
                        st.rerun()
                
                with tr_b2:
                    g_url = get_google_translate_url(word_to_translate)
                    st.link_button("🌍 Google", g_url, use_container_width=True)
                
                with tr_b3:
                    gpt_url = get_chatgpt_translate_url(word_to_translate)
                    st.link_button("🧠 ChatGPT", gpt_url, use_container_width=True)

                # แสดงผล MyMemory
                if st.session_state.get("vocab_translate_result") and st.session_state.get("vocab_translate_target") == word_to_translate:
                    st.markdown(f'<div class="translate-result-box">{st.session_state["vocab_translate_result"]}</div>', unsafe_allow_html=True)

            st.divider()
            
            # Download
            csv = vocab_display_df[show_cols].to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด CSV (ที่กรองแล้ว)", csv, 'hsk_list.csv', 'text/csv')

        else:
            st.info("ไม่พบคำที่ตรงกับการค้นหา")
    else:
        st.info("ไม่มีคำในเลเวลที่เลือก")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: ประวัติ
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    history = st.session_state.get("play_history", [])
    if not history:
        st.info("ยังไม่มีประวัติ")
    else:
        hist_df = pd.DataFrame(history[::-1])
        total, ok, no = len(hist_df), (hist_df["ผล"] == "✅ จำได้").sum(), (hist_df["ผล"] == "❌ จำไม่ได้").sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 ทั้งหมด", total)
        m2.metric("✅ จำได้", ok)
        m3.metric("❌ จำไม่ได้", no)
        m4.metric("🎯 %", f"{int(ok/total*100) if total else 0}%")

        st.divider()
        st.dataframe(hist_df, use_container_width=True, hide_index=True, height=400)
        
        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            if st.button("🗑️ ล้าง", use_container_width=True, key="clear_btn"):
                st.session_state.play_history = []
                st.rerun()
        with c2:
            csv = pd.DataFrame(history).to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด", csv, 'history.csv', 'text/csv', use_container_width=True)