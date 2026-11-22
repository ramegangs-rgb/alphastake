from datetime import datetime, timedelta, timezone
import hashlib
import random
from typing import Any

import requests
import streamlit as st
from supabase import Client, create_client

# ==============================================================================
# PAGE CONFIG & EXCLUSIVE 17 LEAGUES
# ==============================================================================
st.set_page_config(
    page_title="ALPHASTAKE // TERMINAL",
    layout="wide",
    initial_sidebar_state="expanded",
)

LEAGUE_CONFIG: list[dict[str, Any]] = [
    {"name": "English Premier League", "slug": "eng.1", "weight": 1.08},
    {"name": "Ligue 1", "slug": "fra.1", "weight": 1.02},
    {"name": "La Liga", "slug": "esp.1", "weight": 1.05},
    {"name": "Italian Serie A", "slug": "ita.1", "weight": 1.04},
    {"name": "Brazilian Serie A", "slug": "bra.1", "weight": 1.00},
    {"name": "UEFA Champions League", "slug": "uefa.champions", "weight": 1.06},
    {"name": "UEFA Nations League", "slug": "uefa.nations", "weight": 0.96},
    {"name": "UEFA Conference League", "slug": "uefa.europa.conf", "weight": 0.97},
    {"name": "UEFA Europa League", "slug": "uefa.europa", "weight": 1.02},
    {"name": "Scottish Premiership", "slug": "sco.1", "weight": 0.99},
    {"name": "Bundesliga", "slug": "ger.1", "weight": 1.07},
    {"name": "Africa Cup of Nations", "slug": "caf.nations", "weight": 0.95},
    {"name": "Belgian Pro League", "slug": "bel.1", "weight": 1.01},
    {"name": "Netherlands Eredivisie", "slug": "ned.1", "weight": 1.05},
    {"name": "Norwegian Eliteserien", "slug": "nor.1", "weight": 1.02},
    {"name": "Liga Portugal", "slug": "por.1", "weight": 1.03},
    {"name": "Turkish Süper Lig", "slug": "tur.1", "weight": 1.02},
]

FINISHED_TOKENS = (
    "ft",
    "full time",
    "full-time",
    "final",
    "post",
    "completed",
    "finished",
    "aet",
    "pen",
    "end_period",
)

MARKET_TEMPLATES: list[dict[str, Any]] = [
    {"market": "Over 1.5 Match Goals", "base_odds": 1.24},
    {"market": "Home Team Over 0.5 Goals", "base_odds": 1.21},
    {"market": "Double Chance 1X", "base_odds": 1.27},
    {"market": "Both Teams to Score (BTTS - Yes)", "base_odds": 1.34},
    {"market": "Over 2.5 Match Goals", "base_odds": 1.62},
]


# ==============================================================================
# SAFE LEG & STATUS HELPERS
# ==============================================================================
def get_leg_match(leg: Any) -> str:
    if isinstance(leg, str):
        return leg
    if not isinstance(leg, dict):
        return "Match"
    home = leg.get("home") or leg.get("home_team")
    away = leg.get("away") or leg.get("away_team")
    fallback = f"{home} vs {away}" if home and away else "Match"
    return str(
        leg.get("matchup")
        or leg.get("match")
        or leg.get("fixture")
        or leg.get("event")
        or leg.get("name")
        or fallback
    )


def get_leg_league(leg: Any) -> str:
    if not isinstance(leg, dict):
        return "League"
    return str(leg.get("league") or leg.get("competition") or "League")


def get_leg_kickoff(leg: Any) -> str:
    if not isinstance(leg, dict):
        return "Upcoming"
    return str(leg.get("kickoff") or leg.get("time") or leg.get("date") or "Upcoming")


def get_leg_market(leg: Any) -> str:
    if not isinstance(leg, dict):
        return "Market"
    return str(leg.get("market") or leg.get("pick") or leg.get("selection") or "Market")


def get_leg_odds(leg: Any) -> float:
    if not isinstance(leg, dict):
        return 1.0
    try:
        return float(leg.get("odds", 1.0))
    except (TypeError, ValueError):
        return 1.0


