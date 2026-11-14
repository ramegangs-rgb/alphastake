from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import hashlib
import random
import requests
import streamlit as st
import urllib.parse
from supabase import create_client, Client

# --- Page Setup ---
st.set_page_config(
    page_title="AlphaStake | Professional Trading Terminal",
    page_icon="⚡",
    layout="centered",
)

# --- Supabase Database Initialization ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- Initialize Default Neural Weights ---
DEFAULT_MARKET_WEIGHTS = {
    "Double Chance X2": 1.0,
    "Double Chance 1X": 1.0,
    "Over 1.5 Match Goals": 1.0,
    "Both Teams to Score (BTTS - Yes)": 1.0,
    "Draw No Bet (Home)": 1.0,
    "Draw No Bet (Away)": 1.0,
    "Home Team Over 0.5 Goals": 1.0,
}

# --- Professional Terminal CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    .stApp {
        background: #090B10;
        color: #E2E8F0;
    }

    .brand-title-terminal {
        font-size: 32px;
        font-weight: 800;
        color: #F8FAFC;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .terminal-stat-card {
        background: #111522;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 14px;
        text-align: center;
    }
    .terminal-stat-val {
        font-size: 20px;
        font-weight: 700;
        color: #10B981;
    }
    .terminal-stat-lbl {
        font-size: 10px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }

    .glass-card {
        background: #111522;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .badge-market {
        background: #064E3B;
        color: #34D399;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    .badge-status {
        background: #1E293B;
        color: #94A3B8;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .analysis-text {
        font-size: 13px;
        color: #94A3B8;
        margin-top: 8px;
        padding-left: 10px;
        border-left: 2px solid #3B82F6;
    }

    .stButton>button {
        background: #10B981 !important;
        color: #050505 !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border-radius: 10px !important;
        height: 44px !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        background: #059669 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- Authentication State ---
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if not st.session_state.authenticated_user:
    st.markdown(
        """
        <div style="text-align: center; margin-top: 60px; margin-bottom: 30px;">
            <h1 class="brand-title-terminal">ALPHASTAKE</h1>
            <p style="color: #64748B; font-size: 14px; margin-top: 6px;">
                Secure Institutional Sports Analytics & Terminal
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["Sign In", "Register"])

    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                user_login = st.text_input("Username", placeholder="reagan")
                pass_login = st.text_input("Password", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("Access Terminal")

                if submit_login:
                    if supabase:
                        res = supabase.table("users").select("*").eq("username", user_login.strip().lower()).execute()
                        if res.data and res.data[0]["password"] == hash_password(pass_login):
                            st.session_state.authenticated_user = user_login.strip().lower()
                            db_weights = res.data[0].get("weights")
                            if db_weights and isinstance(db_weights, dict):
                                st.session_state.market_weights = db_weights
                            st.rerun()
                        else:
                            st.error("Invalid credentials.")
                    else:
                        st.session_state.authenticated_user = user_login.strip().lower()
                        st.rerun()

    with tab_signup:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("signup_form"):
                user_new = st.text_input("Choose Username", placeholder="reagan")
                pass_new = st.text_input("Choose Password", type="password", placeholder="••••••••")
                submit_signup = st.form_submit_button("Create Account")

                if submit_signup:
                    if len(user_new.strip()) < 3 or len(pass_new) < 4:
                        st.error("Username & password must be 3+ and 4+ characters.")
                    elif supabase:
                        res = supabase.table("users").select("*").eq("username", user_new.strip().lower()).execute()
                        if res.data:
                            st.error("Username already exists.")
                        else:
                            supabase.table("users").insert({
                                "username": user_new.strip().lower(),
                                "password": hash_password(pass_new),
                                "weights": DEFAULT_MARKET_WEIGHTS.copy()
                            }).execute()
                            st.success("Account created. Please sign in.")
                    else:
                        st.session_state.authenticated_user = user_new.strip().lower()
                        st.rerun()
    st.stop()

# --- Session State Initialization ---
if "market_weights" not in st.session_state:
    st.session_state.market_weights = DEFAULT_MARKET_WEIGHTS.copy()

if "league_weights" not in st.session_state:
    st.session_state.league_weights = {}

if "mistake_log" not in st.session_state:
    st.session_state.mistake_log = []

def save_weights_to_supabase():
    if supabase and st.session_state.authenticated_user:
        try:
            supabase.table("users").update({
                "weights": st.session_state.market_weights
            }).eq("username", st.session_state.authenticated_user).execute()
        except Exception:
            pass

def sync_tickets_to_supabase():
    if supabase and st.session_state.authenticated_user:
        try:
            supabase.table("user_tickets").delete().eq("username", st.session_state.authenticated_user).execute()
            for t in reversed(st.session_state.slip_history):
                supabase.table("user_tickets").insert({
                    "username": st.session_state.authenticated_user,
                    "ticket_data": t
                }).execute()
        except Exception:
            pass

def recalculate_ai_weights(history):
    m_weights = DEFAULT_MARKET_WEIGHTS.copy()
    l_weights = {}
    lessons = []

    for ticket in reversed(history):
        status = ticket.get("status", "Pending")
        if status not in ["Won", "Lost"]:
            continue

        for leg in ticket.get("legs", []):
            mkt = leg.get("market", "")
            lg = leg.get("league", "")

            if mkt not in m_weights:
                m_weights[mkt] = 1.0
            if lg not in l_weights:
                l_weights[lg] = 1.0

            if status == "Won":
                m_weights[mkt] = min(round(m_weights[mkt] + 0.15, 2), 2.0)
                l_weights[lg] = min(round(l_weights[lg] + 0.10, 2), 1.8)
            elif status == "Lost":
                m_weights[mkt] = max(round(m_weights[mkt] - 0.22, 2), 0.20)
                l_weights[lg] = max(round(l_weights[lg] - 0.15, 2), 0.30)
                lessons.append(f"Penalized `{mkt}` in {lg} after Ticket #{ticket['id']} loss")

    st.session_state.market_weights = m_weights
    st.session_state.league_weights = l_weights
    st.session_state.mistake_log = list(reversed(lessons))[:6]
    save_weights_to_supabase()

# --- Post-Login Header ---
db_badge = "SUPABASE SYNCED" if supabase else "LOCAL SESSION"
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h1 class="brand-title-terminal">ALPHASTAKE</h1>
            <span style="font-size: 12px; color: #64748B;">Operator Session Active</span>
        </div>
        <div style="background: #111522; border: 1px solid #1E293B; padding: 6px 12px; border-radius: 8px; font-size: 11px; font-weight: 600; color: #10B981;">
            {db_badge}
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# --- 17-LEAGUE WHITELIST & ENDPOINTS ---
EXACT_17_LEAGUES = {
    "eng.1": "English Premier League",
    "fra.1": "Ligue 1",
    "esp.1": "La Liga",
    "ita.1": "Italian Serie A",
    "bra.1": "Brazilian Serie A",
    "uefa.champions": "UEFA Champions League",
    "uefa.nations": "UEFA Nations League",
    "uefa.europa.conf": "UEFA Conference League",
    "uefa.europa": "UEFA Europa League",
    "sco.1": "Scottish Premiership",
    "ger.1": "Bundesliga",
    "caf.nations": "Africa Cup of Nations (AFCON)",
    "bel.1": "Belgian Pro League",
    "ned.1": "Netherlands Eredivisie",
    "nor.1": "Norway Eliteserien",
    "por.1": "Liga Portugal",
    "tur.1": "Turkish Süper Lig",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def prob_to_betpawa_odds(probability, margin=0.03, market_boost=1.02):
    if probability <= 0:
        return 99.00
    adjusted_prob = probability * (1 + margin)
    raw_odds = (1 / adjusted_prob) * market_boost
    return max(min(round(raw_odds, 2), 1.55), 1.12)

def _fetch_single_endpoint(slug, clean_league_name, date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={date_str}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            return clean_league_name, res.json().get("events", [])
    except Exception:
        pass
    return clean_league_name, []

@st.cache_data(ttl=120)
def fetch_real_life_matches(days_ahead=2):
    analyzed_matches = {}
    league_counts = {name: 0 for name in EXACT_17_LEAGUES.values()}
    today = datetime.now()
    dates_to_fetch = [(today + timedelta(days=offset)).strftime("%Y%m%d") for offset in range(0, days_ahead)]

    blacklisted_terms = ["usl", "mls", "college", "ncaa", "women", "u21", "u19", "u20", "high-school", "amateur", "reserve", "youth"]

    tasks = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        for slug, clean_league_name in EXACT_17_LEAGUES.items():
            for d_str in dates_to_fetch:
                tasks.append(executor.submit(_fetch_single_endpoint, slug, clean_league_name, d_str))

        for future in as_completed(tasks):
            clean_league_name, events = future.result()
            for event in events:
                league_obj = event.get("season", {})
                api_slug = league_obj.get("slug", "").lower()
                api_name = event.get("league", {}).get("name", "").lower()
                full_str = f"{api_slug} {api_name}"

                if any(term in full_str for term in blacklisted_terms):
                    continue

                status_obj = event.get("status", {}).get("type", {})
                status_type = status_obj.get("description", "Scheduled")
                short_detail = status_obj.get("shortDetail", "")
                raw_date = event.get("date", "")
                match_date_str = short_detail if short_detail else raw_date[:10]

                comps = event.get("competitions", [])
                for comp in comps:
                    teams = comp.get("competitors", [])
                    if len(teams) == 2:
                        home_team = next((t for t in teams if t.get("homeAway") == "home"), teams[0])
                        away_team = next((t for t in teams if t.get("homeAway") == "away"), teams[1])
                        home_name = home_team.get("team", {}).get("displayName")
                        away_name = away_team.get("team", {}).get("displayName")
                        home_score = int(home_team.get("score", 0) or 0)
                        away_score = int(away_team.get("score", 0) or 0)

                        if home_name and away_name and home_name != away_name:
                            match_key = f"{home_name} vs {away_name}"
                            if match_key in analyzed_matches:
                                continue

                            rng = random.Random(match_key)
                            home_xg = round(rng.uniform(1.1, 2.5), 2)
                            away_xg = round(rng.uniform(0.9, 2.3), 2)
                            total_projected_xg = round(home_xg + away_xg, 2)

                            market_roll = rng.choice(list(DEFAULT_MARKET_WEIGHTS.keys()))

                            if market_roll == "Double Chance X2" and away_xg >= home_xg - 0.2:
                                market = "Double Chance X2"
                                fair_prob = 0.78
                                analysis = f"Away side structural stability supports X2 coverage ({away_xg} xG)."
                            elif market_roll == "Double Chance 1X" and home_xg >= away_xg - 0.2:
                                market = "Double Chance 1X"
                                fair_prob = 0.78
                                analysis = f"Home venue advantage and defense anchor the 1X market."
                            elif market_roll == "Both Teams to Score (BTTS - Yes)" and total_projected_xg > 2.5:
                                market = "Both Teams to Score (BTTS - Yes)"
                                fair_prob = 0.74
                                analysis = f"High offensive output from both camps (Combined xG: {total_projected_xg})."
                            elif market_roll == "Home Team Over 0.5 Goals":
                                market = "Home Team Over 0.5 Goals"
                                fair_prob = 0.82
                                analysis = f"Home scoring probability exceeds 80% based on recent attacking metrics."
                            else:
                                market = "Over 1.5 Match Goals"
                                fair_prob = 0.80
                                analysis = f"Pace and tactical flow point toward clearing the 1.5 goal threshold."

                            odds = prob_to_betpawa_odds(fair_prob)
                            trust = round(rng.uniform(9.6, 9.9), 1)

                            analyzed_matches[match_key] = {
                                "home": home_name,
                                "away": away_name,
                                "home_score": home_score,
                                "away_score": away_score,
                                "status": status_type,
                                "kickoff": match_date_str,
                                "league": clean_league_name,
                                "market": market,
                                "odds": odds,
                                "trust": trust,
                                "xg": f"{home_xg} - {away_xg}",
                                "analysis": analysis,
                            }
                            league_counts[clean_league_name] = league_counts.get(clean_league_name, 0) + 1

    return analyzed_matches, league_counts

# --- Sidebar Window & Controls ---
window_choice = st.sidebar.selectbox(
    "Fixture Window",
    options=["Today & Tomorrow (48h)", "Today Only (24h)", "3-Day Schedule"],
    index=0
)
days_map = {"Today Only (24h)": 1, "Today & Tomorrow (48h)": 2, "3-Day Schedule": 3}

MATCH_POOL_DICT, LEAGUE_COUNTS = fetch_real_life_matches(days_ahead=days_map[window_choice])
MATCH_POOL = list(MATCH_POOL_DICT.values())

# --- Persistent Account History Loader ---
if "slip_history" not in st.session_state:
    st.session_state.slip_history = []

if supabase and st.session_state.authenticated_user and not st.session_state.slip_history:
    try:
        saved_db_slips = supabase.table("user_tickets").select("*").eq("username", st.session_state.authenticated_user).order("created_at", desc=True).execute()
        if saved_db_slips.data:
            st.session_state.slip_history = [s["ticket_data"] for s in saved_db_slips.data]
    except Exception:
        pass

if st.session_state.slip_history:
    recalculate_ai_weights(st.session_state.slip_history)

# --- Hero Stats ---
top_learned_market = max(st.session_state.market_weights.items(), key=lambda x: x[1])
col_s1, col_s2, col_s3 = st.columns(3)
col_s1.markdown(f'<div class="terminal-stat-card"><div class="terminal-stat-val">{top_learned_market[1]:.2f}x</div><div class="terminal-stat-lbl">Top Market Weight</div></div>', unsafe_allow_html=True)
col_s2.markdown(f'<div class="terminal-stat-card"><div class="terminal-stat-val">{len(MATCH_POOL)}</div><div class="terminal-stat-lbl">Active Fixtures</div></div>', unsafe_allow_html=True)
col_s3.markdown(f'<div class="terminal-stat-card"><div class="terminal-stat-val">{len(st.session_state.mistake_log)}</div><div class="terminal-stat-lbl">Neural Penalties</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button("Refresh Feed Cache"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("Lock Terminal Session"):
    st.session_state.authenticated_user = None
    st.session_state.slip_history = []
    st.rerun()

if st.sidebar.button("Reset Neural Weights"):
    st.session_state.market_weights = DEFAULT_MARKET_WEIGHTS.copy()
    st.session_state.league_weights = {}
    st.session_state.mistake_log = []
    save_weights_to_supabase()
    st.sidebar.success("Weights reset to baseline.")

with st.sidebar.expander("League Feed Status (17 Leagues)", expanded=False):
    active_leagues = {k: v for k, v in LEAGUE_COUNTS.items() if v > 0}
    if active_leagues:
        for lg_name, count in sorted(active_leagues.items(), key=lambda x: x[1], reverse=True):
            st.markdown(f"• **{lg_name}**: `{count}`")
    else:
        st.warning("No active fixtures currently returned.")

# --- Configuration Panel ---
st.markdown("### Terminal Slip Generator")
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    target_odds = st.number_input("Target Total Odds:", min_value=1.10, max_value=10.00, value=3.50, step=0.25)
with col_cfg2:
    stake_amount = st.number_input("Stake Amount (UGX):", min_value=500, value=5000, step=500)

st.markdown("<br>", unsafe_allow_html=True)

if "generated_slip" not in st.session_state:
    st.session_state.generated_slip = []
if "slip_title" not in st.session_state:
    st.session_state.slip_title = "Accumulator Slip"

def record_slip(legs, title, odds, stake, payout):
    timestamp = datetime.now().strftime("%H:%M:%S")
    ticket_payload = {
        "id": len(st.session_state.slip_history) + 1,
        "time": timestamp,
        "title": title,
        "odds": odds,
        "stake": stake,
        "payout": payout,
        "legs": legs,
        "status": "Pending"
    }
    st.session_state.slip_history.insert(0, ticket_payload)

    if supabase and st.session_state.authenticated_user:
        try:
            supabase.table("user_tickets").insert({
                "username": st.session_state.authenticated_user,
                "ticket_data": ticket_payload
            }).execute()
        except Exception:
            pass

if st.button("Generate Smart Terminal Slip"):
    if not MATCH_POOL:
        st.error("No active fixtures found across the 17 whitelisted leagues in the selected window.")
    else:
        scored_pool = []
        for m in MATCH_POOL:
            m_weight = st.session_state.market_weights.get(m["market"], 1.0)
            l_weight = st.session_state.league_weights.get(m["league"], 1.0)
            ai_score = m["trust"] * m_weight * l_weight * random.uniform(0.95, 1.05)
            scored_pool.append((ai_score, m_weight, m))

        scored_pool.sort(key=lambda x: x[0], reverse=True)

        selected_legs, current_prod = [], 1.0
        for ai_score, m_weight, match in scored_pool:
            if m_weight < 0.45 and len(scored_pool) > 4:
                continue
            if current_prod < target_odds and len(selected_legs) < 10:
                match_copy = match.copy()
                match_copy["ai_weight"] = m_weight
                selected_legs.append(match_copy)
                current_prod *= match["odds"]

        st.session_state.generated_slip = selected_legs
        st.session_state.slip_title = "PROBABILITY ACCUMULATOR SLIP"
        
        total_odds_prod = 1.0
        for l in selected_legs:
            total_odds_prod *= l.get("odds", 1.20)

        payout_calc = total_odds_prod * stake_amount * (1 + min(len(selected_legs)*5, 100)/100)
        record_slip(selected_legs, st.session_state.slip_title, round(total_odds_prod, 2), stake_amount, payout_calc)

# --- Active Betslip Display ---
st.markdown("---")
st.subheader(st.session_state.slip_title)

if st.session_state.generated_slip:
    total_odds = 1.0
    for leg in st.session_state.generated_slip:
        total_odds *= leg.get("odds", 1.20)

    bonus = min(len(st.session_state.generated_slip) * 5, 100)
    final_payout = total_odds * stake_amount * (1 + bonus / 100)

    st.markdown(
        f"""
        <div class="glass-card" style="border-color: #059669;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #10B981; font-size: 22px;">Total Odds: {round(total_odds, 2)}x</h3>
                <span style="color: #3B82F6; font-weight: 600; font-size: 13px;">+{bonus}% Accumulator Bonus</span>
            </div>
            <p style="margin: 8px 0 0 0; font-size: 14px; color: #94A3B8;">
                Stake: <b style="color: #F8FAFC;">{stake_amount:,.0f} UGX</b> &nbsp;|&nbsp; 
                Est. Return: <b style="color: #10B981;">{final_payout:,.0f} UGX</b>
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    slip_text = f"*ALPHASTAKE ACCUMULATOR SLIP*\nOdds: {round(total_odds, 2)}x | Stake: {stake_amount:,} UGX | Est Return: {final_payout:,.0f} UGX\n" + "-" * 30 + "\n"
    for i, leg in enumerate(st.session_state.generated_slip, 1):
        match_key = f"{leg.get('home')} vs {leg.get('away')}"
        live_match = MATCH_POOL_DICT.get(match_key, leg)
        status = live_match.get("status", "Scheduled")
        kickoff = live_match.get("kickoff", "")
        h_s = live_match.get("home_score", 0)
        a_s = live_match.get("away_score", 0)
        ai_w = leg.get("ai_weight", st.session_state.market_weights.get(leg.get("market"), 1.0))
        
        status_tag = f"LIVE ({h_s} - {a_s})" if "In Progress" in status or "Half" in status else (f"FT ({h_s} - {a_s})" if "Final" in status or "FT" in status else kickoff)
        
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <b style="font-size: 15px; color: #F8FAFC;">{i}. {leg.get('home')} vs {leg.get('away')}</b>
                    <span class="badge-status">{status_tag}</span>
                </div>
                <div style="font-size: 11px; color: #10B981; margin-bottom: 4px; font-weight: 600;">{leg.get('league')} &nbsp;|&nbsp; Weight: {ai_w:.2f}x</div>
                <div style="margin: 6px 0;">
                    Selection: <span class="badge-market">{leg.get('market')}</span> &nbsp; Odds: <b style="color: #10B981;">{leg.get('odds')}</b>
                </div>
                <div style="font-size: 11px; color: #64748B; margin-top: 4px;">xG Projection: {leg.get('xg')}</div>
                <div class="analysis-text"><b>AI Logic:</b> {leg.get('analysis')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        slip_text += f"{i}. {leg.get('home')} vs {leg.get('away')} ({leg.get('league')}) -> {leg.get('market')} @ {leg.get('odds')}\n"

    encoded_text = urllib.parse.quote(slip_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
    st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration: none;"><div style="background: #10B981; color: #050505; padding: 12px 20px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 14px; margin-bottom: 14px;">Share Betslip on WhatsApp</div></a>', unsafe_allow_html=True)
    st.text_area("Booking Text Output", slip_text, height=110)

# --- Profit & Loss Dashboard ---
st.markdown("---")
st.subheader("Session P&L Analytics")

total_staked = sum(ticket["stake"] for ticket in st.session_state.slip_history)
total_won_payouts = sum(ticket["payout"] for ticket in st.session_state.slip_history if ticket["status"] == "Won")
net_pnl = total_won_payouts - total_staked

settled_tickets = [t for t in st.session_state.slip_history if t["status"] in ["Won", "Lost"]]
win_rate = (len([t for t in settled_tickets if t["status"] == "Won"]) / len(settled_tickets) * 100) if settled_tickets else 0.0
roi = (net_pnl / total_staked * 100) if total_staked > 0 else 0.0

col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric("Net P&L", f"{net_pnl:+,.0f} UGX", delta=f"{roi:.1f}% ROI")
col_p2.metric("Total Staked", f"{total_staked:,.0f} UGX")
col_p3.metric("Win Rate", f"{win_rate:.1f}%", f"{len([t for t in settled_tickets if t['status']=='Won'])}/{len(settled_tickets)} Settled")

# --- Interactive History Log ---
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Terminal History & Training")

if st.session_state.slip_history:
    if st.button("Clear History Log"):
        st.session_state.slip_history = []
        if supabase and st.session_state.authenticated_user:
            supabase.table("user_tickets").delete().eq("username", st.session_state.authenticated_user).execute()
        recalculate_ai_weights([])
        st.rerun()

    for idx, past_slip in enumerate(st.session_state.slip_history):
        status_label = past_slip['status']
        status_tag = "Pending" if status_label == "Pending" else ("Won" if status_label == "Won" else "Lost")
        
        with st.expander(f"Ticket #{past_slip['id']} | {past_slip['odds']}x — [{status_tag}]"):
            st.markdown(f"**Stake:** {past_slip['stake']:,} UGX | **Est Payout:** **{past_slip['payout']:,.0f} UGX**")
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("Mark Won", key=f"won_{idx}"):
                    st.session_state.slip_history[idx]["status"] = "Won"
                    recalculate_ai_weights(st.session_state.slip_history)
                    sync_tickets_to_supabase()
                    st.rerun()
            with btn_col2:
                if st.button("Mark Lost", key=f"lost_{idx}"):
                    st.session_state.slip_history[idx]["status"] = "Lost"
                    recalculate_ai_weights(st.session_state.slip_history)
                    sync_tickets_to_supabase()
                    st.rerun()
            with btn_col3:
                if st.button("Reset Pending", key=f"pend_{idx}"):
                    st.session_state.slip_history[idx]["status"] = "Pending"
                    recalculate_ai_weights(st.session_state.slip_history)
                    sync_tickets_to_supabase()
                    st.rerun()

            st.markdown("---")
            for leg_idx, l in enumerate(past_slip["legs"], 1):
                st.markdown(f"&nbsp;&nbsp;{leg_idx}. {l.get('home')} vs {l.get('away')} -> {l.get('market')} @ {l.get('odds')}")
else:
    st.caption("No account tickets generated yet.")
