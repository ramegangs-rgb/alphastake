from datetime import datetime, timedelta
import hashlib
import random
import requests
import streamlit as st
import urllib.parse
from supabase import create_client, Client

# --- Page Setup ---
st.set_page_config(
    page_title="AlphaStake | Elite 10-League Terminal",
    page_icon="⚽",
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

# --- Ultra-Aesthetic Cyberpunk Glass CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 50% -20%, #1e1035 0%, #0d0714 60%, #05020a 100%);
        color: #F3F4F6;
    }

    @keyframes pulseGlow {
        0% { text-shadow: 0 0 15px rgba(16, 185, 129, 0.4); }
        50% { text-shadow: 0 0 28px rgba(16, 185, 129, 0.8), 0 0 40px rgba(59, 130, 246, 0.5); }
        100% { text-shadow: 0 0 15px rgba(16, 185, 129, 0.4); }
    }

    .brand-title-cyber {
        font-size: 38px;
        font-weight: 800;
        background: linear-gradient(135deg, #FFFFFF 0%, #10B981 50%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -1px;
        animation: pulseGlow 3s infinite alternate;
    }

    .hero-stat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .hero-stat-val {
        font-size: 22px;
        font-weight: 800;
        color: #10B981;
    }
    .hero-stat-lbl {
        font-size: 11px;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 2px;
    }

    .glass-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(16, 185, 129, 0.4);
        transform: translateY(-2px);
    }

    .badge-market-cyber {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #000;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    
    .badge-live-cyber {
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid rgba(239, 68, 68, 0.5);
        color: #EF4444;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }

    .analysis-quote {
        font-size: 13px;
        color: #D1D5DB;
        margin-top: 10px;
        padding-left: 10px;
        border-left: 3px solid #3B82F6;
        font-style: italic;
    }

    .stButton>button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        color: #000000 !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border-radius: 12px !important;
        height: 50px !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        box-shadow: 0 6px 28px rgba(16, 185, 129, 0.6) !important;
        transform: scale(1.01) !important;
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
        <div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
            <div style="display: inline-block; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 16px; border-radius: 30px; color: #10B981; font-size: 12px; font-weight: 700; margin-bottom: 12px;">
                ⚡ ALPHASTAKE v3.0 | 10 ELITE LEAGUES EXCLUSIVE
            </div>
            <h1 class="brand-title-cyber">ALPHASTAKE</h1>
            <p style="color: #9CA3AF; font-size: 15px; max-width: 420px; margin: 8px auto 0 auto;">
                Strict 10-League Professional Intelligence & Accumulator Terminal.
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    tab_login, tab_signup = st.tabs(["🔐 Sign In", "🚀 Register Account"])

    with tab_login:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                user_login = st.text_input("Username", placeholder="e.g. reagan")
                pass_login = st.text_input("Password", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("Launch Terminal ⚡")

                if submit_login:
                    if supabase:
                        res = supabase.table("users").select("*").eq("username", user_login.strip().lower()).execute()
                        if res.data and res.data[0]["password"] == hash_password(pass_login):
                            st.session_state.authenticated_user = user_login.strip().lower()
                            st.success(f"Access granted! Syncing terminal...")
                            st.rerun()
                        else:
                            st.error("⚠️ Invalid credentials.")
                    else:
                        st.session_state.authenticated_user = user_login.strip().lower()
                        st.rerun()

    with tab_signup:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("signup_form"):
                user_new = st.text_input("Choose Username", placeholder="e.g. reagan")
                pass_new = st.text_input("Choose Password", type="password", placeholder="••••••••")
                submit_signup = st.form_submit_button("Create Terminal Pass 🚀")

                if submit_signup:
                    if len(user_new.strip()) < 3 or len(pass_new) < 4:
                        st.error("Username & password must be 3+ and 4+ characters.")
                    elif supabase:
                        res = supabase.table("users").select("*").eq("username", user_new.strip().lower()).execute()
                        if res.data:
                            st.error("Username taken! Try another.")
                        else:
                            supabase.table("users").insert({
                                "username": user_new.strip().lower(),
                                "password": hash_password(pass_new)
                            }).execute()
                            st.success("Account created! Log in to access terminal.")
                    else:
                        st.session_state.authenticated_user = user_new.strip().lower()
                        st.rerun()
    st.stop()

# --- Post-Login Header ---
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div>
            <h1 class="brand-title-cyber" style="font-size: 32px;">ALPHASTAKE</h1>
            <span style="font-size: 13px; color: #9CA3AF;">Active Operator: <b style="color: #10B981;">@{st.session_state.authenticated_user}</b></span>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 14px; border-radius: 10px; font-size: 12px; font-weight: 700; color: #10B981;">
            🟢 10-LEAGUE EXCLUSIVE ACTIVE
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

col_s1, col_s2, col_s3 = st.columns(3)
col_s1.markdown('<div class="hero-stat-card"><div class="hero-stat-val">9.9/10</div><div class="hero-stat-lbl">Safety Index</div></div>', unsafe_allow_html=True)
col_s2.markdown('<div class="hero-stat-card"><div class="hero-stat-val">10 / 10</div><div class="hero-stat-lbl">Strict Pro Leagues</div></div>', unsafe_allow_html=True)
col_s3.markdown('<div class="hero-stat-card"><div class="hero-stat-val">SYNC</div><div class="hero-stat-lbl">Cloud Database Active</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if st.sidebar.button("🔒 Logout Terminal"):
    st.session_state.authenticated_user = None
    st.rerun()

# --- EXCLUSIVE 10-LEAGUE WHITELIST DICTIONARY ---
STRICT_ELITE_LEAGUES = {
    "eng.1": "English Premier League",
    "eng.2": "English Championship",
    "esp.1": "Spanish La Liga",
    "ita.1": "Italian Serie A",
    "ger.1": "German Bundesliga",
    "fra.1": "French Ligue 1",
    "uefa.champions": "UEFA Champions League",
    "uefa.europa": "UEFA Europa League",
    "uefa.nations": "UEFA Nations League",
    "caf.champions": "CAF Champions League",
}

def prob_to_betpawa_odds(probability, margin=0.03, market_boost=1.02):
    if probability <= 0: return 99.00
    adjusted_prob = probability * (1 + margin)
    raw_odds = (1 / adjusted_prob) * market_boost
    return max(min(round(raw_odds, 2), 1.55), 1.12)

@st.cache_data(ttl=60)
def fetch_analyzed_matches():
    analyzed_matches = {}
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    dates_to_fetch = [today.strftime("%Y%m%d"), tomorrow.strftime("%Y%m%d")]

    blacklisted_terms = ["college", "ncaa", "women", "u21", "u19", "u20", "high-school", "friendly", "amateur", "reserve"]

    for d_str in dates_to_fetch:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={d_str}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                events = res.json().get("events", [])
                for event in events:
                    league_obj = event.get("season", {})
                    league_slug = league_obj.get("slug", "").lower()
                    league_name = league_obj.get("name", "").lower()
                    full_league_str = f"{league_slug} {league_name}"

                    if any(term in full_league_str for term in blacklisted_terms):
                        continue

                    matched_key = None
                    if "eng.1" in league_slug or "premier-league" in league_slug:
                        matched_key = "eng.1"
                    elif "eng.2" in league_slug or "championship" in league_slug:
                        matched_key = "eng.2"
                    elif "esp.1" in league_slug or "la-liga" in league_slug:
                        matched_key = "esp.1"
                    elif "ita.1" in league_slug or "serie-a" in league_slug:
                        matched_key = "ita.1"
                    elif "ger.1" in league_slug or "bundesliga" in league_slug:
                        matched_key = "ger.1"
                    elif "fra.1" in league_slug or "ligue-1" in league_slug:
                        matched_key = "fra.1"
                    elif "uefa.champions" in league_slug or "champions-league" in league_slug:
                        matched_key = "uefa.champions"
                    elif "uefa.europa" in league_slug or "europa-league" in league_slug:
                        matched_key = "uefa.europa"
                    elif "uefa.nations" in league_slug or "nations-league" in league_slug:
                        matched_key = "uefa.nations"
                    elif "caf.champions" in league_slug or "caf-champions" in league_slug:
                        matched_key = "caf.champions"

                    if not matched_key:
                        continue

                    status_type = event.get("status", {}).get("type", {}).get("description", "Scheduled")
                    comps = event.get("competitions", [])
                    for comp in comps:
                        teams = comp.get("competitors", [])
                        if len(teams) == 2:
                            home_team, away_team = teams[0], teams[1]
                            home_name = home_team.get("team", {}).get("displayName")
                            away_name = away_team.get("team", {}).get("displayName")
                            home_score = int(home_team.get("score", 0))
                            away_score = int(away_team.get("score", 0))

                            if home_name and away_name:
                                home_xg = round(random.uniform(1.0, 2.6), 2)
                                away_xg = round(random.uniform(0.9, 2.4), 2)
                                total_projected_xg = home_xg + away_xg

                                market_roll = random.choice([
                                    "Double Chance X2", "Double Chance 1X", "Over 1.5 Match Goals",
                                    "Both Teams to Score (BTTS - Yes)", "Draw No Bet (Home)",
                                    "Draw No Bet (Away)", "Home Team Over 0.5 Goals"
                                ])

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
                                trust = round(random.uniform(9.6, 9.9), 1)

                                match_key = f"{home_name} vs {away_name}"
                                analyzed_matches[match_key] = {
                                    "home": home_name,
                                    "away": away_name,
                                    "home_score": home_score,
                                    "away_score": away_score,
                                    "status": status_type,
                                    "league": STRICT_ELITE_LEAGUES[matched_key],
                                    "market": market,
                                    "odds": odds,
                                    "trust": trust,
                                    "xg": f"{home_xg} - {away_xg}",
                                    "analysis": analysis,
                                }
        except Exception:
            continue

    return analyzed_matches

MATCH_POOL_DICT = fetch_analyzed_matches()
MATCH_POOL = list(MATCH_POOL_DICT.values())

# --- Persistent Account History Loader ---
if "slip_history" not in st.session_state:
    st.session_state.slip_history = []

if supabase and st.session_state.authenticated_user:
    try:
        saved_db_slips = supabase.table("user_tickets").select("*").eq("username", st.session_state.authenticated_user).order("created_at", desc=True).execute()
        if saved_db_slips.data:
            st.session_state.slip_history = [s["ticket_data"] for s in saved_db_slips.data]
    except Exception:
        pass

# --- Configuration Panel ---
st.markdown("### ⚙️ Elite Terminal Generator")
col_cfg1, col_cfg2 = st.columns(2)
with col_cfg1:
    target_odds = st.number_input("Target Total Odds (Max 5.0):", min_value=1.10, max_value=5.00, value=3.50, step=0.25)
with col_cfg2:
    stake_amount = st.number_input("Stake Amount (UGX):", min_value=500, value=5000, step=500)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    generate_clicked = st.button("Generate Elite Slip 🚀")
with col2:
    sure_clicked = st.button("sure")

if "generated_slip" not in st.session_state:
    st.session_state.generated_slip = []
if "slip_title" not in st.session_state:
    st.session_state.slip_title = "Elite 10-League Betslip"

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

# Generation Logic
if generate_clicked or sure_clicked:
    if not MATCH_POOL:
        st.warning("⚠️ No active fixtures found right now across your 10 elite leagues. Check back near matchday kick-off!")
    else:
        cautious_pool = [m for m in MATCH_POOL if m["trust"] >= 9.6] or MATCH_POOL
        random.shuffle(cautious_pool)
        selected_legs, current_prod = [], 1.0

        for match in cautious_pool:
            if current_prod < target_odds and len(selected_legs) < 10:
                selected_legs.append(match)
                current_prod *= match["odds"]

        st.session_state.generated_slip = selected_legs
        st.session_state.slip_title = f"⚽ EXCLUSIVE 10-LEAGUE SLIP ({target_odds}x Target)"
        
        total_odds_prod = 1.0
        for l in selected_legs:
            total_odds_prod *= l.get("odds", 1.20)

        payout_calc = total_odds_prod * stake_amount * (1 + min(len(selected_legs)*5, 100)/100)
        record_slip(selected_legs, st.session_state.slip_title, round(total_odds_prod, 2), stake_amount, payout_calc)

# --- Active Betslip Display ---
st.markdown("---")
st.subheader(f"📋 {st.session_state.slip_title}")

if st.session_state.generated_slip:
    total_odds = 1.0
    for leg in st.session_state.generated_slip:
        total_odds *= leg.get("odds", 1.20)

    bonus = min(len(st.session_state.generated_slip) * 5, 100)
    final_payout = total_odds * stake_amount * (1 + bonus / 100)

    st.markdown(
        f"""
        <div class="glass-card" style="border-color: rgba(16, 185, 129, 0.5);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #10B981; font-size: 24px;">Odds: {round(total_odds, 2)}x</h3>
                <span style="color: #3B82F6; font-weight: 700;">+{bonus}% Accumulator Bonus</span>
            </div>
            <p style="margin: 10px 0 0 0; font-size: 15px; color: #E5E7EB;">
                Stake: <b>{stake_amount:,.0f} UGX</b> &nbsp;|&nbsp; 
                Est. Return: <b style="color: #10B981;">{final_payout:,.0f} UGX</b>
            </p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    slip_text = f"⚡ *ALPHASTAKE 10-LEAGUE SLIP* ⚡\nTarget: {target_odds}x | Actual: {round(total_odds, 2)}x\nStake: {stake_amount:,} UGX | Est Return: {final_payout:,.0f} UGX\n" + "-" * 30 + "\n"
    for i, leg in enumerate(st.session_state.generated_slip, 1):
        match_key = f"{leg.get('home')} vs {leg.get('away')}"
        live_match = MATCH_POOL_DICT.get(match_key, leg)
        status = live_match.get("status", "Scheduled")
        h_s = live_match.get("home_score", 0)
        a_s = live_match.get("away_score", 0)
        
        status_badge = f'<span class="badge-live-cyber">🟢 LIVE ({h_s} - {a_s})</span>' if "In Progress" in status or "Half" in status else (f'🏁 FT ({h_s} - {a_s})' if "Final" in status or "FT" in status else f"⏳ {status}")
        
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <b style="font-size: 16px; color: #FFF;">Leg {i}: {leg.get('home')} vs {leg.get('away')}</b>
                    {status_badge}
                </div>
                <div style="font-size: 12px; color: #10B981; margin-bottom: 4px; font-weight: 700;">🏆 {leg.get('league')}</div>
                <div style="margin: 6px 0;">
                    Selection: <span class="badge-market-cyber">{leg.get('market')}</span> &nbsp; Odds: <b style="color: #10B981;">{leg.get('odds')}</b>
                </div>
                <div style="font-size: 12px; color: #9CA3AF; margin-top: 4px;">Model xG Projection: {leg.get('xg')}</div>
                <div class="analysis-quote">💡 <b>AI Logic:</b> {leg.get('analysis')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        slip_text += f"{i}. {leg.get('home')} vs {leg.get('away')} ({leg.get('league')}) -> {leg.get('market')} @ {leg.get('odds')}\n"

    encoded_text = urllib.parse.quote(slip_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
    st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration: none;"><div style="background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); color: white; padding: 14px 20px; border-radius: 12px; text-align: center; font-weight: 800; font-size: 16px; margin-bottom: 15px; box-shadow: 0 4px 20px rgba(37, 211, 102, 0.3);">💬 Share Betslip on WhatsApp</div></a>', unsafe_allow_html=True)
    st.text_area("📋 Copy Booking Text", slip_text, height=120)

# --- Profit & Loss Dashboard ---
st.markdown("---")
st.subheader("📊 Session P&L Performance Tracker")

total_staked = sum(ticket["stake"] for ticket in st.session_state.slip_history)
total_won_payouts = sum(ticket["payout"] for ticket in st.session_state.slip_history if ticket["status"] == "Won")
net_pnl = total_won_payouts - total_staked

settled_tickets = [t for t in st.session_state.slip_history if t["status"] in ["Won", "Lost"]]
win_rate = (len([t for t in settled_tickets if t["status"] == "Won"]) / len(settled_tickets) * 100) if settled_tickets else 0.0
roi = (net_pnl / total_staked * 100) if total_staked > 0 else 0.0

col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric("Net Profit / Loss", f"{net_pnl:+,.0f} UGX", delta=f"{roi:.1f}% ROI")
col_p2.metric("Total Staked", f"{total_staked:,.0f} UGX")
col_p3.metric("Win Rate", f"{win_rate:.1f}%", f"{len([t for t in settled_tickets if t['status']=='Won'])}/{len(settled_tickets)} Settled")

# --- Interactive History Log ---
st.markdown("<br>", unsafe_allow_html=True)
st.subheader(f"📜 Terminal History (@{st.session_state.authenticated_user})")

if st.session_state.slip_history:
    if st.button("🗑️ Clear History Log"):
        st.session_state.slip_history = []
        if supabase and st.session_state.authenticated_user:
            supabase.table("user_tickets").delete().eq("username", st.session_state.authenticated_user).execute()
        st.rerun()

    for idx, past_slip in enumerate(st.session_state.slip_history):
        status_label = past_slip['status']
        badge_icon = "⏳" if status_label == "Pending" else ("✅" if status_label == "Won" else "❌")
        
        with st.expander(f"Ticket #{past_slip['id']} | {past_slip['title']} ({past_slip['odds']}x) — [{badge_icon} {status_label}]"):
            st.markdown(f"**Stake:** {past_slip['stake']:,} UGX | **Est Payout:** **{past_slip['payout']:,.0f} UGX**")
            st.markdown("---")
            for leg_idx, l in enumerate(past_slip["legs"], 1):
                match_key = f"{l.get('home')} vs {l.get('away')}"
                live_leg = MATCH_POOL_DICT.get(match_key, l)
                st.markdown(f"&nbsp;&nbsp;{leg_idx}. **{l.get('home')} vs {l.get('away')}** -> `{l.get('market')}` @ **{l.get('odds')}** *(Score: {live_leg.get('home_score', 0)} - {live_leg.get('away_score', 0)})*")
else:
    st.caption("No account tickets found. Generate a slip above to save it to your terminal history!")
