import streamlit as st
import pandas as pd
import requests
import urllib.parse
import unicodedata
import re
import json
import os
import random
import time
import tempfile
import html as html_lib
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from functools import lru_cache

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

st.set_page_config(
    page_title="HSK Flashcard AI",
    page_icon="🇨🇳",
    layout="centered",
    initial_sidebar_state="expanded",
)

HSK_LEVELS = ["1", "2", "3", "4", "5", "6", "7-9"]

# ─── บันทึกความคืบหน้าแบบถาวร (SRS + ประวัติ) ───────────────────────────────
try:
    _DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data")
    os.makedirs(_DATA_DIR, exist_ok=True)
    _PROBE = os.path.join(_DATA_DIR, ".write_test")
    with open(_PROBE, "w") as _f:
        _f.write("ok")
    os.remove(_PROBE)
except Exception:
    _DATA_DIR = tempfile.gettempdir()

PROGRESS_FILE = os.path.join(_DATA_DIR, "hsk_progress.json")

FIXED_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hsk_vocabnew_fixed.csv")

SRS_INTERVAL_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14, 6: 30}
SRS_MAX_BOX = 6

MAX_HISTORY = 300


@st.cache_resource(show_spinner=False)
def _get_gsheet_worksheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None
    try:
        try:
            service_account_info = st.secrets.get("gcp_service_account")
            sheet_id = st.secrets.get("gsheet_id")
        except FileNotFoundError:
            # Running locally without secrets is a supported fallback, not an error.
            st.session_state.pop("_gsheet_error", None)
            return None
        if not service_account_info or not sheet_id:
            st.session_state.pop("_gsheet_error", None)
            return None
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(dict(service_account_info), scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet("hsk_progress")
        except Exception:
            ws = sh.add_worksheet(title="hsk_progress", rows=200, cols=3)
            ws.update(range_name="A1:C1", values=[["key", "value_json", "updated_at"]])
        return ws
    except Exception as e:
        st.session_state["_gsheet_error"] = str(e)
        return None


def _gsheet_read_all(ws):
    try:
        rows = ws.get_all_values()
    except Exception as e:
        st.session_state["_gsheet_error"] = str(e)
        return {}
    result = {}
    for i, row in enumerate(rows[1:], start=2):
        if not row or not row[0]:
            continue
        key = row[0]
        raw = row[1] if len(row) > 1 else ""
        try:
            val = json.loads(raw) if raw else None
        except Exception:
            val = None
        result[key] = (i, val)
    return result


def _gsheet_upsert_row(ws, key, payload_obj, cache):
    payload = json.dumps(payload_obj, ensure_ascii=False, default=str)
    now = datetime.now().isoformat()
    existing = cache.get(key)
    if existing:
        rownum, _ = existing
        ws.update(range_name=f"A{rownum}:C{rownum}", values=[[key, payload, now]])
    else:
        ws.append_row([key, payload, now], value_input_option="RAW")
        cache[key] = (None, payload_obj)


def _is_legacy_flat_srs(srs):
    for v in srs.values():
        if isinstance(v, dict):
            return "box" in v
        break
    return False


def _load_progress():
    ws = _get_gsheet_worksheet()
    if ws is not None:
        try:
            cache = _gsheet_read_all(ws)
            data = {"srs": {}, "history": [], "remembered": [], "forgotten": [], "players": {}}
            if "history" in cache and isinstance(cache["history"][1], list):
                data["history"] = cache["history"][1]
            for key, (_rownum, val) in cache.items():
                if key.startswith("players:") and isinstance(val, dict):
                    name = key[len("players:"):]
                    data["players"][name] = {
                        "correct": val.get("correct", 0),
                        "total": val.get("total", 0),
                        "last_active": val.get("last_active"),
                        "leaderboard_visible": val.get("leaderboard_visible", True),
                        "history": val.get("history", []),
                    }
                    data["srs"][name] = val.get("srs", {})
            legacy_history = data.get("history", [])
            if legacy_history:
                for name, player in data["players"].items():
                    if not player.get("history"):
                        player["history"] = [h for h in legacy_history if h.get("ผู้เล่น") == name]
            st.session_state["_progress_backend"] = "gsheet"
            return data
        except Exception as e:
            st.session_state["_gsheet_error"] = str(e)

    st.session_state["_progress_backend"] = "local"
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("srs", {})
        data.setdefault("history", [])
        data.setdefault("remembered", [])
        data.setdefault("forgotten", [])
        data.setdefault("players", {})
        if _is_legacy_flat_srs(data["srs"]):
            data["srs"] = {"_เดิม (รวม)": data["srs"]}
        legacy_history = data.get("history", [])
        for name, player in data["players"].items():
            if not isinstance(player, dict):
                data["players"][name] = player = {}
            player.setdefault("leaderboard_visible", True)
            if not player.get("history"):
                player["history"] = [h for h in legacy_history if h.get("ผู้เล่น") == name]
        return data
    except Exception:
        return {"srs": {}, "history": [], "remembered": [], "forgotten": [], "players": {}}


# Keep answer flow responsive while limiting Google Sheets requests. Visiting
# History forces a final sync, so the public board does not stay stale.
_GSHEET_SYNC_EVERY_N_ANSWERS = 5
_GSHEET_SYNC_EVERY_SECONDS = 20


def _gsheet_sync_due():
    now = time.time()
    pending = st.session_state.get("_gsheet_pending_count", 0) + 1
    st.session_state["_gsheet_pending_count"] = pending
    last_sync = st.session_state.get("_gsheet_last_sync_time", 0.0)
    if pending >= _GSHEET_SYNC_EVERY_N_ANSWERS or (now - last_sync) >= _GSHEET_SYNC_EVERY_SECONDS:
        st.session_state["_gsheet_pending_count"] = 0
        st.session_state["_gsheet_last_sync_time"] = now
        return True
    return False


def _save_progress(force_gsheet_sync=False):
    name = _current_player_name()
    srs_all = st.session_state.get("srs_data", {})
    my_srs = srs_all.get(name, {})
    players = st.session_state.get("players_data", {})
    my_player = dict(players.get(name, {"correct": 0, "total": 0, "last_active": None}))
    my_history_session = [
        h for h in st.session_state.get("play_history", [])
        if h.get("ผู้เล่น", name) == name
    ][-MAX_HISTORY:]
    st.session_state.play_history = my_history_session
    my_player["history"] = my_history_session
    my_player.setdefault("leaderboard_visible", True)
    players[name] = my_player
    st.session_state.players_data = players

    if force_gsheet_sync or _gsheet_sync_due():
        ws = _get_gsheet_worksheet()
        if ws is not None:
            try:
                cache = _gsheet_read_all(ws)
                _gsheet_upsert_row(ws, f"players:{name}", {
                    "srs": my_srs,
                    "correct": my_player.get("correct", 0),
                    "total": my_player.get("total", 0),
                    "last_active": my_player.get("last_active"),
                    "leaderboard_visible": my_player.get("leaderboard_visible", True),
                    "history": my_history_session,
                }, cache)
                st.session_state["_progress_backend"] = "gsheet"
            except Exception as e:
                st.session_state["_gsheet_error"] = str(e)

    try:
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                existing_local = json.load(f)
        except Exception:
            existing_local = {}
        if not isinstance(existing_local, dict):
            existing_local = {}
        existing_local_players = existing_local.get("players", {})
        existing_local_srs = existing_local.get("srs", {})

        merged_players = dict(existing_local_players) if isinstance(existing_local_players, dict) else {}
        # Preserve profiles already loaded from Google Sheets or another local
        # session; saving one player must not drop everyone else in memory.
        merged_players.update(players)
        merged_players[name] = my_player
        merged_srs = dict(existing_local_srs) if isinstance(existing_local_srs, dict) else {}
        merged_srs.update(srs_all)
        merged_srs[name] = my_srs

        local_data = {
            "srs": merged_srs,
            "history": [],
            "remembered": st.session_state.get("remembered", []),
            "forgotten": st.session_state.get("forgotten", []),
            "players": merged_players,
        }
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(local_data, f, ensure_ascii=False, default=str)
        st.session_state.srs_data = merged_srs
        st.session_state.players_data = merged_players
    except Exception as e:
        st.session_state["_local_save_error"] = str(e)


def _current_player_name():
    name = str(st.session_state.get("player_name", "")).strip()
    return name if name else "Guest"


def _record_player_result(correct):
    name = _current_player_name()
    players = st.session_state.get("players_data", {})
    p = dict(players.get(name, {"correct": 0, "total": 0, "last_active": None}))
    p["total"] = p.get("total", 0) + 1
    if correct:
        p["correct"] = p.get("correct", 0) + 1
    p["last_active"] = datetime.now().isoformat()
    p.setdefault("leaderboard_visible", True)
    p.setdefault("history", [])
    players[name] = p
    st.session_state.players_data = players


def _update_srs(word_id, correct):
    wid = str(word_id)
    name = _current_player_name()
    all_srs = st.session_state.get("srs_data", {})
    my_srs = all_srs.get(name, {})
    entry = my_srs.get(wid, {"box": 1, "next_due": None})
    box = entry.get("box", 1)
    if correct:
        box = min(box + 1, SRS_MAX_BOX)
    else:
        box = 1
    due = datetime.now() + timedelta(days=SRS_INTERVAL_DAYS.get(box, 0))
    current_total = int(st.session_state.get("players_data", {}).get(name, {}).get("total", 0) or 0)
    my_srs[wid] = {
        "box": box,
        "next_due": due.isoformat(),
        "last_result": "correct" if correct else "wrong",
        # A wrong answer becomes eligible only after five other answers.
        # current_total is before _record_player_result increments this answer.
        "retry_after_total": None if correct else current_total + 6,
    }
    all_srs[name] = my_srs
    st.session_state.srs_data = all_srs
    _record_player_result(correct)
    _save_progress()


def pick_srs_word(pool_df, exclude_id=None):
    """Choose due cards, then new cards, while spacing wrong retries."""
    if pool_df.empty:
        return None
    name = _current_player_name()
    srs = st.session_state.get("srs_data", {}).get(name, {})
    if not srs:
        candidates = pool_df
        if exclude_id is not None and len(candidates) > 1:
            candidates = candidates[candidates["id"].astype(str) != str(exclude_id)]
        return candidates.sample().iloc[0]

    srs_rows = [
        {
            "id": k,
            "box": v.get("box", 1),
            "next_due": v.get("next_due"),
            "retry_after_total": v.get("retry_after_total"),
        }
        for k, v in srs.items()
    ]
    srs_df = pd.DataFrame(srs_rows) if srs_rows else pd.DataFrame(columns=["id", "box", "next_due", "retry_after_total"])
    if not srs_df.empty:
        srs_df["id"] = srs_df["id"].astype(str)
        srs_df["next_due"] = pd.to_datetime(srs_df["next_due"], errors="coerce")
        srs_df["retry_after_total"] = pd.to_numeric(srs_df["retry_after_total"], errors="coerce")

    pool = pool_df.copy()
    pool["_id_str"] = pool["id"].astype(str)
    srs_small = srs_df[["id", "box", "next_due", "retry_after_total"]].copy()
    merged = pool.merge(srs_small, left_on="_id_str", right_on="id", how="left", suffixes=("", "_srs"))

    now = pd.Timestamp.now()
    current_total = int(st.session_state.get("players_data", {}).get(name, {}).get("total", 0) or 0)
    retry_ready = merged["retry_after_total"].isna() | (merged["retry_after_total"] <= current_total)
    is_new = merged["box"].isna()
    is_due = (~is_new) & retry_ready & (merged["next_due"] <= now)
    is_future = (~is_new) & retry_ready & (merged["next_due"] > now)

    # Avoid showing the exact same card twice in a row whenever another card
    # in the same priority group is available.
    not_previous = merged["_id_str"] != str(exclude_id) if exclude_id is not None else pd.Series(True, index=merged.index)

    due_pool = merged[is_due & not_previous]
    if due_pool.empty:
        due_pool = merged[is_due]
    if not due_pool.empty:
        min_box = due_pool["box"].min()
        return due_pool[due_pool["box"] == min_box].sample().iloc[0]

    new_pool = merged[is_new & not_previous]
    if new_pool.empty:
        new_pool = merged[is_new]
    if not new_pool.empty:
        return new_pool.sample().iloc[0]

    future_pool = merged[is_future & not_previous]
    if future_pool.empty:
        future_pool = merged[is_future]
    if not future_pool.empty:
        return future_pool.sort_values("next_due").iloc[0]

    # All cards can be temporarily deferred only in a very small custom list.
    # Keep the app usable by selecting the card whose retry gate opens first.
    deferred = merged[~is_new].sort_values("retry_after_total", na_position="last")
    if exclude_id is not None and len(deferred) > 1:
        deferred_without_previous = deferred[deferred["_id_str"] != str(exclude_id)]
        if not deferred_without_previous.empty:
            deferred = deferred_without_previous
    if not deferred.empty:
        return deferred.iloc[0]

    if exclude_id is not None and len(pool_df) > 1:
        pool2 = pool_df[pool_df["id"].astype(str) != str(exclude_id)]
        if not pool2.empty:
            return pool2.sample().iloc[0]
    return pool_df.sample().iloc[0]


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


def render_audio_player(text, label="🔊 ฟังเสียง", autoplay=False):
    """Speak Mandarin in the browser without a server/network round-trip."""
    safe_text_js = json.dumps(str(text), ensure_ascii=False)
    safe_label = html_lib.escape(label)
    autoplay_js = "true" if autoplay else "false"
    component_html = f"""
    <style>
      html, body {{ margin: 0; padding: 0; background: transparent; font-family: sans-serif; }}
      .speech-wrap {{ display: flex; align-items: center; gap: 8px; width: 100%; }}
      button {{
        width: 100%; height: 46px; min-height: 46px; box-sizing: border-box;
        border-radius: 12px; padding: 0 10px;
        border: 1px solid rgba(255,255,255,.22); background: #262a34;
        color: #ffffff; font-size: 18px; font-weight: 700; line-height: 1.1;
        white-space: nowrap; cursor: pointer;
      }}
      button:hover {{ border-color: #7d8799; background: #323744; }}
      #status {{ font-size: 11px; color: #888; white-space: nowrap; }}
    </style>
    <div class="speech-wrap">
      <button id="speak" type="button">{safe_label}</button>
      <span id="status" aria-live="polite"></span>
    </div>
    <script>
    (function() {{
      const button = document.getElementById('speak');
      const status = document.getElementById('status');
      const text = {safe_text_js};

      function speak() {{
        if (!('speechSynthesis' in window)) {{
          status.textContent = 'ไม่รองรับเสียง';
          return;
        }}
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-CN';
        utterance.rate = 0.82;
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => v.lang.toLowerCase() === 'zh-cn')
          || voices.find(v => v.lang.toLowerCase().startsWith('zh'));
        if (voice) utterance.voice = voice;
        utterance.onstart = () => {{ status.textContent = 'กำลังเล่น'; }};
        utterance.onend = () => {{ status.textContent = ''; }};
        utterance.onerror = () => {{ status.textContent = 'กดฟังอีกครั้ง'; }};
        window.speechSynthesis.speak(utterance);
      }}

      button.addEventListener('click', speak);
      if ({autoplay_js}) window.setTimeout(speak, 120);
    }})();
    </script>
    """
    components.html(component_html, height=48, scrolling=False)


_SENSE_MARKER_RE = re.compile(r"(?<=[\u3400-\u9fff])[12]$")


def display_word_text(value):
    """Show official sense markers as superscripts instead of ordinary digits."""
    text = str(value or "").strip()
    return _SENSE_MARKER_RE.sub(lambda m: "¹" if m.group(0) == "1" else "²", text)


def spoken_word_text(value):
    """Remove official sense markers before speech or external translation."""
    return _SENSE_MARKER_RE.sub("", str(value or "").strip())


def normalize_level(level):
    s = str(level).strip()
    primary = s.split("(")[0].strip()
    if primary in ("7", "8", "9", "7-9", "7-9级"):
        return "7-9"
    return primary


def split_level_label(level):
    s = str(level).strip()
    primary_raw = s.split("(")[0].strip()
    primary = normalize_level(primary_raw)

    m = re.search(r"(\(.*\))", s)
    extra = m.group(1) if m else ""

    label = f"{primary} {extra}".strip() if extra else primary
    return primary, extra, label


def extract_level_memberships(level):
    """Return every HSK level encoded in labels such as ``1(2)(4)``."""
    raw = str(level).strip()
    parts = [raw.split("(")[0]] + re.findall(r"\(([^)]+)\)", raw)
    memberships = []
    for part in parts:
        normalized = normalize_level(part)
        if normalized in HSK_LEVELS and normalized not in memberships:
            memberships.append(normalized)
    return tuple(memberships)


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


@lru_cache(maxsize=16)
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
.flip-card {
    background-color:transparent;
    width:100%;
    height:420px;
    perspective:1200px;
    margin:16px 0;
    display:block;
    cursor:pointer;
    user-select:none;
}
.flip-card-inner {
    position:relative;
    width:100%;
    height:100%;
    text-align:center;
    transition:transform 0.65s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    transform-style:preserve-3d;
}
.flip-card.flipped .flip-card-inner {
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
    flex-direction:column;
}
.flip-card-back {
    color:white;
    transform:rotateY(180deg);
    flex-direction:column;
    justify-content:flex-start;
    z-index:1;
    overflow: hidden;
}
.pinyin-text { font-size:36px; margin-bottom:12px; font-weight:700; }
.meaning-text { font-size:28px; font-weight:600; }
.word-frame { padding:12px 18px; }
.ex-line {
    font-size:16px;
    font-weight:500;
    line-height:1.35;
    margin:4px 0;
    opacity:0.95;
    text-align:center;
    background:rgba(255,255,255,0.12);
    border:1px solid rgba(255,255,255,0.25);
    border-radius:10px;
    padding:6px 10px;
}
.example-scroll-wrap {
    position: relative;
    flex: 1;
    min-height: 0;
    width: 100%;
    margin-top: 8px;
}
.example-scroll-inner {
    height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding-bottom: 4px;
}
.example-scroll-wrap::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 22px;
    pointer-events: none;
    border-radius: 0 0 24px 24px;
    background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,0.28) 100%);
}
.click-hint { position:absolute; bottom:18px; left:0; right:0; text-align:center; font-size:13px; opacity:0.75; font-weight:500; }
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
.example-box {
    background: rgba(0,0,0,0.06);
    border-left: 3px solid #FFD54F;
    border-radius: 8px;
    padding: 6px 10px;
    margin: 4px 0;
    font-size: 12px;
    text-align: left;
}
.blurred {
    filter: blur(6px);
    user-select: none;
    -webkit-user-select: none;
    cursor: default;
}
.search-result-card {
    background: rgba(102,126,234,0.08);
    border: 1px solid rgba(102,126,234,0.35);
    border-radius: 10px;
    padding: 8px 10px;
    margin: 6px 0;
}

