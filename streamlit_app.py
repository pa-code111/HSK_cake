import streamlit as st
import pandas as pd
from gtts import gTTS
import io

st.set_page_config(page_title="HSK Flashcard AI", page_icon="🇨🇳", layout="centered")

@st.cache_data
def load_vocab():
    return pd.read_csv("hsk_vocab - zh-th.csv")

def speak_word(text):
    # ใช้ gTTS แปลงตัวอักษรจีนเป็นเสียง (ภาษาจีน)
    tts = gTTS(text, lang='zh-cn')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

df = load_vocab()

st.title("🇨🇳 HSK Flashcard Intelligence")

available_levels = sorted(df['hsk_level'].unique())
selected_levels = st.multiselect("เลือกเลเวล HSK:", options=available_levels, default=available_levels)
filtered_df = df[df['hsk_level'].isin(selected_levels)]

tab1, tab2 = st.tabs(["🎴 Flashcard (สุ่มทาย)", "📖 คำศัพท์ทั้งหมด (List)"])

with tab1:
    if not filtered_df.empty:
        if 'current_word' not in st.session_state or st.session_state.current_word_level not in selected_levels:
            st.session_state.current_word = filtered_df.sample().iloc[0]
            st.session_state.current_word_level = st.session_state.current_word['hsk_level']

        st.markdown(f"### <span style='font-size: 60px;'>{st.session_state.current_word['simplified']}</span>", unsafe_allow_html=True)
        
        # ปุ่มกด
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔊 ฟังเสียงอ่าน"):
                audio_fp = speak_word(st.session_state.current_word['simplified'])
                st.audio(audio_fp, format='audio/mp3')
        with col2:
            if st.button("👁️ เปิดดูคำแปล"):
                st.success(f"**พินอิน:** {st.session_state.current_word['pinyin']}")
                st.info(f"**ความหมาย:** {st.session_state.current_word['meaning']}")
        with col3:
            if st.button("🔄 สุ่มคำใหม่"):
                st.session_state.current_word = filtered_df.sample().iloc[0]
                st.session_state.current_word_level = st.session_state.current_word['hsk_level']
                st.rerun()

with tab2:
    if not filtered_df.empty:
        st.dataframe(filtered_df[['simplified', 'pinyin', 'meaning', 'hsk_level']], use_container_width=True)