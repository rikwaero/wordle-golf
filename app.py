pythonimport re
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
# 3. STATE MANAGEMENT
# ----------------------------------------------------
if "scores" not in st.session_state:
    st.session_state.scores = {}

# ----------------------------------------------------
# 4. SIDEBAR INPUT
# ----------------------------------------------------
st.sidebar.header("🎯 Post Scorecard")
player_name = st.sidebar.text_input("Golfer Name", placeholder="e.g., Tiger").strip()
wordle_paste = st.sidebar.text_area("Paste Wordle Share Text", placeholder="Wordle 1,843 3/6...", height=120)

if st.sidebar.button("🚀 Post Score to Clubhouse"):
    if not player_name or not wordle_paste:
        st.sidebar.error("Fill out both fields first!")
    else:
        w_num, strokes = parse_wordle_text(wordle_paste)
        if w_num is not None:
            _, hole = get_round_start_and_hole(w_num)
            
            if player_name not in st.session_state.scores:
                st.session_state.scores[player_name] = {}
                
            st.session_state.scores[player_name][hole] = strokes
            
            shoutout = SCORE_NAMES.get(strokes, "🎯 SCORE")
            st.toast(f"📢 {player_name} dropped a {shoutout} on Hole {hole}!", icon="⛳")
            st.sidebar.success(f"Logged Hole {hole} (Wordle {w_num})")
        else:
            st.sidebar.error("Could not read Wordle layout. Check your clipboard copy!")