/* Compact AI panel */
.ai-panel { font-size:13px; }
.translate-result-box { padding: 8px 10px; font-size:13px; }
.example-box { font-size:12px; padding:6px 10px; }
.ai-panel .st-button button { padding:6px 8px !important; font-size:13px !important; }
.search-result-word { font-size: 20px; font-weight: 800; }
.search-result-meta { font-size: 12px; opacity: 0.85; }

div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div[role="radiogroup"] {
    gap: 8px;
    flex-wrap: wrap;
}
div[data-testid="stRadio"] label {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    padding: 10px 22px !important;
    border-radius: 999px !important;
    cursor: pointer;
    transition: all 0.18s ease;
    margin: 0 !important;
}
div[data-testid="stRadio"] label:hover {
    background: rgba(102,126,234,0.18);
    border-color: #667eea;
}
div[data-testid="stRadio"] label > div:first-child {
    display: none !important;
}
div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {
    font-size: 16px !important;
    font-weight: 600 !important;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-color: transparent;
}
div[data-testid="stRadio"] label:has(input:checked) p {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

if "progress_loaded" not in st.session_state:
    _saved = _load_progress()
    st.session_state.srs_data = _saved.get("srs", {})
    st.session_state.play_history = _saved.get("history", [])
    st.session_state.remembered = _saved.get("remembered", [])
    st.session_state.forgotten = _saved.get("forgotten", [])
    st.session_state.players_data = _saved.get("players", {})
    st.session_state.progress_loaded = True

if "player_name_history" not in st.session_state:
    st.session_state.player_name_history = []


def _render_user_identification_page():
    st.markdown("""
    <div style='text-align:center; padding: 40px 0 10px 0;'>
        <div style='font-size:80px;'>🇨🇳</div>
        <h1 style='font-size:2.5rem; margin: 0;'>HSK Flashcard Intelligence</h1>
        <p style='color:#888; font-size:1.05rem;'>แอปเรียนรู้คำศัพท์ภาษาจีน HSK ด้วยระบบทบทวนอัจฉริยะ (SRS)</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 👤 ระบุตัวตนของคุณ")

        st.caption("หลังเข้าใช้งาน เลือกระดับ HSK ได้จากแถบด้านข้าง และเลือกได้มากกว่าหนึ่งระดับ")

        def _enter_player(name):
            st.session_state.player_name = name
            st.session_state.level_filter = {level: True for level in HSK_LEVELS}
            for level in HSK_LEVELS:
                st.session_state[f"lv_{level}"] = True

        history = st.session_state.get("player_name_history", [])
        if history:
            st.markdown("**เลือกชื่อที่เคยใช้:**")
            recent = history[-4:]
            hist_cols = st.columns(len(recent))
            for i, name in enumerate(recent):
                with hist_cols[i]:
                    if st.button(f"👤 {name}", key=f"id_hist_{i}", width="stretch"):
                        _enter_player(name)
                        st.rerun()
            st.markdown("---")

        new_name = st.text_input(
            "หรือกรอกชื่อใหม่:",
            placeholder="เช่น สมชาย, Alice, 小明...",
            max_chars=30,
            key="id_new_name_input",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ เข้าใช้งาน", type="primary", width="stretch", key="id_enter_btn"):
                name = new_name.strip()
                if name:
                    _enter_player(name)
                    if name not in st.session_state.player_name_history:
                        st.session_state.player_name_history.append(name)
                    st.rerun()
                else:
                    st.warning("กรุณากรอกชื่อก่อนเข้าใช้งาน")
        with col_b:
            if st.button("🎭 ไม่ระบุตัวตน", width="stretch", key="id_anon_btn"):
                _enter_player("Guest")
                st.rerun()

        st.markdown("""
        <div style='text-align:center; color:#999; font-size:0.85rem; margin-top:20px;'>
            ไม่มีระบบ Login — ชื่อใช้แยกความคืบหน้าการเรียน (SRS) และ Leaderboard เท่านั้น
        </div>
        """, unsafe_allow_html=True)


if not st.session_state.get("player_name"):
    _render_user_identification_page()
    st.stop()


def _activate_player_context(force=False):
    """Load only the active player's private history into this session."""
    name = _current_player_name()
    if not force and st.session_state.get("_active_player_context") == name:
        return

    players = st.session_state.get("players_data", {})
    profile = dict(players.get(name, {}))
    legacy_history = st.session_state.get("play_history", [])
    own_history = profile.get("history")
    if not isinstance(own_history, list):
        own_history = [h for h in legacy_history if h.get("ผู้เล่น") == name]

    profile.setdefault("correct", 0)
    profile.setdefault("total", 0)
    profile.setdefault("last_active", None)
    profile.setdefault("leaderboard_visible", True)
    profile["history"] = own_history[-MAX_HISTORY:]
    players[name] = profile

    st.session_state.players_data = players
    st.session_state.play_history = profile["history"]
    st.session_state.remembered = []
    st.session_state.forgotten = []
    st.session_state._active_player_context = name


_activate_player_context()

st.title("🇨🇳 HSK Flashcard Intelligence")

st.sidebar.markdown('<div class="sidebar-section-title">🙋 ผู้เล่น</div>', unsafe_allow_html=True)
st.sidebar.markdown(f"**👤 {_current_player_name()}**")
if st.sidebar.button("🔄 เปลี่ยนผู้ใช้", width="stretch", key="switch_player_btn"):
    st.session_state.player_name = ""
    st.rerun()


uploaded = st.session_state.get("_uploaded_file_widget_value", None)


def _norm_header(c):
    s = str(c).strip().lower()
    s = s.replace("\ufeff", "")
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


_CANONICAL_ALIASES = {
    "id": ["id"],
    "hsk_level": ["hsk_level", "level", "hsklevel"],
    "word": ["word", "simplified", "hanzi", "chinese"],
    "pinyin": ["pinyin"],
    "trans_th": ["trans_th", "meaning", "translation_th", "thai", "trans th"],
    "trans_en": ["trans_en", "translation_en", "english", "trans en"],
    "pos_en": ["pos_en", "posen", "pos english"],
    "pos_th": ["pos_th", "posth"],
    "pos_zh": ["pos_zh", "poszh"],
    "example_zh": ["example_zh", "examplezh", "example_cn", "examplecn", "ex_zh", "exzh", "sentence_zh", "example chinese"],
    "example_th": ["example_th", "exampleth", "ex_th", "exth", "sentence_th", "example thai"],
    "example_en": ["example_en", "exampleen", "ex_en", "exen", "sentence_en", "example english"],
}


def normalize_uploaded_columns(df_raw):
    rename_map = {}
    used_targets = set()
    for col in df_raw.columns:
        nc = _norm_header(col)
        for canon, aliases in _CANONICAL_ALIASES.items():
            if canon in used_targets:
                continue
            if nc in (_norm_header(a) for a in aliases):
                rename_map[col] = canon
                used_targets.add(canon)
                break
    return df_raw.rename(columns=rename_map)


def map_vocab_columns(df_raw):
    cols = set(df_raw.columns)
    if {"word", "trans_th"}.issubset(cols) and ("level" in cols or "hsk_level" in cols):
        out = df_raw.copy()
        if "level" in out.columns and "hsk_level" not in out.columns:
            out = out.rename(columns={"level": "hsk_level"})
        if "id" not in out.columns:
            out.insert(0, "id", range(1, len(out) + 1))
        return out
    return None


def _load_vocab_with_column_mapping(read_func):
    df = None
    for skip in [1, 0, 2]:
        try:
            df_raw = read_func(skip)
        except Exception:
            continue
        if df_raw is None:
            continue
        df_raw.columns = df_raw.columns.astype(str).str.strip()
        df_raw = normalize_uploaded_columns(df_raw)
        mapped = map_vocab_columns(df_raw)
        if mapped is not None:
            df = mapped
            break
        if {"word", "pinyin", "trans_th"}.issubset(df_raw.columns) and ("level" in df_raw.columns or "hsk_level" in df_raw.columns):
            if "hsk_level" not in df_raw.columns and "level" in df_raw.columns:
                df_raw = df_raw.rename(columns={"level": "hsk_level"})
            df = df_raw
            break
    return df


@st.cache_data
def load_fixed_vocab():
    if not os.path.exists(FIXED_CSV_PATH):
        return None

    def _read_fixed(skip):
        try:
            return pd.read_csv(FIXED_CSV_PATH, skiprows=skip, encoding="utf-8")
        except Exception:
            return pd.read_csv(FIXED_CSV_PATH, skiprows=skip, encoding="utf-8", engine="python")

    return _load_vocab_with_column_mapping(_read_fixed)

if uploaded is not None:
    if "default_vocab_warned" in st.session_state:
        del st.session_state.default_vocab_warned

    def _read_uploaded(skip):
        try:
            if uploaded.name.lower().endswith((".xlsx", ".xls")):
                return pd.read_excel(uploaded, skiprows=skip)
            return pd.read_csv(uploaded, skiprows=skip)
        except Exception:
            uploaded.seek(0)
            return pd.read_csv(uploaded, skiprows=skip, encoding="utf-8", engine="python")

    df = _load_vocab_with_column_mapping(_read_uploaded)
    if df is None:
        st.error("⚠️ ไม่พบคอลัมน์ที่รองรับ (ต้องมี: word, trans_th, และ level/hsk_level)")
        st.stop()
else:
    df = load_fixed_vocab()
    if df is not None:
        if "default_vocab_warned" in st.session_state:
            del st.session_state.default_vocab_warned
    else:
        df = get_default_vocab()
        if "default_vocab_warned" not in st.session_state:
            st.session_state.default_vocab_warned = True
            st.sidebar.warning(
                f"⚠️ **ใช้ข้อมูลตัวอย่าง {len(df)} คำ**\n\n"
                f"อัปโหลดไฟล์ CSV/Excel ของคุณ หรือวางไฟล์ `hsk_vocabnew_fixed.csv` "
                f"ไว้ในโปรเจกต์เพื่อใช้ข้อมูลจำนวนมากขึ้น"
            )

if "id" not in df.columns:
    df = df.reset_index(drop=True)
    df["id"] = df.index + 1

df.columns = df.columns.astype(str).str.strip()

if df.empty:
    st.error("ไฟล์ CSV ว่างเปล่า")
    st.stop()

@st.cache_data(show_spinner=False)
def _prepare_vocab_df(df_in):
    df_in = df_in.copy()
    df_in['hsk_level_raw'] = df_in['hsk_level'].astype(str)
    _split = df_in['hsk_level_raw'].apply(split_level_label)
    df_in['hsk_level'] = _split.apply(lambda t: t[0])
    df_in['hsk_level_extra'] = _split.apply(lambda t: t[1])
    df_in['hsk_level_label'] = _split.apply(lambda t: t[2])
    df_in['hsk_levels'] = df_in['hsk_level_raw'].apply(extract_level_memberships)

    _pinyin_col_for_precompute = None
    for _candidate in ("pinyin",):
        if _candidate in df_in.columns:
            _pinyin_col_for_precompute = _candidate
            break
    if _pinyin_col_for_precompute:
        df_in['_pinyin_toneless'] = df_in[_pinyin_col_for_precompute].apply(strip_tones)
    else:
        df_in['_pinyin_toneless'] = ""
    return df_in


df = _prepare_vocab_df(df)

_current_cols_signature = tuple(sorted(df.columns.tolist()))


def _norm_colname(c):
    s = str(c).strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def _find_col(df_cols, candidates):
    norm_map = {}
    for c in df_cols:
        norm_map.setdefault(_norm_colname(c), c)
    for cand in candidates:
        key = _norm_colname(cand)
        if key in norm_map:
            return norm_map[key]
    return None


def _auto_detect_col_mapping():
    cols = df.columns.tolist()
    return {
        "id": _find_col(cols, ["id"]),
        "hsk_level": _find_col(cols, ["hsk_level", "level", "hsklevel"]),
        "word": _find_col(cols, ["word", "simplified", "hanzi", "chinese"]),
        "pos_en": _find_col(cols, ["pos_en", "posen", "pos english"]),
        "pos_th": _find_col(cols, ["pos_th", "posth"]),
        "pos_zh": _find_col(cols, ["pos_zh", "poszh"]),
        "pinyin": _find_col(cols, ["pinyin"]),
        "trans_th": _find_col(cols, ["trans_th", "meaning", "translation_th", "thai", "trans th"]),
        "trans_en": _find_col(cols, ["trans_en", "translation_en", "english", "trans en"]),
        "example_zh": _find_col(cols, ["example_zh", "examplezh", "example_cn", "examplecn", "ex_zh", "exzh", "sentence_zh", "example chinese", "ตัวอย่างประโยค(zh)", "ตัวอย่างประโยค_zh"]),
        "example_th": _find_col(cols, ["example_th", "exampleth", "ex_th", "exth", "sentence_th", "example thai", "ตัวอย่างประโยค(th)", "ตัวอย่างประโยค_th"]),
        "example_en": _find_col(cols, ["example_en", "exampleen", "ex_en", "exen", "sentence_en", "example english", "ตัวอย่างประโยค(en)", "ตัวอย่างประโยค_en"]),
    }


if "col_mapping" not in st.session_state or st.session_state.get("col_mapping_cols_signature") != _current_cols_signature:
    st.session_state.col_mapping = _auto_detect_col_mapping()
    st.session_state.col_mapping_cols_signature = _current_cols_signature

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
        "example_zh": True,
        "example_th": True,
        "example_en": True,
    }

if "col_mapping_show" not in st.session_state:
    st.session_state.col_mapping_show = True

if "level_filter" not in st.session_state:
    st.session_state.level_filter = {lvl: True for lvl in HSK_LEVELS}

with st.sidebar.expander("📊 เลือกเลเวล HSK", expanded=True):
    for i, lvl in enumerate(HSK_LEVELS):
        widget_key = f"lv_{lvl}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state.level_filter.get(lvl, False)
        if i % 2 == 0:
            c1, c2 = st.columns(2)
        with (c1 if i % 2 == 0 else c2):
            st.session_state.level_filter[lvl] = st.checkbox(
                f"HSK {lvl}",
                key=widget_key,
            )

with st.sidebar.expander("⚙️ การตั้งค่าคอลัมน์ที่แสดง", expanded=False):
    st.caption("เลือกคอลัมน์ที่ต้องการแสดงในตารางคำศัพท์")
    cols_to_show = [
        ("id", "ID"), ("hsk_level", "HSK"), ("word", "คำจีน"), ("pinyin", "พินอิน"),
        ("pos_en", "ชนิดคำ (EN)"), ("pos_th", "ชนิดคำ (TH)"), ("pos_zh", "ชนิดคำ (ZH)"),
        ("trans_th", "แปลไทย"), ("trans_en", "แปลอังกฤษ"), ("example_zh", "ตัวอย่าง (ZH)"),
        ("example_th", "ตัวอย่าง (TH)"), ("example_en", "ตัวอย่าง (EN)")
    ]

    for i in range(0, len(cols_to_show), 2):
        c1, c2 = st.columns(2)
        key1, label1 = cols_to_show[i]
        with c1:
            st.session_state.col_display_toggle[key1] = st.checkbox(
                label1,
                st.session_state.col_display_toggle.get(key1, True),
                key=f"tog_{key1}",
            )
        if i + 1 < len(cols_to_show):
            key2, label2 = cols_to_show[i + 1]
            with c2:
                st.session_state.col_display_toggle[key2] = st.checkbox(
                    label2,
                    st.session_state.col_display_toggle.get(
                        key2,
                        False if key2.startswith("pos_") else True,
                    ),
                    key=f"tog_{key2}",
                )

word_col = st.session_state.col_mapping.get("word", "word")
pinyin_col = st.session_state.col_mapping.get("pinyin", "pinyin")
trans_th_col = st.session_state.col_mapping.get("trans_th", "trans_th")
id_col = st.session_state.col_mapping.get("id", "id")
example_zh_col = st.session_state.col_mapping.get("example_zh")
example_th_col = st.session_state.col_mapping.get("example_th")
example_en_col = st.session_state.col_mapping.get("example_en")


def _clean_val(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def get_example_value(row, lang):
    col = {"zh": example_zh_col, "th": example_th_col, "en": example_en_col}.get(lang)
    toggle_key = f"example_{lang}"
    if not col or not st.session_state.col_display_toggle.get(toggle_key):
        return None
    row_keys = row.index if hasattr(row, "index") else row.keys()
    if col not in row_keys:
        return None
    return _clean_val(row.get(col, ""))


def get_examples_html(row):
    lines = []
    flags = {"zh": "🇨🇳", "th": "🇹🇭", "en": "🇬🇧"}
    for lang in ("zh", "th", "en"):
        val = get_example_value(row, lang)
        if val:
            lines.append(f"{flags[lang]} {val}")
    return lines

st.sidebar.markdown('<div class="sidebar-section-title">🔍 ค้นหา</div>', unsafe_allow_html=True)
query = st.sidebar.text_input("ค้นหาในทุกคอลัมน์", placeholder="id / คำจีน / พินอิน / แปล", label_visibility="collapsed", key="sidebar_search_query")

if "vocab_search_prefill" not in st.session_state:
    st.session_state.vocab_search_prefill = None
if "active_tab_radio" not in st.session_state:
    st.session_state.active_tab_radio = "🎴 Flashcard"

_PREVIEW_COL_ORDER = ["hsk_level", "word", "pinyin", "pos_en", "pos_th", "pos_zh", "trans_th", "trans_en", "example_zh", "example_th", "example_en"]
_PREVIEW_LABELS = {
    "hsk_level": "HSK", "word": "🇨🇳", "pinyin": "พินอิน",
    "pos_en": "ชนิดคำ(EN)", "pos_th": "ชนิดคำ(TH)", "pos_zh": "ชนิดคำ(ZH)",
    "trans_th": "🇹🇭 แปล", "trans_en": "🇬🇧 แปล",
    "example_zh": "🇨🇳 ตัวอย่าง", "example_th": "🇹🇭 ตัวอย่าง", "example_en": "🇬🇧 ตัวอย่าง",
}


def _sidebar_preview_fields(row):
    pairs = []
    for col_key in _PREVIEW_COL_ORDER:
        if not st.session_state.col_display_toggle.get(col_key):
            continue
        actual_col = st.session_state.col_mapping.get(col_key)
        if not actual_col or actual_col not in row.index:
            continue
        if col_key == "hsk_level":
            val = row.get("hsk_level_label", row.get("hsk_level", ""))
        else:
            val = row.get(actual_col, "")
        val = _clean_val(val)
        if val:
            pairs.append((_PREVIEW_LABELS[col_key], val))
    return pairs


@st.dialog("🔍 ผลการค้นหา", width="large")
def _show_search_preview_dialog(results_df):
    st.caption(f"พบทั้งหมด {len(results_df)} คำ — แสดง {min(len(results_df), 30)} คำแรก")
    for _, row in results_df.head(30).iterrows():
        w = row.get(word_col, "") if word_col else ""
        rid = row.get("id", "")
        fields_html = "".join(
            f'<div style="font-size:17px; margin:3px 0; opacity:0.95;"><b>{lbl}:</b> {val}</div>'
            for lbl, val in _sidebar_preview_fields(row)
        )
        st.markdown(
            f'<div style="background:rgba(102,126,234,0.14); border:1px solid rgba(102,126,234,0.45);'
            f'border-radius:16px; padding:18px 22px; margin:12px 0;">'
            f'<div style="font-size:34px; font-weight:800;">{w} '
            f'<span style="font-size:15px; opacity:0.6; font-weight:600;">#{rid}</span></div>'
            f'{fields_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.divider()
    if st.button("✕ ปิดหน้าต่างนี้", width="stretch", key="close_search_dialog_btn", type="primary"):
        st.rerun()


if query:
    q_toneless = strip_tones(query.strip())
    mask = pd.Series([False] * len(df), index=df.index)

    if st.session_state.col_display_toggle.get("id") and id_col:
        mask = mask | (df[id_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("word") and word_col:
        mask = mask | (df[word_col].astype(str).str.contains(query, case=False, na=False, regex=False))
    if st.session_state.col_display_toggle.get("pinyin") and pinyin_col:
        mask = mask | (df['_pinyin_toneless'].str.contains(q_toneless, na=False, regex=False))
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

    search_results_df = df[mask]
    st.sidebar.caption(f"พบ {len(search_results_df)} คำ")

    if len(search_results_df) > 0:
        if st.sidebar.button("🔍 ดูตัวอย่างขยายเต็มจอ", width="stretch", key="open_search_preview_dialog"):
            _show_search_preview_dialog(search_results_df)

    PREVIEW_SHOWN = 5
    if len(search_results_df) == 0:
        st.sidebar.info("ไม่พบคำที่ตรงกับการค้นหา")
    else:
        for _, row in search_results_df.head(PREVIEW_SHOWN).iterrows():
            w = row.get(word_col, "") if word_col else ""
            rid = row.get("id", "")

            fields_html = "".join(
                f'<div class="search-result-meta"><b>{lbl}:</b> {val}</div>'
                for lbl, val in _sidebar_preview_fields(row)
            )
            st.sidebar.markdown(
                f'<div class="search-result-card">'
                f'<span class="search-result-word">{w}</span> '
                f'<span class="search-result-meta">#{rid}</span>'
                f'{fields_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.sidebar.button("📖 ไปดูในหน้าคำศัพท์", key=f"goto_vocab_{rid}_{w}", width="stretch"):
                st.session_state.vocab_search_prefill = str(w)
                st.session_state.active_tab_radio = "📖 คำศัพท์"
                st.rerun()

        if len(search_results_df) > PREVIEW_SHOWN:
            st.sidebar.caption(f"...และอีก {len(search_results_df) - PREVIEW_SHOWN} คำ — กด 'ดูตัวอย่างขยายเต็มจอ' ด้านบน หรือพิมพ์ให้เจาะจงขึ้น")

    df = search_results_df

with st.sidebar.expander("📂 แหล่งข้อมูล", expanded=False):
    st.caption("ไม่จำเป็นต้องอัปโหลดไฟล์ — ระบบมีชุดคำศัพท์เริ่มต้นให้แล้ว อัปโหลดเฉพาะกรณีต้องการใช้ไฟล์คำศัพท์ของตัวเอง (CSV/Excel)")
    uploaded = st.file_uploader("อัปโหลดไฟล์ CSV/Excel", type=["csv", "xlsx", "xls"], key="_uploaded_file_widget_value")
    if uploaded is not None:
        st.success(f"✅ ใช้ไฟล์: {uploaded.name}")
    else:
        st.info("📦 กำลังใช้ชุดคำศัพท์เริ่มต้นของระบบ")

st.sidebar.markdown('<div class="sidebar-section-title">⚙️ ตั้งค่า</div>', unsafe_allow_html=True)

levels_data = {level for memberships in df["hsk_levels"] for level in memberships}
selected_levels = [l for l in HSK_LEVELS if st.session_state.level_filter.get(l) and l in levels_data]
_selected_level_set = set(selected_levels)
filtered_df = df[df["hsk_levels"].apply(lambda memberships: bool(_selected_level_set.intersection(memberships)))] if selected_levels else df.iloc[0:0]

if "audio_enabled" not in st.session_state:
    st.session_state.audio_enabled = True

audio_label = ("🔊 เสียงเปิด" if st.session_state.audio_enabled else "🔇 เสียงปิด")
if st.sidebar.button(audio_label, width="stretch", key="audio_sidebar_btn"):
    st.session_state.audio_enabled = not st.session_state.audio_enabled
    st.rerun()

if "ai_panel_open" not in st.session_state:
    st.session_state.ai_panel_open = True

ai_label = ("🤖 AI เปิด" if st.session_state.ai_panel_open else "🤖 AI ปิด")
if st.sidebar.button(ai_label, width="stretch", key="ai_sidebar_btn"):
    st.session_state.ai_panel_open = not st.session_state.ai_panel_open
    st.rerun()

if "quiz_auto_next" not in st.session_state:
    st.session_state.quiz_auto_next = True
st.sidebar.checkbox("เลื่อนไปข้อถัดไปอัตโนมัติเมื่อตอบ", key="quiz_auto_next")

if st.session_state.quiz_auto_next:
    if "quiz_auto_next_seconds" not in st.session_state:
        st.session_state.quiz_auto_next_seconds = 2
    st.sidebar.number_input(
        "⏱️ หน่วงกี่วินาทีก่อนไปข้อถัดไป",
        min_value=1, max_value=60, step=1,
        key="quiz_auto_next_seconds",
    )

_backend = st.session_state.get("_progress_backend", "local")
if _backend == "gsheet":
    st.sidebar.caption("☁️ บันทึกลง Google Sheets (ถาวรข้าม redeploy)")
else:
    st.sidebar.caption("💾 บันทึกในเครื่อง (หายเมื่อแอป redeploy/reboot)")

_gsheet_error = st.session_state.get("_gsheet_error", "")
if _gsheet_error and not str(_gsheet_error).startswith("No secrets found"):
    st.sidebar.caption(f"⚠️ Google Sheets: {_gsheet_error}")

_srs_now = pd.Timestamp.now()
_due_count = 0
_my_srs_for_due = st.session_state.get("srs_data", {}).get(_current_player_name(), {})
for _v in _my_srs_for_due.values():
    _nd = _v.get("next_due")
    if _nd is None or pd.to_datetime(_nd, errors="coerce") <= _srs_now:
        _due_count += 1
if _due_count > 0:
    st.sidebar.caption(f"📅 มีคำถึงกำหนดทบทวน {_due_count} คำ")

if "confirm_reset_progress" not in st.session_state:
    st.session_state.confirm_reset_progress = False

if not st.session_state.confirm_reset_progress:
    if st.sidebar.button("🗑️ ล้างความคืบหน้าทั้งหมดของผู้เล่นปัจจุบัน", width="stretch", key="reset_progress_btn"):
        st.session_state.confirm_reset_progress = True
        st.rerun()
else:
    st.sidebar.warning(f"ล้างข้อมูล SRS + ประวัติ + คะแนน เฉพาะของ '{_current_player_name()}' เท่านั้น (ไม่กระทบผู้เล่นคนอื่น)? กู้คืนไม่ได้")
    rc1, rc2 = st.sidebar.columns(2)
    with rc1:
        if st.button("✅ ยืนยัน", width="stretch", key="reset_progress_confirm"):
            name = _current_player_name()
            was_visible = st.session_state.players_data.get(name, {}).get("leaderboard_visible", True)
            st.session_state.srs_data[name] = {}
            st.session_state.play_history = []
            st.session_state.remembered = []
            st.session_state.forgotten = []
            st.session_state.players_data[name] = {
                "correct": 0,
                "total": 0,
                "last_active": None,
                "leaderboard_visible": was_visible,
                "history": [],
            }
            _save_progress(force_gsheet_sync=True)
            st.session_state.confirm_reset_progress = False
            st.rerun()
    with rc2:
        if st.button("✕ ยกเลิก", width="stretch", key="reset_progress_cancel"):
            st.session_state.confirm_reset_progress = False
            st.rerun()

_TAB_LABELS = ["🎴 Flashcard", "🎯 Quiz", "📖 คำศัพท์", "📋 ประวัติ"]
active_tab_choice = st.radio(
    "เมนู", _TAB_LABELS,
    horizontal=True, label_visibility="collapsed", key="active_tab_radio",
)
st.divider()


if active_tab_choice == "🎴 Flashcard":
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำในเลเวลที่เลือก")
    else:
        if (
            'current_word' not in st.session_state
            or not _selected_level_set.intersection(st.session_state.get('current_word_levels', ()))
        ):
            st.session_state.current_word = pick_srs_word(filtered_df)
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
            st.session_state.current_word_levels = tuple(st.session_state.current_word.get("hsk_levels", (st.session_state.current_word_level,)))
            st.session_state.card_flipped = False
            st.session_state._last_flip_component_value = None
            st.session_state.flip_generation = st.session_state.get('flip_generation', 0) + 1
            st.session_state.audio_played = False

        for k, v in [('card_flipped', False), ('audio_played', False), ('remembered', []), ('forgotten', []), ('play_history', []), ('ai_response', None), ('ai_response_word', None), ('reveal_side', False), ('last_word_id', None), ('show_translate_options', False), ('card_translate_result', None), ('card_translate_word', None), ('flip_generation', 0), ('_last_flip_component_value', None), ('reveal_mode', 'sync_flip')]:
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
                    "HSK": w.get('hsk_level_label', w['hsk_level']),
                    "ผล": "✅ จำได้" if feedback == "remembered" else "❌ จำไม่ได้",
                    "ผู้เล่น": _current_player_name(),
                    "โหมด": "Flashcard",
                })
                _update_srs(w.get('id'), correct=(feedback == "remembered"))

            prev_id = w.get('id')
            st.session_state.current_word = pick_srs_word(filtered_df, exclude_id=prev_id)
            st.session_state.current_word_level = str(st.session_state.current_word['hsk_level'])
            st.session_state.current_word_levels = tuple(st.session_state.current_word.get("hsk_levels", (st.session_state.current_word_level,)))
            st.session_state.card_flipped = False
            st.session_state._last_flip_component_value = None
            st.session_state.audio_played = False
            st.session_state.reveal_side = False
            st.session_state.ai_response = None
            st.session_state.ai_response_word = None
            st.session_state.last_word_id = st.session_state.current_word.get('id')
            st.session_state.show_translate_options = False
            st.session_state.card_translate_result = None
            st.session_state.card_translate_word = None
            st.session_state.flip_generation = st.session_state.get('flip_generation', 0) + 1

        if st.session_state.ai_panel_open:
            col_left, col_right = st.columns([0.6, 0.4], gap="large")
        else:
            col_left = st.container()
            col_right = None

        with col_left:
            current_word_id = st.session_state.current_word.get('id')
            if st.session_state.last_word_id != current_word_id:
                st.session_state.card_flipped = False
                st.session_state._last_flip_component_value = None
                st.session_state.last_word_id = current_word_id

            flipped_class = "flipped" if st.session_state.card_flipped else ""
            colors = get_hsk_color(st.session_state.current_word['hsk_level'])
            current_word_raw = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']
            current_word_text = display_word_text(current_word_raw)
            current_word_spoken = spoken_word_text(current_word_raw)
            flip_gen = st.session_state.get('flip_generation', 0)
            current_hsk_label = st.session_state.current_word.get(
                'hsk_level_label', st.session_state.current_word['hsk_level']
            )

            example_lines = get_examples_html(st.session_state.current_word)
            example_html = "".join(f'<div class="ex-line">{line}</div>' for line in example_lines)

            _CARD_HEIGHT = 380
            card_html = f"""
<div class="flip-card {flipped_class}" style="height:{_CARD_HEIGHT}px;">
    <div class="flip-card-inner">
        <div class="flip-card-front" style="background:linear-gradient({colors['gradient']}); font-size:48px;">
            <div class="id-badge">#{st.session_state.current_word.get('id','')}</div>
            <div class="hsk-badge">HSK {current_hsk_label}</div>
            <div>{current_word_text}</div>
            <div class="click-hint">แตะเพื่อเปิด</div>
        </div>
        <div class="flip-card-back" style="background:linear-gradient({colors['gradient']});">
            <div class="id-badge">#{st.session_state.current_word.get('id','')}</div>
            <div class="hsk-badge">HSK {current_hsk_label}</div>
            <div class="word-frame">
                <div class="pinyin-text">{st.session_state.current_word.get(pinyin_col, st.session_state.current_word.get('pinyin',''))}</div>
                <div class="meaning-text">{st.session_state.current_word.get(trans_th_col, st.session_state.current_word.get('trans_th',''))}</div>
            </div>
            <div class="example-scroll-wrap">
                <div class="example-scroll-inner">{example_html}</div>
            </div>
        </div>
    </div>
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)

            st.markdown(
                f"""
                <style>
                .st-key-flip_overlay_btn {{
                    margin-top: -{_CARD_HEIGHT}px !important;
                    height: {_CARD_HEIGHT}px !important;
                    position: relative;
                    z-index: 20;
                }}
                .st-key-flip_overlay_btn button {{
                    width: 100% !important;
                    height: {_CARD_HEIGHT}px !important;
                    opacity: 0 !important;
                    cursor: pointer !important;
                    border: none !important;
                    background: transparent !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
            if st.button("แตะเพื่อพลิกการ์ด", key="flip_overlay_btn", width="stretch"):
                st.session_state.card_flipped = not st.session_state.card_flipped
                st.rerun()

            if st.button("🔄 พลิกการ์ด (ถ้าแตะกลางการ์ดไม่ได้)", width="stretch", key="flip_fallback_btn"):
                st.session_state.card_flipped = not st.session_state.card_flipped
                st.rerun()

            r1, r2 = st.columns(2)
            with r1:
                if st.button("✅ จำได้", width="stretch", key="remember_btn"):
                    next_word("remembered")
                    st.rerun()
            with r2:
                if st.button("❌ จำไม่ได้", width="stretch", key="forget_btn"):
                    next_word("forgotten")
                    st.rerun()

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.session_state.audio_enabled:
                    try:
                        render_audio_player(current_word_spoken, "🔊 ฟังเสียง", autoplay=False)
                        st.session_state.audio_played = True
                    except Exception as e:
                        st.caption(f"⚠️ เสียงไม่พร้อม: {e}")
                else:
                    st.caption("🔇 เสียงปิดอยู่")
            with b2:
                if st.button("⏭️ ข้าม", width="stretch", key="skip_btn"):
                    next_word(None)
                    st.rerun()
            with b3:
                audio_txt = "🔇 ปิด" if st.session_state.audio_enabled else "🔊 เปิด"
                if st.button(audio_txt, width="stretch", key="audio_card_btn"):
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

                _reveal_mode_labels = {
                    "always": "👁️ เปิดค้างตลอด",
                    "sync_flip": "🔄 เฉลยพร้อมพลิกการ์ด",
                }
                _mode_keys = list(_reveal_mode_labels.keys())
                if st.session_state.reveal_mode not in _mode_keys:
                    st.session_state.reveal_mode = 'sync_flip'

                with st.expander("⚙️ ตั้งค่าการเฉลย", expanded=False):
                    st.session_state.reveal_mode = st.radio(
                        "โหมดเฉลย", _mode_keys,
                        format_func=lambda k: _reveal_mode_labels[k],
                        index=_mode_keys.index(st.session_state.reveal_mode),
                        horizontal=True, label_visibility="collapsed", key="reveal_mode_radio",
                    )

                if st.session_state.reveal_mode == "always":
                    effective_reveal = True
                else:
                    effective_reveal = st.session_state.card_flipped

                reveal_hint = "🔓 เฉลยแล้ว" if effective_reveal else "🔒 ยังไม่เฉลย (พลิกการ์ดเพื่อดู)"
                st.markdown(f"**คำศัพท์:**  \n:gray[{reveal_hint}]")

                current_word_raw = st.session_state.current_word[word_col] if word_col else st.session_state.current_word['word']
                current_word_text = display_word_text(current_word_raw)
                current_word_spoken = spoken_word_text(current_word_raw)
                pinyin_text = st.session_state.current_word.get(pinyin_col, st.session_state.current_word.get('pinyin', ''))
                meaning_text = st.session_state.current_word.get(trans_th_col, st.session_state.current_word.get('trans_th', ''))

                if effective_reveal:
                    pin_html = str(pinyin_text)
                    mean_html = str(meaning_text)
                else:
                    pin_html = f'<span class="blurred">{pinyin_text}</span>'
                    mean_html = f'<span class="blurred">{meaning_text}</span>'

                st.markdown(
                    f'<ul style="margin:0 0 0 18px; padding:0;">'
                    f'<li>🇨🇳 {current_word_text}</li>'
                    f'<li>📖 {pin_html}</li>'
                    f'<li>🇹🇭 {mean_html}</li>'
                    f'</ul>',
                    unsafe_allow_html=True,
                )

                ex_zh_val = get_example_value(st.session_state.current_word, "zh")
                ex_th_val = get_example_value(st.session_state.current_word, "th")
                ex_en_val = get_example_value(st.session_state.current_word, "en")

                ex_lines = []
                if ex_zh_val:
                    ex_lines.append(f"🇨🇳 {ex_zh_val}")
                if ex_th_val:
                    ex_th_show = ex_th_val if effective_reveal else f'<span class="blurred">{ex_th_val}</span>'
                    ex_lines.append(f"🇹🇭 {ex_th_show}")
                if ex_en_val:
                    ex_en_show = ex_en_val if effective_reveal else f'<span class="blurred">{ex_en_val}</span>'
                    ex_lines.append(f"🇬🇧 {ex_en_show}")

                if ex_lines:
                    st.markdown("**📝 ตัวอย่างประโยค:**")
                    for line in ex_lines:
                        st.markdown(f'<div class="example-box">{line}</div>', unsafe_allow_html=True)

                st.divider()
                st.markdown("**🔠 แปลคำนี้:**")

                if st.button("🤖 MyMemory (แปลทันที)", width="stretch", key="mymemory_card_btn"):
                    with st.spinner("กำลังแปล..."):
                        trans = free_translate(current_word_spoken, "zh-CN", "th")
                    if trans:
                        st.session_state.card_translate_result = f"**{current_word_text}** → {trans}"
                    else:
                        st.session_state.card_translate_result = "⚠️ แปลไม่ได้ ลองใช้ตัวอื่น"
                    st.session_state.card_translate_word = current_word_text
                    st.rerun()

                if st.session_state.card_translate_result and st.session_state.card_translate_word == current_word_text:
                    st.markdown(f'<div class="translate-result-box">{st.session_state.card_translate_result}</div>', unsafe_allow_html=True)

                g_url = get_google_translate_url(current_word_spoken)
                gpt_url = get_chatgpt_translate_url(current_word_spoken)

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    st.link_button("🌍 Google", g_url, width="stretch")
                with btn_c2:
                    st.link_button("🧠 ChatGPT", gpt_url, width="stretch")

                if st.session_state.ai_response and st.session_state.ai_response_word == current_word_text:
                    st.divider()
                    st.markdown(st.session_state.ai_response)

elif active_tab_choice == "🎯 Quiz":
    if filtered_df.empty:
        st.warning("⚠️ ไม่มีคำในเลเวลที่เลือก")
    elif len(filtered_df) < 4:
        st.warning("⚠️ ต้องมีคำอย่างน้อย 4 คำในเลเวลที่เลือก ถึงจะสร้างตัวเลือกให้ได้")
    else:
        st.markdown("### 🎯 Quiz")

        if "quiz_mode" not in st.session_state:
            st.session_state.quiz_mode = "meaning"

        qm1, qm2 = st.columns(2)
        with qm1:
            if st.button("👁️ เห็นคำจีน → เลือกความหมาย", width="stretch",
                         type="primary" if st.session_state.quiz_mode == "meaning" else "secondary"):
                st.session_state.quiz_mode = "meaning"
                st.session_state.quiz_question = None
                st.rerun()
        with qm2:
            if st.button("🔊 ฟังเสียง → เลือกคำ", width="stretch",
                         type="primary" if st.session_state.quiz_mode == "listening" else "secondary"):
                st.session_state.quiz_mode = "listening"
                st.session_state.quiz_question = None
                st.rerun()

        for k, v in [("quiz_question", None), ("quiz_options", None), ("quiz_answered", False),
                     ("quiz_selected", None), ("quiz_correct", None), ("quiz_score_correct", 0),
                     ("quiz_score_total", 0), ("quiz_audio_played", False), ("quiz_auto_advance_pending", False), ("quiz_auto_advance_at", None)]:
            if k not in st.session_state:
                st.session_state[k] = v

        def _new_quiz_question(exclude_id=None):
            target = pick_srs_word(filtered_df, exclude_id=exclude_id)
            distractor_pool = filtered_df[filtered_df["id"] != target["id"]]
            n_distractors = min(3, len(distractor_pool))
            distractors = distractor_pool.sample(n_distractors)
            options = [target] + [distractors.iloc[i] for i in range(len(distractors))]
            random.shuffle(options)
            st.session_state.quiz_question = target
            st.session_state.quiz_options = options
            st.session_state.quiz_answered = False
            st.session_state.quiz_selected = None
            st.session_state.quiz_correct = None
            st.session_state.quiz_audio_played = False
            st.session_state.quiz_auto_advance_pending = False
            st.session_state.quiz_auto_advance_at = None

        if st.session_state.quiz_question is None:
            _new_quiz_question()

        target = st.session_state.quiz_question
        target_word_raw = target[word_col] if word_col else target["word"]
        target_word = display_word_text(target_word_raw)
        target_word_spoken = spoken_word_text(target_word_raw)
        target_meaning = target.get(trans_th_col, target.get("trans_th", ""))
        target_level = target.get("hsk_level_label", target.get("hsk_level", ""))

        if st.session_state.quiz_auto_advance_pending and st.session_state.get("quiz_auto_next", True):
            if st.session_state.quiz_auto_advance_at is not None and time.time() >= st.session_state.quiz_auto_advance_at:
                _new_quiz_question(exclude_id=target.get("id"))
                st.rerun()

        st.divider()
        sc1, sc2 = st.columns(2)
        sc1.metric("✅ ถูก", st.session_state.quiz_score_correct)
        sc2.metric("📊 ทั้งหมด", st.session_state.quiz_score_total)
        st.divider()

        if st.session_state.quiz_mode == "meaning":
            colors = get_hsk_color(target["hsk_level"])
            st.markdown(
                f'<div style="background:linear-gradient({colors["gradient"]});border-radius:20px;'
                f'padding:36px;text-align:center;margin-bottom:16px;">'
                f'<div style="font-size:13px;color:white;opacity:0.8;margin-bottom:8px;">HSK {target_level}</div>'
                f'<div style="font-size:64px;font-weight:800;color:white;">{target_word}</div>'
                f'</div>', unsafe_allow_html=True,
            )
            st.markdown("**เลือกความหมายที่ถูกต้อง:**")
            option_labels = [
                str(opt.get(trans_th_col, opt.get("trans_th", ""))) for opt in st.session_state.quiz_options
            ]
        else:
            st.info(f"HSK {target_level} — กดปุ่มฟังเสียง แล้วเลือกคำจีนที่ได้ยิน")
            try:
                render_audio_player(target_word_spoken, "🔊 ฟังเสียงซ้ำ", autoplay=False)
                st.session_state.quiz_audio_played = True
            except Exception as e:
                st.warning(f"ไม่สามารถโหลดเสียงได้: {e}")
            st.markdown("**เลือกคำจีนที่ได้ยิน:**")
            option_labels = [
                display_word_text(opt[word_col] if word_col else opt["word"]) for opt in st.session_state.quiz_options
            ]

        for i, opt in enumerate(st.session_state.quiz_options):
            is_target = (opt["id"] == target["id"])
            label = option_labels[i]

            btn_type = "secondary"
            suffix = ""
            if st.session_state.quiz_answered:
                if is_target:
                    btn_type = "primary"
                    suffix = " ✅"
                elif st.session_state.quiz_selected == opt["id"]:
                    suffix = " ❌"

            if st.button(f"{label}{suffix}", width="stretch", key=f"quiz_opt_{i}_{opt['id']}",
                         disabled=st.session_state.quiz_answered, type=btn_type):
                st.session_state.quiz_answered = True
                st.session_state.quiz_selected = opt["id"]
                correct = is_target
                st.session_state.quiz_correct = correct
                st.session_state.quiz_score_total += 1
                if correct:
                    st.session_state.quiz_score_correct += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.play_history.append({
                    "เวลา": timestamp,
                    "id": target.get(id_col, target.get('id', '')),
                    "คำจีน": target_word,
                    "พินอิน": target.get(pinyin_col, target.get('pinyin', '')),
                    "คำแปล": target_meaning,
                    "HSK": target_level,
                    "ผล": "✅ จำได้" if correct else "❌ จำไม่ได้",
                    "ผู้เล่น": _current_player_name(),
                    "โหมด": "Quiz",
                })
                # Append history before saving SRS so this answer is persisted
                # in the same Google Sheets update instead of one answer late.
                _update_srs(target["id"], correct=correct)
                st.session_state.quiz_auto_advance_pending = st.session_state.get("quiz_auto_next", True)
                if st.session_state.quiz_auto_advance_pending:
                    st.session_state.quiz_auto_advance_at = time.time() + st.session_state.get("quiz_auto_next_seconds", 2)
                st.rerun()

        if st.session_state.quiz_answered:
            if st.session_state.quiz_correct:
                st.success(f"✅ ถูกต้อง! {target_word} = {target_meaning}")
            else:
                st.error(f"❌ ยังไม่ถูก — {target_word} แปลว่า {target_meaning}")
                st.markdown("**📋 เฉลยของทุกตัวเลือก:**")
                for i, opt in enumerate(st.session_state.quiz_options):
                    opt_word = display_word_text(opt[word_col] if word_col else opt["word"])
                    opt_meaning = opt.get(trans_th_col, opt.get("trans_th", ""))
                    is_target = (opt["id"] == target["id"])
                    is_selected = (st.session_state.quiz_selected == opt["id"])
                    mark = "✅" if is_target else ("❌" if is_selected else "▫️")
                    st.markdown(f'<div class="example-box">{mark} <b>{opt_word}</b> = {opt_meaning}</div>', unsafe_allow_html=True)

            if st.session_state.quiz_auto_advance_pending and st.session_state.get("quiz_auto_next", True):
                st.caption("⏳ กำลังไปข้อถัดไปอัตโนมัติ...")
                if st_autorefresh is not None:
                    st_autorefresh(interval=300, key="quiz_wait_tick")
                if st.button("⏭️ ข้ามการรอ / ข้อถัดไปทันที", width="stretch", key="quiz_skip_wait_btn"):
                    _new_quiz_question(exclude_id=target.get("id"))
                    st.rerun()
            else:
                if st.button("➡️ ข้อถัดไป", width="stretch", key="quiz_next_btn"):
                    _new_quiz_question(exclude_id=target.get("id"))
                    st.rerun()


elif active_tab_choice == "📖 คำศัพท์":
    if not filtered_df.empty:
        st.markdown("### 🔍 ค้นหาคำศัพท์")

        if "vocab_search_clear_flag" not in st.session_state:
            st.session_state.vocab_search_clear_flag = False

        vocab_search_col1, vocab_search_col2 = st.columns([0.75, 0.25])
        with vocab_search_col2:
            if st.button("✕ ล้าง", width="stretch", key="vocab_search_clear"):
                st.session_state.vocab_search_clear_flag = True
                st.session_state.vocab_search_prefill = None
                st.rerun()

        with vocab_search_col1:
            if st.session_state.vocab_search_clear_flag:
                st.session_state.vocab_search_clear_flag = False
                vocab_query = st.text_input(
                    "ค้นหา",
                    value="",
                    placeholder="พิมพ์ id / คำจีน / pinyin (ไม่ต้องมีวรรณยุกต์) / แปล ...",
                    label_visibility="collapsed",
                    key="vocab_search_input"
                )
            elif st.session_state.vocab_search_prefill:
                prefill_val = st.session_state.vocab_search_prefill
                st.session_state.vocab_search_prefill = None
                vocab_query = st.text_input(
                    "ค้นหา",
                    value=prefill_val,
                    placeholder="พิมพ์ id / คำจีน / pinyin (ไม่ต้องมีวรรณยุกต์) / แปล ...",
                    label_visibility="collapsed",
                    key="vocab_search_input"
                )
            else:
                vocab_query = st.text_input(
                    "ค้นหา",
                    placeholder="พิมพ์ id / คำจีน / pinyin (ไม่ต้องมีวรรณยุกต์) / แปล ...",
                    label_visibility="collapsed",
                    key="vocab_search_input"
                )

        vocab_display_df = filtered_df.copy()

        if vocab_query and vocab_query.strip():
            vq = vocab_query.strip()
            vq_toneless = strip_tones(vq)
            vmask = pd.Series([False] * len(vocab_display_df), index=vocab_display_df.index)

            for col_key, actual_col in st.session_state.col_mapping.items():
                if actual_col and actual_col in vocab_display_df.columns:
                    if col_key == "pinyin":
                        vmask = vmask | (vocab_display_df['_pinyin_toneless'].str.contains(vq_toneless, na=False, regex=False))
                    else:
                        vmask = vmask | (vocab_display_df[actual_col].astype(str).str.contains(vq, case=False, na=False, regex=False))

            vocab_display_df = vocab_display_df[vmask]
            st.caption(f"🔎 พบ **{len(vocab_display_df)}** คำ จาก {len(filtered_df)} คำทั้งหมด")
        else:
            st.caption(f"📚 แสดงทั้งหมด **{len(vocab_display_df)}** คำ")

        st.divider()

        items_per_page = 100
        total_items = len(vocab_display_df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        if "vocab_page" not in st.session_state:
            st.session_state.vocab_page = 1

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
                if st.button("⬅️ ก่อนหน้า", width="stretch", key="prev_page"):
                    st.session_state.vocab_page = max(1, st.session_state.vocab_page - 1)
                    st.rerun()
            with col_pg2:
                if st.button("ถัดไป ➡️", width="stretch", key="next_page"):
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
            page_df = vocab_display_df.iloc[start_idx:end_idx].copy()

            disp_cols = []
            col_order = ["id", "hsk_level", "word", "pinyin", "pos_en", "pos_th", "pos_zh", "trans_th", "trans_en", "example_zh", "example_th", "example_en"]
            for col_key in col_order:
                if st.session_state.col_display_toggle.get(col_key) and st.session_state.col_mapping.get(col_key):
                    disp_cols.append(st.session_state.col_mapping[col_key])
            show_cols = disp_cols if disp_cols else [c for c in page_df.columns if c != '_pinyin_toneless']

            display_page_df = page_df
            if "hsk_level" in show_cols and "hsk_level_label" in page_df.columns:
                display_page_df = page_df.copy()
                display_page_df["hsk_level"] = display_page_df["hsk_level_label"]

            selection = st.dataframe(
                display_page_df[show_cols],
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="vocab_df_selection"
            )

            selected_rows = selection.selection.get("rows", [])
            if selected_rows:
                sel_idx = selected_rows[0]
                sel_row = page_df.iloc[sel_idx]
                clicked_word = str(sel_row[word_col]) if word_col and word_col in sel_row.index else ""
                if clicked_word and clicked_word != st.session_state.get("vocab_clicked_word", ""):
                    st.session_state["vocab_clicked_word"] = clicked_word
                    st.session_state["vocab_translate_from_click"] = clicked_word

            st.divider()

            st.markdown("### 🌐 แปลคำศัพท์")

            clicked_from_table = st.session_state.get("vocab_translate_from_click", "")

            tr_input_col1, tr_input_col2 = st.columns([0.55, 0.45])

            with tr_input_col1:
                if word_col and word_col in page_df.columns:
                    word_options = ["(พิมพ์เอง)"] + page_df[word_col].dropna().astype(str).tolist()
                else:
                    word_options = ["(พิมพ์เอง)"]

                select_key = f"vocab_translate_select_{clicked_from_table}"
                default_idx = 0
                if clicked_from_table and clicked_from_table in word_options:
                    default_idx = word_options.index(clicked_from_table)

                selected_word_option = st.selectbox(
                    "เลือกคำที่ต้องการแปล",
                    word_options,
                    index=default_idx,
                    key=select_key
                )

            with tr_input_col2:
                if selected_word_option == "(พิมพ์เอง)":
                    custom_word = st.text_input("พิมพ์คำจีน", placeholder="例: 你好", key="vocab_translate_custom", label_visibility="collapsed")
                    word_to_translate = custom_word.strip() if custom_word else ""
                else:
                    word_to_translate = selected_word_option
                    st.markdown(f"<div style='padding:8px 0; font-size:28px; text-align:center;'>{word_to_translate}</div>", unsafe_allow_html=True)

            # ✅ OPTIMIZATION Task 2: ลบ auto-translate ตอนคลิกแถว
            # เดิมมีโค้ดตรงนี้:
            # if clicked_from_table and st.session_state.get("vocab_auto_translate_done") != clicked_from_table:
            #     with st.spinner("กำลังแปล..."):
            #         trans = free_translate(clicked_from_table, "zh-CN", "th")
            #     ...
            # ตรงนี้ลบเสร็จแล้ว ไม่มีการยิง network ทันที ผู้ใช้ต้องกดปุ่ม MyMemory เอง

            if word_to_translate:
                tr_b1, tr_b2, tr_b3 = st.columns(3)

                with tr_b1:
                    if st.button("🤖 MyMemory", width="stretch", key="vocab_mymemory_btn"):
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
                    st.link_button("🌍 Google", g_url, width="stretch")

                with tr_b3:
                    gpt_url = get_chatgpt_translate_url(word_to_translate)
                    st.link_button("🧠 ChatGPT", gpt_url, width="stretch")

                if st.session_state.get("vocab_translate_result") and st.session_state.get("vocab_translate_target") == word_to_translate:
                    st.markdown(f'<div class="translate-result-box">{st.session_state["vocab_translate_result"]}</div>', unsafe_allow_html=True)

            st.divider()

            csv = vocab_display_df[show_cols].to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด CSV (ที่กรองแล้ว)", csv, 'hsk_list.csv', 'text/csv')

        else:
            st.info("ไม่พบคำที่ตรงกับการค้นหา")
    else:
        st.info("ไม่มีคำในเลเวลที่เลือก")

elif active_tab_choice == "📋 ประวัติ":
    def _empty_board():
        return pd.DataFrame(columns=["อันดับ", "ผู้เล่น", "ตอบถูก", "ตอบทั้งหมด", "ความแม่นยำ (%)"])

    def _add_rank(board):
        if board.empty:
            return _empty_board()
        board = board.sort_values(
            by=["ตอบถูก", "ความแม่นยำ (%)", "ตอบทั้งหมด"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
        medals = ["🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else str(i + 1) for i in range(len(board))]
        board.insert(0, "อันดับ", medals)
        return board

    def _public_players(players_dict):
        return {
            name: p for name, p in players_dict.items()
            if name != "Guest" and p.get("leaderboard_visible", True) and p.get("total", 0) > 0
        }

    def _build_board_from_players(players_dict):
        rows = []
        for name, p in _public_players(players_dict).items():
            total = int(p.get("total", 0) or 0)
            correct = int(p.get("correct", 0) or 0)
            rows.append({
                "ผู้เล่น": name,
                "ตอบถูก": correct,
                "ตอบทั้งหมด": total,
                "ความแม่นยำ (%)": round(correct / total * 100, 1) if total else 0.0,
            })
        return _add_rank(pd.DataFrame(rows)) if rows else _empty_board()

    def _build_mode_board(players_dict, mode):
        rows = []
        for name, p in _public_players(players_dict).items():
            mode_history = [h for h in p.get("history", []) if h.get("โหมด") == mode]
            if not mode_history:
                continue
            total = len(mode_history)
            correct = sum(h.get("ผล") == "✅ จำได้" for h in mode_history)
            rows.append({
                "ผู้เล่น": name,
                "ตอบถูก": correct,
                "ตอบทั้งหมด": total,
                "ความแม่นยำ (%)": round(correct / total * 100, 1) if total else 0.0,
            })
        return _add_rank(pd.DataFrame(rows)) if rows else _empty_board()

    me = _current_player_name()
    players = st.session_state.get("players_data", {})
    my_profile = dict(players.get(me, {}))
    my_profile.setdefault("leaderboard_visible", True)
    my_profile.setdefault("history", st.session_state.get("play_history", []))
    players[me] = my_profile
    st.session_state.players_data = players

    history_sync_marker = (
        me,
        int(my_profile.get("correct", 0) or 0),
        int(my_profile.get("total", 0) or 0),
        len(st.session_state.get("play_history", [])),
    )
    if st.session_state.get("_history_sync_marker") != history_sync_marker:
        _save_progress(force_gsheet_sync=True)
        st.session_state._history_sync_marker = history_sync_marker

    st.markdown("### 🔐 ความเป็นส่วนตัวของคะแนน")
    if me == "Guest":
        st.info("Guest จะไม่ถูกนำชื่อหรือคะแนนขึ้น Leaderboard")
    else:
        if st.session_state.get("_visibility_widget_player") != me:
            st.session_state["leaderboard_visibility_toggle"] = my_profile.get("leaderboard_visible", True)
            st.session_state["_visibility_widget_player"] = me
        visibility = st.toggle(
            "อนุญาตให้เพื่อนเห็นชื่อและคะแนนของฉันบน Leaderboard",
            key="leaderboard_visibility_toggle",
        )
        if visibility != my_profile.get("leaderboard_visible", True):
            my_profile["leaderboard_visible"] = visibility
            players[me] = my_profile
            st.session_state.players_data = players
            _save_progress(force_gsheet_sync=True)
            st.toast("แสดงคะแนนแล้ว" if visibility else "ซ่อนคะแนนของคุณแล้ว")
            st.rerun()
        if not visibility:
            st.caption("คะแนนและชื่อของคุณยังเก็บไว้ตามปกติ แต่คนอื่นจะไม่เห็นบน Leaderboard")

    if "show_leaderboard_panel" not in st.session_state:
        st.session_state.show_leaderboard_panel = True

    lb_col1, lb_col2, lb_col3 = st.columns([0.52, 0.25, 0.23])
    with lb_col1:
        st.markdown("### 🏆 Leaderboard")
    with lb_col2:
        if st.button("🔄 รีเฟรช", width="stretch", key="refresh_leaderboard_btn"):
            _fresh = _load_progress()
            st.session_state.players_data = _fresh.get("players", {})
            st.session_state.srs_data = _fresh.get("srs", {})
            st.session_state._active_player_context = None
            _activate_player_context(force=True)
            st.rerun()
    with lb_col3:
        panel_label = "✕ ปิดตาราง" if st.session_state.show_leaderboard_panel else "🏆 เปิดตาราง"
        if st.button(panel_label, width="stretch", key="toggle_leaderboard_panel_btn"):
            st.session_state.show_leaderboard_panel = not st.session_state.show_leaderboard_panel
            st.rerun()

    if st.session_state.show_leaderboard_panel:
        board_all = _build_board_from_players(st.session_state.players_data)
        if not board_all.empty:
            board_all_display = board_all.copy()
            board_all_display["ผู้เล่น"] = board_all_display["ผู้เล่น"].apply(lambda n: f"⭐ {n} (คุณ)" if n == me else n)
            st.dataframe(board_all_display, width="stretch", hide_index=True)
            st.caption("เรียงจากจำนวนตอบถูกมากที่สุด แล้วใช้ความแม่นยำเป็นตัวตัดสิน")
        else:
            st.info("ยังไม่มีผู้เล่นที่เปิดเผยคะแนนบน Leaderboard")

        lb_left, lb_right = st.columns(2)
        with lb_left:
            st.markdown("#### 🎴 Flashcard")
            board_fc = _build_mode_board(st.session_state.players_data, "Flashcard")
            if not board_fc.empty:
                st.dataframe(board_fc, width="stretch", hide_index=True)
            else:
                st.caption("ยังไม่มีข้อมูล Flashcard")
        with lb_right:
            st.markdown("#### 🎯 Quiz")
            board_qz = _build_mode_board(st.session_state.players_data, "Quiz")
            if not board_qz.empty:
                st.dataframe(board_qz, width="stretch", hide_index=True)
            else:
                st.caption("ยังไม่มีข้อมูล Quiz")

    st.divider()
    st.markdown("### 📋 ประวัติของฉัน")
    history = st.session_state.get("play_history", [])
    if not history:
        st.info("ยังไม่มีประวัติ")
    else:
        hist_df_all = pd.DataFrame(history[::-1])
        hist_mode = st.selectbox("กรองประวัติตามโหมด", ["ทั้งหมด", "Flashcard", "Quiz"], index=0, key="history_mode")
        if hist_mode == "ทั้งหมด":
            hist_df = hist_df_all
        else:
            hist_df = hist_df_all[hist_df_all.get("โหมด") == hist_mode]

        total, ok, no = len(hist_df), (hist_df["ผล"] == "✅ จำได้").sum(), (hist_df["ผล"] == "❌ จำไม่ได้").sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📊 ทั้งหมด", total)
        m2.metric("✅ จำได้", ok)
        m3.metric("❌ จำไม่ได้", no)
        m4.metric("🎯 %", f"{int(ok/total*100) if total else 0}%")

        st.divider()
        display_hist_df = hist_df.drop(columns=["ผู้เล่น"], errors="ignore")
        st.dataframe(display_hist_df, width="stretch", hide_index=True, height=400)

        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            if st.button("🗑️ ล้าง", width="stretch", key="clear_btn"):
                if hist_mode == "ทั้งหมด":
                    st.session_state.play_history = []
                else:
                    st.session_state.play_history = [h for h in st.session_state.play_history if h.get("โหมด") != hist_mode]
                _save_progress(force_gsheet_sync=True)
                st.rerun()
        with c2:
            csv = display_hist_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ ดาวน์โหลด (ผลกรองแล้ว)", csv, 'history.csv', 'text/csv', width="stretch")
