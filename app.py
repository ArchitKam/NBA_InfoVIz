#omsairam omsairam omsairam 
import streamlit as st
import pandas as pd
import os
import altair as alt


#streamlit run app.py
# --- 1. SETTINGS & CONFIG ---
st.set_page_config(page_title="NBA Defensive Impact", layout="wide")

st.title("🛡️ NBA Defensive Impact Explorer")

ZONE_MAP = {
    "At the Rim (< 6ft)": "less_than_6ft.csv",
    "In the Paint (< 10ft)": "less_than_10ft.csv",
    "Perimeter (> 15ft)": "greater_than_15ft.csv",
    "3 Pointers": "3_pointers.csv",
    "2 Pointers": "2_pointers.csv",
    "Overall": "overall.csv"
}

METRIC_OPTIONS = [
    "Defensive Impact (Diff %)", 
    "Shot Contests (FGA)", 
    "Defended FG%", 
    "Expected/Normal FG%", 
    "Defended Field Goals Made", 
    "Frequency of Shots Defended"
]

# NBA Team Colors Hex Dictionary
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

# --- 2. SIDEBAR SELECTION ---
st.sidebar.header("📍 Data Selection")

if os.path.exists("nba_data"):
    available_years = sorted([f for f in os.listdir("nba_data") if os.path.isdir(os.path.join("nba_data", f))], reverse=True)
else:
    available_years = []
    st.error("⚠️ 'nba_data' folder not found. Please run your downloader script!")

selected_year = st.sidebar.selectbox("Season", available_years)
selected_label = st.sidebar.selectbox("Shot Zone", list(ZONE_MAP.keys()))

st.sidebar.header("📊 Chart Metrics")
selected_metrics = st.sidebar.multiselect(
    "Select Metrics to Visualize (Scrollable)", 
    METRIC_OPTIONS, 
    default=["Defensive Impact (Diff %)", "Shot Contests (FGA)"]
)

# --- 3. DATA LOADING ---
def load_data(year, label):
    file_path = os.path.join("nba_data", year, ZONE_MAP[label])
    return pd.read_csv(file_path) if os.path.exists(file_path) else None

df = load_data(selected_year, selected_label)

# --- 4. FILTERS ---
st.sidebar.header("🔍 Filters")

if df is not None:
    all_players = sorted(df['PLAYER_NAME'].unique().tolist())
    selected_players = st.sidebar.multiselect("Search & Select Player(s)", all_players)
    
    teams = ["All Teams"] + sorted(df['PLAYER_LAST_TEAM_ABBREVIATION'].unique().tolist())
    selected_team = st.sidebar.selectbox("Team", teams)
else:
    selected_players = []
    selected_team = "All Teams"

# --- SMART COLUMN MAPPER ---
def get_column_for_metric(dataframe, metric_name):
    cols = dataframe.columns
    if metric_name == "Defensive Impact (Diff %)":
        return [c for c in cols if 'PLUSMINUS' in c][0]
    elif metric_name == "Shot Contests (FGA)":
        return [c for c in cols if 'FGA' in c][0]
    elif metric_name == "Defended FG%":
        return [c for c in cols if 'PCT' in c and 'NS_' not in c and 'NORMAL' not in c and 'PLUSMINUS' not in c][0]
    elif metric_name == "Expected/Normal FG%":
        return [c for c in cols if 'NS_' in c or 'NORMAL' in c][0]
    elif metric_name == "Defended Field Goals Made":
        return [c for c in cols if 'FGM' in c][0]
    elif metric_name == "Frequency of Shots Defended":
        return [c for c in cols if 'FREQ' in c][0]
    return 'PLUSMINUS'