# ----------------------------------------------------
# 5. DATA ANALYSIS & STATE COMPUTATION
# ----------------------------------------------------
if st.session_state.scores:
    all_players = list(st.session_state.scores.keys())
    
    if len(all_players) < 2:
        st.info("👋 Waiting for both golfers to log a score to map out match dynamics.")
    else:
        p1, p2 = all_players[0], all_players[1]
        
        # Track max hole submitted anywhere
        p1_holes = st.session_state.scores[p1].keys()
        p2_holes = st.session_state.scores[p2].keys()
        max_submitted_hole = max(max(p1_holes) if p1_holes else 1, max(p2_holes) if p2_holes else 1)
        
        # 1. Regulation Cumulative Calculations (Only holes completed by BOTH players)
        reg_completed_holes = []
        reg_totals = {p1: 0, p2: 0}
        
        for h in range(1, 19):
            s1 = st.session_state.scores[p1].get(h)
            s2 = st.session_state.scores[p2].get(h)
            if s1 is not None and s2 is not None:
                reg_completed_holes.append(h)
                reg_totals[p1] += s1
                reg_totals[p2] += s2

        regulation_finished = len(reg_completed_holes) == 18
        
        # 2. Playoff Logic Matrix
        playoff_active = False
        playoff_winner = None
        current_playoff_hole = 19
        
        if regulation_finished and reg_totals[p1] == reg_totals[p2]:
            playoff_active = True
            while True:
                s1_p = st.session_state.scores[p1].get(current_playoff_hole)
                s2_p = st.session_state.scores[p2].get(current_playoff_hole)
                
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
        # 6. DYNAMIC COMMENTARY GENERATOR
        # ----------------------------------------------------
        st.header("🎙️ Live Broadcast Booth")
        if st.button("🎤 Get Live Broadcast Commentary"):
            comm_list = []
            
            # Context-based analysis
            if playoff_active:
                comm_list.append(f"🎙️ 'We are deep into unexpected drama here at the Wordle Pro Tour! Regulation play couldn't separate them, and we are officially out on the links in a sudden-death playoff. Total ice in the veins is required right now.'")
                s1_p = st.session_state.scores[p1].get(current_playoff_hole)
                s2_p = st.session_state.scores[p2].get(current_playoff_hole)
                if (s1_p is not None and s2_p is None) or (s2_p is not None and s1_p is None):
                    lone_player = p1 if s1_p is not None else p2
                    comm_list.append(f"🎙️ 'The pressure is mounting. {lone_player} has already thrown down an early marker on Playoff Hole {current_playoff_hole}. The response will dictate the tournament!'")
            else:
                comm_list.append(f"🎙️ 'Welcome back to the gallery. We are analyzing a tense round of regulation action across the standard 18-hole block.'")
                
                # Check for single-player pacing leads
                if len(p1_holes) != len(p2_holes):
                    pacing_leader = p1 if len(p1_holes) > len(p2_holes) else p2
                    comm_list.append(f"🎙️ 'Fascinating pacing dynamic today. {pacing_leader} is moving rapidly through the course, putting early pressure on the clubhouse board while their opponent plays catch-up.'")
                
                # Analyze aggregate standing
                diff = reg_totals[p1] - reg_totals[p2]
                if diff == 0:
                    if len(reg_completed_holes) > 0:
                        comm_list.append(f"🎙️ 'Looking at the official locked scores, it's a dead heat! They are locked completely level over the {len(reg_completed_holes)} holes verified by both scorecards.'")
                    else:
                        comm_list.append("🎙️ 'Early stages yet. The scorecards are clean, and both players are searching for an opening line.'")
                else:
                    leader = p2 if diff > 0 else p1
                    chaser = p1 if diff > 0 else p2
                    comm_list.append(f"🎙️ 'Through the verified shared holes, **{leader}** currently holds the structural advantage, forcing **{chaser}** into an aggressive chasing profile if they want to claw back.'")
                    
                # Look for exceptional highlight scores
                all_combined_scores = list(st.session_state.scores[p1].values()) + list(st.session_state.scores[p2].values())
                if -2 in all_combined_scores or -3 in all_combined_scores:
                    comm_list.append("🎙️ 'The crowds went absolutely wild earlier today—we saw brilliant sub-par accuracy out there. True championship pedigree execution.'")
                    
            st.markdown(f"""
            <div class="commentary-box">
                {'<br><br>'.join(comm_list)}
            </div>
            """, unsafe_allow_html=True)
            
        st.write("---")

        # ----------------------------------------------------
        # 7. WINNER CELEBRATION BANNERS
        # ----------------------------------------------------
        if playoff_winner:
            champ, loser = playoff_winner, (p1 if playoff_winner == p2 else p2)
            st.balloons()
            st.markdown(f'<div class="winner-banner">🏆 SUDDEN DEATH CHAMPION: {champ.upper()}! 🏆</div>', unsafe_allow_html=True)
            st.success(f"👏 **Unbelievable composure, {champ}!** You locked it down when the margin for error was completely zero!")
            st.info(f"🩹 **Tough break, {loser}.** To lose on playoff territory is absolute heartbreak. Your revenge tour starts tomorrow.")
            
        elif regulation_finished and not playoff_active:
            if reg_totals[p1] != reg_totals[p2]:
                champ = p1 if reg_totals[p1] < reg_totals[p2] else p2
                loser = p2 if champ == p1 else p1
                st.balloons()
                st.markdown(f'<div class="winner-banner">👑 TOURNAMENT CHAMPION: {champ.upper()}! 👑</div>', unsafe_allow_html=True)
                st.success(f"🏆 **Great tournament, {champ}!** Slapping on the green jacket after a stellar display over 18 holes!")
                st.info(f"🩹 **Console tent for {loser}:** A few bad bounces out there on the back nine. Reset your letters and challenge them again on the next even track.")

        # ----------------------------------------------------
        # 8. SCANNABLE TOURNAMENT CARDS
        # ----------------------------------------------------
        st.header("🏆 Live Standings")
        col1, col2 = st.columns(2)
        
        with col1:
            diff = reg_totals[p1] - reg_totals[p2]
            if diff < 0:
                leader_str = f"⚡ **{p1}** leads by **{abs(diff)}** strokes (on holes both have finished)"
            elif diff > 0:
                leader_str = f"⚡ **{p2}** leads by **{abs(diff)}** strokes (on holes both have finished)"
            else:
                leader_str = "⚖️ **All Square!** Level pegs on verified territory."
                
            card_style = "metric-card playoff-card" if playoff_active else "metric-card"
            st.markdown(f'<div class="{card_style}"><h4 style="margin:0; color:white;">Aggregate Score Leader</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{leader_str}</p></div>', unsafe_allow_html=True)

        with col2:
            status_text = "🚨 PLAYOFFS ACTIVE (Sudden Death)" if playoff_active else f"⛳ Regulation: {len(reg_completed_holes)}/18 Holes Verified"
            st.markdown(f'<div class="metric-card" style="border-left-color: #3b82f6;"><h4 style="margin:0; color:white;">Tournament Progression</h4><p style="margin:5px 0 0 0; color:#cbd5e1; font-size:16px;">{status_text}</p></div>', unsafe_allow_html=True)

        # ----------------------------------------------------
        # 9. DETAILED SCOREBOARD MATRIX
        # ----------------------------------------------------
        st.subheader("📊 Tournament Scoreboard Matrix")
        
        matrix_rows = []
        limit = max(18, max_submitted_hole)
        for h in range(1, limit + 1):
            if h > 18 and h > max_submitted_hole:
                continue
                
            s1 = st.session_state.scores[p1].get(h, None)
            s2 = st.session_state.scores[p2].get(h, None)
            
            row_label = f"Hole {h}"
            if h > 18:
                row_label += " 🚨 [Playoff]"
                
            matrix_rows.append({
                "Hole": row_label,
                p1: f"{s1:+}" if s1 is not None else "⏳ Waiting",
                p2: f"{s2:+}" if s2 is not None else "⏳ Waiting",
                "Status": "✅ Verified" if (s1 is not None and s2 is not None) else "📢 Unbalanced (Awaiting Opponent)"
            })
            
        st.dataframe(pd.DataFrame(matrix_rows), use_container_width=True, hide_index=True)

        # Clear Option
        if st.button("🔄 Archive and Start New Round"):
            st.session_state.scores = {}
            st.rerun()
else:
    st.info("⛳ The leaderboard is currently vacant. Paste your standard Wordle snippets on the sidebar to tee off!")

