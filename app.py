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
        .tooltip .tooltiptext {
        visibility: hidden;
        width: 160px;
        background-color: #1e293b;
        color: #fff;
        text-align: center;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 99;
        bottom: 125%;
        left: 50%;
        margin-left: -80px;
        opacity: 0;
        transition: opacity 0.2s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
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
    """
    Extracts the anchor based strictly on your 3-digit even rule.
    
    Examples for your modern era block:
    - Wordle 1841: Prefix is 184 (Even). Anchor is 1840. Hole is: 1841 - 1840 = Hole 1.
    - Wordle 1842: Prefix is 184 (Even). Anchor is 1840. Hole is: 1842 - 1840 = Hole 2.
    - Wordle 1843: Prefix is 184 (Even). Anchor is 1840. Hole is: 1843 - 1840 = Hole 3.
    """
    num_str = str(wordle_num).replace(",", "").replace(" ", "")
    
    # 1. Grab the first 3 digits directly from your real pasted Wordle game number
    if len(num_str) >= 3:
        prefix = int(num_str[:3])
        
        # 2. If the prefix is even (like 184), this is our current 3-digit anchor block
        if prefix % 2 == 0:
            start_num = int(num_str[:3] + "0")
        else:
            # If the prefix is odd (e.g. 185), it means we stepped into an odd era 
            # while a current 18-hole block is continuing. Roll back to the even base.
            even_prefix = prefix - 1
            start_num = int(str(even_prefix) + "0")
    else:
        # Emergency absolute structural baseline fallback
        start_num = 1840

    # Your rule: Wordle Game Number minus Baseline Anchor equals Hole Number
    hole_num = wordle_num - start_num
    
    # Structural catch if a user posts a game that perfectly equals the anchor boundary
    if hole_num <= 0:
        hole_num = 1
        
    return start_num, hole_num
    
def parse_wordle_text(text):
    """
    Parses individual free-form Wordle share snippets.
    Aggressively strips all standard, web, and non-breaking whitespace anomalies.
    """
    # CRITICAL ADVANCED FIX: Strip commas, standard spaces, and any hidden web non-breaking spaces (\xa0)
    clean_text = text.replace(",", "").replace(" ", "").replace("\xa0", "").strip()
    
    # Relaxed search captures 'Wordle' anywhere inside the block, absorbing asterisks (*)
    match = re.search(r"Wordle\s*(\d+)[^\d]*([1-6Xx])[/*]6", clean_text)
    if not match:
        return None, None
        
    w_num = int(match.group(1))
    score_char = match.group(2)
    strokes = SCORE_MAP.get(score_char, 0)
    
    # Tally up color grids safely
    greens = text.count("🟩")
    yellows = text.count("🟨")
    misses = text.count("⬛") + text.count("⬜")
    
    # Extract structural layout lines
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
    return {"current_round": {}, "history": []}

def save_db(data):
    """Saves the tracking data structurally back to disk."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- EXECUTE STORAGE SYSTEM SYNCHRONIZATION ---
db_data = load_db()

if "scores" not in st.session_state:
    st.session_state.scores = db_data.get("current_round", {})
if "history" not in st.session_state:
    st.session_state.history = db_data.get("history", [])
if "player_profiles" not in st.session_state:
    st.session_state.player_profiles = db_data.get("player_profiles", ["Dan", "Rik"])

# --- FORCE RESET PASSWORDS KEY REGISTRY ---
st.session_state.player_passwords = {"Dan": "YouareDan", "Rik": "YouareRik"}
db_data["player_passwords"] = st.session_state.player_passwords
save_db(db_data)

# --- TRACK PERSISTENT DEVICE TRACKING TOKENS ---
if "device_sessions" not in st.session_state:
    st.session_state.device_sessions = db_data.get("device_sessions", {})

if "current_user" not in st.session_state:
    st.session_state.current_user = None
    
try:
    from streamlit.web.server.websocket_headers import _get_websocket_headers
    headers = _get_websocket_headers()
    browser_token = f"{headers.get('User-Agent', '')}_{headers.get('X-Forwarded-For', 'local')}"
    
    if browser_token in st.session_state.device_sessions:
        st.session_state.current_user = st.session_state.device_sessions[browser_token]
except Exception:
    pass


# ----------------------------------------------------
# 4. SIDEBAR IDENTITY & USER INPUT (PERSISTENT LOGIN)
# ----------------------------------------------------
st.sidebar.header("🔐 Pro Tour Player Login")

# Generate the device token context for cookie simulation mapping
try:
    from streamlit.web.server.websocket_headers import _get_websocket_headers
    headers = _get_websocket_headers()
    browser_token = f"{headers.get('User-Agent', '')}_{headers.get('X-Forwarded-For', 'local')}"
except Exception:
    browser_token = "fallback_local_token"

if st.session_state.current_user is None:
    # Login Panel Form
    login_name = st.sidebar.selectbox("Select Your Profile Name", st.session_state.player_profiles)
    login_pwd = st.sidebar.text_input("Enter Private Password", type="password", help="Default starting passwords are 'greenjacket1' and 'greenjacket2'")
    remember_me = st.sidebar.checkbox("Keep me logged in on this device", value=True)
    
    if os.environ.get("STREAMLIT_RUNTIME_ENV") == "cloud":
        st.sidebar.caption("💡 Check 'Keep me logged in' to bypass this prompt next time you open your phone!")
    
    if st.sidebar.button("🚪 Enter Clubhouse"):
        correct_pwd = st.session_state.player_passwords.get(login_name)
        if correct_pwd and login_pwd == correct_pwd:
            st.session_state.current_user = login_name
            
            # If "Remember Me" is checked, commit this browser's footprint to disk database
            if remember_me:
                st.session_state.device_sessions[browser_token] = login_name
                current_db = load_db()
                current_db["device_sessions"] = st.session_state.device_sessions
                save_db(current_db)
                
            st.session_state.post_msg = f"🔓 Welcome back, {login_name}! Device remembered successfully."
            st.rerun()
        else:
            st.sidebar.error("Invalid passcode combination. Please try again.")
else:
    # User is securely and persistently logged in!
    st.sidebar.markdown(f"⛳ Logged in as: **{st.session_state.current_user}**")
    
    # Forget Device / Logout Link
    if st.sidebar.button("🔒 Log Out & Forget Device"):
        # Remove this browser instance from the database cache registry
        if browser_token in st.session_state.device_sessions:
            st.session_state.device_sessions.pop(browser_token)
            current_db = load_db()
            current_db["device_sessions"] = st.session_state.device_sessions
            save_db(current_db)
            
        st.session_state.current_user = None
        st.rerun()
        
    st.sidebar.write("---")

    # ----------------------------------------------------
    # PLAYER PROFILE CREATION & ADMINISTRATIVE TOOLS
    # ----------------------------------------------------
    with st.sidebar.expander("🛠️ Profile Administration"):
        st.write("Register a brand new competitor profile or rename yours below.")
        
        new_player_name = st.text_input("Add New Player Name", placeholder="e.g., Rory").strip()
        new_player_pwd = st.text_input("Assign Starter Password", type="password", placeholder="e.g., pass123")
        
        if st.button("➕ Add Player Profile"):
            if new_player_name and new_player_pwd:
                if new_player_name not in st.session_state.player_profiles:
                    st.session_state.player_profiles.append(new_player_name)
                    st.session_state.player_passwords[new_player_name] = new_player_pwd
                    
                    current_db = load_db()
                    current_db["player_profiles"] = st.session_state.player_profiles
                    current_db["player_passwords"] = st.session_state.player_passwords
                    save_db(current_db)
                    
                    st.session_state.post_msg = f"✅ Created profile for {new_player_name}!"
                    st.rerun()
                else:
                    st.error("That profile moniker already exists.")
            else:
                st.error("Fill out both input boxes to launch profile metadata.")

    # ----------------------------------------------------
    # TROUBLESHOOTING & DELETIONS PANEL
    # ----------------------------------------------------
    with st.sidebar.expander("🗑️ Scorecard Corrections"):
        st.write("Wipe out typing errors on your active card. You can only modify your own scores.")
        target_del_hole = st.number_input("Target Hole # to Wipe", min_value=1, max_value=50, value=1, step=1)
        
        if st.button("❌ Wipe Single Score"):
            h_str = str(target_del_hole)
            my_name = st.session_state.current_user
            
            if my_name in st.session_state.scores and h_str in st.session_state.scores[my_name]:
                st.session_state.scores[my_name].pop(h_str)
                current_db = load_db()
                current_db["current_round"] = st.session_state.scores
                save_db(current_db)
                st.session_state.post_msg = f"🗑️ Successfully wiped Hole {target_del_hole} off your card!"
                st.rerun()
            else:
                st.error("No recorded entry found matching that hole layout on your card.")

    # ----------------------------------------------------
    # DATA SUBMISSION ROUTINES
    # ----------------------------------------------------
    st.sidebar.write("---")
    st.sidebar.header("🎯 Individual Entry")
    wordle_paste = st.sidebar.text_area("Paste Single Wordle Snippet", placeholder="Wordle 1,843 5/6*...", height=90)

    if st.sidebar.button("🚀 Post Score to Database"):
        if not wordle_paste:
            st.sidebar.error("Please paste your Wordle snippet first!")
        else:
            w_num, pattern_data = parse_wordle_text(wordle_paste)
            if w_num is not None:
                _, hole = get_round_start_and_hole(w_num)
                hole_str = str(hole)
                my_name = st.session_state.current_user
                
                if my_name not in st.session_state.scores:
                    st.session_state.scores[my_name] = {}
                
                is_update = hole_str in st.session_state.scores[my_name]
                
                # CRITICAL CHANGE: Saves the structured data map instead of a flat integer
                st.session_state.scores[my_name][hole_str] = pattern_data
                
                current_db = load_db()
                current_db["current_round"] = st.session_state.scores
                save_db(current_db)
                
                strokes = pattern_data["strokes"]
                shoutout = SCORE_NAMES.get(strokes, f"{strokes} strokes")
                if is_update:
                    st.session_state.post_msg = f"🔄 OVERWRITE SUCCESSFUL! Updated Hole {hole} for you."
                else:
                    st.session_state.post_msg = f"✅ READ SUCCESSFUL! Logged Hole {hole} to your card: {shoutout}."
                st.rerun()
            else:
                st.sidebar.error("Regex Parsing Mismatch. Check text layout structures.")
                
    # ----------------------------------------------------
    # 4b. BULK THREAD PARSER (RESTRICTED TO CURRENT USER)
    # ----------------------------------------------------
    st.sidebar.write("---")
    st.sidebar.header("📂 Bulk Historical Messenger Input")
    with st.sidebar.expander("📬 Dump Chat Thread Data Here"):
        st.write(f"This will extract Wordle text strings directly onto your scorecard profile (**{st.session_state.current_user}**).")
        bulk_text = st.text_area("Paste Chat Text Content", placeholder="Wordle 1,816 3/6*...", height=150)
        
        if st.button("⚡ Parse & Save All Historical Text"):
            if not bulk_text:
                st.error("Paste text before compiling!")
            else:
                my_name = st.session_state.current_user
                clean_bulk = bulk_text.replace(",", "")
                matches = re.findall(r"Wordle\s*(\d+[\s\d]*)\s*([1-6Xx])[/*]6", clean_bulk)
                
                if not matches:
                    st.error("No valid Wordle blocks found inside that chunk of text.")
                else:
                    success_count = 0
                    if my_name not in st.session_state.scores:
                        st.session_state.scores[my_name] = {}
                        
                    for m in matches:
                        try:
                            raw_w_num = m.replace(" ", "").strip()
                            w_num = int(raw_w_num)
                            score_char = m
                            strokes = SCORE_MAP.get(score_char, 0)
                            _, hole = get_round_start_and_hole(w_num)
                            st.session_state.scores[my_name][str(hole)] = strokes
                            success_count += 1
                        except Exception:
                            continue
                    
                    if success_count > 0:
                        current_db = load_db()
                        current_db["current_round"] = st.session_state.scores
                        save_db(current_db)
                        st.session_state.post_msg = f"⚡ BULK IMPORT SUCCESSFUL! Saved {success_count} scores to your profile card."
                        st.rerun()
                    else:
                        st.error("Pattern processing failed during internal structural extraction.")

# ----------------------------------------------------
# 5. DATA COMPUTATION & DYNAMICS
# ----------------------------------------------------
# PERSISTENT SYSTEM CONFIRMATION VIEWER
if "post_msg" not in st.session_state:
    st.session_state.post_msg = ""

if st.session_state.post_msg:
    st.success(st.session_state.post_msg)
    st.session_state.post_msg = ""  # Wipes track after clean rendering

active_players = list(st.session_state.scores.keys())

# Render immediate instructions if entirely clean scorecard database
if not active_players:
    st.info("⛳ The scoreboard matrix is vacant. Use the player profiles dashboard to configure profiles and upload entries!")
else:
    # Set fallback variables dynamically to allow structural table loops for single users
    p1 = active_players[0]
    p2 = active_players[1] if len(active_players) > 1 else None
    
    # Calculate matrix limits safely depending on whether 1 or 2 players exist
    p1_holes = [int(k) for k in st.session_state.scores[p1].keys()]
    p2_holes = [int(k) for k in st.session_state.scores[p2].keys()] if p2 else []
    max_submitted_hole = max(max(p1_holes) if p1_holes else 1, max(p2_holes) if p2_holes else 1)

    # 1. Isolation Math Matrix (Common holes only)
    reg_completed_holes = []
    reg_totals = {p1: 0}
    if p2:
        reg_totals[p2] = 0
    
    for h in range(1, 19):
        res1 = st.session_state.scores[p1].get(str(h))
        res2 = st.session_state.scores[p2].get(str(h)) if p2 else None
        
        # Pull out strokes safely considering backward-compatible structures
        s1 = res1.get("strokes") if isinstance(res1, dict) else res1
        s2 = res2.get("strokes") if isinstance(res2, dict) else res2
        
        if s1 is not None and s2 is not None and p2:
            reg_completed_holes.append(h)
            reg_totals[p1] += s1
            reg_totals[p2] += s2

    regulation_finished = len(reg_completed_holes) == 18 and p2 is not None
    
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
    # COMPLETELY DYNAMIC ROUND SPAN ENGINE (HIGHEST CURRENT ERA)
    # Default fallback era anchor
    start_wordle_num = 1841  
    
    # 1. Parse out all numbers found inside your raw text box strings 
    # to find the absolute maximum Wordle number uploaded in this session
    raw_text_pool = []
    if "wordle_paste" in st.session_state and st.session_state.wordle_paste:
        raw_text_pool.append(st.session_state.wordle_paste)
    if "bulk_text" in st.session_state and st.session_state.bulk_text:
        raw_text_pool.append(st.session_state.bulk_text)
        
    extracted_nums = []
    for txt in raw_text_pool:
        found = [int(n.replace(",", "").replace(" ", "")) for n in re.findall(r"Wordle\s*(\d+[\s\d]*)", txt.replace(",", ""))]
        extracted_nums.extend(found)
        
    # 2. Match the highest Wordle number against its relative golf hole matrix index
    p1_holes = [int(k) for k in st.session_state.scores[p1].keys()]
    p2_holes = [int(k) for k in st.session_state.scores[p2].keys()] if p2 else []
    all_holes = p1_holes + p2_holes
    
    if extracted_nums and all_holes:
        highest_w_num = max(extracted_nums)
        highest_hole = max(all_holes)
        
        # Calculate exactly where Hole 1 launched for this specific highest game
        base_start, _ = get_round_start_and_hole(highest_w_num)
        start_wordle_num = base_start
    elif all_holes:
        # If text logs cleared but scores exist in database, check modern era range down from 2500
        highest_hole = max(all_holes)
        for w_test in range(2500, 1000, -1):
            _, h_test = get_round_start_and_hole(w_test)
            if h_test == highest_hole:
                start_wordle_num, _ = get_round_start_and_hole(w_test)
                break

    end_wordle_num = start_wordle_num + 17
    
    # DISPLAY HEADER WITH DYNAMIC ROUND BOUNDARIES
    st.header(f"🏆 Live Standings (Round: {start_wordle_num} - {end_wordle_num})")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if p2:
            diff = reg_totals[p1] - reg_totals[p2]
            if diff < 0:
                leader_str = f"⚡ **{p1}** leads by **{abs(diff)}** strokes (on synced holes)"
            elif diff > 0:
                leader_str = f"⚡ **{p2}** leads by **{abs(diff)}** strokes (on synced holes)"
            else:
                leader_str = "⚖️ **All Square!** Level scoreboards on verified entries."
        else:
            leader_str = f"🏌️‍♂️ **{p1}** is playing solo. Waiting for an opponent to log a score!"
            
        card_style = "metric-card playoff-card" if playoff_active else "metric-card"
        st.markdown(f'<div class="{card_style}"><h4 style="margin:0; color:white;">Synced Leader</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{leader_str}</p></div>', unsafe_allow_html=True)

    with col2:
        if p2:
            status_text = "🚨 PLAYOFFS ACTIVE" if playoff_active else f"⛳ Regulation: {len(reg_completed_holes)}/18 Holes Synced"
        else:
            status_text = "⏳ Awaiting Player 2"
        st.markdown(f'<div class="metric-card" style="border-left-color: #3b82f6;"><h4 style="margin:0; color:white;">Status Phase</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{status_text}</p></div>', unsafe_allow_html=True)
    
    # ----------------------------------------------------
    # 9. HORIZONTAL TRADITIONAL GOLF SCORECARD MATRIX
    # ----------------------------------------------------
    st.subheader("📊 Tournament Scoreboard Matrix")
    st.caption("💡 Hover your mouse or press on any cell score to preview its color grids and block patterns!")

    p1_name = p1
    p2_name = p2 if p2 else "Awaiting Opponent"
    display_players = [p1_name]
    if p2:
        display_players.append(p2_name)

    p1_holes = [int(k) for k in st.session_state.scores[p1_name].keys()]
    p2_holes = [int(k) for k in st.session_state.scores[p2_name].keys()] if p2 else []
    all_holes_list = p1_holes + p2_holes
    max_hole = max(all_holes_list) if all_holes_list else 18
    limit_holes = max(18, max_hole)

    scorecard_rows = {}
    total_synced_holes = 0  # Track maximum matched holes for header label mapping

    for player in display_players:
        scorecard_rows[player] = {
            "total": 0,
            "synced_count": 0,
            "front_9": 0,
            "back_9": 0,
            "holes_html": {}
        }
        
        for h in range(1, limit_holes + 1):
            res = st.session_state.scores.get(player, {}).get(str(h), None) if player != "Awaiting Opponent" else None
            
            if res is None:
                cell_html = "<span style='color: #64748b;'>⏳</span>"
            else:
                if not isinstance(res, dict):
                    strokes = int(res)
                    summary = "Legacy Entry"
                    clean_grid = ""
                else:
                    strokes = res.get("strokes", 0)
                    summary = res.get("summary", "")
                    raw_grid = str(res.get("grid", ""))
                    clean_grid = raw_grid.replace("\\n", "<br>").replace("\n", "<br>").replace(r"\n", "<br>").strip()

                # Accumulate values strictly if BOTH players have logged data
                if p2 and str(h) in st.session_state.scores[p1_name] and str(h) in st.session_state.scores[p2_name]:
                    scorecard_rows[player]["total"] += strokes
                    scorecard_rows[player]["synced_count"] += 1
                    if 1 <= h <= 9:
                        scorecard_rows[player]["front_9"] += strokes
                    elif 10 <= h <= 18:
                        scorecard_rows[player]["back_9"] += strokes

                cell_html = f'<div class="wordle-tooltip">{strokes:+}<span class="wordle-tooltiptext"><b>Hole {h} Grid:</b><br>{summary}<br><br>{clean_grid}</span></div>'
            
            scorecard_rows[player]["holes_html"][h] = cell_html

    # Capture the active synced count to insert into table header
    if p2 and p1_name in scorecard_rows:
        total_synced_holes = scorecard_rows[p1_name]["synced_count"]

    # Assemble HTML Table
    html_table = "<table><thead><tr>"
    html_table += "<th>Competitor</th>"
    html_table += f"<th style='background-color: #d97706; color: white;'>Total ({total_synced_holes})</th>"
    html_table += "<th style='background-color: #1e293b;'>F (1-9)</th>"
    html_table += "<th style='background-color: #1e293b;'>B (10-18)</th>"
    
    for h in range(1, limit_holes + 1):
        lbl = str(h)
        if h > 18:
            lbl += "🚨"
        html_table += f"<th>{lbl}</th>"
    html_table += "</tr></thead><tbody>"

    for player in display_players:
        if player == "Awaiting Opponent":
            tot_str, f9_str, b9_str = "⏳", "⏳", "⏳"
        else:
            tot_val = scorecard_rows[player]['total']
            tot_str = f"{tot_val:+}" if tot_val != 0 else "E"
            
            f9_val = scorecard_rows[player]['front_9']
            f9_str = f"{f9_val:+}" if f9_val != 0 else "E"
            
            b9_val = scorecard_rows[player]['back_9']
            b9_str = f"{b9_val:+}" if b9_val != 0 else "E"

        html_table += "<tr>"
        html_table += f"<td><b>{player}</b></td>"
        html_table += f"<td style='background-color: rgba(217,119,6,0.15); font-weight: bold; color: #f59e0b;'>{tot_str}</td>"
        html_table += f"<td>{f9_str}</td>"
        html_table += f"<td>{b9_str}</td>"
        
        for h in range(1, limit_holes + 1):
            html_table += f"<td>{scorecard_rows[player]['holes_html'][h]}</td>"
        html_table += "</tr>"

    html_table += "</tbody></table>"

    clean_html_table = html_table.replace("\n", "").strip()
    st.markdown(clean_html_table, unsafe_allow_html=True)

    # Scorecard Layout Stylesheet Settings
    st.markdown("""
    <style>
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
    </style>
    """, unsafe_allow_html=True)

    if round_ended:
        if st.button("📦 Archive Current Round Results & Clear Table"):
            current_db = load_db()
            history_entry = {
                "date_archived": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "winner": winner_name,
                "summary": summary_msg
            }
            current_db["history"].append(history_entry)
            current_db["current_round"] = {}
            current_db["player_profiles"] = st.session_state.player_profiles
            current_db["player_passwords"] = st.session_state.player_passwords
            current_db["device_sessions"] = st.session_state.device_sessions
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
