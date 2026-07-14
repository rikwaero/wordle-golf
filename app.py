import re
import os
import json
import time
import hashlib
import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# ----------------------------------------------------
# 1. CONFIGURATION & STYLING
# ----------------------------------------------------
st.set_page_config(page_title="Dan and Rik's Wordle Golf", page_icon="⛳")

st.markdown("""
<style>
    /* ── Base font ── */
    html, body, [class*="css"], table, th, td {
        font-family: 'Segoe UI', Arial, sans-serif !important;
        font-size: 14px !important;
    }

    /* ── Page cards ── */
    .metric-card {
        background: linear-gradient(135deg, #1a2744 0%, #0f1a2e 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #22c55e;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
    }
    .playoff-card {
        background: linear-gradient(135deg, #450a0a 0%, #180000 100%);
        border-left: 5px solid #ef4444;
    }
    .winner-banner {
        background: linear-gradient(90deg, #b45309 0%, #f59e0b 50%, #b45309 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        color: white;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 25px;
    }
    .commentary-box {
        background-color: #1a2744;
        border: 1px solid #2d3f6b;
        border-radius: 8px;
        padding: 15px;
        font-style: italic;
        color: #e2e8f0;
        line-height: 1.6;
    }

/* ── Tooltip ── */
.wordle-tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
    font-weight: bold;
    text-align: center;
    width: 100%;
}
.wordle-tooltip .wordle-tooltiptext {
    visibility: hidden;
    width: 180px;
    background-color: #1a2744;
    color: #fff;
    text-align: center;
    border: 1px solid #2d3f6b;
    border-radius: 6px;
    padding: 10px;
    position: absolute;
    z-index: 99999;
    bottom: 135%;
    left: 50%;
    margin-left: -90px;
    opacity: 0;
    transition: opacity 0.2s;
    font-family: monospace;
    font-size: 13px !important;
    line-height: 1.4;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
}
.wordle-tooltip:hover .wordle-tooltiptext {
    visibility: visible !important;
    opacity: 1 !important;
}

/* ── Scorecard table ── */
.scorecard-outer {
    overflow: visible;
    position: relative;
    margin-top: 15px;
}
.scorecard-wrap {
    overflow-x: auto;
    margin-bottom: 0;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.scorecard-wrap table {
    width: 100%;
    border-collapse: collapse;
    background-color: #ffffff;
    border-radius: 10px;
    overflow: visible;
    display: table;
}
.scorecard-wrap th {
    background-color: #1e3a5f;
    color: #ffffff;
    font-weight: 700;
    font-size: 14px !important;
    padding: 10px 10px !important;
    text-align: center !important;
    border: 1px solid #cbd5e1;
    min-width: 42px;
}
.scorecard-wrap td {
    padding: 9px 8px !important;
    text-align: center !important;
    border: 1px solid #cbd5e1;
    color: #1e293b;
    font-size: 14px !important;
    min-width: 42px;
    background-color: #ffffff;
}
.scorecard-wrap td:first-child,
.scorecard-wrap th:first-child {
    text-align: left !important;
    min-width: 90px;
    background-color: #1e3a5f;
    color: #ffffff;
    position: sticky;
    left: 0;
    z-index: 10;
    font-size: 14px !important;
}
.scorecard-wrap tr.score-row:hover td {
    background-color: #f0f7ff;
}
.scorecard-wrap tr.score-row:hover td:first-child {
    background-color: #163154;
}
/* ── Running-total sub-row ── */
.scorecard-wrap tr.thru-row td {
    background-color: #f8fafc !important;
    border-top: 1px dashed #94a3b8 !important;
    color: #475569;
    font-size: 13px !important;
    padding: 5px 8px !important;
}
.scorecard-wrap tr.thru-row td:first-child {
    color: #e2e8f0;
    font-style: italic;
    font-size: 13px !important;
    background-color: #1e3a5f !important;
}
/* ── PGA score badges ── */
.badge {
    display: inline-block;
    width: 28px;
    height: 28px;
    line-height: 28px;
    border-radius: 50%;
    font-weight: 700;
    font-size: 13px !important;
    text-align: center;
}
.badge-eagle     { background: #1d4ed8; color: #fff; border-radius: 50%; }
.badge-birdie    { background: transparent; color: #1e293b;
                   border: 2px solid #dc2626; border-radius: 50%; }
.badge-par       { color: #1e293b; }
.badge-bogey     { background: transparent; color: #1e293b;
                   border: 2px solid #64748b; border-radius: 4px; }
.badge-double    { background: transparent; color: #dc2626;
                   border: 2px solid #dc2626; border-radius: 4px; }
.badge-triple    { background: #fef2f2; color: #991b1b;
                   border: 2px solid #dc2626; border-radius: 4px; }
.badge-albatross { background: #7c3aed; color: #fff; border-radius: 50%; }

/* ── Running total colours ── */
.run-under { color: #16a34a; font-weight: 600; }
.run-over  { color: #dc2626; font-weight: 600; }
.run-even  { color: #1e293b; font-weight: 600; }
.run-blank { color: #94a3b8; }

/* ── Section label ── */
.section-label {
    color: #1e3a5f;
    font-weight: 700;
    font-size: 15px !important;
    margin: 20px 0 6px 0;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-left: 4px solid #f59e0b;
    padding-left: 8px;
}

    /* ── Mobile ── */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
            min-width: 100% !important;
        }
        .scorecard-wrap th,
        .scorecard-wrap td { font-size: 12px !important; padding: 6px 4px !important; min-width: 30px !important; }
        .scorecard-wrap td:first-child,
        .scorecard-wrap th:first-child { min-width: 65px !important; }
        .badge { width:22px; height:22px; line-height:22px; font-size:11px !important; }
        .wordle-tooltip .wordle-tooltiptext {
            width: 140px !important; font-size: 11px !important;
            left: 0% !important; margin-left: -70px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


st.title("⛳ Dan and Rik's Wordle Golf")
st.write("Welcome to the clubhouse. Drop your scores, track the board, and catch the live broadcast.")

# ----------------------------------------------------
# CONSTANTS
# ----------------------------------------------------
SCORE_MAP = {"1": -3, "2": -2, "3": -1, "4": 0, "5": 1, "6": 2, "X": 3, "x": 3}
SCORE_NAMES = {
    -3: "🚀 ALBATROSS!",
    -2: "🦅 EAGLE!!",
    -1: "🐦 BIRDIE!",
     0: "Par",
     1: "⚠️ Bogey",
     2: "❌ Double Bogey",
     3: "💥 TRIPLE BOGEY (FAIL)"
}
PLAYERS = ["Dan", "Rik"]

# ----------------------------------------------------
# 2. SUPABASE CONNECTION
# ----------------------------------------------------
@st.cache_resource
def get_supabase_client():
    """Creates a Supabase client."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ----------------------------------------------------
# 3. BROWSER TOKEN
# ----------------------------------------------------
def get_browser_token():
    """
    Generates a stable browser token using Streamlit's supported API.
    Falls back gracefully if context headers are unavailable.
    """
    try:
        user_agent = st.context.headers.get("User-Agent", "default")
        forwarded_for = st.context.headers.get("X-Forwarded-For", "local")
        raw = f"{user_agent}_{forwarded_for}"
        return hashlib.md5(raw.encode()).hexdigest()
    except Exception:
        return "fallback_local_token"

# ----------------------------------------------------
# 4. DATABASE FUNCTIONS
# ----------------------------------------------------
def load_players():
    """Loads player profiles and passwords."""
    try:
        db = get_supabase_client()
        result = db.table("players").select("*").execute()
        profiles = [r["name"] for r in result.data]
        passwords = {r["name"]: r["password"] for r in result.data}
        return profiles, passwords
    except Exception as e:
        st.error(f"Error loading players: {e}")
        return ["Dan", "Rik"], {"Dan": "YouareDan", "Rik": "YouareRik"}


def load_sessions():
    """Loads device sessions."""
    try:
        db = get_supabase_client()
        result = db.table("sessions").select("*").execute()
        return {r["token"]: r["player"] for r in result.data}
    except Exception:
        return {}


def save_session(token, player):
    """Saves or updates a device session."""
    try:
        db = get_supabase_client()
        db.table("sessions").upsert(
            {
                "token": token,
                "player": player,
                "timestamp": datetime.now().isoformat()
            },
            on_conflict="token"
        ).execute()
    except Exception as e:
        st.error(f"Error saving session: {e}")


def delete_session(token):
    """Removes a device session."""
    try:
        db = get_supabase_client()
        db.table("sessions").delete().eq("token", token).execute()
    except Exception as e:
        st.error(f"Error deleting session: {e}")


def load_all_scores():
    """
    Loads all scores.
    Returns {wordle_num(int): {player: {strokes, summary, grid, timestamp}}}
    """
    try:
        db = get_supabase_client()
        result = db.table("scores").select("*").execute()
        scores = {}
        for r in result.data:
            w_num = int(r["wordle_num"])
            player = r["player"]
            if w_num not in scores:
                scores[w_num] = {}
            scores[w_num][player] = {
                "strokes": int(r["strokes"]),
                "summary": r.get("summary", ""),
                "grid": r.get("grid", ""),
                "timestamp": r.get("timestamp", "")
            }
        return scores
    except Exception as e:
        st.error(f"Error loading scores: {e}")
        return {}


def save_score(wordle_num, player, strokes, summary, grid):
    """Saves or updates a single score entry."""
    try:
        db = get_supabase_client()
        db.table("scores").upsert(
            {
                "wordle_num": wordle_num,
                "player": player,
                "strokes": strokes,
                "summary": summary,
                "grid": grid,
                "timestamp": datetime.now().isoformat()
            },
            on_conflict="wordle_num,player"
        ).execute()
    except Exception as e:
        st.error(f"❌ Save failed: {e}")
        st.exception(e)


def delete_score(wordle_num, player):
    """Deletes a score entry."""
    try:
        db = get_supabase_client()
        db.table("scores").delete().eq(
            "wordle_num", wordle_num
        ).eq(
            "player", player
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting score: {e}")
        return False


def load_history():
    """Loads archived round history."""
    try:
        db = get_supabase_client()
        result = db.table("history").select("*").order("round_start").execute()
        history = []
        for r in result.data:
            entry = {
                "round_start": int(r["round_start"]),
                "date_archived": r["date_archived"],
                "winner": r["winner"],
                "summary": r["summary"],
                "scorecard": json.loads(r["scorecard_json"]) if r["scorecard_json"] else {}
            }
            history.append(entry)
        return history
    except Exception as e:
        st.error(f"Error loading history: {e}")
        return []


def save_history_entry(round_start, winner, summary, scorecard_dict):
    """Saves a completed round to history."""
    try:
        db = get_supabase_client()
        db.table("history").insert({
            "round_start": round_start,
            "date_archived": datetime.now().isoformat(),
            "winner": winner,
            "summary": summary,
            "scorecard_json": json.dumps(scorecard_dict)
        }).execute()
    except Exception as e:
        st.error(f"Error saving history: {e}")


def archive_round_scores(round_start):
    """Deletes all scores belonging to a completed round."""
    try:
        db = get_supabase_client()
        result = db.table("scores").select("wordle_num").execute()
        nums_to_delete = []
        for r in result.data:
            w_num = int(r["wordle_num"])
            r_start, _ = get_round_start_and_hole(w_num)
            if r_start == round_start:
                nums_to_delete.append(w_num)

        if nums_to_delete:
            db.table("scores").delete().in_(
                "wordle_num", nums_to_delete
            ).execute()
    except Exception as e:
        st.error(f"Error archiving round scores: {e}")

# ----------------------------------------------------
# 5. ROUND LOGIC ENGINE
# ----------------------------------------------------
def get_round_start_and_hole(wordle_num):
    """
    Determines the round start number and hole number for a given Wordle number.
    """
    wordle_num = int(wordle_num)
    for candidate in range(wordle_num, wordle_num - 25, -1):
        c_str = str(candidate)
        last_digit = int(c_str[-1])
        second_last_digit = int(c_str[-2]) if len(c_str) >= 2 else 0
        if last_digit == 1 and second_last_digit % 2 == 0:
            round_start = candidate
            hole_num = wordle_num - round_start + 1
            return round_start, hole_num
    return wordle_num, 1

def is_practice_hole(hole_num):
    """Returns True if the hole is a practice hole (19 or 20)."""
    return hole_num in (19, 20)

def get_all_rounds_from_scores(scores_dict):
    """
    Given the full scores dict, returns a sorted list of unique round start numbers.
    """
    round_starts = set()
    for w_num in scores_dict:
        try:
            r_start, _ = get_round_start_and_hole(int(w_num))
            round_starts.add(r_start)
        except (ValueError, TypeError):
            continue
    return sorted(round_starts)

def get_scores_for_round(scores_dict, round_start):
    """
    Filters scores_dict to only include entries belonging to a specific round.
    Returns {hole_num: {player: data}} for holes 1-20 of that round.
    """
    round_start = int(round_start)
    round_scores = {}
    round_end = round_start + 19

    for w_num_raw, player_data in scores_dict.items():
        try:
            w_num = int(w_num_raw)
        except (ValueError, TypeError):
            continue

        r_start, hole_num = get_round_start_and_hole(w_num)

        if r_start == round_start and 1 <= hole_num <= 20:
            if hole_num not in round_scores:
                round_scores[hole_num] = {}
            round_scores[hole_num].update(player_data)

        if w_num > round_end and w_num <= round_start + 29:
            playoff_hole = w_num - round_start + 1
            if playoff_hole not in round_scores:
                round_scores[playoff_hole] = {}
            round_scores[playoff_hole].update(player_data)

    return round_scores

def parse_wordle_text(text):
    """
    Parses a Wordle share snippet and returns the puzzle number
    and a structured pattern data dictionary.
    """
    clean_text = text.replace(",", "").replace(" ", "").replace("\xa0", "").strip()
    match = re.search(r"Wordle\s*(\d+)[^\d]*([1-6Xx])[/*]6", clean_text)
    if not match:
        return None, None

    w_num = int(match.group(1))
    score_char = match.group(2)
    strokes = SCORE_MAP.get(score_char, 0)

    greens = text.count("🟩")
    yellows = text.count("🟨")
    misses = text.count("⬛") + text.count("⬜")

    grid_lines = []
    for line in text.split("\n"):
        if any(emoji in line for emoji in ["🟩", "🟨", "⬛", "⬜"]):
            grid_lines.append(line.strip())
    grid_visual = "\n".join(grid_lines)

    pattern_data = {
        "strokes": strokes,
        "summary": f"🟩 {greens} | 🟨 {yellows} | 🟥 {misses}",
        "grid": grid_visual
    }

    return w_num, pattern_data

@st.cache_data(ttl=3600)
def get_wordle_answer(wordle_num):
    """
    Fetches the correct Wordle answer for a given puzzle number.
    Returns None cleanly if answer cannot be found.
    """
    try:
        url = "https://wordfinder.yourdictionary.com/wordle/answers/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        full_text = soup.get_text(separator=" ")

        pattern1 = rf"#\s*{wordle_num}\s*[:\-–]\s*([A-Za-z]{{5}})"
        match = re.search(pattern1, full_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        pattern2 = rf"[Ww]ordle\s*{wordle_num}\s+([A-Za-z]{{5}})"
        match = re.search(pattern2, full_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        pattern3 = rf"\b{wordle_num}\b\s+([A-Za-z]{{5}})\b"
        match = re.search(pattern3, full_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        return None

    except Exception:
        return None

def safe_answer_display(answer):
    """
    Validates a Wordle answer before displaying it.
    Filters out debug strings, error messages, and invalid values.
    """
    if not answer:
        return None
    if str(answer).startswith("DEBUG:"):
        return None
    if str(answer).startswith("ERROR:"):
        return None
    if not re.match(r"^[A-Za-z]{5}$", str(answer)):
        return None
    return answer.upper()

# ----------------------------------------------------
# 6. SESSION STATE INITIALIZATION
# ----------------------------------------------------
if "post_msg" not in st.session_state:
    st.session_state.post_msg = ""
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "scores" not in st.session_state:
    st.session_state.scores = load_all_scores()
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "player_profiles" not in st.session_state:
    profiles, passwords = load_players()
    st.session_state.player_profiles = profiles
    st.session_state.player_passwords = passwords
if "device_sessions" not in st.session_state:
    st.session_state.device_sessions = load_sessions()
if "clear_paste" not in st.session_state:
    st.session_state.clear_paste = False

# Restore login from device session
browser_token = get_browser_token()
if (st.session_state.current_user is None
        and browser_token in st.session_state.device_sessions):
    st.session_state.current_user = st.session_state.device_sessions[browser_token]

# ----------------------------------------------------
# 7. SIDEBAR: LOGIN
# ----------------------------------------------------
st.sidebar.header("🔐 Pro Tour Player Login")

if st.session_state.current_user is None:
    login_name = st.sidebar.selectbox(
        "Select Your Profile Name",
        st.session_state.player_profiles
    )
    login_pwd = st.sidebar.text_input(
        "Enter Private Password",
        type="password"
    )
    remember_me = st.sidebar.checkbox("Keep me logged in on this device", value=True)

    if st.sidebar.button("🚪 Enter Clubhouse"):
        correct_pwd = st.session_state.player_passwords.get(login_name)
        if correct_pwd and login_pwd == correct_pwd:
            st.session_state.current_user = login_name
            if remember_me:
                st.session_state.device_sessions[browser_token] = login_name
                save_session(browser_token, login_name)
            st.session_state.post_msg = f"🔓 Welcome back, {login_name}!"
            st.rerun()
        else:
            st.sidebar.error("Invalid passcode. Please try again.")
else:
    st.sidebar.markdown(f"⛳ Logged in as: **{st.session_state.current_user}**")

    if st.sidebar.button("🔒 Log Out & Forget Device"):
        if browser_token in st.session_state.device_sessions:
            del st.session_state.device_sessions[browser_token]
            delete_session(browser_token)
        st.session_state.current_user = None
        st.rerun()

    st.sidebar.write("---")

    # ----------------------------------------------------
    # PROFILE ADMINISTRATION
    # ----------------------------------------------------
    with st.sidebar.expander("🛠️ Profile Administration"):
        st.write("Register a new competitor profile.")
        new_player_name = st.text_input(
            "Add New Player Name",
            placeholder="e.g., Rory"
        ).strip()
        new_player_pwd = st.text_input(
            "Assign Starter Password",
            type="password",
            placeholder="e.g., pass123"
        )

        if st.button("➕ Add Player Profile"):
            if new_player_name and new_player_pwd:
                if new_player_name not in st.session_state.player_profiles:
                    st.session_state.player_profiles.append(new_player_name)
                    st.session_state.player_passwords[new_player_name] = new_player_pwd
                    try:
                        ws = get_worksheet("players")
                        sheets_operation_with_retry(
                            lambda: ws.append_row([new_player_name, new_player_pwd])
                        )
                    except Exception as e:
                        st.error(f"Error saving player: {e}")
                    st.session_state.post_msg = f"✅ Created profile for {new_player_name}!"
                    st.rerun()
                else:
                    st.error("That profile name already exists.")
            else:
                st.error("Fill out both fields to create a profile.")

    # ----------------------------------------------------
    # SCORECARD CORRECTIONS
    # ----------------------------------------------------
    with st.sidebar.expander("🗑️ Scorecard Corrections"):
        st.write("Delete a score from your card by entering the Wordle number.")
        target_wordle_num = st.number_input(
            "Wordle # to Delete",
            min_value=1,
            max_value=99999,
            value=1841,
            step=1
        )

        if st.button("❌ Delete This Score"):
            my_name = st.session_state.current_user
            w_num_int = int(target_wordle_num)
            if (w_num_int in st.session_state.scores
                    and my_name in st.session_state.scores[w_num_int]):
                del st.session_state.scores[w_num_int][my_name]
                if not st.session_state.scores[w_num_int]:
                    del st.session_state.scores[w_num_int]
                deleted = delete_score(w_num_int, my_name)
                if deleted:
                    st.session_state.post_msg = (
                        f"🗑️ Deleted Wordle #{w_num_int} from your card!"
                    )
                    st.rerun()
            else:
                st.error("No score found for that Wordle number on your card.")



    # ----------------------------------------------------
    # BULK HISTORICAL IMPORT
    # ----------------------------------------------------
    st.sidebar.write("---")
    st.sidebar.header("📂 Bulk Historical Import")
    with st.sidebar.expander("📬 Dump Chat Thread Data Here"):
        st.write(
            f"Extracts all Wordle results onto "
            f"**{st.session_state.current_user}**'s card."
        )
        bulk_text = st.sidebar.text_area(
            "Paste Chat Text Content",
            placeholder="Wordle 1,816 3/6*...",
            height=150
        )

        if st.sidebar.button("⚡ Parse & Save All"):
            if not bulk_text:
                st.sidebar.error("Paste text before compiling!")
            else:
                my_name = st.session_state.current_user
                clean_bulk = bulk_text.replace(",", "")
                matches = re.findall(
                    r"Wordle\s*(\d[\d\s]*)\s+([1-6Xx])[/*]6",
                    clean_bulk
                )

                if not matches:
                    st.sidebar.error("No valid Wordle blocks found in that text.")
                else:
                    success_count = 0
                    for w_num_raw, score_char in matches:
                        try:
                            w_num = int(w_num_raw.replace(" ", "").strip())
                            strokes = SCORE_MAP.get(score_char, 0)

                            pattern_data = {
                                "strokes": strokes,
                                "summary": "Bulk Import",
                                "grid": ""
                            }

                            if w_num not in st.session_state.scores:
                                st.session_state.scores[w_num] = {}
                            st.session_state.scores[w_num][my_name] = pattern_data

                            save_score(w_num, my_name, strokes, "Bulk Import", "")
                            success_count += 1
                        except Exception:
                            continue

                    if success_count > 0:
                        st.session_state.post_msg = (
                            f"⚡ Bulk import successful! Saved {success_count} scores."
                        )
                        st.rerun()
                    else:
                        st.sidebar.error("No scores could be extracted.")

# ----------------------------------------------------
# 8. POST MESSAGE DISPLAY
# ----------------------------------------------------
if st.session_state.post_msg:
    st.success(st.session_state.post_msg)
    st.session_state.post_msg = ""

# ----------------------------------------------------
# 8b. SCORE ENTRY (MAIN PAGE)
# ----------------------------------------------------
st.write("---")
st.header("🎯 Post Your Score")

if st.session_state.current_user is None:
    st.info("🔐 Log in using the sidebar to post your score!")
else:
    st.markdown(f"Posting as: **{st.session_state.current_user}**")

    tab1, tab2 = st.tabs(["📋 Paste Full Result", "✏️ Manual Entry"])

    with tab1:
        st.write("**Paste your full Wordle share text below**")
        st.caption("📱 Mobile: Tap the box below, then long-press inside to paste")

        paste_key = (
            "wordle_paste_main_clear"
            if st.session_state.clear_paste
            else "wordle_paste_main"
        )
        wordle_paste = st.text_area(
            "Wordle Result",
            placeholder="Wordle 1,845 4/6*\n\n⬛🟨⬛⬛⬛\n🟨⬛⬛🟩⬛\n🟩🟩🟩🟩🟩",
            height=200,
            key=paste_key,
            label_visibility="collapsed"
        )

        if st.button("🚀 Post Score", use_container_width=True):
            if not wordle_paste:
                st.error("Please paste your Wordle snippet first!")
            else:
                w_num, pattern_data = parse_wordle_text(wordle_paste)
                if w_num is not None:
                    my_name = st.session_state.current_user
                    is_update = (
                        w_num in st.session_state.scores
                        and my_name in st.session_state.scores[w_num]
                    )

                    if w_num not in st.session_state.scores:
                        st.session_state.scores[w_num] = {}
                    st.session_state.scores[w_num][my_name] = pattern_data

                    save_score(
                        w_num,
                        my_name,
                        pattern_data["strokes"],
                        pattern_data["summary"],
                        pattern_data["grid"]
                    )

                    _, hole = get_round_start_and_hole(w_num)
                    shoutout = SCORE_NAMES.get(pattern_data["strokes"], "Score logged")

                    if is_update:
                        st.session_state.post_msg = (
                            f"🔄 Updated Wordle #{w_num} (Hole {hole}): {shoutout}"
                        )
                    else:
                        st.session_state.post_msg = (
                            f"✅ Logged Wordle #{w_num} (Hole {hole}): {shoutout}"
                        )

                    st.session_state.clear_paste = not st.session_state.clear_paste
                    st.rerun()
                else:
                    st.error("Could not parse Wordle text. Check your snippet!")

    with tab2:
        st.write("**Enter your result manually**")

        col1, col2 = st.columns(2)
        with col1:
            manual_wordle_num = st.number_input(
                "Wordle Number",
                min_value=1,
                max_value=99999,
                value=1841,
                step=1
            )
        with col2:
            manual_score = st.selectbox(
                "Guesses",
                options=["1", "2", "3", "4", "5", "6", "X"],
                index=3,
                format_func=lambda x: {
                    "1": "1 🚀 Hole in One!",
                    "2": "2 🦅 Eagle",
                    "3": "3 🐦 Birdie",
                    "4": "4 ⛳ Par",
                    "5": "5 ⚠️ Bogey",
                    "6": "6 ❌ Double Bogey",
                    "X": "X 💥 Failed"
                }[x]
            )

        st.caption("📱 Paste just the emoji grid below (optional but recommended)")
        st.caption("In Wordle: Share → Copy → paste ONLY the coloured squares here")

        grid_key = (
            "grid_main_clear"
            if st.session_state.clear_paste
            else "grid_main"
        )
        manual_grid = st.text_area(
            "Emoji Grid",
            placeholder="⬛🟨⬛⬛⬛\n🟨⬛⬛🟩⬛\n🟩🟩🟩🟩🟩",
            height=150,
            key=grid_key
        )

        if st.button(
            "🚀 Post Score",
            use_container_width=True,
            key="post_manual_main"
        ):
            my_name = st.session_state.current_user
            w_num = int(manual_wordle_num)
            strokes = SCORE_MAP.get(manual_score, 0)

            # Parse grid if provided
            grid_lines = []
            if manual_grid:
                for line in manual_grid.split("\n"):
                    if any(emoji in line for emoji in ["🟩", "🟨", "⬛", "⬜"]):
                        grid_lines.append(line.strip())
            grid_visual = "\n".join(grid_lines)

            # Build summary from grid if available
            if grid_visual:
                greens = manual_grid.count("🟩")
                yellows = manual_grid.count("🟨")
                misses = manual_grid.count("⬛") + manual_grid.count("⬜")
                summary = f"🟩 {greens} | 🟨 {yellows} | 🟥 {misses}"
            else:
                summary = f"Manual entry: {manual_score}/6"

            is_update = (
                w_num in st.session_state.scores
                and my_name in st.session_state.scores[w_num]
            )

            pattern_data = {
                "strokes": strokes,
                "summary": summary,
                "grid": grid_visual
            }

            if w_num not in st.session_state.scores:
                st.session_state.scores[w_num] = {}
            st.session_state.scores[w_num][my_name] = pattern_data

            save_score(w_num, my_name, strokes, summary, grid_visual)

            _, hole = get_round_start_and_hole(w_num)
            shoutout = SCORE_NAMES.get(strokes, "Score logged")

            if is_update:
                st.session_state.post_msg = (
                    f"🔄 Updated Wordle #{w_num} (Hole {hole}): {shoutout}"
                )
            else:
                st.session_state.post_msg = (
                    f"✅ Logged Wordle #{w_num} (Hole {hole}): {shoutout}"
                )

            st.session_state.clear_paste = not st.session_state.clear_paste
            st.rerun()
# ----------------------------------------------------
# 9. DETERMINE ACTIVE ROUND
# ----------------------------------------------------
def get_active_round(scores_dict, players):
    """
    Returns the most recent round start where both players
    have at least one score entry.
    """
    clean_scores = {}
    for k, v in scores_dict.items():
        try:
            clean_scores[int(k)] = v
        except (ValueError, TypeError):
            continue

    all_rounds = get_all_rounds_from_scores(clean_scores)

    for round_start in reversed(all_rounds):
        round_scores = get_scores_for_round(clean_scores, round_start)
        players_in_round = set()
        for hole_data in round_scores.values():
            players_in_round.update(hole_data.keys())
        if all(p in players_in_round for p in players):
            return round_start

    if all_rounds:
        return all_rounds[-1]
    return None

# Ensure all score keys are integers
all_scores = {}
for k, v in st.session_state.scores.items():
    try:
        all_scores[int(k)] = v
    except (ValueError, TypeError):
        continue

all_round_starts = get_all_rounds_from_scores(all_scores)
active_round_start = get_active_round(all_scores, PLAYERS)

# ----------------------------------------------------
# 10. MAIN SCOREBOARD
# ----------------------------------------------------
st.header("🏆 Live Standings")

if active_round_start is None:
    st.info("⛳ No scores yet. Log in and post your first Wordle result!")
else:
    active_round_end = active_round_start + 17
    st.subheader(f"Current Round: Wordle {active_round_start} – {active_round_end}")

    round_scores = get_scores_for_round(all_scores, active_round_start)

    p1, p2 = PLAYERS[0], PLAYERS[1]

    # Compute regulation totals (holes 1-18, both players synced)
    reg_completed_holes = []
    reg_totals = {p1: 0, p2: 0}

    for h in range(1, 19):
        h_data = round_scores.get(h, {})
        s1_data = h_data.get(p1)
        s2_data = h_data.get(p2)
        s1 = s1_data["strokes"] if isinstance(s1_data, dict) else s1_data
        s2 = s2_data["strokes"] if isinstance(s2_data, dict) else s2_data
        if s1 is not None and s2 is not None:
            reg_completed_holes.append(h)
            reg_totals[p1] += s1
            reg_totals[p2] += s2

    regulation_finished = len(reg_completed_holes)
    regulation_complete = regulation_finished == 18

    # Playoff sudden death logic
    playoff_active = False
    playoff_winner = None
    current_playoff_hole = 19

    if regulation_complete and reg_totals[p1] == reg_totals[p2]:
        playoff_active = True
        while True:
            h_data = round_scores.get(current_playoff_hole, {})
            s1_data = h_data.get(p1)
            s2_data = h_data.get(p2)
            s1_p = s1_data["strokes"] if isinstance(s1_data, dict) else s1_data
            s2_p = s2_data["strokes"] if isinstance(s2_data, dict) else s2_data

            if s1_p is not None and s2_p is not None:
                if s1_p < s2_p:
                    playoff_winner = p1
                    break
                elif s2_p < s1_p:
                    playoff_winner = p2
                    break
                current_playoff_hole += 1
            else:
                break

    # ----------------------------------------------------
    # 11. CHAMPIONSHIP RESOLUTIONS
    # ----------------------------------------------------
    round_ended = False
    winner_name = None
    summary_msg = ""

    if playoff_winner:
        round_ended = True
        winner_name = playoff_winner
        loser_name = p1 if playoff_winner == p2 else p2
        summary_msg = f"{winner_name} defeated {loser_name} in Sudden Death Playoffs."
        st.balloons()
        st.markdown(
            f'<div class="winner-banner">'
            f'🏆 SUDDEN DEATH CHAMPION: {winner_name.upper()}! 🏆'
            f'</div>',
            unsafe_allow_html=True
        )
        st.success(f"👏 **Pure ice in your veins, {winner_name}!**")

    elif regulation_complete and not playoff_active:
        if reg_totals[p1] != reg_totals[p2]:
            round_ended = True
            winner_name = p1 if reg_totals[p1] < reg_totals[p2] else p2
            loser_name = p2 if winner_name == p1 else p1
            summary_msg = (
                f"{winner_name} ({reg_totals[winner_name]:+}) "
                f"def. {loser_name} ({reg_totals[loser_name]:+})"
            )
            st.balloons()
            st.markdown(
                f'<div class="winner-banner">'
                f'👑 TOURNAMENT CHAMPION: {winner_name.upper()}! 👑'
                f'</div>',
                unsafe_allow_html=True
            )
            st.success(f"🏆 **Put on the green jacket, {winner_name}!**")

    # ----------------------------------------------------
    # 12. STANDINGS CARDS
    # ----------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        diff = reg_totals[p1] - reg_totals[p2]
        if diff < 0:
            leader_str = f"⚡ **{p1}** leads by **{abs(diff)}** strokes (synced holes)"
        elif diff > 0:
            leader_str = f"⚡ **{p2}** leads by **{abs(diff)}** strokes (synced holes)"
        else:
            if reg_completed_holes:
                leader_str = "⚖️ **All Square!** Level on verified entries."
            else:
                leader_str = "⏳ Waiting for synced scores..."

        card_style = "metric-card playoff-card" if playoff_active else "metric-card"
        st.markdown(
            f'<div class="{card_style}">'
            f'<h4 style="margin:0; color:white;">Synced Leader</h4>'
            f'<p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{leader_str}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    with col2:
        if playoff_active:
            status_text = f"🚨 PLAYOFFS ACTIVE (Hole {current_playoff_hole})"
        else:
            status_text = f"⛳ Regulation: {regulation_finished}/18 Holes Synced"
        st.markdown(
            f'<div class="metric-card" style="border-left-color: #3b82f6;">'
            f'<h4 style="margin:0; color:white;">Round Status</h4>'
            f'<p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{status_text}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ----------------------------------------------------
    # 13. SCORECARD TABLE
    # ----------------------------------------------------
    st.subheader("📊 Tournament Scoreboard")
    st.caption("💡 Hover over any score to see the colour grid!")

    front_9_holes   = list(range(1, 10))
    back_9_holes    = list(range(10, 19))

    playoff_holes_display = []
    if playoff_active or playoff_winner:
        playoff_holes_display = sorted([
            h for h in round_scores.keys() if h > 18
        ])

    display_holes = front_9_holes + back_9_holes + playoff_holes_display

    # ── helpers ──────────────────────────────────────────
    def score_badge(strokes, grid, hole, both_have, active_round_start):
        """Return a tooltip-wrapped PGA-style badge for a raw hole score."""
        # Badge style by score
        if   strokes <= -3: css, label = "badge-albatross", f"{strokes:+}"
        elif strokes == -2: css, label = "badge-eagle",     f"{strokes:+}"
        elif strokes == -1: css, label = "badge-birdie",    f"{strokes:+}"
        elif strokes ==  0: css, label = "badge-par",       "E"
        elif strokes ==  1: css, label = "badge-bogey",     f"{strokes:+}"
        elif strokes ==  2: css, label = "badge-double",    f"{strokes:+}"
        else:               css, label = "badge-triple",    f"{strokes:+}"

        badge_html = f"<span class='badge {css}'>{label}</span>"

        # Tooltip content
        clean_grid = (
            str(grid).replace("\\n", "<br>").replace("\n", "<br>").strip()
        )
        if both_have:
            wordle_num_for_hole = active_round_start + hole - 1
            raw_answer = get_wordle_answer(wordle_num_for_hole)
            answer = safe_answer_display(raw_answer)
            answer_line = (
                f"<b style='color:#22c55e; font-size:14px; "
                f"letter-spacing:3px;'>🟩 {answer} 🟩</b><br><br>"
                if answer else ""
            )
        else:
            answer_line = (
                "<i style='color:#94a3b8;'>Revealed when "
                "both players submit</i><br><br>"
            )

        return (
            '<div class="wordle-tooltip">'
            + badge_html
            + '<span class="wordle-tooltiptext">'
            + f"<b>Hole {hole}</b><br><br>"
            + answer_line
            + clean_grid
            + "</span></div>"
        )

    def run_span(value, blank=False):
        """Return a coloured running-total span."""
        if blank:
            return "<span class='run-blank'>—</span>"
        if value < 0:
            return f"<span class='run-under'>{value:+}</span>"
        if value > 0:
            return f"<span class='run-over'>{value:+}</span>"
        return "<span class='run-even'>E</span>"

    def fmt_total(value):
        if value < 0:  return f"<span class='run-under'>{value:+}</span>"
        if value > 0:  return f"<span class='run-over'>{value:+}</span>"
        return "<span class='run-even'>E</span>"

    # ── Collect raw strokes ───────────────────────────────
    raw_strokes   = {p: {} for p in PLAYERS}   # hole -> int|None
    scorecard_totals = {
        p: {"total": 0, "front_9": 0, "back_9": 0, "synced": 0}
        for p in PLAYERS
    }

    for h in display_holes:
        h_data     = round_scores.get(h, {})
        both_have  = all(p in h_data for p in PLAYERS)
        for player in PLAYERS:
            res = h_data.get(player)
            if res is None:
                raw_strokes[player][h] = None
            else:
                strokes = res["strokes"] if isinstance(res, dict) else int(res)
                raw_strokes[player][h] = strokes
                if both_have and h <= 18:
                    scorecard_totals[player]["total"]   += strokes
                    scorecard_totals[player]["synced"]  += 1
                    if 1 <= h <= 9:
                        scorecard_totals[player]["front_9"] += strokes
                    else:
                        scorecard_totals[player]["back_9"]  += strokes

    total_synced = scorecard_totals[p1]["synced"]

    # ── Build HTML cells ──────────────────────────────────
    hole_cells = {p: {} for p in PLAYERS}
    thru_cells = {p: {} for p in PLAYERS}

    for player in PLAYERS:
        running = 0
        for h in display_holes:
            h_data    = round_scores.get(h, {})
            both_have = all(p in h_data for p in PLAYERS)
            res       = h_data.get(player)

            if res is None:
                hole_cells[player][h] = "<span class='run-blank'>⏳</span>"
                thru_cells[player][h] = run_span(0, blank=True)
            else:
                strokes  = raw_strokes[player][h]
                grid     = res.get("grid", "") if isinstance(res, dict) else ""
                hole_cells[player][h] = score_badge(
                    strokes, grid, h, both_have, active_round_start
                )
                if both_have and h <= 18:
                    running += strokes
                    thru_cells[player][h] = run_span(running)
                else:
                    thru_cells[player][h] = run_span(0, blank=True)

    # ── Table builder ─────────────────────────────────────
    def build_scorecard(holes, title):
        is_front    = title == "Front 9"
        is_back     = title == "Back 9"
        is_playoff  = title == "⚡ Playoffs"

        out = f"<p class='section-label'>{title}</p>"
        out += "<div class='scorecard-outer'><div class='scorecard-wrap'><table>"

        # ── Header row ──
        out += "<thead><tr>"
        out += "<th>Player</th>"
        if is_front:
            out += (
                "<th style='background:#b45309; color:#fff;'>"
                f"Total ({total_synced}/18)</th>"
                "<th>F 1–9</th>"
            )
        elif is_back:
            out += "<th>B 10–18</th>"
        elif is_playoff:
            out += "<th style='background:#7f1d1d; color:#fca5a5;'>PO</th>"

        for h in holes:
            lbl = f"{h}🚨" if h > 18 else str(h)
            out += f"<th>{lbl}</th>"
        out += "</tr></thead>"

        # ── Player rows ──
        out += "<tbody>"
        for player in PLAYERS:
            tot   = scorecard_totals[player]

            # Score row
            out += f"<tr class='score-row'>"
            out += f"<td><b>{player}</b></td>"

            if is_front:
                out += (
                    f"<td style='background:rgba(180,83,9,0.2); font-weight:700;'>"
                    f"{fmt_total(tot['total'])}</td>"
                    f"<td>{fmt_total(tot['front_9'])}</td>"
                )
            elif is_back:
                out += f"<td>{fmt_total(tot['back_9'])}</td>"
            elif is_playoff:
                out += "<td>—</td>"

            for h in holes:
                out += f"<td>{hole_cells[player].get(h, run_span(0,blank=True))}</td>"
            out += "</tr>"

            # Thru row
            out += "<tr class='thru-row'>"
            out += "<td></td>"

            if is_front:
                # running total after hole 9
                run_f9 = 0
                for hh in range(1, 10):
                    hd = round_scores.get(hh, {})
                    if (raw_strokes[player].get(hh) is not None
                            and all(p in hd for p in PLAYERS)):
                        run_f9 += raw_strokes[player][hh]
                out += (
                    f"<td style='background:rgba(180,83,9,0.1);'>"
                    f"{run_span(run_f9)}</td>"
                    "<td></td>"
                )
            elif is_back:
                out += f"<td>{run_span(tot['total'])}</td>"
            elif is_playoff:
                out += "<td></td>"

            for h in holes:
                out += f"<td>{thru_cells[player].get(h, run_span(0,blank=True))}</td>"
            out += "</tr>"

        out += "</tbody></table></div></div>"
        return out

    # ── Render ────────────────────────────────────────────
    st.markdown(build_scorecard(front_9_holes,  "Front 9"),   unsafe_allow_html=True)
    st.markdown(build_scorecard(back_9_holes,   "Back 9"),    unsafe_allow_html=True)
    if playoff_holes_display:
        st.markdown(build_scorecard(playoff_holes_display, "⚡ Playoffs"), unsafe_allow_html=True)


    # ----------------------------------------------------
    # 14. ARCHIVE BUTTON
    # ----------------------------------------------------
    if round_ended and st.session_state.current_user is not None:
        if st.button("📦 Archive This Round & Start Fresh"):
            scorecard_snapshot = {}
            for h in display_holes:
                h_data = round_scores.get(h, {})
                scorecard_snapshot[str(h)] = {}
                for player in PLAYERS:
                    res = h_data.get(player)
                    if res is not None:
                        scorecard_snapshot[str(h)][player] = res

            save_history_entry(
                active_round_start,
                winner_name,
                summary_msg,
                scorecard_snapshot
            )
            archive_round_scores(active_round_start)

            st.session_state.scores = load_all_scores()
            st.session_state.history = load_history()
            st.session_state.post_msg = "📦 Round archived successfully!"
            st.rerun()

# ----------------------------------------------------
# 15. BROADCAST COMMENTARY BOOTH
# ----------------------------------------------------
st.write("---")
st.header("🎙️ Live Broadcast Booth")

if active_round_start is not None:
    if st.button("🎤 Get Live Commentary"):

        # ── Build match context for the LLM ──
        def get_best_hole(player):
            best_h, best_s = None, 99
            for h in reg_completed_holes:
                h_data = round_scores.get(h, {})
                res = h_data.get(player)
                if res is not None:
                    s = res["strokes"] if isinstance(res, dict) else int(res)
                    if s < best_s:
                        best_s, best_h = s, h
            return best_h, best_s

        def get_worst_hole(player):
            worst_h, worst_s = None, -99
            for h in reg_completed_holes:
                h_data = round_scores.get(h, {})
                res = h_data.get(player)
                if res is not None:
                    s = res["strokes"] if isinstance(res, dict) else int(res)
                    if s > worst_s:
                        worst_s, worst_h = s, h
            return worst_h, worst_s

        def count_birdies_or_better(player):
            count = 0
            for h in reg_completed_holes:
                h_data = round_scores.get(h, {})
                res = h_data.get(player)
                if res is not None:
                    s = res["strokes"] if isinstance(res, dict) else int(res)
                    if s <= -1:
                        count += 1
            return count

        def recent_trend(player, last_n=3):
            recent = reg_completed_holes[-last_n:] if len(reg_completed_holes) >= last_n else reg_completed_holes
            total = 0
            for h in recent:
                h_data = round_scores.get(h, {})
                res = h_data.get(player)
                if res is not None:
                    s = res["strokes"] if isinstance(res, dict) else int(res)
                    total += s
            return total

        def score_name(s):
            return {
                -3: "albatross", -2: "eagle", -1: "birdie",
                 0: "par", 1: "bogey", 2: "double bogey", 3: "triple bogey"
            }.get(s, f"{s:+}")

        def fmt_standing(val):
            if val < 0: return f"{abs(val)}-under"
            if val > 0: return f"{val}-over"
            return "even par"

        holes_played   = len(reg_completed_holes)
        diff           = reg_totals[p1] - reg_totals[p2]
        leader         = p2 if diff > 0 else p1
        chaser         = p1 if diff > 0 else p2
        lead_amt       = abs(diff)
        p1_best_h,  p1_best_s  = get_best_hole(p1)
        p2_best_h,  p2_best_s  = get_best_hole(p2)
        p1_worst_h, p1_worst_s = get_worst_hole(p1)
        p2_worst_h, p2_worst_s = get_worst_hole(p2)
        p1_birdies = count_birdies_or_better(p1)
        p2_birdies = count_birdies_or_better(p2)
        p1_trend   = recent_trend(p1)
        p2_trend   = recent_trend(p2)

        # Build hole-by-hole summary string
        hole_summary_lines = []
        for h in reg_completed_holes:
            h_data = round_scores.get(h, {})
            p1_res = h_data.get(p1)
            p2_res = h_data.get(p2)
            p1_s = (p1_res["strokes"] if isinstance(p1_res, dict) else int(p1_res)) if p1_res else None
            p2_s = (p2_res["strokes"] if isinstance(p2_res, dict) else int(p2_res)) if p2_res else None
            if p1_s is not None and p2_s is not None:
                hole_summary_lines.append(
                    f"  Hole {h}: {p1}={score_name(p1_s)} ({p1_s:+}), "
                    f"{p2}={score_name(p2_s)} ({p2_s:+})"
                )

        hole_summary = "\n".join(hole_summary_lines) if hole_summary_lines else "No holes completed yet."

        # Build the full context prompt
        if playoff_active:
            match_status = f"SUDDEN DEATH PLAYOFFS active at hole {current_playoff_hole}"
        elif regulation_complete:
            match_status = "Regulation complete"
        else:
            match_status = f"Regulation in progress, {holes_played}/18 holes completed"

        context = f"""
You are an enthusiastic, witty golf commentator covering a head-to-head Wordle Golf match.
In Wordle Golf, players solve the daily Wordle puzzle. Their score is based on guesses:
1 guess = albatross (-3), 2 = eagle (-2), 3 = birdie (-1), 4 = par (0), 5 = bogey (+1), 6 = double bogey (+2), fail = triple bogey (+3).
Lower scores are better, just like real golf.

Match status: {match_status}
Players: {p1} vs {p2}
Holes played: {holes_played}/18

Current standings:
- {p1}: {fmt_standing(reg_totals[p1])} (total: {reg_totals[p1]:+})
- {p2}: {fmt_standing(reg_totals[p2])} (total: {reg_totals[p2]:+})
{"- " + leader + " leads by " + str(lead_amt) + " stroke(s)" if diff != 0 else "- All square"}

Hole by hole results so far:
{hole_summary}

Key stats:
- {p1}: {p1_birdies} birdie(s) or better, best hole was hole {p1_best_h} ({score_name(p1_best_s) if p1_best_h else "N/A"}), worst hole was hole {p1_worst_h} ({score_name(p1_worst_s) if p1_worst_h else "N/A"})
- {p2}: {p2_birdies} birdie(s) or better, best hole was hole {p2_best_h} ({score_name(p2_best_s) if p2_best_h else "N/A"}), worst hole was hole {p2_worst_h} ({score_name(p2_worst_s) if p2_worst_h else "N/A"})
- Recent form (last 3 holes): {p1}={fmt_standing(p1_trend)}, {p2}={fmt_standing(p2_trend)}
{"- PLAYOFF: Sudden death is active!" if playoff_active else ""}

Please write 4-5 paragraphs of lively, dramatic golf commentary about this match.
Mention specific holes, momentum shifts, standout scores, and the current standings.
Use golf broadcasting language and make it entertaining. Do not use bullet points.
Write it as if you are speaking live on air.
"""

        try:
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
            with st.spinner("🎙️ Our commentator is live on air..."):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an enthusiastic live golf commentator. "
                                "Be dramatic, use golf terminology, and keep it entertaining."
                            )
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    max_tokens=600,
                    temperature=0.85
                )
            commentary = response.choices[0].message.content.strip()
            st.markdown(
                f'<div class="commentary-box">{commentary}</div>',
                unsafe_allow_html=True
            )

        except Exception as e:
            st.error(f"Commentary unavailable: {e}")

# ----------------------------------------------------
# 16. HISTORICAL ARCHIVE
# ----------------------------------------------------
st.write("---")
st.header("📜 Historical Tournament Records")

if not st.session_state.history:
    st.caption("No completed rounds archived yet.")
else:
    for i, entry in enumerate(reversed(st.session_state.history)):
        round_start = entry["round_start"]
        round_end = round_start + 17
        label = (
            f"Round {round_start}–{round_end} | "
            f"🏆 {entry['winner']} | {entry['summary']} | "
            f"📅 {entry['date_archived']}"
        )
        with st.expander(label):
            scorecard = entry.get("scorecard", {})
            if not scorecard:
                st.caption("No scorecard data available.")
            else:
                hist_holes   = sorted([int(h) for h in scorecard.keys()])
                hist_display = [h for h in hist_holes if h <= 18]
                hist_playoff = [h for h in hist_holes if h > 18]
                hist_display += hist_playoff

                # Collect raw strokes and totals per player
                h_raw  = {p: {} for p in PLAYERS}
                h_tots = {p: {"total": 0, "front": 0, "back": 0} for p in PLAYERS}

                for h in hist_display:
                    h_data = scorecard.get(str(h), {})
                    for player in PLAYERS:
                        res = h_data.get(player)
                        if res is not None:
                            s = res["strokes"] if isinstance(res, dict) else int(res)
                            h_raw[player][h] = s
                            if h <= 18:
                                h_tots[player]["total"] += s
                                if 1 <= h <= 9:
                                    h_tots[player]["front"] += s
                                else:
                                    h_tots[player]["back"] += s
                        else:
                            h_raw[player][h] = None

                # Build score and running total cells per player
                h_cells = {p: {} for p in PLAYERS}
                t_cells = {p: {} for p in PLAYERS}

                for player in PLAYERS:
                    running = 0
                    for h in hist_display:
                        h_data = scorecard.get(str(h), {})
                        res    = h_data.get(player)

                        if res is None:
                            h_cells[player][h] = "<span class='run-blank'>—</span>"
                            t_cells[player][h] = "<span class='run-blank'>—</span>"
                        else:
                            s       = h_raw[player][h]
                            grid    = res.get("grid", "") if isinstance(res, dict) else ""
                            clean_g = str(grid).replace("\\n", "<br>").replace("\n", "<br>").strip()

                            wordle_num_for_hole = round_start + h - 1
                            raw_answer = get_wordle_answer(wordle_num_for_hole)
                            answer     = safe_answer_display(raw_answer)
                            ans_line   = (
                                f"<b style='color:#22c55e; font-size:14px; "
                                f"letter-spacing:3px;'>🟩 {answer} 🟩</b><br><br>"
                                if answer else ""
                            )

                            # Badge style
                            if   s <= -3: css, lbl = "badge-albatross", f"{s:+}"
                            elif s == -2: css, lbl = "badge-eagle",     f"{s:+}"
                            elif s == -1: css, lbl = "badge-birdie",    f"{s:+}"
                            elif s ==  0: css, lbl = "badge-par",       "E"
                            elif s ==  1: css, lbl = "badge-bogey",     f"{s:+}"
                            elif s ==  2: css, lbl = "badge-double",    f"{s:+}"
                            else:         css, lbl = "badge-triple",    f"{s:+}"

                            h_cells[player][h] = (
                                '<div class="wordle-tooltip">'
                                f"<span class='badge {css}'>{lbl}</span>"
                                '<span class="wordle-tooltiptext">'
                                f"<b>Hole {h}</b><br><br>"
                                + ans_line + clean_g +
                                "</span></div>"
                            )

                            if h <= 18:
                                running += s
                                t_cells[player][h] = run_span(running)
                            else:
                                t_cells[player][h] = run_span(0, blank=True)

                # Build table
                ht  = "<div class='scorecard-outer'><div class='scorecard-wrap'>"
                ht += "<table><thead><tr>"
                ht += "<th>Player</th>"
                ht += "<th style='background:#b45309; color:#fff;'>Total</th>"
                ht += "<th>F 1–9</th>"
                ht += "<th>B 10–18</th>"
                for h in hist_display:
                    ht += f"<th>{h}{'🚨' if h > 18 else ''}</th>"
                ht += "</tr></thead><tbody>"

                for player in PLAYERS:
                    t = h_tots[player]

                    # Score row
                    ht += f"<tr class='score-row'><td><b>{player}</b></td>"
                    ht += (
                        f"<td class='total-col'>"
                        f"{fmt_total(t['total'])}</td>"
                        f"<td>{fmt_total(t['front'])}</td>"
                        f"<td>{fmt_total(t['back'])}</td>"
                    )
                    for h in hist_display:
                        ht += f"<td>{h_cells[player].get(h, '<span class=run-blank>—</span>')}</td>"
                    ht += "</tr>"

                    # Thru row
                    ht += "<tr class='thru-row'><td></td>"
                    ht += "<td class='total-col'></td>"
                    ht += "<td></td><td></td>"
                    for h in hist_display:
                        ht += f"<td>{t_cells[player].get(h, '<span class=run-blank>—</span>')}</td>"
                    ht += "</tr>"

                ht += "</tbody></table></div></div>"
                st.markdown(ht, unsafe_allow_html=True)
