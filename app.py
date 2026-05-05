#omsairam omsairam omsairam omsairam omsairam omsairam 
import streamlit as st
import pandas as pd
import os
import altair as alt

# streamlit run app.py

# --- 1. SETTINGS & CONFIG ---
st.set_page_config(page_title="NBA Defensive Impact", layout="wide")

st.title("🛡️ NBA Defensive Impact Explorer")

ZONE_MAP = {
    "Overall": "overall.csv",
    "At the Rim (< 6ft)": "less_than_6ft.csv",
    "In the Paint (< 10ft)": "less_than_10ft.csv",
    "Perimeter (> 15ft)": "greater_than_15ft.csv"
}

METRIC_OPTIONS = [
    "Defensive Composite Score",
    "Defensive Impact (Diff %)",
    "Shot Contests (FGA)",
    "Defended FG%",
    "Expected/Normal FG%",
    "Defended Field Goals Made",
    "Frequency of Shots Defended"
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

# --- 2. DATA HELPERS ---
@st.cache_data
def load_data(year, label):
    file_path = os.path.join("nba_data", year, ZONE_MAP[label])
    return pd.read_csv(file_path) if os.path.exists(file_path) else None

def get_column_for_metric(dataframe, metric_name):
    cols = dataframe.columns

    if metric_name == "Defensive Impact (Diff %)":
        matches = [c for c in cols if "PLUSMINUS" in c]
    elif metric_name == "Shot Contests (FGA)":
        matches = [c for c in cols if "FGA" in c]
    elif metric_name == "Defended FG%":
        matches = [c for c in cols if "PCT" in c and "NS_" not in c and "NORMAL" not in c and "PLUSMINUS" not in c]
    elif metric_name == "Expected/Normal FG%":
        matches = [c for c in cols if "NS_" in c or "NORMAL" in c]
    elif metric_name == "Defended Field Goals Made":
        matches = [c for c in cols if "FGM" in c]
    elif metric_name == "Frequency of Shots Defended":
        matches = [c for c in cols if "FREQ" in c]
    else:
        matches = []

    return matches[0] if matches else None

def percentile_rank(series, higher_is_better=True):
    s = pd.to_numeric(series, errors="coerce")
    if higher_is_better:
        return s.rank(pct=True, method="average") * 100
    return (-s).rank(pct=True, method="average") * 100

def add_defensive_composite(dataframe):
    if dataframe is None or dataframe.empty:
        return dataframe

    df_local = dataframe.copy()

    impact_col = get_column_for_metric(df_local, "Defensive Impact (Diff %)")
    fga_col = get_column_for_metric(df_local, "Shot Contests (FGA)")
    pct_col = get_column_for_metric(df_local, "Defended FG%")
    expected_col = get_column_for_metric(df_local, "Expected/Normal FG%")
    freq_col = get_column_for_metric(df_local, "Frequency of Shots Defended")

    required_cols = [impact_col, fga_col, pct_col, expected_col]
    if any(col is None for col in required_cols):
        df_local["DEFENSIVE_COMPOSITE_SCORE"] = None
        return df_local

    for col in required_cols:
        df_local[col] = pd.to_numeric(df_local[col], errors="coerce")

    if freq_col is not None:
        df_local[freq_col] = pd.to_numeric(df_local[freq_col], errors="coerce")

    df_local["FG_SUPPRESSION"] = df_local[expected_col] - df_local[pct_col]

    df_local["IMPACT_PCTL"] = percentile_rank(df_local[impact_col], higher_is_better=False)
    df_local["VOLUME_PCTL"] = percentile_rank(df_local[fga_col], higher_is_better=True)
    df_local["SUPPRESSION_PCTL"] = percentile_rank(df_local["FG_SUPPRESSION"], higher_is_better=True)

    if freq_col is not None:
        df_local["FREQ_PCTL"] = percentile_rank(df_local[freq_col], higher_is_better=True)
    else:
        df_local["FREQ_PCTL"] = 50.0

    df_local["DEFENSIVE_COMPOSITE_SCORE"] = (
        0.55 * df_local["IMPACT_PCTL"] +
        0.20 * df_local["VOLUME_PCTL"] +
        0.15 * df_local["SUPPRESSION_PCTL"] +
        0.10 * df_local["FREQ_PCTL"]
    ).round(1)

    return df_local

def get_chart_column(dataframe, metric_name):
    if metric_name == "Defensive Composite Score":
        return "DEFENSIVE_COMPOSITE_SCORE"
    return get_column_for_metric(dataframe, metric_name)

# --- 3. SIDEBAR SELECTION ---
st.sidebar.header("📍 Data Selection")

if os.path.exists("nba_data"):
    available_years = sorted(
        [f for f in os.listdir("nba_data") if os.path.isdir(os.path.join("nba_data", f))],
        reverse=True
    )
else:
    available_years = []
    st.error("⚠️ 'nba_data' folder not found. Please run your downloader script!")

if not available_years:
    st.stop()

selected_year = st.sidebar.selectbox("Season", available_years)

zone_options = list(ZONE_MAP.keys())
default_zone_index = zone_options.index("Overall")
selected_label = st.sidebar.selectbox("Shot Zone", zone_options, index=default_zone_index)

st.sidebar.header("📊 Chart Metrics")
selected_metrics = st.sidebar.multiselect(
    "Select Metrics to Visualize (Scrollable)",
    METRIC_OPTIONS,
    default=["Defensive Composite Score"]
)

# --- 4. DATA LOADING ---
df = load_data(selected_year, selected_label)

# --- 5. FILTERS ---
st.sidebar.header("🔍 Filters")

if df is not None:
    all_players = sorted(df["PLAYER_NAME"].dropna().unique().tolist())
    selected_players = st.sidebar.multiselect("Search & Select Player(s)", all_players)

    teams = ["All Teams"] + sorted(df["PLAYER_LAST_TEAM_ABBREVIATION"].dropna().unique().tolist())
    selected_team = st.sidebar.selectbox("Team", teams)
else:
    selected_players = []
    selected_team = "All Teams"

# --- 6. MAIN CONTENT ---
if df is not None:
    filtered_df = df.copy()

    if selected_players:
        filtered_df = filtered_df[filtered_df["PLAYER_NAME"].isin(selected_players)]

    if selected_team != "All Teams":
        filtered_df = filtered_df[filtered_df["PLAYER_LAST_TEAM_ABBREVIATION"] == selected_team]

    filtered_df = add_defensive_composite(filtered_df)

    fga_col = get_column_for_metric(filtered_df, "Shot Contests (FGA)")
    pct_col = get_column_for_metric(filtered_df, "Defended FG%")

    if not filtered_df.empty and selected_metrics:
        primary_metric = selected_metrics[0]
        primary_col = get_chart_column(filtered_df, primary_metric)

        if primary_col is None or primary_col not in filtered_df.columns:
            st.warning(f"Could not compute {primary_metric} for this selection.")
            st.stop()

        primary_ascending = primary_metric in ["Defensive Impact (Diff %)", "Defended FG%"]

        if selected_players:
            threshold = 0
            hero_df = filtered_df.sort_values(primary_col, ascending=primary_ascending)
        else:
            if fga_col is not None:
                threshold = filtered_df[fga_col].mean()
                hero_df = filtered_df[filtered_df[fga_col] >= threshold].sort_values(primary_col, ascending=primary_ascending)
            else:
                threshold = 0
                hero_df = filtered_df.sort_values(primary_col, ascending=primary_ascending)

        if not hero_df.empty:
            top_player = hero_df.iloc[0]

            # --- HERO SECTION ---
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    try:
                        p_id = int(top_player["CLOSE_DEF_PERSON_ID"])
                        st.image(
                            f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{p_id}.png",
                            width=250
                        )
                    except Exception:
                        st.image("https://stats.nba.com/media/img/league/nba-logo.svg", width=200)

                with col2:
                    full_name = top_player["PLAYER_NAME"]
                    first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")

                    st.markdown(f"""
                        <div style="line-height: 1.0; margin-bottom: 20px;">
                            <h1 style="font-size: 55px; margin: 0; text-transform: uppercase; font-weight: 700; opacity: 0.8;">{first_name}</h1>
                            <h1 style="font-size: 90px; margin: 0; text-transform: uppercase; font-weight: 900; color: {NBA_COLORS.get(top_player['PLAYER_LAST_TEAM_ABBREVIATION'], '#1D428A')};">{last_name}</h1>
                        </div>
                    """, unsafe_allow_html=True)

                    st.subheader(f"{top_player['PLAYER_LAST_TEAM_ABBREVIATION']} | {top_player['PLAYER_POSITION']}")

                    m1, m2, m3, m4 = st.columns(4)

                    if primary_metric in ["Defended FG%", "Expected/Normal FG%"]:
                        primary_display = f"{top_player[primary_col] * 100:.1f}%"
                    elif primary_metric == "Defensive Composite Score":
                        primary_display = f"{top_player[primary_col]:.1f}"
                    elif primary_metric in ["Shot Contests (FGA)", "Defended Field Goals Made"]:
                        primary_display = f"{top_player[primary_col]:.1f}"
                    else:
                        primary_display = f"{top_player[primary_col]:.1f}%"

                    m1.metric(primary_metric, primary_display)
                    m2.metric("Shot Contests/G", f"{top_player[fga_col]:.1f}" if fga_col else "—")
                    m3.metric("Defended FG%", f"{top_player[pct_col] * 100:.1f}%" if pct_col else "—")
                    m4.metric("Composite Score", f"{top_player['DEFENSIVE_COMPOSITE_SCORE']:.1f}" if "DEFENSIVE_COMPOSITE_SCORE" in top_player.index else "—")

                    if primary_metric == "Defensive Composite Score":
                        st.caption(
                            "Composite Score = 55% Impact percentile + 20% Volume percentile + "
                            "15% FG Suppression percentile + 10% Frequency percentile, "
                            "computed from the current filtered zone and player pool."
                        )

            st.markdown("---")

            # --- VISUALIZATION TABS ---
            tab1, tab2 = st.tabs(["📊 Visual Comparisons", "📜 Full Rankings Table"])

            with tab1:
                st.write(f"### Player Comparisons: {selected_label}")

                team_color_scale = alt.Scale(
                    domain=list(NBA_COLORS.keys()),
                    range=list(NBA_COLORS.values())
                )

                for metric in selected_metrics:
                    st.markdown(f"#### 📉 {metric}")

                    chart_col = get_chart_column(filtered_df, metric)
                    if chart_col is None or chart_col not in filtered_df.columns:
                        st.info(f"{metric} is not available for this selection.")
                        continue

                    sort_asc = metric in ["Defensive Impact (Diff %)", "Defended FG%"]

                    if selected_players:
                        chart_df = filtered_df.sort_values(chart_col, ascending=sort_asc).copy()
                    else:
                        if fga_col is not None:
                            chart_df = (
                                filtered_df[filtered_df[fga_col] >= threshold]
                                .sort_values(chart_col, ascending=sort_asc)
                                .head(10)
                                .copy()
                            )
                        else:
                            chart_df = filtered_df.sort_values(chart_col, ascending=sort_asc).head(10).copy()

                    if chart_df.empty:
                        st.info(f"No players available to display for {metric}.")
                        continue

                    chart_df["PLAYER_LABEL"] = chart_df["PLAYER_NAME"] + " (" + chart_df["PLAYER_LAST_TEAM_ABBREVIATION"] + ")"

                    if metric in ["Defended FG%", "Expected/Normal FG%"]:
                        chart_df[f"{chart_col}_DISPLAY"] = chart_df[chart_col] * 100
                        y_col = f"{chart_col}_DISPLAY"
                        tooltip_format = ".1f"
                    else:
                        y_col = chart_col
                        tooltip_format = ".1f"

                    chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X(
                            "PLAYER_LABEL:N",
                            sort=[x for x in chart_df["PLAYER_LABEL"]],
                            axis=alt.Axis(title=None, labelAngle=0)
                        ),
                        y=alt.Y(f"{y_col}:Q", title=metric),
                        color=alt.Color(
                            "PLAYER_LAST_TEAM_ABBREVIATION:N",
                            scale=team_color_scale,
                            legend=alt.Legend(title="Team")
                        ),
                        tooltip=[
                            "PLAYER_NAME:N",
                            "PLAYER_LAST_TEAM_ABBREVIATION:N",
                            alt.Tooltip(f"{y_col}:Q", title=metric, format=tooltip_format)
                        ]
                    ).properties(height=350)

                    st.altair_chart(chart, width="stretch")
                    st.markdown("<br>", unsafe_allow_html=True)

                if not selected_players and threshold > 0:
                    st.caption(f"Note: Showing top 10 league leaders with at least {threshold:.1f} avg contests/game.")

            with tab2:
                st.write("### All Player Stats")

                pm_col = get_column_for_metric(filtered_df, "Defensive Impact (Diff %)")
                ns_pct_col = get_column_for_metric(filtered_df, "Expected/Normal FG%")
                fgm_col = get_column_for_metric(filtered_df, "Defended Field Goals Made")
                freq_col = get_column_for_metric(filtered_df, "Frequency of Shots Defended")

                table_cols = [
                    "PLAYER_NAME",
                    "PLAYER_LAST_TEAM_ABBREVIATION",
                    "PLAYER_POSITION",
                    "DEFENSIVE_COMPOSITE_SCORE"
                ]

                for col in [freq_col, fga_col, fgm_col, ns_pct_col, pct_col, pm_col]:
                    if col is not None and col not in table_cols:
                        table_cols.append(col)

                final_table = filtered_df[table_cols].copy()

                if "DEFENSIVE_COMPOSITE_SCORE" in final_table.columns:
                    final_table["DEFENSIVE_COMPOSITE_SCORE"] = final_table["DEFENSIVE_COMPOSITE_SCORE"].round(1)

                if pct_col is not None:
                    final_table[pct_col] = (final_table[pct_col] * 100).round(1).astype(str) + "%"
                if ns_pct_col is not None:
                    final_table[ns_pct_col] = (final_table[ns_pct_col] * 100).round(1).astype(str) + "%"
                if freq_col is not None:
                    final_table[freq_col] = (final_table[freq_col] * 100).round(1).astype(str) + "%"

                rename_map = {
                    "PLAYER_NAME": "Player",
                    "PLAYER_LAST_TEAM_ABBREVIATION": "Team",
                    "PLAYER_POSITION": "Pos",
                    "DEFENSIVE_COMPOSITE_SCORE": "Composite Score"
                }

                if freq_col is not None:
                    rename_map[freq_col] = "Shot Frequency"
                if fga_col is not None:
                    rename_map[fga_col] = "Shot Contests/G"
                if fgm_col is not None:
                    rename_map[fgm_col] = "Defended FGM"
                if ns_pct_col is not None:
                    rename_map[ns_pct_col] = "Expected FG%"
                if pct_col is not None:
                    rename_map[pct_col] = "Defended FG%"
                if pm_col is not None:
                    rename_map[pm_col] = "Defensive Impact"

                final_table = final_table.rename(columns=rename_map)

                sort_col = "Composite Score" if primary_metric == "Defensive Composite Score" else rename_map.get(primary_col, primary_col)
                ascending_sort = primary_ascending if primary_metric != "Defensive Composite Score" else False

                st.dataframe(
                    final_table.sort_values(sort_col, ascending=ascending_sort),
                    width="stretch",
                    hide_index=True
                )

        else:
            st.warning("Not enough data. Try clearing some filters.")
    elif not selected_metrics:
        st.info("👆 Please select at least one metric from the sidebar to generate charts.")
    else:
        st.warning("No players found with those filters.")
else:
    st.error("Please run your data download script to populate the folders!")