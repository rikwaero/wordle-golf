import re
import os
import json
import streamlit as st
import pandas as pd

# ----------------------------------------------------
# 1. CONFIGURATION & STYLING
# ----------------------------------------------------
st.set_page_config(page_title="Wordle Golf Pro Tour", page_icon="⛳", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.title("⛳ Wordle Golf Pro Tour")
st.write("Welcome to the clubhouse. Drop your scores, track the board, and catch the live broadcast.")

SCORE_MAP = {"1": -3, "2": -2, "3": -1, "4": 0, "5": 1, "6": 2, "X": 3, "x": 3}
SCORE_NAMES = {-3: "🚀 ALBATROSS!", -2: "🦅 EAGLE!!", -1: "🐦 BIRDIE!", 0: "Par", 1: "⚠️ Bogey", 2: "❌ Double Bogey", 3: "💥 TRIPLE BOGEY (FAIL)"}

# ----------------------------------------------------
# 2. CALCULATION ENGINE
# ----------------------------------------------------
def get_round_start_and_hole(wordle_num):
    for test_num in range(wordle_num, wordle_num - 40, -1):
        prefix = int(str(test_num)[:3])
        if prefix % 2 == 0:
            start_num = test_num
            hole_num = (wordle_num - start_num) + 1
            return start_num, hole_num
    return wordle_num, 1

def parse_wordle_text(text):
    clean_text = text.replace(",", "").replace(" ", "")
    match = re.search(r"Wordle(\d+)([1-6Xx])/6", clean_text)
    if match:
        return int(match.group(1)), SCORE_MAP.get(match.group(2), 0)
    return None, None

# ----------------------------------------------------
# 3. STATE MANAGEMENT (LOCAL FILE DATABASE SYSTEM)
# ----------------------------------------------------

DB_FILE = "golf_history.json"
def load_db():
    """Loads all current round and historical data from the JSON file."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default schema if file doesn't exist
    return {"current_round": {}, "history": []}

def save_db(data):
    """Saves the tracking data structurally back to disk."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize Session State from DB
# Initialize Session State from DB
db_data = load_db()
if "scores" not in st.session_state:
    st.session_state.scores = db_data.get("current_round", {})
if "history" not in st.session_state:
    st.session_state.history = db_data.get("history", [])
if "player_profiles" not in st.session_state:
    # Default names to start with if nothing is in the database yet
    st.session_state.player_profiles = db_data.get("player_profiles", ["Dan", "Rik"])

# ----------------------------------------------------
# 4. SIDEBAR IDENTITY & USER INPUT
# ----------------------------------------------------
st.sidebar.header("👤 Player Profiles Manager")

# Ensure default profiles match dynamic state
player_identity = st.sidebar.selectbox(
    "Who is uploading an individual score?",
    st.session_state.player_profiles,
    help="Select your name before individual posting."
)

with st.sidebar.expander("🛠️ Add, Edit, or Rename Players"):
    new_player_name = st.text_input("Add New Player Name", placeholder="e.g., Rory").strip()
    if st.button("➕ Add Player"):
        if new_player_name and new_player_name not in st.session_state.player_profiles:
            st.session_state.player_profiles.append(new_player_name)
            current_db = load_db()
            current_db["player_profiles"] = st.session_state.player_profiles
            save_db(current_db)
            st.rerun()
            
    st.write("---")
    
    player_to_rename = st.selectbox("Select Player to Rename", st.session_state.player_profiles)
    target_new_name = st.text_input("New Name for Selected Player", placeholder="e.g., Jack").strip()
    if st.button("✏️ Save New Name"):
        if target_new_name and target_new_name not in st.session_state.player_profiles:
            idx = st.session_state.player_profiles.index(player_to_rename)
            st.session_state.player_profiles[idx] = target_new_name
            if player_to_rename in st.session_state.scores:
                st.session_state.scores[target_new_name] = st.session_state.scores.pop(player_to_rename)
            current_db = load_db()
            current_db["player_profiles"] = st.session_state.player_profiles
            current_db["current_round"] = st.session_state.scores
            save_db(current_db)
            st.rerun()

st.sidebar.write("---")
st.sidebar.header("🎯 Individual Entry")
wordle_paste = st.sidebar.text_area("Paste Single Wordle Snippet", placeholder="Wordle 1,843 3/6...", height=90)

if st.sidebar.button("🚀 Post Score to Database"):
    if not wordle_paste:
        st.sidebar.error("Please paste your Wordle snippet first!")
    else:
        w_num, strokes = parse_wordle_text(wordle_paste)
        if w_num is not None:
            _, hole = get_round_start_and_hole(w_num)
            if player_identity not in st.session_state.scores:
                st.session_state.scores[player_identity] = {}
            st.session_state.scores[player_identity][str(hole)] = strokes
            current_db = load_db()
            current_db["current_round"] = st.session_state.scores
            save_db(current_db)
            shoutout = SCORE_NAMES.get(strokes, "🎯 SCORE")
            st.toast(f"📢 {player_identity} secured a {shoutout} on Hole {hole}!", icon="⛳")
            st.sidebar.success(f"Logged Hole {hole} (Wordle {w_num})")
            st.rerun()
        else:
            st.sidebar.error("Could not parse single text. Check alignment.")

# ----------------------------------------------------
# NEW EXTRA FEATURE: MESSENGER BULK THREAD PARSER
# ----------------------------------------------------
st.sidebar.write("---")
st.sidebar.header("📂 Bulk Historical Messenger Input")
with st.sidebar.expander("📬 Dump Chat Thread Data Here"):
    st.write("Select which player sent the text below, paste the giant thread block, and the app will parse every Wordle score hidden in it.")
    
    bulk_player = st.selectbox("Sender of this Chat Dump", st.session_state.player_profiles, key="bulk_p_sel")
    bulk_text = st.text_area("Paste Chat Text Content", placeholder="Dan\nWordle 1,816 3/6*...\nArchive June 3...", height=250)
    
    if st.button("⚡ Parse & Save All Historical Text"):
        if not bulk_text:
            st.error("Paste text before compiling!")
        else:
            # Multi-line match engine looking for 'Wordle' followed by tracking codes
            # Handles varying spaces and commas implicitly (e.g. 'Wordle 1 810' or 'Wordle 1,816')
            clean_bulk = bulk_text.replace(",", "")
            matches = re.findall(r"Wordle\s*(\d+[\s\d]*)\s*([1-6Xx])/6", clean_bulk)
            
            if not matches:
                st.error("No valid Wordle blocks found inside that chunk of text.")
            else:
                success_count = 0
                if bulk_player not in st.session_state.scores:
                    st.session_state.scores[bulk_player] = {}
                    
                for m in matches:
                    try:
                        # Clean inner spaces inside game index numbers
                        raw_w_num = m[0].replace(" ", "").strip()
                        w_num = int(raw_w_num)
                        score_char = m[1]
                        strokes = SCORE_MAP.get(score_char, 0)
                        
                        # Apply your core anchoring logic to find the 1-18 relative track index
                        _, hole = get_round_start_and_hole(w_num)
                        
                        st.session_state.scores[bulk_player][str(hole)] = strokes
                        success_count += 1
                    except Exception:
                        continue
                
                if success_count > 0:
                    current_db = load_db()
                    current_db["current_round"] = st.session_state.scores
                    save_db(current_db)
                    st.success(f"Successfully processed and stored {success_count} scores for {bulk_player}!")
                    st.rerun()
                else:
                    st.error("Found patterns but structural execution failed during numerical mapping.")
# ----------------------------------------------------
# 5. DATA COMPUTATION & DYNAMICS
# ----------------------------------------------------
active_players = list(st.session_state.scores.keys())

if len(active_players) < 2:
    st.info("👋 Waiting for both players to submit at least one score to activate the live scoreboard boards.")
else:
    p1, p2 = active_players[0], active_players[1]
    
    p1_holes = [int(k) for k in st.session_state.scores[p1].keys()]
    p2_holes = [int(k) for k in st.session_state.scores[p2].keys()]
    max_submitted_hole = max(max(p1_holes) if p1_holes else 1, max(p2_holes) if p2_holes else 1)
    
    # 1. Isolation Math Matrix (Common holes only)
    reg_completed_holes = []
    reg_totals = {p1: 0, p2: 0}
    
    for h in range(1, 19):
        s1 = st.session_state.scores[p1].get(str(h))
        s2 = st.session_state.scores[p2].get(str(h))
        if s1 is not None and s2 is not None:
            reg_completed_holes.append(h)
            reg_totals[p1] += s1
            reg_totals[p2] += s2

    regulation_finished = len(reg_completed_holes) == 18
    
    # 2. Playoff Sudden Death Matrix Engine
    playoff_active = False
    playoff_winner = None
    current_playoff_hole = 19
    
    if regulation_finished and reg_totals[p1] == reg_totals[p2]:
        playoff_active = True
        while True:
            s1_p = st.session_state.scores[p1].get(str(current_playoff_hole))
            s2_p = st.session_state.scores[p2].get(str(current_playoff_hole))
            
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
    # 6. BROADCAST COMMENTARY BOOTH
    # ----------------------------------------------------
    st.header("🎙️ Live Broadcast Booth")
    if st.button("🎤 Get Live Broadcast Commentary"):
        comm_list = []
        if playoff_active:
            comm_list.append(f"🎙️ 'Absolute deadlock! Regulation play couldn't split them. We are out on the sudden-death track.'")
        else:
            comm_list.append(f"🎙️ 'Welcome to the gallery. We are monitoring a pristine 18-hole regulation round context.'")
            diff = reg_totals[p1] - reg_totals[p2]
            if diff == 0:
                comm_list.append(f"🎙️ 'Through the synced cards, it is an absolute tie across {len(reg_completed_holes)} balanced holes!'")
            else:
                leader = p2 if diff > 0 else p1
                chaser = p1 if diff > 0 else p2
                comm_list.append(f"🎙️ 'With verified data, **{leader}** holds a tight grip on the match projection, putting pressure on **{chaser}**.'")
        st.markdown(f'<div class="commentary-box">{"<br><br>".join(comm_list)}</div>', unsafe_allow_html=True)
        st.write("---")

    # ----------------------------------------------------
    # 7. CHAMPIONSHIP RESOLUTIONS
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
        st.markdown(f'<div class="winner-banner">🏆 SUDDEN DEATH CHAMPION: {winner_name.upper()}! 🏆</div>', unsafe_allow_html=True)
        st.success(f"👏 **Pure ice in your veins, {winner_name}!**")
        
    elif regulation_finished and not playoff_active:
        if reg_totals[p1] != reg_totals[p2]:
            round_ended = True
            winner_name = p1 if reg_totals[p1] < reg_totals[p2] else p2
            loser_name = p2 if winner_name == p1 else p1
            summary_msg = f"{winner_name} ({reg_totals[winner_name]:+}) def. {loser_name} ({reg_totals[loser_name]:+})"
            st.balloons()
            st.markdown(f'<div class="winner-banner">👑 TOURNAMENT CHAMPION: {winner_name.upper()}! 👑</div>', unsafe_allow_html=True)
            st.success(f"🏆 **Put on the green jacket, {winner_name}!**")

 # ----------------------------------------------------
    # 8. MATCH OVERVIEW TOURNAMENT CARDS
    # ----------------------------------------------------
    st.header("🏆 Live Standings")
    col1, col2 = st.columns(2)
    
    with col1:
        diff = reg_totals[p1] - reg_totals[p2]
        if diff < 0:
            leader_str = f"⚡ **{p1}** leads by **{abs(diff)}** strokes (on synced holes)"
        elif diff > 0:
            leader_str = f"⚡ **{p2}** leads by **{abs(diff)}** strokes (on synced holes)"
        else:
            leader_str = "⚖️ **All Square!** Level scoreboards on verified entries."
            
        card_style = "metric-card playoff-card" if playoff_active else "metric-card"
        st.markdown(f'<div class="{card_style}"><h4 style="margin:0; color:white;">Synced Leader</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{leader_str}</p></div>', unsafe_allow_html=True)

    with col2:
        status_text = "🚨 PLAYOFFS ACTIVE" if playoff_active else f"⛳ Regulation: {len(reg_completed_holes)}/18 Holes Synced"
        st.markdown(f'<div class="metric-card" style="border-left-color: #3b82f6;"><h4 style="margin:0; color:white;">Status Phase</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{status_text}</p></div>', unsafe_allow_html=True)

    # ----------------------------------------------------
    # 9. SCOREBOARD MATRIX GRID
    # ----------------------------------------------------
    st.subheader("📊 Tournament Scoreboard Matrix")
    matrix_rows = []
    limit = max(18, max_submitted_hole)
    for h in range(1, limit + 1):
        if h > 18 and h > max_submitted_hole:
            continue
            
        s1 = st.session_state.scores[p1].get(str(h), None)
        s2 = st.session_state.scores[p2].get(str(h), None)
        
        row_label = f"Hole {h}"
        if h > 18:
            row_label += " 🚨 [Playoff]"
            
        matrix_rows.append({
            "Hole": row_label,
            p1: f"{s1:+}" if s1 is not None else "⏳ Waiting",
            p2: f"{s2:+}" if s2 is not None else "⏳ Waiting",
            "Status": "✅ Verified" if (s1 is not None and s2 is not None) else "📢 Unbalanced"
        })
        
    st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

# Archive Option
    if round_ended:
        if st.button("📦 Archive Current Round Results & Clear Table"):
            current_db = load_db()
            
            history_entry = {
                "date_archived": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "winner": winner_name,
                "summary": summary_msg
            }
            current_db["history"].append(history_entry)
            current_db["current_round"] = {}  # Clears active scores
            current_db["player_profiles"] = st.session_state.player_profiles  # Keeps player profiles!
            
            save_db(current_db)
            st.session_state.scores = {}
            st.session_state.history = current_db["history"]
            st.rerun()

# ----------------------------------------------------
# 10. HISTORICAL CHAMPIONS ARCHIVE VIEW
# ----------------------------------------------------
st.write("---")
st.header("📜 Historical Tournament Records")
if st.session_state.history:
    df_hist = pd.DataFrame(st.session_state.history)
    df_hist.columns = ["Timestamp Logged", "Champion 👑", "Match Summary Breakdown"]
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
else:
    st.caption("No historical games archived yet. Complete an 18-hole segment to register the record book.")