def is_upcoming_fixture(item: Any) -> bool:
    if not isinstance(item, dict):
        return True
    if item.get("is_completed") or item.get("is_finished") or item.get("completed"):
        return False
    status_str = " ".join(
        str(item.get(k) or "")
        for k in ("status", "status_detail", "match_status", "state")
    ).strip().lower()
    if not status_str:
        return True
    return not any(tok in status_str for tok in FINISHED_TOKENS)


# ==============================================================================
# MINIMALIST QUANT TERMINAL THEME
# ==============================================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        code, pre, .mono {
            font-family: 'JetBrains Mono', monospace !important;
            font-variant-numeric: tabular-nums;
        }
        .stApp {
            background: radial-gradient(circle at 12% 0%, #0d1b2a 0%, #070b12 45%, #05070c 100%);
            color: #e6edf3;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3.5rem;
            max-width: 1220px;
        }
        section[data-testid="stSidebar"] {
            background-color: #090e17;
            border-right: 1px solid rgba(148, 163, 184, 0.12);
        }
        .terminal-header {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            justify-content: space-between;
            gap: 0.75rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            margin-bottom: 1.4rem;
        }
        .brand-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            color: #f8fafc;
            margin: 0;
        }
        .brand-sub {
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #64748b;
            margin-top: 0.15rem;
        }
        .status-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.28rem 0.7rem;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.73rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            background: rgba(16, 185, 129, 0.08);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.28);
        }
        .status-chip.warn {
            background: rgba(245, 158, 11, 0.08);
            color: #fbbf24;
            border-color: rgba(251, 191, 36, 0.28);
        }
        .dot-live {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #34d399;
            box-shadow: 0 0 8px #34d399;
        }
        .telemetry-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
            gap: 0.75rem;
            margin-bottom: 1.75rem;
        }
        .tele-card {
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 10px;
            padding: 0.8rem 0.95rem;
        }
        .tele-label {
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 0.3rem;
        }
        .tele-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.15rem;
            font-weight: 700;
            color: #f8fafc;
            font-variant-numeric: tabular-nums;
        }
        .panel-card {
            background: rgba(13, 19, 31, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1.25rem;
        }
        .panel-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.11em;
            text-transform: uppercase;
            color: #cbd5e1;
            margin-bottom: 0.9rem;
        }
        .slip-leg {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.55rem;
            border-radius: 8px;
            background: rgba(2, 6, 23, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.11);
            border-left: 3px solid #10b981;
        }
        .leg-match {
            font-weight: 600;
            font-size: 0.94rem;
            color: #f1f5f9;
        }
        .leg-meta {
            font-size: 0.76rem;
            color: #94a3b8;
            margin-top: 0.15rem;
        }
        .leg-right {
            text-align: right;
            white-space: nowrap;
        }
        .leg-mkt {
            font-size: 0.82rem;
            color: #cbd5e1;
        }
        .leg-odds {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            font-weight: 700;
            color: #34d399;
        }
        .slip-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 0.75rem;
            margin-top: 0.35rem;
            border-top: 1px dashed rgba(148, 163, 184, 0.2);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.88rem;
            color: #e2e8f0;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.85rem;
        }
        @media (max-width: 768px) {
            .kpi-grid { grid-template-columns: 1fr; }
        }
        .kpi-card {
            background: rgba(2, 6, 23, 0.65);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 10px;
            padding: 0.95rem 1.05rem;
        }
        .kpi-title {
            font-size: 0.72rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            color: #94a3b8;
        }
        .kpi-num {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.45rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0.25rem 0;
            font-variant-numeric: tabular-nums;
        }
        .kpi-num.pos { color: #34d399; }
        .kpi-num.neg { color: #f87171; }
        .kpi-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #64748b;
        }
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.84rem;
            border: 1px solid rgba(148, 163, 184, 0.2);
            transition: all 0.15s ease;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: #04130d;
            border: none;
        }
        .stButton > button[kind="primary"]:hover {
            filter: brightness(1.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# SUPABASE & AUTH HELPERS
# ==============================================================================
@st.cache_resource
def get_supabase_client() -> Client | None:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_session_state() -> None:
    defaults: dict[str, Any] = {
        "authenticated": False,
        "username": "",
        "weights": {"market_multiplier": 1.00, "penalties": 0},
        "tickets": [],
        "current_slip": [],
        "fixture_cache_bust": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def fetch_user_record(sb: Client | None, username: str) -> dict[str, Any] | None:
    if not sb:
        return None
    res = sb.table("users").select("*").eq("username", username).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def load_user_tickets(sb: Client | None, username: str) -> list[dict[str, Any]]:
    if not sb:
        return st.session_state.get("tickets", [])
    res = (
        sb.table("user_tickets")
        .select("*")
        .eq("username", username)
        .order("id", desc=False)
        .execute()
    )
    rows = res.data or []
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        data = row.get("ticket_data") or {}
        if isinstance(data, dict):
            item = dict(data)
            item.setdefault("db_id", row.get("id"))
            item.setdefault("ticket_no", idx)
            normalized.append(item)
    return normalized


def save_ticket_to_db(sb: Client | None, username: str, ticket: dict[str, Any]) -> None:
    if not sb:
        st.session_state.tickets.append(ticket)
        return
    inserted = (
        sb.table("user_tickets")
        .insert({"username": username, "ticket_data": ticket})
        .execute()
    )
    if inserted.data and isinstance(inserted.data, list):
        ticket["db_id"] = inserted.data[0].get("id")


def update_ticket_status_in_db(
    sb: Client | None, username: str, ticket: dict[str, Any], new_status: str
) -> None:
    ticket["status"] = new_status
    if not sb:
        return
    db_id = ticket.get("db_id")
    if db_id is not None:
        sb.table("user_tickets").update({"ticket_data": ticket}).eq("id", db_id).execute()
    else:
        rows = (
            sb.table("user_tickets")
            .select("id, ticket_data")
            .eq("username", username)
            .execute()
            .data
            or []
        )
        for r in rows:
            td = r.get("ticket_data") or {}
            if td.get("created_at") == ticket.get("created_at") and td.get("odds") == ticket.get("odds"):
                sb.table("user_tickets").update({"ticket_data": ticket}).eq("id", r["id"]).execute()
                break


def update_weights_in_db(sb: Client | None, username: str, weights: dict[str, Any]) -> None:
    st.session_state.weights = weights
    if not sb:
        return
    sb.table("users").update({"weights": weights}).eq("username", username).execute()


# ==============================================================================
# ESPN FIXTURE FEED (UPCOMING MATCHES ONLY — ZERO FT MATCHES)
# ==============================================================================
@st.cache_data(ttl=600, show_spinner=False)
def fetch_espn_fixtures(window_days: int, cache_bust: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    _ = cache_bust
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc + timedelta(days=window_days)
    dates_to_query = [
        (now_utc + timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(0, max(window_days, 1) + 1)
    ]

    all_upcoming: list[dict[str, Any]] = []
    league_counts: dict[str, int] = {cfg["name"]: 0 for cfg in LEAGUE_CONFIG}
    seen_ids: set[str] = set()

    for cfg in LEAGUE_CONFIG:
        league_name = cfg["name"]
        slug = cfg["slug"]
        weight = cfg["weight"]

        for d_str in dates_to_query:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={d_str}"
            try:
                resp = requests.get(url, timeout=6)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
            except Exception:
                continue

            for event in payload.get("events", []):
                ev_id = str(event.get("id", ""))
                if not ev_id or ev_id in seen_ids:
                    continue

                competitions = event.get("competitions", [])
                if not competitions:
                    continue
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue

                home_comp = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away_comp = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

                home_team = (
                    home_comp.get("team", {}).get("shortDisplayName")
                    or home_comp.get("team", {}).get("displayName")
                    or "Home"
                )
                away_team = (
                    away_comp.get("team", {}).get("shortDisplayName")
                    or away_comp.get("team", {}).get("displayName")
                    or "Away"
                )

                status_obj = comp.get("status") or event.get("status") or {}
                status_type = status_obj.get("type") or {}
                completed = bool(status_type.get("completed", False))
                state_str = str(status_type.get("state") or "")
                name_str = str(status_type.get("name") or "")
                short_detail = str(status_type.get("shortDetail") or status_type.get("detail") or "")

                kickoff_str = comp.get("date") or event.get("date") or ""
                kickoff_dt: datetime | None = None
                if kickoff_str:
                    try:
                        kickoff_dt = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
                    except ValueError:
                        kickoff_dt = None

                if kickoff_dt is not None:
                    if kickoff_dt <= now_utc:
                        continue
                    if kickoff_dt > cutoff_utc:
                        continue

                fixture = {
                    "id": ev_id,
                    "league": league_name,
                    "weight": weight,
                    "home": home_team,
                    "away": away_team,
                    "matchup": f"{home_team} vs {away_team}",
                    "kickoff": kickoff_dt.strftime("%b %d %H:%M UTC") if kickoff_dt else "Upcoming",
                    "status": short_detail or state_str or "Scheduled",
                    "status_detail": name_str,
                    "is_completed": completed,
                }

                if not is_upcoming_fixture(fixture):
                    continue

                seen_ids.add(ev_id)
                all_upcoming.append(fixture)
                league_counts[league_name] = league_counts.get(league_name, 0) + 1

    active_league_counts = {k: v for k, v in league_counts.items() if v > 0}
    return all_upcoming, active_league_counts


# ==============================================================================
# SMART SLIP BUILDER (STRICTLY UPCOMING MATCHES)
# ==============================================================================
def build_smart_slip(
    fixtures: list[dict[str, Any]],
    target_odds: float,
    market_multiplier: float,
) -> tuple[list[dict[str, Any]], float]:
    eligible = [f for f in fixtures if is_upcoming_fixture(f)]
    if not eligible:
        return [], 1.0

    rng = random.Random()
    pool = eligible.copy()
    rng.shuffle(pool)

    selected_legs: list[dict[str, Any]] = []
    running_odds = 1.0
    max_legs = min(10, len(pool))

    for fix in pool:
        if len(selected_legs) >= max_legs:
            break
        if running_odds >= target_odds and len(selected_legs) >= 2:
            break

        candidates = sorted(
            MARKET_TEMPLATES,
            key=lambda m: abs(
                (running_odds * round(m["base_odds"] * float(fix.get("weight", 1.0)) * market_multiplier, 2))
                - target_odds
            ),
        )
        chosen_mkt = candidates[0] if running_odds * 1.4 < target_odds else rng.choice(MARKET_TEMPLATES[:4])
        leg_odds = round(
            max(1.15, chosen_mkt["base_odds"] * float(fix.get("weight", 1.0)) * market_multiplier),
            2,
        )

        selected_legs.append(
            {
                "matchup": get_leg_match(fix),
                "league": get_leg_league(fix),
                "kickoff": get_leg_kickoff(fix),
                "status": str(fix.get("status", "Scheduled")),
                "market": chosen_mkt["market"],
                "odds": leg_odds,
            }
        )
        running_odds = round(running_odds * leg_odds, 2)

    return selected_legs, running_odds


# ==============================================================================
# AUTHENTICATION SCREEN
# ==============================================================================
def render_auth_screen(sb: Client | None) -> None:
    chip_cls = "" if sb else "warn"
    chip_txt = "SUPABASE SYNCED" if sb else "LOCAL SESSION"

    st.markdown(
        f"""
        <div class="terminal-header">
            <div>
                <h1 class="brand-title">ALPHASTAKE</h1>
                <div class="brand-sub">QUANTITATIVE MATCH ANALYTICS &amp; SLIP ENGINE</div>
            </div>
            <div>
                <span class="status-chip {chip_cls}"><span class="dot-live"></span>{chip_txt}</span>
                <span class="status-chip">17 LEAGUES</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center_col, _ = st.columns([1, 1.35, 1])
    with center_col:
        st.markdown('<div class="panel-card"><div class="panel-title">Operator Authentication</div>', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username").strip().lower()
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Access Terminal", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Enter both username and password.")
                else:
                    pw_hash = hash_password(password)
                    if sb:
                        user_row = fetch_user_record(sb, username)
                        if not user_row:
                            st.error("Account not found. Switch to Register to create an account.")
                        else:
                            stored_pw = user_row.get("password", "")
                            if pw_hash != stored_pw and password != stored_pw:
                                st.error("Invalid password.")
                            else:
                                st.session_state.authenticated = True
                                st.session_state.username = username
                                st.session_state.weights = user_row.get("weights") or {
                                    "market_multiplier": 1.00,
                                    "penalties": 0,
                                }
                                st.session_state.tickets = load_user_tickets(sb, username)
                                st.session_state.current_slip = []
                                st.rerun()
                    else:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.rerun()

        with tab_register:
            with st.form("register_form"):
                new_user = st.text_input("Choose Username").strip().lower()
                new_pw = st.text_input("Choose Password", type="password")
                confirm_pw = st.text_input("Confirm Password", type="password")
                reg_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if reg_submitted:
                if not new_user or not new_pw:
                    st.error("Username and password are required.")
                elif new_pw != confirm_pw:
                    st.error("Passwords do not match.")
                else:
                    default_weights = {"market_multiplier": 1.00, "penalties": 0}
                    pw_hash = hash_password(new_pw)
                    if sb:
                        if fetch_user_record(sb, new_user):
                            st.error("Username already exists. Sign in instead.")
                        else:
                            sb.table("users").insert(
                                {
                                    "username": new_user,
                                    "password": pw_hash,
                                    "weights": default_weights,
                                }
                            ).execute()
                            st.session_state.authenticated = True
                            st.session_state.username = new_user
                            st.session_state.weights = default_weights
                            st.session_state.tickets = []
                            st.session_state.current_slip = []
                            st.rerun()
                    else:
                        st.session_state.authenticated = True
                        st.session_state.username = new_user
                        st.session_state.weights = default_weights
                        st.session_state.tickets = []
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# MAIN TERMINAL
# ==============================================================================
def render_terminal(sb: Client | None) -> None:
    window_options = {
        "Today & Tomorrow (48h)": 2,
        "3-Day Schedule": 3,
        "7-Day Schedule": 7,
    }

    with st.sidebar:
        st.markdown('<div class="panel-title">Feed &amp; Session Controls</div>', unsafe_allow_html=True)
        selected_window_label = st.selectbox(
            "Fixture Window",
            list(window_options.keys()),
            index=0,
        )
        window_days = window_options[selected_window_label]

        if st.button("Refresh Feed Cache", use_container_width=True):
            st.session_state.fixture_cache_bust += 1
            fetch_espn_fixtures.clear()
            st.rerun()

        if st.button("Reset Neural Weights", use_container_width=True):
            reset_w = {"market_multiplier": 1.00, "penalties": 0}
            update_weights_in_db(sb, st.session_state.username, reset_w)
            st.rerun()

        if st.button("Lock Terminal Session", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_slip = []
            st.rerun()

        fixtures, active_leagues = fetch_espn_fixtures(
            window_days=window_days,
            cache_bust=st.session_state.fixture_cache_bust,
        )

        st.markdown("---")
        with st.expander(f"League Feed Status ({len(active_leagues)}/17)", expanded=False):
            if active_leagues:
                for lg_name, cnt in sorted(active_leagues.items(), key=lambda x: (-x[1], x[0])):
                    st.markdown(f"`{cnt:02d}` · {lg_name}")
            else:
                st.caption("No upcoming fixtures in this window.")

    weights = st.session_state.weights
    multiplier = float(weights.get("market_multiplier", 1.00))
    penalties = int(weights.get("penalties", 0))
    chip_cls = "" if sb else "warn"
    chip_txt = "SUPABASE SYNCED" if sb else "LOCAL SESSION"

    st.markdown(
        f"""
        <div class="terminal-header">
            <div>
                <h1 class="brand-title">ALPHASTAKE</h1>
                <div class="brand-sub">OPERATOR // {st.session_state.username.upper()}</div>
            </div>
            <div>
                <span class="status-chip {chip_cls}"><span class="dot-live"></span>{chip_txt}</span>
            </div>
        </div>
        <div class="telemetry-strip">
            <div class="tele-card">
                <div class="tele-label">Market Weight</div>
                <div class="tele-val">{multiplier:.2f}x</div>
            </div>
            <div class="tele-card">
                <div class="tele-label">Upcoming Fixtures</div>
                <div class="tele-val">{len(fixtures)}</div>
            </div>
            <div class="tele-card">
                <div class="tele-label">Active Leagues</div>
                <div class="tele-val">{len(active_leagues)} / 17</div>
            </div>
            <div class="tele-card">
                <div class="tele-label">Neural Penalties</div>
                <div class="tele-val">{penalties}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1.05, 1.25], gap="large")

    # --------------------------------------------------------------------------
    # LEFT: SLIP GENERATOR & P&L
    # --------------------------------------------------------------------------
    with left_col:
        st.markdown('<div class="panel-card"><div class="panel-title">Terminal Slip Generator</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            target_odds = st.number_input(
                "Target Total Odds",
                min_value=1.20,
                max_value=100.0,
                value=3.50,
                step=0.25,
            )
        with c2:
            stake_amount = st.number_input(
                "Stake Amount (UGX)",
                min_value=500,
                max_value=50_000_000,
                value=5000,
                step=500,
            )

        if st.button("Generate Smart Terminal Slip", type="primary", use_container_width=True):
            legs, total_odds = build_smart_slip(
                fixtures=fixtures,
                target_odds=float(target_odds),
                market_multiplier=multiplier,
            )
            if not legs:
                st.warning("No upcoming fixtures in this window. Try 7-Day Schedule or Refresh Feed Cache.")
            else:
                st.session_state.current_slip = legs
                next_num = len(st.session_state.tickets) + 1
                est_payout = int(round(stake_amount * total_odds))
                new_ticket = {
                    "ticket_no": next_num,
                    "odds": total_odds,
                    "stake": int(stake_amount),
                    "est_payout": est_payout,
                    "status": "Pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "legs": legs,
                }
                save_ticket_to_db(sb, st.session_state.username, new_ticket)
                if sb:
                    st.session_state.tickets = load_user_tickets(sb, st.session_state.username)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Session P&L
        tickets = st.session_state.tickets
        total_staked = sum(int(t.get("stake", 0)) for t in tickets)
        settled = [t for t in tickets if t.get("status") in {"Won", "Lost"}]
        won_tickets = [t for t in settled if t.get("status") == "Won"]

        net_pnl = 0
        for t in settled:
            st_val = int(t.get("stake", 0))
            if t.get("status") == "Won":
                net_pnl += int(t.get("est_payout", round(st_val * float(t.get("odds", 1.0))))) - st_val
            else:
                net_pnl -= st_val

        roi_pct = (net_pnl / total_staked * 100.0) if total_staked > 0 else 0.0
        win_rate = (len(won_tickets) / len(settled) * 100.0) if settled else 0.0
        pnl_cls = "pos" if net_pnl > 0 else ("neg" if net_pnl < 0 else "")

        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-title">Session P&amp;L Telemetry</div>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-title">Net P&amp;L</div>
                        <div class="kpi-num {pnl_cls}">{net_pnl:+,}</div>
                        <div class="kpi-sub">UGX · {roi_pct:+.1f}% ROI</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Total Staked</div>
                        <div class="kpi-num">{total_staked:,}</div>
                        <div class="kpi-sub">UGX · {len(tickets)} SLIPS</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Win Rate</div>
                        <div class="kpi-num">{win_rate:.1f}%</div>
                        <div class="kpi-sub">{len(won_tickets)}/{len(settled)} SETTLED</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------------------------
    # RIGHT: ACTIVE ACCUMULATOR SLIP (UPCOMING ONLY)
    # --------------------------------------------------------------------------
    with right_col:
        st.markdown('<div class="panel-card"><div class="panel-title">Accumulator Slip · Upcoming Only</div>', unsafe_allow_html=True)
        upcoming_slip_legs = [
            leg for leg in (st.session_state.get("current_slip") or []) if is_upcoming_fixture(leg)
        ]

        if upcoming_slip_legs:
            slip_odds = 1.0
            for idx, leg in enumerate(upcoming_slip_legs, start=1):
                leg_match = get_leg_match(leg)
                leg_league = get_leg_league(leg)
                leg_kickoff = get_leg_kickoff(leg)
                leg_market = get_leg_market(leg)
                leg_odds = get_leg_odds(leg)
                slip_odds = round(slip_odds * leg_odds, 2)

                st.markdown(
                    f"""
                    <div class="slip-leg">
                        <div>
                            <div class="leg-match">{idx:02d}. {leg_match}</div>
                            <div class="leg-meta">{leg_league} · {leg_kickoff}</div>
                        </div>
                        <div class="leg-right">
                            <div class="leg-mkt">{leg_market}</div>
                            <div class="leg-odds">@{leg_odds:.2f}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            est_return = int(round(stake_amount * slip_odds))
            st.markdown(
                f"""
                <div class="slip-footer">
                    <span>{len(upcoming_slip_legs)} LEGS · {slip_odds:.2f}x</span>
                    <span>EST. PAYOUT: {est_return:,} UGX</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("No active upcoming slip staged. Generate a slip on the left to inspect legs.")
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # BOTTOM: HISTORY & WEIGHT TRAINING
    # --------------------------------------------------------------------------
    st.markdown('<div class="panel-card"><div class="panel-title">Terminal History &amp; Weight Training</div>', unsafe_allow_html=True)

    if tickets:
        if st.button("Clear History Log"):
            if sb:
                sb.table("user_tickets").delete().eq("username", st.session_state.username).execute()
            st.session_state.tickets = []
            st.session_state.current_slip = []
            st.rerun()

        for idx, ticket in enumerate(reversed(tickets)):
            t_num = ticket.get("ticket_no", len(tickets) - idx)
            t_odds = float(ticket.get("odds", 1.0))
            t_status = str(ticket.get("status", "Pending")).upper()
            t_stake = int(ticket.get("stake", 5000))
            t_payout = int(ticket.get("est_payout", round(t_stake * t_odds)))
            t_legs = ticket.get("legs") or []

            with st.expander(f"SLIP #{t_num:02d}  |  {t_odds:.2f}x  |  {t_stake:,} -> {t_payout:,} UGX  |  [{t_status}]", expanded=(idx == 0)):
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("Mark Won", key=f"won_{t_num}_{idx}", use_container_width=True):
                        updated_w = {
                            "market_multiplier": round(min(1.30, multiplier + 0.01), 2),
                            "penalties": penalties,
                        }
                        update_ticket_status_in_db(sb, st.session_state.username, ticket, "Won")
                        update_weights_in_db(sb, st.session_state.username, updated_w)
                        st.rerun()
                with b2:
                    if st.button("Mark Lost", key=f"lost_{t_num}_{idx}", use_container_width=True):
                        updated_w = {
                            "market_multiplier": round(max(0.80, multiplier - 0.01), 2),
                            "penalties": penalties + 1,
                        }
                        update_ticket_status_in_db(sb, st.session_state.username, ticket, "Lost")
                        update_weights_in_db(sb, st.session_state.username, updated_w)
                        st.rerun()
                with b3:
                    if st.button("Reset Pending", key=f"pend_{t_num}_{idx}", use_container_width=True):
                        update_ticket_status_in_db(sb, st.session_state.username, ticket, "Pending")
                        st.rerun()

                for l_idx, leg in enumerate(t_legs, start=1):
                    st.markdown(
                        f"`{l_idx:02d}` **{get_leg_match(leg)}** — {get_leg_market(leg)} "
                        f"@ `{get_leg_odds(leg):.2f}` *({get_leg_league(leg)})*"
                    )
    else:
        st.caption("No logged tickets yet.")

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# ENTRYPOINT
# ==============================================================================
def main() -> None:
    init_session_state()
    sb = get_supabase_client()
    if not st.session_state.authenticated:
        render_auth_screen(sb)
    else:
        render_terminal(sb)


if __name__ == "__main__":
    main()
