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
</style>
""", unsafe_allow_html=True)

st.title("🇨🇳 HSK Flashcard Intelligence")

# ─── Sidebar: data source ────────────────────────────────────────────────────
st.sidebar.header("แหล่งข้อมูล")
uploaded = st.sidebar.file_uploader("อัปโหลดไฟล์ CSV/Excel", type=["csv", "xlsx", "xls"])

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
    if "default_vocab_warned" in st.session_state:
        del st.session_state.default_vocab_warned
    df = None
    for skip in [0, 1]:
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
        if {"simplified", "pinyin", "meaning", "hsk_level"}.issubset(df_raw.columns):
            df = df_raw
            break
    if df is None:
        st.error("⚠️ ไม่พบคอลัมน์ที่รองรับ")
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
        "simplified": "simplified" if "simplified" in df.columns else "word" if "word" in df.columns else None,
        "pinyin": "pinyin" if "pinyin" in df.columns else None,
        "meaning": "meaning" if "meaning" in df.columns else "trans_th" if "trans_th" in df.columns else None,
        "hsk_level": "hsk_level" if "hsk_level" in df.columns else "level" if "level" in df.columns else None,
        "pos": "pos_th" if "pos_th" in df.columns else "pos_en" if "pos_en" in df.columns else "pos" if "pos" in df.columns else None,
    }

if "col_display_toggle" not in st.session_state:
    st.session_state.col_display_toggle = {
        "id": True,
        "pinyin": True,
        "meaning": True,
        "hsk_level": True,
        "pos": bool(st.session_state.col_mapping.get("pos")),
    }

if "col_mapping_show" not in st.session_state:
    st.session_state.col_mapping_show = False

# ─── Sidebar: column mapping ────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">⚙️ การตั้งค่าคอลัมน์</div>', unsafe_allow_html=True)

if st.sidebar.button("🔧 ตั้งค่าคอลัมน์ CSV", key="col_config_btn", use_container_width=True):
    st.session_state.col_mapping_show = not st.session_state.col_mapping_show

if st.session_state.col_mapping_show:
    st.sidebar.markdown("**เลือกคอลัมน์จาก CSV:**")
    avail_cols = ["(ไม่ใช้)"] + sorted(df.columns.tolist())
    
    m = st.session_state.col_mapping
    
    new_id = st.sidebar.selectbox("ID (เลขที่)", avail_cols, index=avail_cols.index(m.get("id")) if m.get("id") in avail_cols else 0, key="sel_id")
    st.session_state.col_mapping["id"] = new_id if new_id != "(ไม่ใช้)" else None

    new_pin = st.sidebar.selectbox("พินอิน", avail_cols, index=avail_cols.index(m.get("pinyin")) if m.get("pinyin") in avail_cols else 0, key="sel_pin")
    st.session_state.col_mapping["pinyin"] = new_pin if new_pin != "(ไม่ใช้)" else None

    new_mean = st.sidebar.selectbox("คำแปล", avail_cols, index=avail_cols.index(m.get("meaning")) if m.get("meaning") in avail_cols else 0, key="sel_mean")
    st.session_state.col_mapping["meaning"] = new_mean if new_mean != "(ไม่ใช้)" else None

    new_hsk = st.sidebar.selectbox("HSK Level", avail_cols, index=avail_cols.index(m.get("hsk_level")) if m.get("hsk_level") in avail_cols else 0, key="sel_hsk")
    st.session_state.col_mapping["hsk_level"] = new_hsk if new_hsk != "(ไม่ใช้)" else None

    new_pos = st.sidebar.selectbox("ชนิดคำ", avail_cols, index=avail_cols.index(m.get("pos")) if m.get("pos") in avail_cols else 0, key="sel_pos")
    st.session_state.col_mapping["pos"] = new_pos if new_pos != "(ไม่ใช้)" else None

    st.sidebar.markdown("**คอลัมน์ที่แสดง:**")
    st.session_state.col_display_toggle["id"] = st.sidebar.checkbox("ID", st.session_state.col_display_toggle.get("id", True), key="tog_id")
    st.session_state.col_display_toggle["pinyin"] = st.sidebar.checkbox("พินอิน", st.session_state.col_display_toggle.get("pinyin", True), key="tog_pin")
    st.session_state.col_display_toggle["meaning"] = st.sidebar.checkbox("คำแปล", st.session_state.col_display_toggle.get("meaning", True), key="tog_mean")
    st.session_state.col_display_toggle["hsk_level"] = st.sidebar.checkbox("HSK", st.session_state.col_display_toggle.get("hsk_level", True), key="tog_hsk")
    if st.session_state.col_mapping.get("pos"):
        st.session_state.col_display_toggle["pos"] = st.sidebar.checkbox("ชนิดคำ", st.session_state.col_display_toggle.get("pos", False), key="tog_pos")

# ─── Sidebar: search ──────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="sidebar-section-title">🔍 ค้นหา</div>', unsafe_allow_html=True)
query = st.sidebar.text_input("ค้นหา", placeholder="id / คำจีน / พินอิน / คำแปล", label_visibility="collapsed")

if query:
    q_toneless = strip_tones(query.strip())
    mask = (
        (df['simplified'].astype(str).str.contains(query, case=False, na=False, regex=False))
        | (df['pinyin'].apply(strip_tones).str.contains(q_toneless, na=False, regex=False))
        | (df['meaning'].astype(str).str.contains(query, case=False, na=False, regex=False))
        | (df['id'].astype(str) == query.strip())
    )
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

with tab1:
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำในเลเวลที่เลือก")
    else:
        if 'current_word' not in st.session_state or st.session_state.get('current_word_level') not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])

        for k, v in [('card_flipped', False), ('audio_played', False), ('remembered', []), ('forgotten', []), ('play_history', []), ('ai_response', None), ('ai_response_word', None), ('reveal_side', False)]:
            if k not in st.session_state:
                st.session_state[k] = v

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

        if st.session_state.audio_enabled and not st.session_state.audio_played:
            try:
                audio_fp = speak_word(st.session_state.current_word['simplified'])
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
            flipped = "flipped" if st.session_state.card_flipped else ""
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])

            st.markdown(f"""
            <input type="checkbox" id="flip-toggle" class="flip-toggle-checkbox">
            <label for="flip-toggle" class="flip-card {flipped}">
                <div class="flip-card-inner">
                    <div class="flip-card-front" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word['id']}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div>{st.session_state.current_word['simplified']}<div class="click-hint">แตะเพื่อเปิด</div></div>
                    </div>
                    <div class="flip-card-back" style="background: linear-gradient({colors['gradient']});">
                        <div class="id-badge">#{st.session_state.current_word['id']}</div>
                        <div class="hsk-badge">HSK {st.session_state.current_word['hsk_level']}</div>
                        <div class="pinyin-text">{st.session_state.current_word['pinyin']}</div>
                        <div class="meaning-text">{st.session_state.current_word['meaning']}</div>
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
                    audio_fp = speak_word(st.session_state.current_word['simplified'])
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

                if st.session_state.reveal_side:
                    pin = st.session_state.current_word['pinyin']
                    mean = st.session_state.current_word['meaning']
                else:
                    pin = "●" * max(len(str(st.session_state.current_word['pinyin'])), 4)
                    mean = "●" * max(len(str(st.session_state.current_word['meaning'])), 4)

                st.markdown(f"- 🇨🇳 {st.session_state.current_word['simplified']}\n- 📖 {pin}\n- 🇹🇭 {mean}")

                if st.button("🆓 แปลฟรี", use_container_width=True, key="translate_btn"):
                    with st.spinner("..."):
                        trans = free_translate(st.session_state.current_word['simplified'], "zh-CN", "th")
                    st.session_state.ai_response = f"**แปล:** {trans}" if trans else "⚠️ แปลไม่ได้"
                    st.session_state.ai_response_word = st.session_state.current_word['simplified']

                if st.session_state.ai_response and st.session_state.ai_response_word == st.session_state.current_word['simplified']:
                    st.divider()
                    st.markdown(st.session_state.ai_response)

