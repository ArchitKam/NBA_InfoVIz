#omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam
#omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam omsairam

import streamlit as st
import pandas as pd
import os
import altair as alt
import plotly.graph_objects as go
import numpy as np
from PIL import Image

# streamlit run app.py

# -----------------------------
# 1. SETTINGS & CONFIG
# -----------------------------
st.set_page_config(page_title="NBA Defensive Impact", layout="wide")
st.title("NBA Defensive Impact Explorer")

DEFAULT_CHART_TYPE = "Bar Chart"
DEFAULT_ZONE = "Overall"
MIN_GAMES_PLAYED = 25

ZONE_MAP = {
    "Overall": "overall.csv",
    "At the Rim (< 6ft)": "less_than_6ft.csv",
    "In the Paint (< 10ft)": "less_than_10ft.csv",
    "Perimeter (> 15ft)": "greater_than_15ft.csv",
    "3 Pointers": "3_pointers.csv",
    "2 Pointers": "2_pointers.csv",
}

METRIC_OPTIONS = [
    "Defensive Composite Score",
    "Defensive Impact (Diff %)",
    "Shot Contests (FGA)",
    "Defended FG%",
    "Expected/Normal FG%",
    "Defended Field Goals Made",
    "Frequency of Shots Defended",
]

RAW_HEATMAP_METRICS = [
    "Defensive Impact (Diff %)",
    "Shot Contests (FGA)",
    "Defended FG%",
    "Expected/Normal FG%",
    "Defended Field Goals Made",
    "Frequency of Shots Defended",
]

NBA_COLORS = {
    "ATL": "#E03A3E", "BOS": "#007A33", "BKN": "#000000", "CHA": "#1D1160",
    "CHI": "#CE1141", "CLE": "#860038", "DAL": "#00538C", "DEN": "#0E2240",
    "DET": "#C8102E", "GSW": "#1D428A", "HOU": "#CE1141", "IND": "#002D62",
    "LAC": "#C8102E", "LAL": "#552583", "MEM": "#5D76A9", "MIA": "#98002D",
    "MIL": "#00471B", "MIN": "#0C2340", "NOP": "#0C2340", "NYK": "#F58426",
    "OKC": "#007AC1", "ORL": "#0077C0", "PHI": "#006BB6", "PHX": "#1D1160",
    "POR": "#E03A3E", "SAC": "#5A2D81", "SAS": "#C4CED4", "TOR": "#CE1141",
    "UTA": "#002B5C", "WAS": "#002B5C"
}

COURT_SIZEX = 50
COURT_SIZEY = 33
COURT_Y_RANGE = [0, 33]
BASKET_CENTER_X = 0
BASKET_CENTER_Y = 3


# -----------------------------
# 2. DATA HELPERS
# -----------------------------
@st.cache_data
def load_data(year, label):
    file_path = os.path.join("nba_data", year, ZONE_MAP[label])
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path)


