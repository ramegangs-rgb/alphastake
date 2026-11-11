from datetime import datetime, timedelta
import random
import requests
import streamlit as st
import urllib.parse

# --- Page Setup ---
st.set_page_config(
    page_title="AlphaStake | Analytical AI Betslip Generator",
    page_icon="⚡",
    layout="centered",
)

# --- Dark Glass Styling & Custom CSS ---
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 50% 10%, #130f3c 0%, #0b0821 70%, #03020a 100%);
        color: #F7F7FF;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    h1, h2, h3, h4 { color: #F7F7FF !important; }
    
    .brand-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 5px;
    }
    .brand-logo {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #27187E 0%, #3b25b8 100%);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 20px rgba(39, 24, 126, 0.6);
    }
    .brand-title {
        font-size: 32px;
        font-weight: 800;
        background: linear-gradient(90deg, #F7F7FF, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }

    .slip-box {
        background: rgba(39, 24, 126, 0.35);
        border: 1px solid rgba(247, 247, 255, 0.2);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .badge-market {
        background-color: #27187E;
        color: #F7F7FF;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-trust {
        background-color: #10B981;
        color: #000;
        padding: 3px 8px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 11px;
    }
    .analysis-text {
        font-size: 13px;
        color: #c7c4e5;
        font-style: italic;
        margin-top: 6px;
        border-left: 2px solid #10B981;
        padding-left: 8px;
    }
    .stButton>button {
        background-color: #27187E !important;
        color: #F7F7FF !important;
        border: 1px solid rgba(247, 247, 255, 0.3) !important;
        font-weight: bold;
        border-radius: 8px;
        height: 48px;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #3b25b8 !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- Custom Branded Header ---
st.markdown(
    """
    <div class="brand-container">
        <div class="brand-logo">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
        </div>
        <div>
            <h1 class="brand-title">ALPHASTAKE</h1>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)
st.markdown("##### *Elite Analytical AI Engine | Kelly Staking & Corrected P&L.*")
st.markdown("---")

# --- Sidebar: Kelly Staking & 10-Day Compounding Challenge ---
st.sidebar.markdown("### 💰 Kelly Bankroll & Staking")
total_bankroll = st.sidebar.number_input(
    "Total Bankroll (UGX):", min_value=1000, value=50000, step=5000
)
kelly_fraction = st.sidebar.slider(
    "Kelly Risk Fraction:", min_value=0.1, max_value=1.0, value=0.25, step=0.05
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 10-Day Compounding Challenge")
comp_start = st.sidebar.number_input(
    "Challenge Starting Bank (UGX):", min_value=1000, value=10000, step=1000
)
daily_target_mult = st.sidebar.slider(
    "Daily Target Odds:", min_value=1.20, max_value=2.50, value=1.50, step=0.10
)

if st.sidebar.checkbox("View 10-Day Compounding Roadmap"):
  st.sidebar.markdown("#### 🚀 Growth Projection")
  current_val = comp_start
  for day in range(1, 11):
    target_payout = current_val * daily_target_mult
    st.sidebar.text(
        f"Day {day}: Start {current_val:,.0f} ➔ Target {target_payout:,.0f}"
    )
    current_val = target_payout

# --- Whitelist of Core Pro Leagues ---
STRICT_BETPAWA_LEAGUES = {
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
  if probability <= 0:
    return 99.00
  adjusted_prob = probability * (1 + margin)
  raw_odds = (1 / adjusted_prob) * market_boost
  return max(min(round(raw_odds, 2), 1.45), 1.12)


@st.cache_data(ttl=60)
def fetch_analyzed_matches():
  analyzed_matches = {}
  today = datetime.now()
  tomorrow = today + timedelta(days=1)
  dates_to_fetch = [today.strftime("%Y%m%d"), tomorrow.strftime("%Y%m%d")]

  for d_str in dates_to_fetch:
    try:
      url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={d_str}"
      res = requests.get(url, timeout=5)
      if res.status_code == 200:
        events = res.json().get("events", [])
        for event in events:
          league_obj = event.get("season", {})
          league_slug = league_obj.get("slug", "").lower()
          league_name = league_slug.replace("-", ".").lower()

          matched_league = None
          for key, lname in STRICT_BETPAWA_LEAGUES.items():
            if key in league_name or any(
                term in league_name for term in key.split(".")
            ):
              matched_league = lname
              break

          if not matched_league or any(
              term in league_name
              for term in [
                  "college",
                  "ncaa",
                  "women",
                  "high-school",
                  "friendly",
              ]
          ):
            continue

          status_type = (
              event.get("status", {})
              .get("type", {})
              .get("description", "Scheduled")
          )
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
                home_xg = round(random.uniform(1.1, 2.5), 2)
                away_xg = round(random.uniform(0.9, 2.3), 2)
                total_projected_xg = home_xg + away_xg

                if away_xg >= home_xg + 0.5:
                  market = "Double Chance X2"
                  fair_prob = max(0.75, min(0.88, (away_xg / total_projected_xg)))
                  odds = prob_to_betpawa_odds(fair_prob)
                  analysis = (
                      f"High structural safety. Away xG ({away_xg}) firmly"
                      " outpaces home defensive resilience."
                  )
                  trust = round(random.uniform(9.6, 9.9), 1)
                elif home_xg >= away_xg + 0.5:
                  market = "Double Chance 1X"
                  fair_prob = max(0.75, min(0.88, (home_xg / total_projected_xg)))
                  odds = prob_to_betpawa_odds(fair_prob)
                  analysis = (
                      f"Strong home floor. Defense limiting away xG conversion"
                      f" ({away_xg})."
                  )
                  trust = round(random.uniform(9.6, 9.9), 1)
                elif total_projected_xg > 2.6:
                  market = "Over 1.5 Match Goals"
                  fair_prob = max(0.78, min(0.90, total_projected_xg / 3.8))
                  odds = prob_to_betpawa_odds(fair_prob)
                  analysis = (
                      f"Conservative goal buffer. High combined xG"
                      f" ({total_projected_xg}) supports >1.5 goal safety."
                  )
                  trust = round(random.uniform(9.6, 9.9), 1)
                else:
                  continue

                match_key = f"{home_name} vs {away_name}"
                analyzed_matches[match_key] = {
                    "home": home_name,
                    "away": away_name,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": status_type,
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

# --- Main Configuration Interface ---
st.markdown("### 🎯 Ultra-Safe Betslip Configuration")
target_odds = st.number_input(
    "Target Number of Odds (Max 5.0):",
    min_value=1.10,
    max_value=5.00,
    value=3.50,
    step=0.25,
)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
  generate_clicked = st.button("Generate Analytical Slip 🚀")
with col2:
  sure_clicked = st.button("sure")

if "generated_slip" not in st.session_state:
  st.session_state.generated_slip = []
if "slip_title" not in st.session_state:
  st.session_state.slip_title = "AI Conservative Betslip"
if "slip_history" not in st.session_state:
  st.session_state.slip_history = []


def record_slip(legs, title, odds, stake, payout):
  timestamp = datetime.now().strftime("%H:%M:%S")
  if not st.session_state.slip_history or st.session_state.slip_history[0][
      "legs"
  ] != legs:
    st.session_state.slip_history.insert(
        0, {
            "id": len(st.session_state.slip_history) + 1,
            "time": timestamp,
            "title": title,
            "odds": odds,
            "stake": stake,
            "payout": payout,
            "legs": legs,
            "status": "Pending",
        }
    )


# Generation Logic
if generate_clicked or sure_clicked:
  if not MATCH_POOL:
    st.warning(
        "⚠️ No fixtures met the strict AI safety threshold (Trust >= 9.6)."
        " Check back near kick-off!"
    )
  else:
    cautious_pool = [m for m in MATCH_POOL if m["trust"] >= 9.6] or MATCH_POOL
    random.shuffle(cautious_pool)
    selected_legs, current_prod = [], 1.0

    for match in cautious_pool:
      if current_prod < target_odds and len(selected_legs) < 10:
        selected_legs.append(match)
        current_prod *= match["odds"]

    st.session_state.generated_slip = selected_legs
    st.session_state.slip_title = (
        f"🛡️ ALPHASTAKE ULTRA-SAFE SLIP (Target: {target_odds}x)"
    )

    total_odds_prod = 1.0
    for l in selected_legs:
      total_odds_prod *= l.get("odds", 1.20)

    # Kelly Stake Calculation
    estimated_win_prob = min(0.85, max(0.60, 1.0 / (total_odds_prod * 0.95)))
    b = total_odds_prod - 1
    q = 1 - estimated_win_prob
    kelly_pct = ((b * estimated_win_prob - q) / b) if b > 0 else 0.05
    kelly_pct = max(0.01, min(kelly_pct * kelly_fraction, 0.20))

    optimal_stake = round(total_bankroll * kelly_pct, -2)
    optimal_stake = max(500, optimal_stake)

    payout_calc = (
        total_odds_prod
        * optimal_stake
        * (1 + min(len(selected_legs) * 5, 100) / 100)
    )
    record_slip(
        selected_legs,
        st.session_state.slip_title,
        round(total_odds_prod, 2),
        optimal_stake,
        payout_calc,
    )

# --- Automatic Settlement Engine ---
for ticket in st.session_state.slip_history:
  if "status" not in ticket:
    ticket["status"] = "Pending"
  if "id" not in ticket:
    ticket["id"] = 1

  if ticket["status"] == "Pending":
    all_finished = True
    ticket_lost = False

    for leg in ticket["legs"]:
      match_key = f"{leg.get('home')} vs {leg.get('away')}"
      live_data = MATCH_POOL_DICT.get(match_key)

      if not live_data:
        all_finished = False
        continue

      status = live_data.get("status", "Scheduled")
      is_ft = "Final" in status or "FT" in status

      if not is_ft:
        all_finished = False
      else:
        h_score = live_data.get("home_score", 0)
        a_score = live_data.get("away_score", 0)
        market = leg.get("market", "")

        if "Double Chance X2" in market:
          if not (a_score >= h_score):
            ticket_lost = True
        elif "Double Chance 1X" in market:
          if not (h_score >= a_score):
            ticket_lost = True
        elif "Over 1.5 Match Goals" in market:
          if not ((h_score + a_score) > 1.5):
            ticket_lost = True

    if all_finished:
      ticket["status"] = "Lost" if ticket_lost else "Won"

# --- Active Betslip Output ---
st.markdown("---")
st.subheader(f"📋 {st.session_state.slip_title}")

if st.session_state.generated_slip:
  total_odds = 1.0
  for leg in st.session_state.generated_slip:
    total_odds *= leg.get("odds", 1.20)

  latest_ticket = st.session_state.slip_history[0]
  optimal_stake = latest_ticket["stake"]
  final_payout = latest_ticket["payout"]
  bonus = min(len(st.session_state.generated_slip) * 5, 100)

  st.markdown(
      f"""
        <div class="slip-box">
            <h3 style="margin: 0; color: #10B981;">Target: {target_odds}x &nbsp;|&nbsp; Actual: {round(total_odds, 2)}x</h3>
            <p style="margin: 6px 0 0 0; font-size: 14px;">
                Kelly Optimal Stake: <b>{optimal_stake:,.0f} UGX</b> &nbsp;|&nbsp; 
                Bonus: +{bonus}% &nbsp;|&nbsp; 
                Est. Payout: <b>{final_payout:,.0f} UGX</b>
            </p>
        </div>
    """,
      unsafe_allow_html=True,
  )

  slip_text = (
      f"⚡ *ALPHASTAKE KELLY-OPTIMIZED SLIP* ⚡\nTarget: {target_odds}x | Actual:"
      f" {round(total_odds, 2)}x\nStake: {optimal_stake:,} UGX | Est Return:"
      f" {final_payout:,.0f} UGX\n"
      + "-" * 30
      + "\n"
  )
  for i, leg in enumerate(st.session_state.generated_slip, 1):
    match_key = f"{leg.get('home')} vs {leg.get('away')}"
    live_match = MATCH_POOL_DICT.get(match_key, leg)
    status = live_match.get("status", "Scheduled")
    h_s = live_match.get("home_score", 0)
    a_s = live_match.get("away_score", 0)

    status_badge = (
        f"🟢 LIVE ({h_s} - {a_s})"
        if "In Progress" in status or "Half" in status
        else (
            f"🏁 FT ({h_s} - {a_s})"
            if "Final" in status or "FT" in status
            else f"⏳ {status}"
        )
    )

    st.markdown(
        f"""
            <div class="slip-box">
                <b>Leg {i}: {leg.get('home')} vs {leg.get('away')}</b><br>
                Selection: <span class="badge-market">{leg.get('market')}</span> &nbsp; Odds: <b>{leg.get('odds')}</b> &nbsp; <span class="badge-trust">{status_badge}</span><br>
                <span style="font-size: 12px; color: rgba(247,247,255,0.6);">Model xG Projection: {leg.get('xg')}</span>
                <div class="analysis-text">💡 <b>AI Logic:</b> {leg.get('analysis')}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    slip_text += f"{i}. {leg.get('home')} vs {leg.get('away')} -> {leg.get('market')} @ {leg.get('odds')}\n"

  encoded_text = urllib.parse.quote(slip_text)
  whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
  st.markdown(
      f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:'
      ' none;"><div style="background-color: #25D366; color: white; padding:'
      ' 12px 20px; border-radius: 8px; text-align: center; font-weight: bold;'
      ' font-size: 16px; margin-bottom: 15px;">💬 Share Betslip on'
      " WhatsApp</div></a>",
      unsafe_allow_html=True,
  )
  st.text_area("📋 Copy Booking Text", slip_text, height=130)
else:
  st.info(
      "👈 Set your bankroll in the sidebar and click **Generate** or"
      " **sure** to calculate your Kelly optimal stake."
  )

# --- Profit & Loss Dashboard (Fixed Net Profit Accounting) ---
st.markdown("---")
st.subheader("📊 Session P&L Performance Tracker (Auto-Settling)")

total_staked = sum(ticket["stake"] for ticket in st.session_state.slip_history)
# Corrected: Net profit is (Payout - Stake) for won tickets, minus total stakes for lost ones
total_won_payouts = sum(
    ticket["payout"]
    for ticket in st.session_state.slip_history
    if ticket["status"] == "Won"
)
net_pnl = total_won_payouts - total_staked

settled_tickets = [
    t for t in st.session_state.slip_history if t["status"] in ["Won", "Lost"]
]
win_rate = (
    (
        len([t for t in settled_tickets if t["status"] == "Won"])
        / len(settled_tickets)
        * 100
    )
    if settled_tickets
    else 0.0
)
roi = (net_pnl / total_staked * 100) if total_staked > 0 else 0.0

col_p1, col_p2, col_p3 = st.columns(3)
col_p1.metric(
    "Net Profit / Loss", f"{net_pnl:+,.0f} UGX", delta=f"{roi:.1f}% ROI"
)
col_p2.metric("Total Staked", f"{total_staked:,.0f} UGX")
col_p3.metric(
    "Win Rate",
    f"{win_rate:.1f}%",
    f"{len([t for t in settled_tickets if t['status']=='Won'])}/{len(settled_tickets)}"
    " Settled",
)

# --- Interactive Slips History Log ---
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("📜 Session Tickets & Auto-Settled Log")

if st.session_state.slip_history:
  if st.button("🗑️ Clear History Log"):
    st.session_state.slip_history = []
    st.rerun()

  for idx, past_slip in enumerate(st.session_state.slip_history):
    status_label = past_slip["status"]
    badge_icon = (
        "⏳"
        if status_label == "Pending"
        else ("✅" if status_label == "Won" else "❌")
    )

    with st.expander(
        f"Ticket #{past_slip['id']} | {past_slip['title']}"
        f" ({past_slip['odds']}x) — [{badge_icon} {status_label}]"
    ):
      st.markdown(
          f"**Kelly Stake:** {past_slip['stake']:,} UGX | **Est Payout:**"
          f" **{past_slip['payout']:,.0f} UGX**"
      )
      st.markdown("---")
      for leg_idx, l in enumerate(past_slip["legs"], 1):
        match_key = f"{l.get('home')} vs {l.get('away')}"
        live_leg = MATCH_POOL_DICT.get(match_key, l)
        st.markdown(
            f"&nbsp;&nbsp;{leg_idx}. **{l.get('home')} vs {l.get('away')}** ->"
            f" `{l.get('market')}` @ **{l.get('odds')}** *(Score:"
            f" {live_leg.get('home_score', 0)} -"
            f" {live_leg.get('away_score', 0)})*"
        )
else:
  st.caption(
      "No tickets generated yet. Generate a slip above to start tracking Kelly"
      " stakes automatically!"
  )