# --- 5. MAIN CONTENT ---
if df is not None:
    filtered_df = df.copy()
    
    # Apply Filters
    if selected_players:
        filtered_df = filtered_df[filtered_df['PLAYER_NAME'].isin(selected_players)]
    if selected_team != "All Teams":
        filtered_df = filtered_df[filtered_df['PLAYER_LAST_TEAM_ABBREVIATION'] == selected_team]

    fga_col = get_column_for_metric(df, "Shot Contests (FGA)")
    pct_col = get_column_for_metric(df, "Defended FG%")
    
    if not filtered_df.empty and selected_metrics:
        
        primary_metric = selected_metrics[0]
        primary_col = get_column_for_metric(df, primary_metric)
        primary_ascending = primary_metric in ["Defensive Impact (Diff %)", "Defended FG%"]

        if selected_players:
            threshold = 0
            hero_df = filtered_df.sort_values(primary_col, ascending=primary_ascending)
        else:
            threshold = filtered_df[fga_col].mean()
            hero_df = filtered_df[filtered_df[fga_col] >= threshold].sort_values(primary_col, ascending=primary_ascending)
        
        if not hero_df.empty:
            top_player = hero_df.iloc[0]
            
            # --- HERO SECTION ---
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])
                with col1:
                    try:
                        p_id = int(top_player['CLOSE_DEF_PERSON_ID'])
                        st.image(f"https://ak-static.cms.nba.com/wp-content/uploads/headshots/nba/latest/260x190/{p_id}.png", width=250)
                    except:
                        st.image("https://stats.nba.com/media/img/league/nba-logo.svg", width=200)
                
                with col2:
                    full_name = top_player['PLAYER_NAME']
                    first_name, last_name = full_name.split(" ", 1) if " " in full_name else (full_name, "")
                    
                    st.html(f"""
                        <div style="line-height: 1.0; margin-bottom: 20px;">
                            <h1 style="font-size: 55px; margin: 0; text-transform: uppercase; font-weight: 700; opacity: 0.8;">{first_name}</h1>
                            <h1 style="font-size: 90px; margin: 0; text-transform: uppercase; font-weight: 900; color: {NBA_COLORS.get(top_player['PLAYER_LAST_TEAM_ABBREVIATION'], '#1D428A')};">{last_name}</h1>
                        </div>
                    """)
                    st.subheader(f"{top_player['PLAYER_LAST_TEAM_ABBREVIATION']} | {top_player['PLAYER_POSITION']}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Shot Contests/G", f"{top_player[fga_col]:.1f}")
                    m2.metric("Defended FG%", f"{top_player[pct_col]*100:.1f}%")
                    pm_col = get_column_for_metric(df, "Defensive Impact (Diff %)")
                    m3.metric("Defensive Impact", f"{top_player[pm_col]}%", delta_color="inverse")

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
                    
                    chart_col = get_column_for_metric(df, metric)
                    sort_asc = metric in ["Defensive Impact (Diff %)", "Defended FG%"]
                    
                    if selected_players:
                        chart_df = filtered_df.sort_values(chart_col, ascending=sort_asc)
                    else:
                        chart_df = filtered_df[filtered_df[fga_col] >= threshold].sort_values(chart_col, ascending=sort_asc).head(10)
                    
                    # --- NEW: Create a combined label with the team in parentheses ---
                    chart_df['PLAYER_LABEL'] = chart_df['PLAYER_NAME'] + ' (' + chart_df['PLAYER_LAST_TEAM_ABBREVIATION'] + ')'
                    
                    chart = alt.Chart(chart_df).mark_bar().encode(
                        x=alt.X(
                            'PLAYER_LABEL:N', 
                            sort=[x for x in chart_df['PLAYER_LABEL']], 
                            axis=alt.Axis(title=None, labelAngle=0, labelExpr="split(datum.value, ' ')")
                        ),
                        y=alt.Y(f'{chart_col}:Q', title=metric),
                        color=alt.Color(
                            'PLAYER_LAST_TEAM_ABBREVIATION:N',
                            scale=team_color_scale,
                            legend=alt.Legend(title="Team")
                        ),
                        # Keep the tooltip simple so it doesn't duplicate the team name
                        tooltip=['PLAYER_NAME', 'PLAYER_LAST_TEAM_ABBREVIATION', f'{chart_col}:Q']
                    ).properties(height=350) 
                    
                    st.altair_chart(chart, width="stretch")
                    st.markdown("<br>", unsafe_allow_html=True) 

                if not selected_players and threshold > 0:
                    st.caption(f"Note: Showing top 10 league leaders with at least {threshold:.1f} avg contests/game.")

            with tab2:
                st.write("### All Player Stats")
                
                pm_col = get_column_for_metric(df, "Defensive Impact (Diff %)")
                ns_pct_col = get_column_for_metric(df, "Expected/Normal FG%")
                fgm_col = get_column_for_metric(df, "Defended Field Goals Made")
                freq_col = get_column_for_metric(df, "Frequency of Shots Defended")
                
                final_table = filtered_df[['PLAYER_NAME', 'PLAYER_LAST_TEAM_ABBREVIATION', 'PLAYER_POSITION', freq_col, fga_col, fgm_col, ns_pct_col, pct_col, pm_col]].copy()
                
                final_table[pct_col] = (final_table[pct_col] * 100).round(1).astype(str) + '%'
                final_table[ns_pct_col] = (final_table[ns_pct_col] * 100).round(1).astype(str) + '%'
                final_table[freq_col] = (final_table[freq_col] * 100).round(1).astype(str) + '%'
                
                st.dataframe(final_table.sort_values(primary_col, ascending=primary_ascending), width="stretch", hide_index=True)

        else:
            st.warning("Not enough data. Try clearing some filters.")
    elif not selected_metrics:
        st.info("👆 Please select at least one metric from the sidebar to generate charts.")
    else:
        st.warning("No players found with those filters.")
else:
    st.error("Please run your data download script to populate the folders!")