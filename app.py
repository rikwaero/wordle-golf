import re
import os
import json
import time
import hashlib
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------
# 1. CONFIGURATION & STYLING
# ----------------------------------------------------
st.set_page_config(page_title="Dan and Rik's Wordle Golf", page_icon="⛳")

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #22c55e;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .playoff-card {
        background: linear-gradient(135deg, #450a0a 0%, #180000 100%);
        border-left: 5px solid #ef4444;
    }
    .winner-banner {
        background: linear-gradient(90deg, #d97706 0%, #f59e0b 50%, #d97706 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        color: white;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 25px;
    }
    .commentary-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px;
        font-style: italic;
        color: #e2e8f0;
        line-height: 1.6;
    }
    .wordle-tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
        font-weight: bold;
        color: #22c55e;
        text-align: center;
        width: 100%;
    }
    .wordle-tooltip .wordle-tooltiptext {
        visibility: hidden;
        width: 180px;
        background-color: #1e293b;
        color: #fff;
        text-align: center;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 999;
        bottom: 135%;
        left: 50%;
        margin-left: -90px;
        opacity: 0;
        transition: opacity 0.2s;
        font-family: monospace;
        font-size: 13px;
        line-height: 1.4;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
    }
    .wordle-tooltip:hover .wordle-tooltiptext {
        visibility: visible !important;
        opacity: 1 !important;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        background-color: #0f172a;
        border-radius: 8px;
        overflow-x: auto;
        display: block;
    }
    th, td {
        padding: 10px 12px !important;
        text-align: center !important;
        border: 1px solid #1e293b;
        color: #e2e8f0;
        min-width: 45px;
    }
    th {
        background-color: #1e293b;
        color: #f8fafc;
        font-weight: bold;
        font-size: 13px;
    }
    td:first-child, th:first-child {
        text-align: left !important;
        min-width: 120px;
        background-color: #111827;
        position: sticky;
        left: 0;
        z-index: 10;
    }
    tr:hover {
        background-color: #1e293b;
    }
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
            min-width: 100% !important;
        }
        table {
            font-size: 11px !important;
        }
        th, td {
            padding: 6px 4px !important;
            min-width: 30px !important;
        }
        td:first-child, th:first-child {
            min-width: 70px !important;
        }
        .wordle-tooltip .wordle-tooltiptext {
            width: 140px !important;
            font-size: 11px !important;
            left: 0% !important;
            margin-left: -70px !important;
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
# 2. GOOGLE SHEETS CONNECTION
# ----------------------------------------------------
@st.cache_resource(ttl=300)
def get_spreadsheet():
    """
    Creates a Google Sheets connection cached for 5 minutes.
    TTL ensures credentials are refreshed regularly.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(credentials)
    return client.open_by_url(st.secrets["sheet"]["url"])

def get_worksheet(tab_name):
    """Gets a specific worksheet tab by name."""
    return get_spreadsheet().worksheet(tab_name)

def sheets_operation_with_retry(operation, max_retries=3):
    """
    Wraps a Google Sheets operation with exponential backoff retry.
    Handles rate limiting (429) and transient errors gracefully.
    """
    for attempt in range(max_retries):
        try:
            return operation()
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429:
                wait_time = (2 ** attempt)
                time.sleep(wait_time)
            else:
                raise
        except Exception:
            raise
    raise Exception("Google Sheets: Max retries exceeded. Please try again.")

# ----------------------------------------------------
# 3. BROWSER TOKEN (replaces broken private Streamlit API)
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
    """Loads player profiles and passwords from the players tab."""
    try:
        ws = get_worksheet("players")
        records = sheets_operation_with_retry(ws.get_all_records)
        profiles = [r["name"] for r in records]
        passwords = {r["name"]: r["password"] for r in records}
        return profiles, passwords
    except Exception as e:
        st.error(f"Error loading players: {e}")
        return ["Dan", "Rik"], {"Dan": "YouareDan", "Rik": "YouareRik"}

def load_sessions():
    """Loads device sessions from the sessions tab."""
    try:
        ws = get_worksheet("sessions")
        records = sheets_operation_with_retry(ws.get_all_records)
        return {r["token"]: r["player"] for r in records}
    except Exception:
        return {}

def save_session(token, player):
    """Saves a device session to the sessions tab."""
    try:
        ws = get_worksheet("sessions")
        records = sheets_operation_with_retry(ws.get_all_records)
        tokens = [r["token"] for r in records]
        if token in tokens:
            row_idx = tokens.index(token) + 2
            sheets_operation_with_retry(
                lambda: ws.update(
                    f"A{row_idx}:C{row_idx}",
                    [[token, player, datetime.now().isoformat()]]
                )
            )
        else:
            sheets_operation_with_retry(
                lambda: ws.append_row([token, player, datetime.now().isoformat()])
            )
    except Exception as e:
        st.error(f"Error saving session: {e}")

def delete_session(token):
    """Removes a device session from the sessions tab."""
    try:
        ws = get_worksheet("sessions")
        records = sheets_operation_with_retry(ws.get_all_records)
        for i, r in enumerate(records):
            if r["token"] == token:
                sheets_operation_with_retry(lambda: ws.delete_rows(i + 2))
                break
    except Exception as e:
        st.error(f"Error deleting session: {e}")

def load_all_scores():
    """
    Loads all scores from the scores tab.
    Returns a dict keyed by wordle_num (int), then player.
    {wordle_num(int): {player: {strokes, summary, grid, timestamp}}}
    """
    try:
        ws = get_worksheet("scores")
        records = sheets_operation_with_retry(ws.get_all_records)
        scores = {}
        for r in records:
            try:
                w_num = int(r["wordle_num"])
            except (ValueError, TypeError):
                continue
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
    """Saves or updates a single score entry in the scores tab."""
    try:
        ws = get_worksheet("scores")
        records = sheets_operation_with_retry(ws.get_all_records)
        timestamp = datetime.now().isoformat()

        for i, r in enumerate(records):
            if int(r["wordle_num"]) == wordle_num and r["player"] == player:
                row_idx = i + 2
                sheets_operation_with_retry(
                    lambda: ws.update(
                        f"A{row_idx}:F{row_idx}",
                        [[wordle_num, player, strokes, summary, grid, timestamp]]
                    )
                )
                return

        sheets_operation_with_retry(
            lambda: ws.append_row([wordle_num, player, strokes, summary, grid, timestamp])
        )

    except Exception as e:
        st.error(f"❌ Save failed: {e}")
        st.exception(e)

def delete_score(wordle_num, player):
    """Deletes a score entry from the scores tab."""
    try:
        ws = get_worksheet("scores")
        records = sheets_operation_with_retry(ws.get_all_records)
        for i, r in enumerate(records):
            if int(r["wordle_num"]) == wordle_num and r["player"] == player:
                sheets_operation_with_retry(lambda: ws.delete_rows(i + 2))
                return True
        return False
    except Exception as e:
        st.error(f"Error deleting score: {e}")
        return False

def load_history():
    """Loads archived round history from the history tab."""
    try:
        ws = get_worksheet("history")
        records = sheets_operation_with_retry(ws.get_all_records)
        history = []
        for r in records:
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
    """Saves a completed round to the history tab."""
    try:
        ws = get_worksheet("history")
        sheets_operation_with_retry(
            lambda: ws.append_row([
                round_start,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                winner,
                summary,
                json.dumps(scorecard_dict)
            ])
        )
    except Exception as e:
        st.error(f"Error saving history: {e}")

def archive_round_scores(round_start):
    """Deletes all scores belonging to a completed round from the scores tab."""
    try:
        ws = get_worksheet("scores")
        records = sheets_operation_with_retry(ws.get_all_records)
        rows_to_delete = []
        for i, r in enumerate(records):
            w_num = int(r["wordle_num"])
            r_start, _ = get_round_start_and_hole(w_num)
            if r_start == round_start:
                rows_to_delete.append(i + 2)
        for row_idx in sorted(rows_to_delete, reverse=True):
            sheets_operation_with_retry(lambda: ws.delete_rows(row_idx))
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
    # SINGLE SCORE SUBMISSION
    # ----------------------------------------------------
    st.sidebar.write("---")
    st.sidebar.header("🎯 Individual Entry")

    paste_key = "wordle_paste_input_clear" if st.session_state.clear_paste else "wordle_paste_input"
    wordle_paste = st.sidebar.text_area(
        "Paste Single Wordle Snippet",
        placeholder="Wordle 1,845 4/6*...",
        height=90,
        key=paste_key
    )

    if st.sidebar.button("🚀 Post Score to Database"):
        if not wordle_paste:
            st.sidebar.error("Please paste your Wordle snippet first!")
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
                st.sidebar.error("Could not parse Wordle text. Check your snippet!")

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
    st.caption("💡 Hover over any score to see the color grid!")

    front_9_holes = list(range(1, 10))
    back_9_holes = list(range(10, 19))

    # FIXED: was > 20, now > 18 to correctly capture all playoff holes
    playoff_holes_display = []
    if playoff_active or playoff_winner:
        playoff_holes_display = sorted([
            h for h in round_scores.keys()
            if h > 18
        ])

    display_holes = front_9_holes + back_9_holes + playoff_holes_display

    # Calculate totals for display
    scorecard_data = {}
    for player in PLAYERS:
        scorecard_data[player] = {
            "total": 0,
            "synced_count": 0,
            "front_9": 0,
            "back_9": 0,
            "holes_html": {}
        }

    for h in display_holes:
        h_data = round_scores.get(h, {})
        both_have = all(p in h_data for p in PLAYERS)

        for player in PLAYERS:
            res = h_data.get(player)
            if res is None:
                cell_html = "<span style='color: #64748b;'>⏳</span>"
            else:
                strokes = res["strokes"] if isinstance(res, dict) else int(res)
                raw_grid = res.get("grid", "") if isinstance(res, dict) else ""
                clean_grid = (
                    str(raw_grid)
                    .replace("\\n", "<br>")
                    .replace("\n", "<br>")
                    .strip()
                )

                if both_have and h <= 18:
                    scorecard_data[player]["total"] += strokes
                    scorecard_data[player]["synced_count"] += 1
                    if 1 <= h <= 9:
                        scorecard_data[player]["front_9"] += strokes
                    elif 10 <= h <= 18:
                        scorecard_data[player]["back_9"] += strokes

                # Only show answer if both players have submitted
                if both_have:
                    wordle_num_for_hole = active_round_start + h - 1
                    raw_answer = get_wordle_answer(wordle_num_for_hole)
                    answer = safe_answer_display(raw_answer)
                    answer_line = (
                        f"<b style='color:#22c55e; font-size:15px; "
                        f"letter-spacing:3px;'>🟩 {answer} 🟩</b><br><br>"
                        if answer else ""
                    )
                else:
                    answer_line = (
                        "<i style='color:#94a3b8;'>Answer revealed when "
                        "both players submit</i><br><br>"
                    )

                cell_html = (
                    '<div class="wordle-tooltip">' + f"{strokes:+}" +
                    '<span class="wordle-tooltiptext">'
                    "<b>Hole " + str(h) + ":</b><br><br>" +
                    answer_line +
                    clean_grid +
                    "</span></div>"
                )

            scorecard_data[player]["holes_html"][h] = cell_html

    total_synced = scorecard_data[p1]["synced_count"]

    def build_hole_table(holes, title):
        """Builds an HTML table for a given set of holes."""
        tbl = f"<p style='color:#94a3b8; font-weight:bold; margin-top:15px;'>{title}</p>"
        tbl += "<table><thead><tr>"
        tbl += "<th>Player</th>"

        if title == "Front 9":
            tbl += (
                "<th style='background-color: #d97706; color: white;'>"
                f"Total ({total_synced})</th>"
                "<th style='background-color: #1e293b;'>F (1-9)</th>"
            )
        elif title == "Back 9":
            tbl += "<th style='background-color: #1e293b;'>B (10-18)</th>"
        elif title == "⚡ Playoffs":
            tbl += "<th style='background-color: #ef4444; color:white;'>Playoff</th>"

        for h in holes:
            lbl = str(h)
            if h > 18:
                lbl += "🚨"
            tbl += "<th>" + lbl + "</th>"
        tbl += "</tr></thead><tbody>"

        for player in PLAYERS:
            tbl += "<tr>"
            tbl += "<td><b>" + player + "</b></td>"

            if title == "Front 9":
                tot_val = scorecard_data[player]["total"]
                tot_str = f"{tot_val:+}" if tot_val != 0 else "E"
                f9_val = scorecard_data[player]["front_9"]
                f9_str = f"{f9_val:+}" if f9_val != 0 else "E"
                tbl += (
                    "<td style='background-color: rgba(217,119,6,0.15); "
                    "font-weight: bold; color: #f59e0b;'>" + tot_str + "</td>"
                    "<td>" + f9_str + "</td>"
                )
            elif title == "Back 9":
                b9_val = scorecard_data[player]["back_9"]
                b9_str = f"{b9_val:+}" if b9_val != 0 else "E"
                tbl += "<td>" + b9_str + "</td>"
            elif title == "⚡ Playoffs":
                tbl += "<td>—</td>"

            for h in holes:
                cell = scorecard_data[player]["holes_html"].get(
                    h, "<span style='color:#64748b'>⏳</span>"
                )
                tbl += "<td>" + cell + "</td>"
            tbl += "</tr>"

        tbl += "</tbody></table>"
        return tbl

    # Render Front 9
    st.markdown(
        build_hole_table(front_9_holes, "Front 9").replace("\n", "").strip(),
        unsafe_allow_html=True
    )

    # Render Back 9
    st.markdown(
        build_hole_table(back_9_holes, "Back 9").replace("\n", "").strip(),
        unsafe_allow_html=True
    )

    # Render Playoffs if active
    if playoff_holes_display:
        st.markdown(
            build_hole_table(playoff_holes_display, "⚡ Playoffs").replace("\n", "").strip(),
            unsafe_allow_html=True
        )

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
        comm_list = []
        if playoff_active:
            comm_list.append(
                "🎙️ 'Absolute deadlock! Regulation couldn't split them. "
                "We are in sudden death!'"
            )
        else:
            comm_list.append(
                "🎙️ 'Welcome to the clubhouse. "
                "18-hole regulation is underway.'"
            )
            diff = reg_totals[p1] - reg_totals[p2]
            if diff == 0 and reg_completed_holes:
                comm_list.append(
                    f"🎙️ 'Dead level through {len(reg_completed_holes)} synced holes!'"
                )
            elif diff != 0:
                leader = p2 if diff > 0 else p1
                chaser = p1 if diff > 0 else p2
                comm_list.append(
                    f"🎙️ '**{leader}** has the edge, "
                    f"putting pressure on **{chaser}**.'"
                )
        st.markdown(
            f'<div class="commentary-box">{"<br><br>".join(comm_list)}</div>',
            unsafe_allow_html=True
        )

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
                hist_holes = sorted([int(h) for h in scorecard.keys()])
                hist_display = [h for h in hist_holes if h <= 18]
                hist_playoff = [h for h in hist_holes if h > 18]
                hist_display += hist_playoff

                hist_table = "<table><thead><tr>"
                hist_table += "<th>Player</th>"
                hist_table += "<th style='background-color: #d97706; color:white;'>Total</th>"
                hist_table += "<th>F (1-9)</th>"
                hist_table += "<th>B (10-18)</th>"
                for h in hist_display:
                    lbl = str(h) + ("🚨" if h > 18 else "")
                    hist_table += f"<th>{lbl}</th>"
                hist_table += "</tr></thead><tbody>"

                for player in PLAYERS:
                    total = 0
                    front = 0
                    back = 0
                    cells = {}

                    for h in hist_display:
                        h_data = scorecard.get(str(h), {})
                        res = h_data.get(player)
                        if res is None:
                            cells[h] = "<span style='color:#64748b'>—</span>"
                        else:
                            strokes = res["strokes"] if isinstance(res, dict) else int(res)
                            raw_grid = res.get("grid", "") if isinstance(res, dict) else ""
                            clean_grid = (
                                str(raw_grid)
                                .replace("\\n", "<br>")
                                .replace("\n", "<br>")
                                .strip()
                            )
                            if h <= 18:
                                total += strokes
                                if 1 <= h <= 9:
                                    front += strokes
                                elif 10 <= h <= 18:
                                    back += strokes

                            wordle_num_for_hole = round_start + h - 1
                            raw_answer = get_wordle_answer(wordle_num_for_hole)
                            answer = safe_answer_display(raw_answer)
                            answer_line = (
                                f"<b style='color:#22c55e; font-size:15px; "
                                f"letter-spacing:3px;'>🟩 {answer} 🟩</b><br><br>"
                                if answer else ""
                            )
                            cells[h] = (
                                '<div class="wordle-tooltip">' + f"{strokes:+}" +
                                '<span class="wordle-tooltiptext">'
                                "<b>Hole " + str(h) + ":</b><br><br>" +
                                answer_line +
                                clean_grid +
                                "</span></div>"
                            )

                    tot_str = f"{total:+}" if total != 0 else "E"
                    f_str = f"{front:+}" if front != 0 else "E"
                    b_str = f"{back:+}" if back != 0 else "E"

                    hist_table += "<tr>"
                    hist_table += f"<td><b>{player}</b></td>"
                    hist_table += (
                        f"<td style='background-color: rgba(217,119,6,0.15); "
                        f"font-weight: bold; color: #f59e0b;'>{tot_str}</td>"
                    )
                    hist_table += f"<td>{f_str}</td>"
                    hist_table += f"<td>{b_str}</td>"
                    for h in hist_display:
                        hist_table += f"<td>{cells.get(h, '<span style=color:#64748b>—</span>')}</td>"
                    hist_table += "</tr>"

                hist_table += "</tbody></table>"
                st.markdown(hist_table.replace("\n", "").strip(), unsafe_allow_html=True)
