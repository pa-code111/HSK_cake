ฃ"""
HSK Vocabulary Learning Web Application
========================================
แอปพลิเคชันสำหรับเรียนรู้และฝึกฝนคำศัพท์ HSK
อ่านข้อมูลจากไฟล์ hsk_vocabnew_fixed.csv

โครงสร้าง:
- User Identification (ระบุตัวตน)
- Sidebar (การตั้งค่า)
- Page: Flashcard (การ์ดช่วยจำ)
- Page: Quiz (แบบทดสอบ)
- Page: Vocabulary (คลังคำศัพท์)
- Page: Summary & Leaderboard (สรุปผล)
"""

import streamlit as st
import pandas as pd
import random
import io
import urllib.parse
from gtts import gTTS

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HSK Flashcard AI",
    page_icon="🇨🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS Styling ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Flashcard styles */
.flashcard-front {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 0;
    text-align: center;
    color: white;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    min-height: 280px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.flashcard-back {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    border-radius: 20px;
    padding: 0;
    text-align: center;
    color: white;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    min-height: 280px;
}
.chinese-word {
    font-size: 72px;
    font-weight: bold;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}
.pinyin-text {
    font-size: 28px;
    margin-bottom: 15px;
    opacity: 0.95;
}
.translation-text {
    font-size: 22px;
    margin-bottom: 10px;
}
.example-text {
    font-size: 16px;
    opacity: 0.9;
    font-style: italic;
    margin-top: 10px;
}
.hsk-badge {
    background: rgba(255,255,255,0.25);
    border-radius: 20px;
    padding: 0;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 15px;
    display: inline-block;
}
.side-assistant {
    background: #f8f9fa;
    border-radius: 16px;
    padding: 0;
    border: 1px solid #e9ecef;
}
.blurred {
    filter: blur(6px);
    user-select: none;
    pointer-events: none;
}
.stat-box {
    background: white;
    border-radius: 12px;
    padding: 0;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border-left: 4px solid #667eea;
}
.quiz-option {
    background: white;
    border: 2px solid #e9ecef;
    border-radius: 10px;
    padding: 0;
    margin: 0;
    cursor: pointer;
    transition: all 0.2s;
}
.correct-answer { border-color: #28a745 !important; background: #d4edda !important; }
.wrong-answer   { border-color: #dc3545 !important; background: #f8d7da !important; }
.leaderboard-row { padding: 0; border-bottom: 1px solid #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
CSV_PATH = "hsk_vocabnew_fixed.csv"
DEFAULT_COLUMNS = ["id", "hsk_level", "word", "pinyin", "pos_en", "trans_th", "example_zh", "example_th"]
ALL_COLUMNS = ["id", "hsk_level", "word", "pinyin", "pos_zh", "pos_en", "pos_th",
               "trans_en", "trans_th", "example_zh", "example_th", "example_en"]

# ─── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    """โหลดข้อมูล CSV และ cache ไว้"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    df["hsk_level"] = df["hsk_level"].astype(str)
    return df

@st.cache_data
def get_levels(df):
    """ดึงระดับ HSK ที่ไม่ซ้ำกัน"""
    levels = sorted(df["hsk_level"].str.split("(").str[0].str.strip().unique())
    return levels

# ─── Session State Initialization ────────────────────────────────────────────
def init_session_state():
    """กำหนดค่าเริ่มต้นของ session state ทั้งหมด"""
    defaults = {
        # User
        "username": None,
        "user_history": [],
        # Navigation
        "current_page": "flashcard",
        # Settings
        "selected_levels": [],
        "lang_mode": "ทั้งไทยและอังกฤษ",
        "show_columns": DEFAULT_COLUMNS,
        # Flashcard state
        "fc_index": 0,
        "fc_flipped": False,
        "fc_deck": [],
        "fc_always_show": False,
        "fc_got_it": 0,
        "fc_need_review": 0,
        "fc_history": [],  # list of {id, result}
        # Quiz state
        "quiz_mode": "Reading MCQ",
        "quiz_index": 0,
        "quiz_deck": [],
        "quiz_answered": False,
        "quiz_selected": None,
        "quiz_correct": 0,
        "quiz_wrong": 0,
        "quiz_history": [],  # list of {word, correct}
        "quiz_options": [],
        "quiz_audio_bytes": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# ─── Helper Functions ─────────────────────────────────────────────────────────
def get_filtered_df(df):
    """กรองข้อมูลตาม HSK Level ที่เลือก"""
    if not st.session_state.selected_levels:
        return df
    mask = df["hsk_level"].str.split("(").str[0].str.strip().isin(
        st.session_state.selected_levels
    )
    return df[mask].reset_index(drop=True)

def get_translation(row):
    """ดึงคำแปลตาม lang_mode"""
    mode = st.session_state.lang_mode
    if mode == "ไทยอย่างเดียว":
        return row.get("trans_th", "")
    elif mode == "อังกฤษอย่างเดียว":
        return row.get("trans_en", "")
    else:
        th = row.get("trans_th", "")
        en = row.get("trans_en", "")
        return f"{th}\n{en}" if th and en else (th or en)

def get_example(row):
    """ดึงประโยคตัวอย่างตาม lang_mode"""
    mode = st.session_state.lang_mode
    zh = row.get("example_zh", "")
    th = row.get("example_th", "")
    en = row.get("example_en", "")
    if mode == "ไทยอย่างเดียว":
        return f"{zh}\n{th}" if zh else th
    elif mode == "อังกฤษอย่างเดียว":
        return f"{zh}\n{en}" if zh else en
    else:
        parts = [p for p in [zh, th, en] if p]
        return "\n".join(parts)

def generate_tts(text, lang="zh"):
    """สร้างไฟล์เสียงจาก gTTS และคืนค่าเป็น bytes"""
    try:
        tts = gTTS(text=text, lang=lang)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None

def hsk_color(level):
    """คืนค่าสีตาม HSK Level"""
    colors = {
        "1": "#4CAF50", "2": "#8BC34A", "3": "#FFC107",
        "4": "#FF9800", "5": "#FF5722", "6": "#9C27B0", "7-9": "#FFD700",
    }
    lv = str(level).split("(")[0].strip()
    return colors.get(lv, "#667eea")

# ─── Google Sheets Functions ──────────────────────────────────────────────────
def get_gsheet_client():
    """
    เชื่อมต่อ Google Sheets ผ่าน gspread
    ต้องตั้งค่า secrets.toml ก่อน (ดูคำอธิบายท้ายไฟล์)
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        return None

def load_leaderboard():
    """โหลดข้อมูล Leaderboard จาก Google Sheets"""
    try:
        client = get_gsheet_client()
        if client is None:
            return None
        sheet_url = st.secrets.get("gsheet_url", "")
        if not sheet_url:
            return None
        sh = client.open_by_url(sheet_url)
        ws = sh.sheet1
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(
            columns=["rank", "username", "quiz_score", "flashcard_score", "total", "date"]
        )
    except Exception:
        return None

def save_to_leaderboard(username, quiz_correct, quiz_total, fc_got, fc_total):
    """บันทึกคะแนนลง Google Sheets"""
    try:
        client = get_gsheet_client()
        if client is None:
            return False
        sheet_url = st.secrets.get("gsheet_url", "")
        sh = client.open_by_url(sheet_url)
        ws = sh.sheet1
        from datetime import datetime
        total = quiz_correct + fc_got
        row = [
            username,
            quiz_correct,
            quiz_total,
            fc_got,
            fc_total,
            total,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ]
        ws.append_row(row)
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: USER IDENTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
def page_user_identification():
    """หน้าระบุตัวตนก่อนเข้าใช้งาน"""
    st.markdown("""
    <div style='text-align:center; padding: 0;'>
        <div style='font-size:80px;'>🇨🇳</div>
        <h1 style='font-size:2.5rem; margin: 0;'>HSK Flashcard AI</h1>
        <p style='color:#666; font-size:1.1rem;'>แอปเรียนรู้คำศัพท์ภาษาจีน HSK ระดับ 1-9</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 👤 ระบุตัวตนของคุณ")

        # ประวัติผู้ใช้
        history = st.session_state.user_history
        if history:
            st.markdown("**เลือกชื่อที่เคยใช้:**")
            cols = st.columns(min(len(history), 4))
            for i, name in enumerate(history[-4:]):
                with cols[i % 4]:
                    if st.button(f"👤 {name}", key=f"hist_{i}", use_container_width=True):
                        st.session_state.username = name
                        st.rerun()
            st.markdown("---")

        # กรอกชื่อใหม่
        new_name = st.text_input(
            "หรือกรอกชื่อใหม่:",
            placeholder="เช่น สมชาย, Alice, 小明...",
            max_chars=30,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ เข้าใช้งาน", type="primary", use_container_width=True):
                name = new_name.strip()
                if name:
                    st.session_state.username = name
                    if name not in st.session_state.user_history:
                        st.session_state.user_history.append(name)
                    st.rerun()
                else:
                    st.warning("กรุณากรอกชื่อก่อนเข้าใช้งาน")
        with col_b:
            if st.button("🎭 ไม่ระบุตัวตน", use_container_width=True):
                st.session_state.username = "Anonymous"
                st.rerun()

        st.markdown("""
        <div style='text-align:center; color:#999; font-size:0.85rem; margin-top:20px;'>
            ไม่มีระบบ Login — ชื่อใช้สำหรับ Leaderboard เท่านั้น
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar(df):
    """แถบด้านข้างสำหรับการตั้งค่าและนำทาง"""
    with st.sidebar:
        # User info
        username = st.session_state.username
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#667eea,#764ba2);
                    border-radius:12px; padding: 0; color:white; margin-bottom:16px;'>
            <div style='font-size:1.1rem; font-weight:700;'>👤 {username}</div>
            <div style='font-size:0.8rem; opacity:0.85;'>
                Quiz: {st.session_state.quiz_correct}✅ {st.session_state.quiz_wrong}❌ &nbsp;|&nbsp;
                Card: {st.session_state.fc_got_it}💚 {st.session_state.fc_need_review}🔴
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 เปลี่ยนผู้ใช้", use_container_width=True):
            st.session_state.username = None
            st.rerun()

        st.markdown("---")

        # Navigation
        st.markdown("### 📌 เมนูหลัก")
        pages = {
            "flashcard":   "🃏 Flashcard",
            "quiz":        "📝 Quiz",
            "vocabulary":  "📚 Vocabulary",
            "summary":     "📊 Summary & Leaderboard",
        }
        for key, label in pages.items():
            active = st.session_state.current_page == key
            btn_type = "primary" if active else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state.current_page = key
                st.rerun()

        st.markdown("---")

        # HSK Level Filter
        st.markdown("### 🎯 ระดับ HSK")
        levels = get_levels(df)
        selected = st.multiselect(
            "เลือกระดับ (ว่าง = ทั้งหมด):",
            options=levels,
            default=st.session_state.selected_levels,
            key="level_select",
        )
        if selected != st.session_state.selected_levels:
            st.session_state.selected_levels = selected
            # Reset decks เมื่อเปลี่ยน level
            st.session_state.fc_deck = []
            st.session_state.quiz_deck = []
            st.session_state.fc_index = 0
            st.session_state.quiz_index = 0
            st.rerun()

        filtered = get_filtered_df(df)
        st.caption(f"📖 คำศัพท์ที่เลือก: **{len(filtered):,}** คำ")

        st.markdown("---")

        # Language Mode
        st.markdown("### 🌐 ภาษาแปล/ตัวอย่าง")
        lang_mode = st.radio(
            "แสดงผลเป็น:",
            ["ไทยอย่างเดียว", "อังกฤษอย่างเดียว", "ทั้งไทยและอังกฤษ"],
            index=["ไทยอย่างเดียว", "อังกฤษอย่างเดียว", "ทั้งไทยและอังกฤษ"].index(
                st.session_state.lang_mode
            ),
        )
        st.session_state.lang_mode = lang_mode

        st.markdown("---")

        # Column Settings (for Vocabulary page)
        if st.session_state.current_page == "vocabulary":
            st.markdown("### 📋 คอลัมน์ที่แสดง")
            show_cols = st.multiselect(
                "เลือกคอลัมน์:",
                options=ALL_COLUMNS,
                default=st.session_state.show_columns,
            )
            if show_cols:
                st.session_state.show_columns = show_cols

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FLASHCARD
# ══════════════════════════════════════════════════════════════════════════════
def page_flashcard(df):
    """หน้า Flashcard — การ์ดช่วยจำ"""
    filtered = get_filtered_df(df)
    if filtered.empty:
        st.warning("ไม่มีคำศัพท์ในระดับที่เลือก กรุณาเลือกระดับใหม่ใน Sidebar")
        return

    # สร้าง deck ถ้ายังไม่มี
    if not st.session_state.fc_deck:
        deck = filtered.to_dict("records")
        random.shuffle(deck)
        st.session_state.fc_deck = deck
        st.session_state.fc_index = 0
        st.session_state.fc_flipped = False

    deck = st.session_state.fc_deck
    idx = st.session_state.fc_index % len(deck)
    row = deck[idx]
    flipped = st.session_state.fc_flipped
    always_show = st.session_state.fc_always_show

    # ─── Layout: Card (left) + Side Assistant (right) ─────────────────────
    col_card, col_side = st.columns([3, 2], gap="large")

    # ── CARD ──────────────────────────────────────────────────────────────
    with col_card:
        lv = str(row.get("hsk_level", "")).split("(")[0].strip()
        color = hsk_color(lv)

        if not flipped:
            # หน้าแรก: แสดงคำจีน
            st.markdown(f"""
            <div class="flashcard-front" style="background:linear-gradient(135deg,{color} 0%,#764ba2 100%);">
                <div class="hsk-badge">HSK {lv} &nbsp;·&nbsp; #{row.get('id','')}</div>
                <div class="chinese-word">{row.get('word','')}</div>
                <div style="font-size:16px; opacity:0.7; margin-top:10px;">
                    กดปุ่มด้านล่างเพื่อดูคำแปล 👇
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # หน้าหลัง: แสดงคำแปล
            trans = get_translation(row)
            example = get_example(row)
            st.markdown(f"""
            <div class="flashcard-back">
                <div class="hsk-badge">HSK {lv} &nbsp;·&nbsp; #{row.get('id','')}</div>
                <div class="chinese-word" style="font-size:52px;">{row.get('word','')}</div>
                <div class="pinyin-text">🔊 {row.get('pinyin','')}</div>
                <div class="translation-text">📖 {trans.replace(chr(10),' / ')}</div>
                <div class="example-text">{example.replace(chr(10),'<br>')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── ปุ่มควบคุมการ์ด ──────────────────────────────────────────────
        btn1, btn2, btn3 = st.columns(3)
        with btn1:
            if st.button("⬅️ ก่อนหน้า", use_container_width=True):
                st.session_state.fc_index = (idx - 1) % len(deck)
                st.session_state.fc_flipped = False
                st.rerun()
        with btn2:
            flip_label = "🔄 พลิกการ์ด" if not flipped else "🔄 ซ่อนคำแปล"
            if st.button(flip_label, use_container_width=True, type="primary"):
                st.session_state.fc_flipped = not flipped
                st.rerun()
        with btn3:
            if st.button("➡️ ถัดไป", use_container_width=True):
                st.session_state.fc_index = (idx + 1) % len(deck)
                st.session_state.fc_flipped = False
                st.rerun()

        # ── ปุ่มประเมินตัวเอง (แสดงเมื่อพลิกแล้ว) ───────────────────────
        if flipped:
            st.markdown("**ประเมินตัวเอง:**")
            ev1, ev2, ev3 = st.columns(3)
            with ev1:
                if st.button("💚 จำได้!", use_container_width=True):
                    st.session_state.fc_got_it += 1
                    st.session_state.fc_history.append({"id": row["id"], "result": "got_it"})
                    st.session_state.fc_index = (idx + 1) % len(deck)
                    st.session_state.fc_flipped = False
                    st.rerun()
            with ev2:
                if st.button("🔴 จำไม่ได้", use_container_width=True):
                    st.session_state.fc_need_review += 1
                    st.session_state.fc_history.append({"id": row["id"], "result": "need_review"})
                    st.session_state.fc_index = (idx + 1) % len(deck)
                    st.session_state.fc_flipped = False
                    st.rerun()
            with ev3:
                if st.button("⏭️ ข้าม", use_container_width=True):
                    st.session_state.fc_index = (idx + 1) % len(deck)
                    st.session_state.fc_flipped = False
                    st.rerun()

        # ── ปุ่มตรวจสอบ ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**🔍 ตรวจสอบความถูกต้อง:**")
        word = row.get("word", "")
        pinyin = row.get("pinyin", "")
        vb1, vb2 = st.columns(2)
        with vb1:
            google_url = f"https://www.google.com/search?q={urllib.parse.quote(word)}"
            st.link_button("🔍 ค้นหาใน Google", google_url, use_container_width=True)
        with vb2:
            prompt = f"ช่วยอธิบายและตรวจสอบความหมายของคำศัพท์ภาษาจีนคำนี้: {word} (pinyin: {pinyin}) ให้หน่อยว่าแปลว่าอะไร พร้อมยกตัวอย่างการใช้"
            chatgpt_url = f"https://chatgpt.com/?q={urllib.parse.quote(prompt)}"
            st.link_button("🤖 ถาม ChatGPT", chatgpt_url, use_container_width=True)

        # Progress
        st.markdown(f"""
        <div style='text-align:center; color:#999; font-size:0.85rem; margin-top:8px;'>
            การ์ดที่ {idx+1} / {len(deck)} &nbsp;·&nbsp;
            💚 {st.session_state.fc_got_it} &nbsp;·&nbsp;
            🔴 {st.session_state.fc_need_review}
        </div>
        """, unsafe_allow_html=True)

    # ── SIDE ASSISTANT ─────────────────────────────────────────────────────
    with col_side:
        st.markdown("### 📋 Side Assistant")

        # Toggle always show
        always_show = st.toggle(
            "👁️ เปิดตลอดเวลา (Always Show)",
            value=st.session_state.fc_always_show,
        )
        st.session_state.fc_always_show = always_show

        reveal = flipped or always_show

        with st.container():
            # คำจีนและ example_zh แสดงเสมอ
            st.markdown(f"""
            <div class="side-assistant">
                <div style='font-size:2rem; font-weight:bold; color:#333; margin-bottom:4px;'>
                    {row.get('word','')}
                </div>
                <div style='color:#666; font-size:0.9rem; margin-bottom:12px;'>
                    HSK {lv} &nbsp;·&nbsp; #{row.get('id','')} &nbsp;·&nbsp; {row.get('pos_th','')}
                </div>
            """, unsafe_allow_html=True)

            # Pinyin — ซ่อน/แสดงตาม reveal
            pinyin_display = row.get("pinyin", "")
            if reveal:
                st.markdown(f"🔊 **Pinyin:** `{pinyin_display}`")
            else:
                st.markdown(f"🔊 **Pinyin:** <span class='blurred'>{pinyin_display}</span>",
                            unsafe_allow_html=True)

            # คำแปล
            trans = get_translation(row)
            if reveal:
                st.markdown(f"📖 **คำแปล:** {trans.replace(chr(10), ' / ')}")
            else:
                st.markdown("📖 **คำแปล:** ···")

            # ตัวอย่างภาษาจีน (แสดงเสมอ)
            ex_zh = row.get("example_zh", "")
            if ex_zh:
                st.markdown(f"💬 **ตัวอย่าง (จีน):** {ex_zh}")

            # ตัวอย่างแปล
            ex_th = row.get("example_th", "")
            ex_en = row.get("example_en", "")
            mode = st.session_state.lang_mode
            if reveal:
                if mode in ["ไทยอย่างเดียว", "ทั้งไทยและอังกฤษ"] and ex_th:
                    st.markdown(f"🇹🇭 {ex_th}")
                if mode in ["อังกฤษอย่างเดียว", "ทั้งไทยและอังกฤษ"] and ex_en:
                    st.markdown(f"🇬🇧 {ex_en}")
            else:
                st.markdown("🇹🇭/🇬🇧 ···")

            st.markdown("</div>", unsafe_allow_html=True)

        # เสียงอ่าน
        st.markdown("---")
        if st.button("🔊 ฟังเสียงอ่าน", use_container_width=True):
            audio_bytes = generate_tts(row.get("word", ""), lang="zh")
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
            else:
                st.warning("ไม่สามารถสร้างเสียงได้ในขณะนี้")

        # สุ่มการ์ดใหม่
        if st.button("🔀 สุ่มใหม่ทั้งหมด", use_container_width=True):
            deck2 = filtered.to_dict("records")
            random.shuffle(deck2)
            st.session_state.fc_deck = deck2
            st.session_state.fc_index = 0
            st.session_state.fc_flipped = False
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: QUIZ
# ══════════════════════════════════════════════════════════════════════════════
def page_quiz(df):
    """หน้า Quiz — แบบทดสอบ"""
    filtered = get_filtered_df(df)
    if len(filtered) < 4:
        st.warning("ต้องมีคำศัพท์อย่างน้อย 4 คำ กรุณาเลือกระดับเพิ่มเติม")
        return

    st.markdown("## 📝 Quiz")

    # เลือกโหมด
    mode = st.radio(
        "เลือกโหมด:",
        ["Reading MCQ", "Listening"],
        horizontal=True,
        key="quiz_mode_radio",
    )
    st.session_state.quiz_mode = mode

    # สร้าง deck ถ้ายังไม่มี
    if not st.session_state.quiz_deck:
        deck = filtered.to_dict("records")
        random.shuffle(deck)
        st.session_state.quiz_deck = deck
        st.session_state.quiz_index = 0
        st.session_state.quiz_answered = False
        st.session_state.quiz_selected = None
        st.session_state.quiz_options = []

    deck = st.session_state.quiz_deck
    idx = st.session_state.quiz_index % len(deck)
    row = deck[idx]
    answered = st.session_state.quiz_answered

    # สร้างตัวเลือก MCQ
    if not st.session_state.quiz_options or not answered:
        correct_ans = row.get("trans_th", "") or row.get("trans_en", "")
        # สุ่มตัวเลือกหลอก 3 ข้อ
        other_rows = [r for r in deck if r["id"] != row["id"]]
        distractors = random.sample(other_rows, min(3, len(other_rows)))
        wrong_ans = [r.get("trans_th", "") or r.get("trans_en", "") for r in distractors]
        options = [correct_ans] + wrong_ans
        random.shuffle(options)
        st.session_state.quiz_options = options
        st.session_state.quiz_correct_ans = correct_ans

    options = st.session_state.quiz_options
    correct_ans = st.session_state.get("quiz_correct_ans", "")

    # ── Score bar ──────────────────────────────────────────────────────────
    total_q = st.session_state.quiz_correct + st.session_state.quiz_wrong
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("✅ ถูก", st.session_state.quiz_correct)
    with col_s2:
        st.metric("❌ ผิด", st.session_state.quiz_wrong)
    with col_s3:
        acc = f"{st.session_state.quiz_correct/total_q*100:.0f}%" if total_q > 0 else "—"
        st.metric("🎯 ความแม่นยำ", acc)

    st.markdown(f"**ข้อที่ {idx+1} / {len(deck)}**")
    st.progress((idx) / len(deck))
    st.markdown("---")

    lv = str(row.get("hsk_level", "")).split("(")[0].strip()

    # ── โหมด Listening ────────────────────────────────────────────────────
    if mode == "Listening":
        st.markdown("### 🎧 ฟังเสียงแล้วเลือกความหมายที่ถูกต้อง")

        # สร้างเสียง
        if st.button("▶️ เล่นเสียง", type="primary"):
            audio_bytes = generate_tts(row.get("word", ""), lang="zh")
            if audio_bytes:
                st.session_state.quiz_audio_bytes = audio_bytes
            else:
                st.warning("ไม่สามารถสร้างเสียงได้")

        if st.session_state.quiz_audio_bytes:
            st.audio(st.session_state.quiz_audio_bytes, format="audio/mp3")

        if answered:
            st.markdown(f"**คำศัพท์:** {row.get('word','')} ({row.get('pinyin','')})")

    # ── โหมด Reading MCQ ──────────────────────────────────────────────────
    else:
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,{hsk_color(lv)},#764ba2);
                    border-radius:16px; padding: 0; text-align:center; color:white; margin-bottom:20px;'>
            <div style='font-size:0.9rem; opacity:0.8; margin-bottom:8px;'>HSK {lv}</div>
            <div style='font-size:56px; font-weight:bold;'>{row.get('word','')}</div>
            <div style='font-size:1rem; opacity:0.8; margin-top:8px;'>{row.get('pos_th','')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── ตัวเลือก ──────────────────────────────────────────────────────────
    st.markdown("**เลือกความหมายที่ถูกต้อง:**")
    for i, opt in enumerate(options):
        if answered:
            if opt == correct_ans:
                st.success(f"✅ {opt}")
            elif opt == st.session_state.quiz_selected:
                st.error(f"❌ {opt}")
            else:
                st.markdown(f"&nbsp;&nbsp;&nbsp;{opt}")
        else:
            if st.button(f"{opt}", key=f"opt_{i}_{idx}", use_container_width=True):
                st.session_state.quiz_selected = opt
                st.session_state.quiz_answered = True
                if opt == correct_ans:
                    st.session_state.quiz_correct += 1
                    st.session_state.quiz_history.append({"word": row["word"], "correct": True})
                else:
                    st.session_state.quiz_wrong += 1
                    st.session_state.quiz_history.append({"word": row["word"], "correct": False})
                st.rerun()

    # ── ปุ่มถัดไป ─────────────────────────────────────────────────────────
    if answered:
        if st.session_state.quiz_selected == correct_ans:
            st.balloons()
            st.success("🎉 ถูกต้อง!")
        else:
            st.error(f"❌ ผิด! คำตอบที่ถูกคือ: **{correct_ans}**")

        # แสดงข้อมูลเพิ่มเติม
        with st.expander("📖 ดูรายละเอียดคำศัพท์"):
            st.markdown(f"**คำ:** {row.get('word','')} ({row.get('pinyin','')})")
            st.markdown(f"**คำแปลไทย:** {row.get('trans_th','')}")
            st.markdown(f"**คำแปลอังกฤษ:** {row.get('trans_en','')}")
            st.markdown(f"**ตัวอย่าง:** {row.get('example_zh','')}")
            st.markdown(f"🇹🇭 {row.get('example_th','')}")

        if st.button("➡️ ข้อถัดไป", type="primary", use_container_width=True):
            st.session_state.quiz_index = (idx + 1) % len(deck)
            st.session_state.quiz_answered = False
            st.session_state.quiz_selected = None
            st.session_state.quiz_options = []
            st.session_state.quiz_audio_bytes = None
            st.rerun()

    # ── ปุ่มสุ่มใหม่ ──────────────────────────────────────────────────────
    if st.button("🔀 สุ่มชุดคำถามใหม่", use_container_width=True):
        deck2 = filtered.to_dict("records")
        random.shuffle(deck2)
        st.session_state.quiz_deck = deck2
        st.session_state.quiz_index = 0
        st.session_state.quiz_answered = False
        st.session_state.quiz_selected = None
        st.session_state.quiz_options = []
        st.session_state.quiz_audio_bytes = None
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VOCABULARY
# ══════════════════════════════════════════════════════════════════════════════
def page_vocabulary(df):
    """หน้า Vocabulary — คลังคำศัพท์"""
    st.markdown("## 📚 คลังคำศัพท์")

    filtered = get_filtered_df(df)

    # Search
    search = st.text_input("🔍 ค้นหาคำศัพท์:", placeholder="พิมพ์คำจีน, พินอิน, หรือคำแปล...")
    if search:
        mask = (
            filtered["word"].str.contains(search, na=False) |
            filtered["pinyin"].str.contains(search, case=False, na=False) |
            filtered["trans_th"].str.contains(search, case=False, na=False) |
            filtered["trans_en"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    st.caption(f"แสดง **{len(filtered):,}** คำ")

    # แสดงตาราง
    show_cols = [c for c in st.session_state.show_columns if c in filtered.columns]
    if not show_cols:
        show_cols = DEFAULT_COLUMNS

    st.dataframe(
        filtered[show_cols].reset_index(drop=True),
        use_container_width=True,
        height=600,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "hsk_level": st.column_config.TextColumn("Level", width="small"),
            "word": st.column_config.TextColumn("คำศัพท์", width="medium"),
            "pinyin": st.column_config.TextColumn("Pinyin", width="medium"),
            "pos_zh": st.column_config.TextColumn("词性", width="small"),
            "pos_en": st.column_config.TextColumn("POS", width="small"),
            "pos_th": st.column_config.TextColumn("ประเภทคำ", width="medium"),
            "trans_en": st.column_config.TextColumn("English", width="large"),
            "trans_th": st.column_config.TextColumn("ไทย", width="large"),
            "example_zh": st.column_config.TextColumn("ตัวอย่าง (จีน)", width="large"),
            "example_th": st.column_config.TextColumn("ตัวอย่าง (ไทย)", width="large"),
            "example_en": st.column_config.TextColumn("ตัวอย่าง (EN)", width="large"),
        },
    )

    # Download
    csv_data = filtered[show_cols].to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ ดาวน์โหลด CSV",
        data=csv_data,
        file_name="hsk_vocabulary_export.csv",
        mime="text/csv",
    )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SUMMARY & LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
def page_summary():
    """หน้า Summary & Leaderboard"""
    st.markdown("## 📊 สรุปผลและตารางคะแนน")

    username = st.session_state.username

    # ── Summary ───────────────────────────────────────────────────────────
    st.markdown("### 📈 สถิติ Session ปัจจุบัน")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🃏 Flashcard")
        fc_got = st.session_state.fc_got_it
        fc_need = st.session_state.fc_need_review
        fc_total = fc_got + fc_need
        c1, c2, c3 = st.columns(3)
        c1.metric("💚 จำได้", fc_got)
        c2.metric("🔴 จำไม่ได้", fc_need)
        c3.metric("📊 รวม", fc_total)
        if fc_total > 0:
            st.progress(fc_got / fc_total)
            st.caption(f"ความแม่นยำ: {fc_got/fc_total*100:.1f}%")

    with col2:
        st.markdown("#### 📝 Quiz")
        q_correct = st.session_state.quiz_correct
        q_wrong = st.session_state.quiz_wrong
        q_total = q_correct + q_wrong
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ ถูก", q_correct)
        c2.metric("❌ ผิด", q_wrong)
        c3.metric("📊 รวม", q_total)
        if q_total > 0:
            st.progress(q_correct / q_total)
            st.caption(f"ความแม่นยำ: {q_correct/q_total*100:.1f}%")

    # คำที่ตอบผิดบ่อย
    if st.session_state.quiz_history:
        wrong_words = [h["word"] for h in st.session_state.quiz_history if not h["correct"]]
        if wrong_words:
            st.markdown("#### ⚠️ คำที่ตอบผิด")
            st.write(", ".join(set(wrong_words)))

    # Reset
    if st.button("🔄 รีเซ็ตสถิติ Session", type="secondary"):
        st.session_state.fc_got_it = 0
        st.session_state.fc_need_review = 0
        st.session_state.fc_history = []
        st.session_state.quiz_correct = 0
        st.session_state.quiz_wrong = 0
        st.session_state.quiz_history = []
        st.rerun()

    st.markdown("---")

    # ── Leaderboard ───────────────────────────────────────────────────────
    st.markdown("### 🏆 Leaderboard")

    # บันทึกคะแนน
    col_save, col_refresh = st.columns(2)
    with col_save:
        if st.button("💾 บันทึกผลคะแนนของฉัน", type="primary", use_container_width=True):
            if username == "Anonymous":
                st.warning("กรุณาระบุชื่อก่อนบันทึกคะแนน")
            else:
                success = save_to_leaderboard(
                    username,
                    st.session_state.quiz_correct,
                    st.session_state.quiz_correct + st.session_state.quiz_wrong,
                    st.session_state.fc_got_it,
                    st.session_state.fc_got_it + st.session_state.fc_need_review,
                )
                if success:
                    st.success("✅ บันทึกคะแนนสำเร็จ!")
                else:
                    st.error("❌ ไม่สามารถบันทึกได้ — กรุณาตั้งค่า Google Sheets ก่อน")

    with col_refresh:
        if st.button("🔄 รีเฟรช Leaderboard", use_container_width=True):
            st.rerun()

    # แสดง Leaderboard
    lb_df = load_leaderboard()
    if lb_df is not None and not lb_df.empty:
        # จัดอันดับ
        if "total" in lb_df.columns:
            lb_df = lb_df.sort_values("total", ascending=False).reset_index(drop=True)
            lb_df.index += 1
            lb_df.index.name = "อันดับ"

        st.dataframe(lb_df, use_container_width=True)
    else:
        st.info("""
        📋 **ยังไม่มีข้อมูล Leaderboard**

        เพื่อเปิดใช้งาน Leaderboard:
        1. ตั้งค่า Google Sheets API (ดูคำอธิบายด้านล่าง)
        2. เพิ่ม credentials ใน `.streamlit/secrets.toml`
        3. กด "บันทึกผลคะแนนของฉัน"
        """)

    # คำอธิบาย Google Sheets Setup
    with st.expander("⚙️ วิธีตั้งค่า Google Sheets API"):
        st.markdown("""
        ### ขั้นตอนการตั้งค่า Google Sheets

        **1. สร้าง Google Cloud Project**
        - ไปที่ [console.cloud.google.com](https://console.cloud.google.com)
        - สร้าง Project ใหม่
        - เปิดใช้งาน **Google Sheets API** และ **Google Drive API**

        **2. สร้าง Service Account**
        - ไปที่ IAM & Admin → Service Accounts
        - สร้าง Service Account ใหม่
        - ดาวน์โหลด JSON Key

        **3. สร้าง Google Sheet**
        - สร้าง Google Sheet ใหม่
        - แชร์ให้ Service Account email (Editor)
        - คัดลอก URL ของ Sheet

        **4. ตั้งค่า secrets.toml**
        ```toml
        # .streamlit/secrets.toml

        gsheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

        [gcp_service_account]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "your-key-id"
        private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
        client_email = "your-service-account@project.iam.gserviceaccount.com"
        client_id = "your-client-id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        ```

        **5. โครงสร้าง Google Sheet (Row 1 = Header)**
        ```
        username | quiz_correct | quiz_total | fc_got | fc_total | total | date
        ```
        """)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    """ฟังก์ชันหลักของแอปพลิเคชัน"""
    init_session_state()

    # โหลดข้อมูล
    try:
        df = load_data()
    except FileNotFoundError:
        st.error(f"❌ ไม่พบไฟล์ `{CSV_PATH}` — กรุณาวางไฟล์ CSV ในโฟลเดอร์เดียวกับ app.py")
        st.stop()

    # ── User Identification ────────────────────────────────────────────────
    if st.session_state.username is None:
        page_user_identification()
        return

    # ── Sidebar ────────────────────────────────────────────────────────────
    render_sidebar(df)

    # ── Page Routing ───────────────────────────────────────────────────────
    page = st.session_state.current_page

    if page == "flashcard":
        page_flashcard(df)
    elif page == "quiz":
        page_quiz(df)
    elif page == "vocabulary":
        page_vocabulary(df)
    elif page == "summary":
        page_summary()
    else:
        page_flashcard(df)


if __name__ == "__main__":
    main()