with tab2:
    if not filtered_df.empty:
        disp_cols = []
        if st.session_state.col_display_toggle.get("id") and st.session_state.col_mapping.get("id"):
            disp_cols.append(st.session_state.col_mapping["id"])
        if st.session_state.col_display_toggle.get("pinyin") and st.session_state.col_mapping.get("pinyin"):
            disp_cols.append(st.session_state.col_mapping["pinyin"])
        if st.session_state.col_display_toggle.get("meaning") and st.session_state.col_mapping.get("meaning"):
            disp_cols.append(st.session_state.col_mapping["meaning"])
        if st.session_state.col_display_toggle.get("hsk_level") and st.session_state.col_mapping.get("hsk_level"):
            disp_cols.append(st.session_state.col_mapping["hsk_level"])
        if st.session_state.col_display_toggle.get("pos") and st.session_state.col_mapping.get("pos"):
            disp_cols.append(st.session_state.col_mapping["pos"])

        show_cols = disp_cols if disp_cols else list(filtered_df.columns)
        st.dataframe(filtered_df[show_cols], use_container_width=True, hide_index=True)
        csv = filtered_df[show_cols].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ ดาวน์โหลด CSV", csv, 'hsk_list.csv', 'text/csv')
    else:
        st.info("ไม่มีคำในเลเวลที่เลือก")

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