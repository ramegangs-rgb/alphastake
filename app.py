from datetime import datetime, timedelta, timezone
import hashlib
import random
from typing import Any

import requests
import streamlit as st
from supabase import Client, create_client

# ==============================================================================
# PAGE CONFIG & EXCLUSIVE 16 LEAGUES
# ==============================================================================
st.set_page_config(
    page_title="AlphaStake",
    layout="wide",
    initial_sidebar_state="expanded",
)

LEAGUE_CONFIG: list[dict[str, Any]] = [
    {"name": "English Premier League", "slug": "eng.1", "weight": 1.08},
    {"name": "Ligue 1", "slug": "fra.1", "weight": 1.02},
    {"name": "La Liga", "slug": "esp.1", "weight": 1.05},
    {"name": "Italian Serie A", "slug": "ita.1", "weight": 1.04},
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
# MINIMAL SPACING OVERRIDE (THEME HANDLED BY .streamlit/config.toml)
# ==============================================================================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.75rem;
            padding-bottom: 3rem;
            max-width: 1120px;
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
# ESPN FIXTURE FEED & COMPLETED RESULTS LOOKUP
# ==============================================================================
def _parse_espn_event(event: dict[str, Any], league_name: str, weight: float) -> dict[str, Any] | None:
    ev_id = str(event.get("id", ""))
    competitions = event.get("competitions", [])
    if not competitions:
        return None
    comp = competitions[0]
    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        return None

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

    try:
        home_score = int(float(home_comp.get("score", 0) or 0))
    except (TypeError, ValueError):
        home_score = 0
    try:
        away_score = int(float(away_comp.get("score", 0) or 0))
    except (TypeError, ValueError):
        away_score = 0

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

    return {
        "id": ev_id,
        "league": league_name,
        "weight": weight,
        "home": home_team,
        "away": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "matchup": f"{home_team} vs {away_team}",
        "kickoff": kickoff_dt.strftime("%b %d %H:%M UTC") if kickoff_dt else "Upcoming",
        "kickoff_dt": kickoff_dt,
        "status": short_detail or state_str or "Scheduled",
        "status_detail": name_str,
        "is_completed": completed,
    }


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
                parsed = _parse_espn_event(event, league_name, weight)
                if not parsed or not parsed["id"] or parsed["id"] in seen_ids:
                    continue

                kickoff_dt = parsed.get("kickoff_dt")
                if kickoff_dt is not None:
                    if kickoff_dt <= now_utc:
                        continue
                    if kickoff_dt > cutoff_utc:
                        continue

                if not is_upcoming_fixture(parsed):
                    continue

                seen_ids.add(parsed["id"])
                all_upcoming.append(parsed)
                league_counts[league_name] = league_counts.get(league_name, 0) + 1

    active_league_counts = {k: v for k, v in league_counts.items() if v > 0}
    return all_upcoming, active_league_counts


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recent_finished_results(days_back: int, cache_bust: int) -> dict[str, tuple[int, int]]:
    _ = cache_bust
    now_utc = datetime.now(timezone.utc)
    dates_to_query = [
        (now_utc - timedelta(days=offset)).strftime("%Y%m%d")
        for offset in range(0, max(days_back, 1) + 1)
    ]
    results_by_pair: dict[str, tuple[int, int]] = {}

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
                parsed = _parse_espn_event(event, league_name, weight)
                if not parsed:
                    continue
                if is_upcoming_fixture(parsed):
                    continue
                key = f"{parsed['home'].strip().lower()}||{parsed['away'].strip().lower()}"
                results_by_pair[key] = (int(parsed["home_score"]), int(parsed["away_score"]))

    return results_by_pair


# ==============================================================================
# AUTOMATIC SETTLEMENT & P&L ENGINE
# ==============================================================================
def _evaluate_market_outcome(market: str, home_goals: int, away_goals: int) -> bool:
    total_goals = home_goals + away_goals
    m_low = market.lower()
    if "over 1.5" in m_low:
        return total_goals >= 2
    if "over 2.5" in m_low:
        return total_goals >= 3
    if "home team over 0.5" in m_low:
        return home_goals >= 1
    if "double chance 1x" in m_low:
        return home_goals >= away_goals
    if "btts" in m_low and "yes" in m_low:
        return home_goals >= 1 and away_goals >= 1
    return total_goals >= 2


def _find_match_score(match_label: str, finished_map: dict[str, tuple[int, int]]) -> tuple[int, int] | None:
    if " vs " not in match_label:
        return None
    parts = match_label.split(" vs ", 1)
    h_key = parts[0].strip().lower()
    a_key = parts[1].strip().lower()
    direct = finished_map.get(f"{h_key}||{a_key}")
    if direct is not None:
        return direct
    for pair_key, scores in finished_map.items():
        p_home, p_away = pair_key.split("||", 1)
        if (h_key in p_home or p_home in h_key) and (a_key in p_away or p_away in a_key):
            return scores
    return None


def auto_settle_tickets(
    sb: Client | None,
    username: str,
    tickets: list[dict[str, Any]],
    weights: dict[str, Any],
    finished_map: dict[str, tuple[int, int]],
) -> tuple[int, dict[str, Any]]:
    settled_count = 0
    cur_mult = float(weights.get("market_multiplier", 1.00))
    cur_pen = int(weights.get("penalties", 0))
    weights_changed = False

    for ticket in tickets:
        if ticket.get("status") in {"Won", "Lost"}:
            continue
        legs = ticket.get("legs") or []
        if not legs:
            continue

        leg_outcomes: list[bool | None] = []
        for leg in legs:
            score = _find_match_score(get_leg_match(leg), finished_map)
            if score is None:
                leg_outcomes.append(None)
            else:
                h_g, a_g = score
                leg_outcomes.append(_evaluate_market_outcome(get_leg_market(leg), h_g, a_g))

        if any(outcome is False for outcome in leg_outcomes):
            update_ticket_status_in_db(sb, username, ticket, "Lost")
            cur_mult = round(max(0.80, cur_mult - 0.01), 2)
            cur_pen += 1
            weights_changed = True
            settled_count += 1
        elif all(outcome is True for outcome in leg_outcomes):
            update_ticket_status_in_db(sb, username, ticket, "Won")
            cur_mult = round(min(1.30, cur_mult + 0.01), 2)
            weights_changed = True
            settled_count += 1

    updated_weights = {"market_multiplier": cur_mult, "penalties": cur_pen}
    if weights_changed:
        update_weights_in_db(sb, username, updated_weights)

    return settled_count, updated_weights


def compute_session_pnl(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    total_staked = sum(int(t.get("stake", 0)) for t in tickets)
    settled = [t for t in tickets if t.get("status") in {"Won", "Lost"}]
    won_tickets = [t for t in settled if t.get("status") == "Won"]
    pending_tickets = [t for t in tickets if t.get("status") not in {"Won", "Lost"}]

    net_pnl = 0
    for t in settled:
        st_val = int(t.get("stake", 0))
        if t.get("status") == "Won":
            net_pnl += int(t.get("est_payout", round(st_val * float(t.get("odds", 1.0))))) - st_val
        else:
            net_pnl -= st_val

    roi_pct = (net_pnl / total_staked * 100.0) if total_staked > 0 else 0.0
    win_rate = (len(won_tickets) / len(settled) * 100.0) if settled else 0.0
    return {
        "total_staked": total_staked,
        "settled_count": len(settled),
        "won_count": len(won_tickets),
        "pending_count": len(pending_tickets),
        "net_pnl": net_pnl,
        "roi_pct": roi_pct,
        "win_rate": win_rate,
    }


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
    st.title("AlphaStake")
    sync_label = "Supabase Synced" if sb else "Local Session"
    st.caption(f"16 Leagues · Upcoming Fixtures Only · {sync_label}")

    _, center, _ = st.columns([1, 1.4, 1])
    with center:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Sign In", "Register"])

            with tab_login:
                with st.form("login_form", border=False):
                    username = st.text_input("Username").strip().lower()
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("Enter both username and password.")
                    else:
                        pw_hash = hash_password(password)
                        if sb:
                            user_row = fetch_user_record(sb, username)
                            if not user_row:
                                st.error("Account not found. Switch to Register.")
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
                with st.form("register_form", border=False):
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


# ==============================================================================
# MAIN TERMINAL (NATIVE BORDERED CARDS + CLEAN TABS + AUTO P&L)
# ==============================================================================
def render_terminal(sb: Client | None) -> None:
    window_options = {
        "Today & Tomorrow (48h)": 2,
        "3-Day Schedule": 3,
        "7-Day Schedule": 7,
    }

    with st.sidebar:
        st.subheader("Feed & Session")
        selected_window_label = st.selectbox(
            "Fixture Window",
            list(window_options.keys()),
            index=0,
        )
        window_days = window_options[selected_window_label]

        if st.button("Refresh Feed Cache", use_container_width=True):
            st.session_state.fixture_cache_bust += 1
            fetch_espn_fixtures.clear()
            fetch_recent_finished_results.clear()
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

        st.divider()
        with st.expander(f"League Feed Status ({len(active_leagues)}/16)", expanded=False):
            if active_leagues:
                for lg_name, cnt in sorted(active_leagues.items(), key=lambda x: (-x[1], x[0])):
                    st.write(f"`{cnt:02d}` · {lg_name}")
            else:
                st.caption("No upcoming fixtures in this window.")

    finished_map = fetch_recent_finished_results(
        days_back=7,
        cache_bust=st.session_state.fixture_cache_bust,
    )
    auto_settled_now, updated_weights = auto_settle_tickets(
        sb=sb,
        username=st.session_state.username,
        tickets=st.session_state.tickets,
        weights=st.session_state.weights,
        finished_map=finished_map,
    )
    if auto_settled_now > 0 and sb:
        st.session_state.tickets = load_user_tickets(sb, st.session_state.username)

    weights = updated_weights
    multiplier = float(weights.get("market_multiplier", 1.00))
    penalties = int(weights.get("penalties", 0))
    sync_status = "SUPABASE SYNCED" if sb else "LOCAL SESSION"

    st.title("AlphaStake")
    st.caption(f"Operator: {st.session_state.username} · {sync_status} · Auto P&L Active")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.metric("Market Weight", f"{multiplier:.2f}x")
    with m2:
        with st.container(border=True):
            st.metric("Upcoming Fixtures", len(fixtures))
    with m3:
        with st.container(border=True):
            st.metric("Active Leagues", f"{len(active_leagues)} / 16")
    with m4:
        with st.container(border=True):
            st.metric("Neural Penalties", penalties)

    tab_slip, tab_history, tab_pnl = st.tabs(
        ["Slip Terminal", "History & Training", "P&L Analytics"]
    )

    tickets = st.session_state.tickets
    pnl = compute_session_pnl(tickets)

    # --------------------------------------------------------------------------
    # TAB 1: SLIP GENERATOR & ACTIVE ACCUMULATOR SLIP
    # --------------------------------------------------------------------------
    with tab_slip:
        with st.container(border=True):
            st.subheader("Slip Generator")
            c1, c2, c3 = st.columns([1, 1, 1.1], vertical_alignment="bottom")
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
            with c3:
                generate_clicked = st.button(
                    "Generate Smart Slip",
                    type="primary",
                    use_container_width=True,
                )

            if generate_clicked:
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

        st.subheader("Accumulator Slip")
        upcoming_slip_legs = [
            leg for leg in (st.session_state.get("current_slip") or []) if is_upcoming_fixture(leg)
        ]

        if upcoming_slip_legs:
            slip_odds = 1.0
            for idx, leg in enumerate(upcoming_slip_legs, start=1):
                leg_odds = get_leg_odds(leg)
                slip_odds = round(slip_odds * leg_odds, 2)
                with st.container(border=True):
                    col_left, col_right = st.columns([3, 1.2])
                    with col_left:
                        st.markdown(f"**{idx:02d}. {get_leg_match(leg)}**")
                        st.caption(f"{get_leg_league(leg)} · {get_leg_kickoff(leg)}")
                    with col_right:
                        st.markdown(f"**{get_leg_market(leg)}**")
                        st.caption(f"Odds: `{leg_odds:.2f}`")

            est_return = int(round(stake_amount * slip_odds))
            with st.container(border=True):
                s1, s2, s3 = st.columns(3)
                s1.metric("Selections", f"{len(upcoming_slip_legs)} Legs")
                s2.metric("Combined Odds", f"{slip_odds:.2f}x")
                s3.metric("Est. Payout", f"{est_return:,} UGX")
        else:
            with st.container(border=True):
                st.caption("No active upcoming slip staged. Click Generate Smart Slip above.")

    # --------------------------------------------------------------------------
    # TAB 2: HISTORY & WEIGHT TRAINING
    # --------------------------------------------------------------------------
    with tab_history:
        if tickets:
            h_left, h_mid, h_right = st.columns([2.2, 1, 1], vertical_alignment="center")
            with h_left:
                st.subheader(f"Ticket Log ({len(tickets)})")
            with h_mid:
                if st.button("Auto-Check Results", use_container_width=True):
                    st.session_state.fixture_cache_bust += 1
                    fetch_recent_finished_results.clear()
                    st.rerun()
            with h_right:
                if st.button("Clear History Log", use_container_width=True):
                    if sb:
                        sb.table("user_tickets").delete().eq("username", st.session_state.username).execute()
                    st.session_state.tickets = []
                    st.session_state.current_slip = []
                    st.rerun()

            for idx, ticket in enumerate(reversed(tickets)):
                t_num = ticket.get("ticket_no", len(tickets) - idx)
                t_odds = float(ticket.get("odds", 1.0))
                t_status = ticket.get("status", "Pending")
                t_stake = int(ticket.get("stake", 5000))
                t_payout = int(ticket.get("est_payout", round(t_stake * t_odds)))
                t_legs = ticket.get("legs") or []

                with st.expander(
                    f"Ticket #{t_num:02d}  ·  {t_odds:.2f}x  ·  {t_stake:,} → {t_payout:,} UGX  ·  [{t_status}]",
                    expanded=(idx == 0),
                ):
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
                        with st.container(border=True):
                            lc1, lc2 = st.columns([3, 1.2])
                            with lc1:
                                st.markdown(f"**{l_idx:02d}. {get_leg_match(leg)}**")
                                st.caption(get_leg_league(leg))
                            with lc2:
                                st.markdown(f"**{get_leg_market(leg)}**")
                                st.caption(f"Odds: `{get_leg_odds(leg):.2f}`")
        else:
            with st.container(border=True):
                st.caption("No logged tickets yet. Generate a slip in the Slip Terminal tab.")

    # --------------------------------------------------------------------------
    # TAB 3: AUTOMATIC SESSION P&L ANALYTICS
    # --------------------------------------------------------------------------
    with tab_pnl:
        with st.container(border=True):
            top_l, top_r = st.columns([3, 1], vertical_alignment="center")
            with top_l:
                st.subheader("Automatic Session P&L")
                st.caption("Automatically settles finished matches from your 16-league feed and updates P&L, ROI, and win rate.")
            with top_r:
                if st.button("Sync Live Results", type="primary", use_container_width=True):
                    st.session_state.fixture_cache_bust += 1
                    fetch_recent_finished_results.clear()
                    st.rerun()

        p1, p2, p3 = st.columns(3)
        with p1:
            with st.container(border=True):
                st.metric("Net P&L", f"{pnl['net_pnl']:+,} UGX", f"{pnl['roi_pct']:+.1f}% ROI")
        with p2:
            with st.container(border=True):
                st.metric("Total Staked", f"{pnl['total_staked']:,} UGX", f"{len(tickets)} tickets")
        with p3:
            with st.container(border=True):
                st.metric(
                    "Win Rate",
                    f"{pnl['win_rate']:.1f}%",
                    f"{pnl['won_count']}/{pnl['settled_count']} settled · {pnl['pending_count']} pending",
                )


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