def apply_games_threshold(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    if "GP" in df.columns:
        df["GP"] = pd.to_numeric(df["GP"], errors="coerce")
        df = df[df["GP"] >= MIN_GAMES_PLAYED]

    return df


def get_column_for_metric(df, metric_name):
    if df is None or df.empty:
        return None

    cols = list(df.columns)

    try:
        if metric_name == "Defensive Impact (Diff %)":
            return [c for c in cols if "PLUSMINUS" in c][0]

        if metric_name == "Shot Contests (FGA)":
            return [c for c in cols if "FGA" in c or "FG3A" in c or "FG2A" in c][0]

        if metric_name == "Defended FG%":
            return [
                c for c in cols
                if "PCT" in c
                and "NS_" not in c
                and "NORMAL" not in c
                and "PLUSMINUS" not in c
            ][0]

        if metric_name == "Expected/Normal FG%":
            return [c for c in cols if "NS_" in c or "NORMAL" in c][0]

        if metric_name == "Defended Field Goals Made":
            return [c for c in cols if "FGM" in c or "FG3M" in c or "FG2M" in c][0]

        if metric_name == "Frequency of Shots Defended":
            return [c for c in cols if "FREQ" in c][0]

    except IndexError:
        return None

    return None


def percentile_rank(series, higher_is_better=True):
    s = pd.to_numeric(series, errors="coerce")
    if higher_is_better:
        return s.rank(pct=True, method="average") * 100
    return (-s).rank(pct=True, method="average") * 100


def add_defensive_composite(df):
    if df is None or df.empty:
        return df

    df = df.copy()

    fga_col = get_column_for_metric(df, "Shot Contests (FGA)")
    pct_col = get_column_for_metric(df, "Defended FG%")
    expected_col = get_column_for_metric(df, "Expected/Normal FG%")

    required_cols = [fga_col, pct_col, expected_col, "GP"]

    if any(col is None for col in required_cols) or "GP" not in df.columns:
        df["DEFENSIVE_COMPOSITE_SCORE"] = np.nan
        return df

    df[fga_col] = pd.to_numeric(df[fga_col], errors="coerce")
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")
    df[expected_col] = pd.to_numeric(df[expected_col], errors="coerce")
    df["GP"] = pd.to_numeric(df["GP"], errors="coerce")

    # Raw defensive impact computed from endpoint fields:
    # positive = opponent shot worse than expected when defended by this player.
    df["DEFENSIVE_IMPACT_RAW"] = df[expected_col] - df[pct_col]

    df["IMPACT_PCTL"] = percentile_rank(
        df["DEFENSIVE_IMPACT_RAW"],
        higher_is_better=True
    )

    df["VOLUME_PCTL"] = percentile_rank(
        df[fga_col],
        higher_is_better=True
    )

    df["GAMES_PCTL"] = percentile_rank(
        df["GP"],
        higher_is_better=True
    )

    df["DEFENSIVE_COMPOSITE_SCORE"] = (
        0.50 * df["IMPACT_PCTL"]
        + 0.25 * df["VOLUME_PCTL"]
        + 0.25 * df["GAMES_PCTL"]
    ).round(1)

    return df


def get_chart_column(df, metric_name):
    if metric_name == "Defensive Composite Score":
        return "DEFENSIVE_COMPOSITE_SCORE"
    return get_column_for_metric(df, metric_name)


def metric_is_lower_better(metric_name):
    return metric_name in ["Defensive Impact (Diff %)", "Defended FG%"]


def metric_is_percent_display(metric_name):
    return metric_name in [
        "Defensive Impact (Diff %)",
        "Defended FG%",
        "Expected/Normal FG%",
        "Frequency of Shots Defended",
    ]


def metric_display_label(metric_name):
    if metric_name == "Defensive Impact (Diff %)":
        return "Defensive Impact (pct pts)"
    return metric_name


def add_metric_display_column(df, source_col, metric_name):
    display_col = f"{source_col}_DISPLAY"
    df[display_col] = pd.to_numeric(df[source_col], errors="coerce")

    if metric_is_percent_display(metric_name):
        df[display_col] = df[display_col] * 100

    return display_col


def format_percent_series(series, signed=False):
    values = pd.to_numeric(series, errors="coerce") * 100
    if signed:
        return values.map(lambda value: "—" if pd.isna(value) else f"{value:+.1f}%")
    return values.map(lambda value: "—" if pd.isna(value) else f"{value:.1f}%")


def display_value(value, metric_name):
    if pd.isna(value):
        return "—"

    if metric_name == "Defensive Impact (Diff %)":
        return f"{value * 100:+.1f}%"

    if metric_is_percent_display(metric_name):
        return f"{value * 100:.1f}%"

    return f"{value:.1f}"


def get_selected_player_from_chart_state(chart_key):
    chart_state = st.session_state.get(chart_key)
    if not chart_state:
        return None

    selection = getattr(chart_state, "selection", None)
    if not selection:
        return None

    click_selection = selection.get("click") if isinstance(selection, dict) else None
    if not click_selection:
        return None

    if isinstance(click_selection, list) and click_selection:
        selected_point = click_selection[0]
        if isinstance(selected_point, dict):
            return selected_point.get("PLAYER_NAME")

    if isinstance(click_selection, dict):
        player_name = click_selection.get("PLAYER_NAME")
        if isinstance(player_name, list):
            return player_name[0] if player_name else None
        return player_name

    return None


@st.cache_data
def prepare_standard_df(year, label):
    df = load_data(year, label)
    df = apply_games_threshold(df)
    df = add_defensive_composite(df)
    return df


# -----------------------------
# 3. SIDEBAR
# -----------------------------
st.sidebar.header("📍 Data Selection")

if os.path.exists("nba_data"):
    available_years = sorted(
        [
            f for f in os.listdir("nba_data")
            if os.path.isdir(os.path.join("nba_data", f))
        ],
        reverse=True
    )
else:
    available_years = []
    st.error("⚠️ 'nba_data' folder not found. Please run your downloader script.")

if not available_years:
    st.stop()

selected_year = st.sidebar.selectbox("Season", available_years)

selected_labels = st.sidebar.multiselect(
    "Shot Zone(s)",
    list(ZONE_MAP.keys()),
    default=[DEFAULT_ZONE],
)

st.sidebar.header("📊 Chart Metrics")
selected_metrics = st.sidebar.multiselect(
    "Select Metrics to Visualize",
    METRIC_OPTIONS,
    default=["Defensive Composite Score"],
)

st.sidebar.header("🎨 Visualization Style")
chart_options = [
    "Bar Chart",
    "Scatter Plot",
    "Team Distribution (Pie)",
    "Court Heat Map (Abstract)",
    "Court Heat Map (Image Overlay)",
]
chart_type = st.sidebar.radio(
    "Select Chart Pattern",
    chart_options,
    index=chart_options.index(DEFAULT_CHART_TYPE),
)

base_df = prepare_standard_df(selected_year, "Overall")

st.sidebar.header("🔍 Filters")

if base_df is not None and not base_df.empty:
    all_players = sorted(base_df["PLAYER_NAME"].dropna().unique().tolist())
    selected_players = st.sidebar.multiselect("Search & Select Player(s)", all_players)

    teams = ["All Teams"] + sorted(
        base_df["PLAYER_LAST_TEAM_ABBREVIATION"].dropna().unique().tolist()
    )
    selected_team = st.sidebar.selectbox("Team", teams)
else:
    selected_players = []
    selected_team = "All Teams"


# -----------------------------
# 4. HEATMAP VIEW
# -----------------------------
def aggregate_zone(zone_df):
    if zone_df is None or zone_df.empty:
        return 0, 0, 0

    temp_df = zone_df.copy()

    if selected_players:
        temp_df = temp_df[temp_df["PLAYER_NAME"].isin(selected_players)]

    if selected_team != "All Teams":
        temp_df = temp_df[temp_df["PLAYER_LAST_TEAM_ABBREVIATION"] == selected_team]

    if temp_df.empty:
        return 0, 0, 0

    fga_c = get_column_for_metric(temp_df, "Shot Contests (FGA)")
    fgm_c = get_column_for_metric(temp_df, "Defended Field Goals Made")
    nspct_c = get_column_for_metric(temp_df, "Expected/Normal FG%")

    if fga_c is None:
        return 0, 0, 0

    temp_df[fga_c] = pd.to_numeric(temp_df[fga_c], errors="coerce")
    total_fga = temp_df[fga_c].sum()

    if fgm_c is not None:
        temp_df[fgm_c] = pd.to_numeric(temp_df[fgm_c], errors="coerce")
        total_fgm = temp_df[fgm_c].sum()
    else:
        total_fgm = 0

    if nspct_c is not None:
        temp_df[nspct_c] = pd.to_numeric(temp_df[nspct_c], errors="coerce")
        total_expected_fgm = (temp_df[fga_c] * temp_df[nspct_c]).sum()
    else:
        total_expected_fgm = 0

    return total_fga, total_fgm, total_expected_fgm


def calc_heatmap_metric(fga, fgm, expected, metric_name, total_fga_all):
    if fga == 0:
        return None

    if metric_name == "Defensive Impact (Diff %)":
        return ((fgm / fga) - (expected / fga)) * 100

    if metric_name == "Defended FG%":
        return (fgm / fga) * 100

    if metric_name == "Expected/Normal FG%":
        return (expected / fga) * 100

    if metric_name == "Shot Contests (FGA)":
        return fga

    if metric_name == "Defended Field Goals Made":
        return fgm

    if metric_name == "Frequency of Shots Defended":
        return (fga / total_fga_all) * 100 if total_fga_all > 0 else 0

    return None


def get_league_zone_values(year, metric_name):
    league_values = []

    zone_labels = [
        "At the Rim (< 6ft)",
        "In the Paint (< 10ft)",
        "Perimeter (> 15ft)",
    ]

    for zone_label in zone_labels:
        zone_df = prepare_standard_df(year, zone_label)

        if zone_df is None or zone_df.empty:
            continue

        fga_c = get_column_for_metric(zone_df, "Shot Contests (FGA)")
        fgm_c = get_column_for_metric(zone_df, "Defended Field Goals Made")
        nspct_c = get_column_for_metric(zone_df, "Expected/Normal FG%")

        if fga_c is None:
            continue

        for _, row in zone_df.iterrows():
            fga = pd.to_numeric(row.get(fga_c), errors="coerce")

            if pd.isna(fga) or fga == 0:
                continue

            fgm = pd.to_numeric(row.get(fgm_c), errors="coerce") if fgm_c else np.nan
            expected_pct = pd.to_numeric(row.get(nspct_c), errors="coerce") if nspct_c else np.nan

            if pd.isna(fgm) or pd.isna(expected_pct):
                continue

            expected = fga * expected_pct
            value = calc_heatmap_metric(fga, fgm, expected, metric_name, fga)

            if value is not None and not pd.isna(value):
                league_values.append(value)

    return league_values


def heat_color(value, metric_name, league_values=None):
    if value is None:
        return "rgba(100, 100, 100, 0.45)"

    if not league_values:
        return "rgba(100, 100, 100, 0.45)"

    league_series = pd.Series(league_values).dropna()

    if league_series.empty:
        return "rgba(100, 100, 100, 0.45)"

    if metric_is_lower_better(metric_name):
        percentile = (league_series >= value).mean() * 100
    else:
        percentile = (league_series <= value).mean() * 100

    if percentile >= 50:
        intensity = max(0.25, min(1.0, percentile / 100))
        return f"rgba(0, 200, 80, {intensity})"

    red_intensity = max(0.25, min(1.0, (100 - percentile) / 100))
    return f"rgba(220, 0, 0, {red_intensity})"


def ring_coords(r_inner, r_outer, cx=0, cy=0, n=100):
    theta = np.linspace(0, np.pi, n)
    x_out = cx + r_outer * np.cos(theta)
    y_out = cy + r_outer * np.sin(theta)
    x_in = cx + r_inner * np.cos(theta)[::-1]
    y_in = cy + r_inner * np.sin(theta)[::-1]
    return (
        np.concatenate([x_out, x_in, [x_out[0]]]),
        np.concatenate([y_out, y_in, [y_out[0]]]),
    )


def render_heatmap(primary_metric):
    if primary_metric == "Defensive Composite Score":
        st.warning(
            "Court heat maps aggregate raw zone statistics, so Defensive Composite Score is not available here. "
            "Select a raw metric such as Defensive Impact, Defended FG%, or Shot Contests."
        )
        return

    show_rim = "At the Rim (< 6ft)" in selected_labels
    show_paint = "In the Paint (< 10ft)" in selected_labels
    show_perimeter = "Perimeter (> 15ft)" in selected_labels

    if not (show_rim or show_paint or show_perimeter):
        st.warning("Select at least one of Rim, Paint, or Perimeter for the heat map.")
        return

    st.header(f"🏀 Spatial Defensive Heat Map: {primary_metric}")

    df_6 = prepare_standard_df(selected_year, "At the Rim (< 6ft)") if show_rim else None
    df_10 = prepare_standard_df(selected_year, "In the Paint (< 10ft)") if show_paint else None
    df_15 = prepare_standard_df(selected_year, "Perimeter (> 15ft)") if show_perimeter else None
    df_overall = prepare_standard_df(selected_year, "Overall")

    fga_6, fgm_6, exp_6 = aggregate_zone(df_6) if show_rim else (0, 0, 0)
    fga_10, fgm_10, exp_10 = aggregate_zone(df_10) if show_paint else (0, 0, 0)
    fga_15, fgm_15, exp_15 = aggregate_zone(df_15) if show_perimeter else (0, 0, 0)
    fga_all, _, _ = aggregate_zone(df_overall)

    fga_6_10 = max(0, fga_10 - fga_6) if show_paint and show_rim else fga_10
    fgm_6_10 = max(0, fgm_10 - fgm_6) if show_paint and show_rim else fgm_10
    exp_6_10 = max(0, exp_10 - exp_6) if show_paint and show_rim else exp_10

    val_6 = calc_heatmap_metric(fga_6, fgm_6, exp_6, primary_metric, fga_all) if show_rim else None
    val_6_10 = calc_heatmap_metric(fga_6_10, fgm_6_10, exp_6_10, primary_metric, fga_all) if show_paint else None
    val_15 = calc_heatmap_metric(fga_15, fgm_15, exp_15, primary_metric, fga_all) if show_perimeter else None

    valid_vals = [v for v in [val_6, val_6_10, val_15] if v is not None]
    max_v = max(valid_vals) if valid_vals else 1
    league_values = get_league_zone_values(selected_year, primary_metric)

    fig = go.Figure()

    if chart_type == "Court Heat Map (Image Overlay)":
        try:
            court_img = Image.open("omsairam_nba_ct.webp")
            fig.add_layout_image(
                dict(
                    source=court_img,
                    xref="x",
                    yref="y",
                    x=-25,
                    y=COURT_SIZEY,
                    sizex=COURT_SIZEX,
                    sizey=COURT_SIZEY,
                    sizing="stretch",
                    opacity=1.0,
                    layer="below",
                )
            )
            center_y = BASKET_CENTER_Y
            y_range = COURT_Y_RANGE
            height = 650
            line_color = "black"
        except Exception:
            st.warning("Could not load court image. Rendering abstract court instead.")
            center_y = 0
            y_range = [-1.5, 26]
            height = 500
            line_color = "white"
    else:
        center_y = 0
        y_range = [-1.5, 26]
        height = 500
        line_color = "white"

        theta_bg = np.linspace(0, np.pi, 100)
        x_bg = np.concatenate([25 * np.cos(theta_bg), [-25]])
        y_bg = np.concatenate([25 * np.sin(theta_bg), [0]])
        fig.add_trace(
            go.Scatter(
                x=x_bg,
                y=y_bg,
                fill="toself",
                fillcolor="rgba(20,20,30,0.95)",
                mode="lines",
                line=dict(color="rgba(80,80,80,0.5)", width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    zones = []
    if show_rim and val_6 is not None:
        zones.append(("Rim (< 6ft)", 0, 6, val_6, fga_6))
    if show_paint and val_6_10 is not None:
        zones.append(("Paint (6-10ft)", 6, 10, val_6_10, fga_6_10))
    if show_perimeter and val_15 is not None:
        zones.append(("Perimeter (> 15ft)", 15, 25, val_15, fga_15))

    for name, r_in, r_out, value, fga in zones:
        x, y = ring_coords(r_in, r_out, cy=center_y, n=80)

        if "Diff" in primary_metric:
            hover_text = f"<b>{name}</b><br>Contests: {int(fga)}<br>{primary_metric}: {value:+.1f}%"
        elif "%" in primary_metric:
            hover_text = f"<b>{name}</b><br>Contests: {int(fga)}<br>{primary_metric}: {value:.1f}%"
        else:
            hover_text = f"<b>{name}</b><br>{primary_metric}: {value:.1f}"

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",
                fillcolor=heat_color(value, primary_metric, league_values),
                mode="lines",
                line=dict(color=line_color, width=2),
                name=name,
                text=hover_text,
                hoverinfo="text",
                opacity=0.85,
            )
        )

    fig.update_layout(
        xaxis=dict(range=[-25, 25], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(
            range=y_range,
            showgrid=False,
            zeroline=False,
            visible=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        showlegend=True,
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor="rgba(0,0,0,0.6)",
            font=dict(color="white"),
        ),
    )

    st.plotly_chart(fig, width="stretch")
    st.caption(f"Minimum games played threshold applied: {MIN_GAMES_PLAYED} games.")
    st.caption("Heat map color is normalized relative to league-wide player-zone values for the selected season.")


def render_player_card(top_player, fga_col, pct_col, pm_col):
    with st.container(border=True):
        col1, col2 = st.columns([1, 2])

        with col1:
            try:
                p_id = int(top_player["CLOSE_DEF_PERSON_ID"])
                st.image(
                    f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{p_id}.png",
                    width=250,
                )
            except Exception:
                st.image("https://stats.nba.com/media/img/league/nba-logo.svg", width=200)

        with col2:
            full_name = top_player["PLAYER_NAME"]
            first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")

            st.html(
                f"""
                <div style="line-height: 1.0; margin-bottom: 20px;">
                    <h1 style="font-size: 55px; margin: 0; text-transform: uppercase; font-weight: 700; opacity: 0.8;">{first_name}</h1>
                    <h1 style="font-size: 90px; margin: 0; text-transform: uppercase; font-weight: 900; color: {NBA_COLORS.get(top_player['PLAYER_LAST_TEAM_ABBREVIATION'], '#1D428A')};">{last_name}</h1>
                </div>
                """
            )

            st.subheader(
                f"{top_player['PLAYER_LAST_TEAM_ABBREVIATION']} | {top_player['PLAYER_POSITION']}"
            )

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "Composite Score",
                f"{top_player['DEFENSIVE_COMPOSITE_SCORE']:.1f}"
                if "DEFENSIVE_COMPOSITE_SCORE" in top_player.index else "—",
            )

            m2.metric("Shot Contests/G", f"{top_player[fga_col]:.1f}")

            m3.metric("Defended FG%", f"{top_player[pct_col] * 100:.1f}%")

            m4.metric(
                "Defensive Impact",
                f"{top_player[pm_col] * 100:+.1f}%" if pm_col else "—",
                delta_color="inverse",
            )


# -----------------------------
# 5. MAIN RENDER
# -----------------------------
if not selected_metrics:
    st.info("Please select at least one metric.")
    st.stop()

if chart_type in ["Court Heat Map (Abstract)", "Court Heat Map (Image Overlay)"]:
    render_heatmap(selected_metrics[0])
    st.stop()

if not selected_labels:
    st.info("Please select at least one shot zone.")
    st.stop()

for label in selected_labels:
    st.header(f"📍 Zone Analysis: {label}")

    df = prepare_standard_df(selected_year, label)

    if df is None or df.empty:
        st.error(f"Missing or empty data for {label}. Run your downloader script.")
        st.markdown("---")
        continue

    fga_col = get_column_for_metric(df, "Shot Contests (FGA)")
    pct_col = get_column_for_metric(df, "Defended FG%")
    pm_col = get_column_for_metric(df, "Defensive Impact (Diff %)")

    if fga_col is None or pct_col is None:
        st.error(f"Data missing expected columns for {label}.")
        st.markdown("---")
        continue

    filtered_df = df.copy()

    if selected_players:
        filtered_df = filtered_df[filtered_df["PLAYER_NAME"].isin(selected_players)]

    if selected_team != "All Teams":
        filtered_df = filtered_df[filtered_df["PLAYER_LAST_TEAM_ABBREVIATION"] == selected_team]

    if filtered_df.empty:
        st.warning("No players found with those filters.")
        st.markdown("---")
        continue

    primary_metric = selected_metrics[0]
    primary_col = get_chart_column(filtered_df, primary_metric)

    if primary_col is None or primary_col not in filtered_df.columns:
        st.warning(f"Could not compute {primary_metric} for {label}.")
        st.markdown("---")
        continue

    primary_ascending = metric_is_lower_better(primary_metric)

    if selected_players:
        threshold = 0
        hero_df = filtered_df.sort_values(primary_col, ascending=primary_ascending)
    else:
        threshold = pd.to_numeric(filtered_df[fga_col], errors="coerce").mean()
        hero_df = filtered_df[
            pd.to_numeric(filtered_df[fga_col], errors="coerce") >= threshold
        ].sort_values(primary_col, ascending=primary_ascending)

    if hero_df.empty:
        st.warning("Not enough data after applying volume threshold.")
        st.markdown("---")
        continue

    @st.fragment
    def render_zone_interactive():
        selected_player_key = f"selected_player::{selected_year}::{label}"
        clicked_player = st.session_state.get(selected_player_key)

        if chart_type in ["Bar Chart", "Scatter Plot", "Team Distribution (Pie)"]:
            chart_key_prefix = "scatter" if chart_type == "Scatter Plot" else ("pie" if chart_type == "Team Distribution (Pie)" else "bar")
            for metric in selected_metrics:
                selected_from_chart = get_selected_player_from_chart_state(
                    f"{chart_key_prefix}_{label}_{metric}"
                )
                if selected_from_chart:
                    clicked_player = selected_from_chart
                    st.session_state[selected_player_key] = clicked_player
                    break

        if clicked_player not in filtered_df["PLAYER_NAME"].values:
            clicked_player = None
            st.session_state.pop(selected_player_key, None)

        if clicked_player:
            top_player = filtered_df[filtered_df["PLAYER_NAME"] == clicked_player].iloc[0]
        else:
            top_player = hero_df.iloc[0]

        render_player_card(top_player, fga_col, pct_col, pm_col)

        view_mode = st.radio(
            "View",
            ["Visual Comparisons", "Full Rankings Table"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key=f"view_{selected_year}_{label}",
        )

        if view_mode == "Visual Comparisons":
            team_color_scale = alt.Scale(
                domain=list(NBA_COLORS.keys()),
                range=list(NBA_COLORS.values()),
            )

            for metric in selected_metrics:
                st.markdown(f"**{metric}**")

                chart_col = get_chart_column(filtered_df, metric)

                if chart_col is None or chart_col not in filtered_df.columns:
                    st.info(f"{metric} is not available for this selection.")
                    continue

                sort_asc = metric_is_lower_better(metric)

                if selected_players:
                    chart_df = filtered_df.sort_values(chart_col, ascending=sort_asc).copy()
                elif chart_type == "Scatter Plot":
                    chart_df = filtered_df.sort_values(chart_col, ascending=sort_asc).copy()
                else:
                    chart_df = filtered_df[
                        pd.to_numeric(filtered_df[fga_col], errors="coerce") >= threshold
                    ].sort_values(chart_col, ascending=sort_asc).head(10).copy()

                if chart_df.empty:
                    st.info(f"No players available to display for {metric}.")
                    continue

                chart_df[chart_col] = pd.to_numeric(chart_df[chart_col], errors="coerce")
                chart_df[fga_col] = pd.to_numeric(chart_df[fga_col], errors="coerce")
                display_col = add_metric_display_column(chart_df, chart_col, metric)
                display_title = metric_display_label(metric)
                tooltip_format = "+.1f" if metric == "Defensive Impact (Diff %)" else ".1f"

                chart_df["PLAYER_LABEL"] = (
                    chart_df["PLAYER_NAME"] + " (" + chart_df["PLAYER_LAST_TEAM_ABBREVIATION"] + ")"
                )

                click_selection = alt.selection_point(name="click", fields=["PLAYER_NAME"])

                if selected_team != "All Teams":
                    base_color = alt.Color("PLAYER_NAME:N", legend=alt.Legend(title="Player"))
                else:
                    base_color = alt.Color(
                        "PLAYER_LAST_TEAM_ABBREVIATION:N",
                        scale=team_color_scale,
                        legend=alt.Legend(title="Team"),
                    )

                if chart_type == "Bar Chart":
                    base_chart = alt.Chart(chart_df).mark_bar(opacity=0.9).encode(
                        x=alt.X(
                            "PLAYER_LABEL:N",
                            sort=list(chart_df["PLAYER_LABEL"]),
                            axis=alt.Axis(title=None, labelAngle=0),
                        ),
                        y=alt.Y(f"{display_col}:Q", title=display_title),
                        color=base_color,
                        tooltip=[
                            alt.Tooltip("PLAYER_NAME:N", title="Player"),
                            alt.Tooltip("PLAYER_LAST_TEAM_ABBREVIATION:N", title="Team"),
                            alt.Tooltip(f"{display_col}:Q", title=display_title, format=tooltip_format),
                        ],
                        stroke=alt.condition(
                            click_selection,
                            alt.value("#00FF00"),
                            alt.value("transparent"),
                        ),
                        strokeWidth=alt.condition(
                            click_selection,
                            alt.value(2),
                            alt.value(0),
                        ),
                    ).add_params(click_selection)

                    final_chart = base_chart.properties(height=350)

                    event = st.altair_chart(
                        final_chart,
                        width="stretch",
                        on_select="rerun",
                        selection_mode="click",
                        key=f"bar_{label}_{metric}",
                    )

                    try:
                        if event.selection.click:
                            clicked_player = event.selection.click[0]["PLAYER_NAME"]
                            st.session_state[selected_player_key] = clicked_player
                    except Exception:
                        pass

                elif chart_type == "Scatter Plot":
                    scatter_df = chart_df.copy()

                    base_chart = alt.Chart(scatter_df).mark_circle(size=120, opacity=0.8).encode(
                        x=alt.X(
                            f"{fga_col}:Q",
                            title="Shot Contests / G",
                            scale=alt.Scale(zero=False),
                        ),
                        y=alt.Y(
                            f"{display_col}:Q",
                            title=display_title,
                            scale=alt.Scale(zero=False),
                        ),
                        color=base_color,
                        tooltip=[
                            alt.Tooltip("PLAYER_NAME:N", title="Player"),
                            alt.Tooltip("PLAYER_LAST_TEAM_ABBREVIATION:N", title="Team"),
                            alt.Tooltip(f"{fga_col}:Q", title="Shot Contests/G", format=".1f"),
                            alt.Tooltip(f"{display_col}:Q", title=display_title, format=tooltip_format),
                        ],
                        stroke=alt.condition(
                            click_selection,
                            alt.value("#00FF00"),
                            alt.value("transparent"),
                        ),
                        strokeWidth=alt.condition(
                            click_selection,
                            alt.value(2),
                            alt.value(0),
                        ),
                    ).add_params(click_selection)

                    final_chart = base_chart.properties(height=450).interactive()

                    event = st.altair_chart(
                        final_chart,
                        width="stretch",
                        on_select="rerun",
                        selection_mode="click",
                        key=f"scatter_{label}_{metric}",
                    )

                    try:
                        if event.selection.click:
                            clicked_player = event.selection.click[0]["PLAYER_NAME"]
                            st.session_state[selected_player_key] = clicked_player
                    except Exception:
                        pass

                elif chart_type == "Team Distribution (Pie)":
                    if metric != "Shot Contests (FGA)":
                        st.info("Team Distribution is only available for Shot Contests (FGA).")
                        continue

                    if selected_team == "All Teams":
                        st.warning("Select a specific team to view the Team Distribution Pie Chart.")
                        continue

                    pie_df = filtered_df[
                        pd.to_numeric(filtered_df[chart_col], errors="coerce") > 0
                    ].copy()

                    pie_df[chart_col] = pd.to_numeric(pie_df[chart_col], errors="coerce")
                    total = pie_df[chart_col].sum()

                    if total <= 0:
                        st.info("No contests available for this team and zone.")
                        continue

                    pie_df["Percentage (%)"] = pie_df[chart_col] / total * 100

                    pie_click_selection = alt.selection_point(name="click", fields=["PLAYER_NAME"])

                    pie = alt.Chart(pie_df).mark_arc(innerRadius=60).encode(
                        theta=alt.Theta("Percentage (%):Q"),
                        color=alt.Color("PLAYER_NAME:N", legend=alt.Legend(title="Player")),
                        tooltip=[
                            alt.Tooltip("PLAYER_NAME:N", title="Player"),
                            alt.Tooltip(f"{chart_col}:Q", title="Total Contests", format=".1f"),
                            alt.Tooltip("Percentage (%):Q", title="% of Team Total", format=".1f"),
                        ],
                        stroke=alt.condition(
                            pie_click_selection,
                            alt.value("#00FF00"),
                            alt.value("transparent"),
                        ),
                        strokeWidth=alt.condition(
                            pie_click_selection,
                            alt.value(2),
                            alt.value(0),
                        ),
                    ).add_params(pie_click_selection).properties(height=450)

                    event = st.altair_chart(
                        pie,
                        width="stretch",
                        on_select="rerun",
                        selection_mode="click",
                        key=f"pie_{label}_{metric}",
                    )

                    try:
                        if event.selection.click:
                            clicked_player = event.selection.click[0]["PLAYER_NAME"]
                            st.session_state[selected_player_key] = clicked_player
                    except Exception:
                        pass

        if view_mode == "Full Rankings Table":
            ns_pct_col = get_column_for_metric(filtered_df, "Expected/Normal FG%")
            fgm_col = get_column_for_metric(filtered_df, "Defended Field Goals Made")
            freq_col = get_column_for_metric(filtered_df, "Frequency of Shots Defended")

            table_cols = [
                "PLAYER_NAME",
                "PLAYER_LAST_TEAM_ABBREVIATION",
                "PLAYER_POSITION",
                "GP",
                "DEFENSIVE_COMPOSITE_SCORE",
                freq_col,
                fga_col,
                fgm_col,
                ns_pct_col,
                pct_col,
                pm_col,
            ]

            table_cols = [c for c in table_cols if c is not None and c in filtered_df.columns]

            final_table = filtered_df[table_cols].copy()
            sort_key = "__SORT_KEY__"
            final_table[sort_key] = pd.to_numeric(filtered_df[primary_col], errors="coerce")

            rename_map = {
                "PLAYER_NAME": "Player",
                "PLAYER_LAST_TEAM_ABBREVIATION": "Team",
                "PLAYER_POSITION": "Pos",
                "GP": "Games Played",
                "DEFENSIVE_COMPOSITE_SCORE": "Composite Score",
            }

            if freq_col:
                rename_map[freq_col] = "Shot Frequency"
            if fga_col:
                rename_map[fga_col] = "Shot Contests/G"
            if fgm_col:
                rename_map[fgm_col] = "Defended FGM"
            if ns_pct_col:
                rename_map[ns_pct_col] = "Expected FG%"
            if pct_col:
                rename_map[pct_col] = "Defended FG%"
            if pm_col:
                rename_map[pm_col] = "Defensive Impact"

            for col in [freq_col, pct_col, ns_pct_col]:
                if col in final_table.columns:
                    final_table[col] = format_percent_series(final_table[col])

            if pm_col in final_table.columns:
                final_table[pm_col] = format_percent_series(final_table[pm_col], signed=True)

            if "DEFENSIVE_COMPOSITE_SCORE" in final_table.columns:
                final_table["DEFENSIVE_COMPOSITE_SCORE"] = (
                    pd.to_numeric(final_table["DEFENSIVE_COMPOSITE_SCORE"], errors="coerce").round(1)
                )

            final_table = final_table.rename(columns=rename_map)

            ascending_sort = primary_ascending if primary_metric != "Defensive Composite Score" else False
            sorted_table = final_table.sort_values(sort_key, ascending=ascending_sort)
            sorted_table = sorted_table.drop(columns=[sort_key])

            st.dataframe(
                sorted_table,
                width="stretch",
                hide_index=True,
            )

        if chart_type == "Scatter Plot":
            st.caption(
                f"Scatter plot shows all players matching the current filters "
                f"and the {MIN_GAMES_PLAYED}-game minimum."
            )
        else:
            st.caption(
                f"Showing top players with at least {threshold:.1f} shot contests/G "
                f"when no players are manually selected."
            )

        st.markdown("---")

    render_zone_interactive()