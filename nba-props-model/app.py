import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
from typing import Any, Optional

# Utility function for safe printing that works in both console and Streamlit
def safe_print(*args, **kwargs):
    """Print to both console and Streamlit for debugging"""
    print(*args, **kwargs)
    if 'st' in sys.modules:
        st.text(' '.join(str(arg) for arg in args))
import time
import re
from enum import Enum
from difflib import SequenceMatcher

def render_hit_rate_buttons():
    """Render the hit rate filter buttons in the UI"""
    # Initialize session state if not exists
    if 'hit_rate_range' not in st.session_state:
        st.session_state.hit_rate_range = "last_10"
    
    # Create a container for the buttons
    with st.container():
        st.markdown("#### 📊 Performance Metrics")
        
        # Use columns for button layout
        col1, col2, col3 = st.columns(3)
        
        # Button configurations
        button_configs = [
            {"label": "Last 5 Games", "key": "last_5", "help": "Show performance for last 5 games"},
            {"label": "Last 10 Games", "key": "last_10", "help": "Show performance for last 10 games"},
            {"label": "Season", "key": "season", "help": "Show performance for entire season"}
        ]
        
        # Create buttons
        for i, config in enumerate(button_configs):
            with [col1, col2, col3][i]:
                is_active = st.session_state.hit_rate_range == config["key"]
                if st.button(
                    config["label"],
                    key=f"hit_rate_btn_{config['key']}",
                    help=config["help"],
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    # Update the selected range in session state
                    st.session_state.hit_rate_range = config["key"]
                    # Force a rerun to update the UI
                    st.rerun()
        
        # Display the current selection
        st.caption(f"Showing: {st.session_state.hit_rate_range.replace('_', ' ').title()}")
    
    # Add a small space after the buttons
    st.markdown("<br>", unsafe_allow_html=True)

class HitRateRange(Enum):
    LAST_5 = "last_5"
    LAST_10 = "last_10"
    SEASON = "season"

# Initialize session state for hit rate range if it doesn't exist
if 'hit_rate_range' not in st.session_state:
    st.session_state.hit_rate_range = "last_10"  # Default to last 10 games

# Initialize session state for bet sheet
if 'bet_sheet' not in st.session_state:
    st.session_state.bet_sheet = []

import time
from datetime import datetime, timedelta

# make sure we can import from utils/
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

from utils.data_fetcher import (
    get_player_id,
    get_opponent_recent_games,
    get_head_to_head_history,
    get_player_position,
    get_team_defense_rank_vs_position,
    get_players_by_team,
    get_upcoming_games,
    fetch_fanduel_lines,      # live Odds API -> FanDuel lines
    get_event_id_for_game,    # resolve game -> event id
    get_player_fanduel_line,  # pull line for one player/stat
)

from utils.cached_data_fetcher import (
    get_player_game_logs_cached_db,
    get_team_stats_cached_db,
    scrape_defense_vs_position_cached_db,
)

from utils.database import get_cache_stats, clear_old_seasons

from utils.features import (
    build_enhanced_feature_vector,
)

from utils.model import PlayerPropModel


# ─────────────────────────────
# Page config
# ─────────────────────────────
st.set_page_config(
    page_title="NBA Player Props Model",
    page_icon="🏀",
    layout="wide",
)

# ─────────────────────────────
# Theme Toggle Functionality
# ─────────────────────────────
# Initialize theme early
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# Apply theme CSS immediately (before any content)
def apply_theme_css(theme):
    """Apply custom CSS based on selected theme"""
    if theme == 'dark':
        dark_mode_css = """
        <style>
        /* Main background and text */
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        [data-testid="stSidebar"] .css-1d391kg {
            background-color: #1E1E1E;
        }
        
        /* Main content area */
        .main .block-container {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* Headers and text */
        h1, h2, h3, h4, h5, h6 {
            color: #FAFAFA !important;
        }
        
        /* Paragraphs and body text */
        p, span, div, label {
            color: #E0E0E0 !important;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #FAFAFA !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: #B0B0B0 !important;
        }
        
        /* Dataframes */
        .dataframe {
            background-color: #1E1E1E !important;
            color: #FAFAFA !important;
        }
        
        .dataframe th {
            background-color: #2E2E2E !important;
            color: #FAFAFA !important;
        }
        
        .dataframe td {
            background-color: #1E1E1E !important;
            color: #FAFAFA !important;
        }
        
        /* Buttons */
        .stButton > button {
            background-color: #2E2E2E;
            color: #FAFAFA;
            border: 1px solid #404040;
        }
        
        .stButton > button:hover {
            background-color: #3E3E3E;
            border-color: #505050;
        }
        
        /* Selectbox and inputs */
        .stSelectbox > div > div {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        /* Selectbox dropdown menu - enhanced for readability */
        .stSelectbox [data-baseweb="select"] {
            background-color: #1E1E1E !important;
            color: #FAFAFA !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div {
            background-color: #1E1E1E !important;
            color: #FAFAFA !important;
        }
        
        /* Dropdown menu options container */
        [data-baseweb="popover"] {
            background-color: #2E2E2E !important;
            border: 1px solid #404040 !important;
        }
        
        /* Individual dropdown options */
        [data-baseweb="option"] {
            background-color: #2E2E2E !important;
            color: #FAFAFA !important;
        }
        
        [data-baseweb="option"]:hover {
            background-color: #3E3E3E !important;
            color: #FFFFFF !important;
        }
        
        [data-baseweb="option"][aria-selected="true"] {
            background-color: #1F77B4 !important;
            color: #FFFFFF !important;
        }
        
        /* Selectbox text visibility */
        .stSelectbox label {
            color: #FAFAFA !important;
            font-weight: 500 !important;
        }
        
        /* Selectbox value display */
        .stSelectbox [data-baseweb="select"] > div > div {
            color: #FAFAFA !important;
        }
        
        /* Dropdown list items - additional styling */
        ul[role="listbox"] {
            background-color: #2E2E2E !important;
        }
        
        ul[role="listbox"] li {
            background-color: #2E2E2E !important;
            color: #FAFAFA !important;
        }
        
        ul[role="listbox"] li:hover {
            background-color: #3E3E3E !important;
            color: #FFFFFF !important;
        }
        
        /* Ensure dropdown text is visible */
        [data-baseweb="select"] span {
            color: #FAFAFA !important;
        }
        
        /* Additional dropdown styling for all variations */
        div[data-baseweb="select"] {
            color: #FAFAFA !important;
        }
        
        /* Dropdown menu container */
        div[role="listbox"] {
            background-color: #2E2E2E !important;
        }
        
        div[role="listbox"] > div {
            background-color: #2E2E2E !important;
            color: #FAFAFA !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #1E1E1E;
            color: #FAFAFA !important;
        }
        
        .streamlit-expanderContent {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        
        /* Info, success, warning, error boxes */
        .stAlert {
            background-color: #1E1E1E;
            border: 1px solid #404040;
        }
        
        .stInfo {
            background-color: #1E3A5F;
            color: #E0F2FF !important;
        }
        
        .stSuccess {
            background-color: #1E4A3E;
            color: #E0FFE0 !important;
        }
        
        .stWarning {
            background-color: #4A3E1E;
            color: #FFF4E0 !important;
        }
        
        .stError {
            background-color: #4A1E1E;
            color: #FFE0E0 !important;
        }
        
        /* Captions */
        .stCaption {
            color: #B0B0B0 !important;
        }
        
        /* Markdown text */
        .stMarkdown {
            color: #E0E0E0 !important;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #FAFAFA !important;
        }
        
        /* Code blocks */
        code {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        /* Tables */
        table {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        table th {
            background-color: #2E2E2E;
            color: #FAFAFA;
        }
        
        table td {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        /* Dividers */
        hr {
            border-color: #404040;
        }
        
        /* Links */
        a {
            color: #4A9EFF !important;
        }
        
        a:hover {
            color: #6BB0FF !important;
        }
        
        /* Columns */
        [data-testid="column"] {
            background-color: transparent;
        }
        
        /* Streamlit widgets */
        .stTextInput > div > div > input {
            background-color: #1E1E1E;
            color: #FAFAFA;
            border: 1px solid #404040;
        }
        
        /* Checkbox and radio */
        .stCheckbox label, .stRadio label {
            color: #FAFAFA !important;
        }
        
        /* Tooltips */
        [data-testid="stTooltip"] {
            background-color: #2E2E2E;
            color: #FAFAFA;
        }
        
        /* Multi-select */
        .stMultiSelect [data-baseweb="select"] {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        /* Number input */
        .stNumberInput > div > div > input {
            background-color: #1E1E1E;
            color: #FAFAFA;
            border: 1px solid #404040;
        }
        
        /* Slider */
        .stSlider {
            color: #FAFAFA;
        }
        
        /* Progress bar */
        .stProgress > div > div > div {
            background-color: #2E2E2E;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-color: #404040;
        }
        
        /* JSON viewer */
        .stJson {
            background-color: #1E1E1E;
            color: #FAFAFA;
        }
        
        /* Balloons and snow */
        .stBalloon, .stSnow {
            filter: brightness(0.8);
        }
        
        /* Sidebar navigation */
        .css-1d391kg {
            background-color: #1E1E1E;
        }
        
        /* Main content blocks */
        .element-container {
            color: #E0E0E0;
        }
        
        /* Ensure all text in widgets is visible */
        .stWidget label {
            color: #FAFAFA !important;
        }
        
        /* Data editor */
        [data-testid="stDataEditor"] {
            background-color: #1E1E1E;
        }
        
        /* Charts and plots */
        .js-plotly-plot {
            background-color: #1E1E1E;
        }
        </style>
        """
        st.markdown(dark_mode_css, unsafe_allow_html=True)
    else:
        # Light mode - enhanced contrast and readability
        light_mode_css = """
        <style>
        /* Main background and text - high contrast */
        .stApp {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* Headers - very dark for maximum readability */
        h1, h2, h3, h4, h5, h6 {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        /* Body text - dark for readability */
        p, span, div, label {
            color: #1A1A1A !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #F8F9FA;
            color: #000000;
        }
        
        [data-testid="stSidebar"] .css-1d391kg {
            background-color: #F8F9FA;
        }
        
        /* Main content area */
        .main .block-container {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* Metrics - high contrast */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stMetricLabel"] {
            color: #333333 !important;
            font-weight: 500 !important;
        }
        
        /* Dataframes - enhanced visibility */
        .dataframe {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E0E0E0 !important;
        }
        
        .dataframe th {
            background-color: #F5F5F5 !important;
            color: #000000 !important;
            font-weight: 600 !important;
            border: 1px solid #D0D0D0 !important;
        }
        
        .dataframe td {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E0E0E0 !important;
        }
        
        .dataframe tr:hover {
            background-color: #F0F0F0 !important;
        }
        
        /* Buttons - high contrast */
        .stButton > button {
            background-color: #1F77B4;
            color: #FFFFFF;
            border: 1px solid #1F77B4;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: #1565A0;
            border-color: #1565A0;
        }
        
        /* Selectbox and inputs */
        .stSelectbox > div > div {
            background-color: #2E2E2E;
            color: #FFFFFF;
            border: 1px solid #404040;
        }
        
        /* Selectbox dropdown menu - enhanced for readability */
        .stSelectbox [data-baseweb="select"] {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
            border: 1px solid #404040 !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
        }
        
        /* Dropdown menu options container */
        [data-baseweb="popover"] {
            background-color: #2E2E2E !important;
            border: 2px solid #1F77B4 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        
        /* Individual dropdown options */
        [data-baseweb="option"] {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
            font-weight: 400 !important;
        }
        
        [data-baseweb="option"]:hover {
            background-color: #3E3E3E !important;
            color: #FFFFFF !important;
        }
        
        [data-baseweb="option"][aria-selected="true"] {
            background-color: #1F77B4 !important;
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }
        
        /* Selectbox text visibility */
        .stSelectbox label {
            color: #000000 !important;
            font-weight: 500 !important;
        }
        
        /* Selectbox value display - white text on dark background */
        .stSelectbox [data-baseweb="select"] > div > div {
            color: #FFFFFF !important;
            font-weight: 400 !important;
        }
        
        /* Selectbox value text - ensure white - ALL variations */
        .stSelectbox [data-baseweb="select"] span,
        .stSelectbox [data-baseweb="select"] p,
        .stSelectbox [data-baseweb="select"] div,
        .stSelectbox [data-baseweb="select"] * {
            color: #FFFFFF !important;
        }
        
        /* Selectbox input value */
        .stSelectbox [data-baseweb="select"] input {
            color: #FFFFFF !important;
        }
        
        /* Dropdown list items - additional styling */
        ul[role="listbox"] {
            background-color: #2E2E2E !important;
        }
        
        ul[role="listbox"] li,
        ul[role="listbox"] li *,
        ul[role="listbox"] li span,
        ul[role="listbox"] li div,
        ul[role="listbox"] li p {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
        }
        
        ul[role="listbox"] li:hover,
        ul[role="listbox"] li:hover *,
        ul[role="listbox"] li:hover span,
        ul[role="listbox"] li:hover div {
            background-color: #3E3E3E !important;
            color: #FFFFFF !important;
        }
        
        /* Additional dropdown styling for all variations */
        div[data-baseweb="select"] {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
        }
        
        div[data-baseweb="select"] * {
            color: #FFFFFF !important;
        }
        
        /* Dropdown menu container */
        div[role="listbox"] {
            background-color: #2E2E2E !important;
        }
        
        div[role="listbox"] > div,
        div[role="listbox"] > div *,
        div[role="listbox"] span,
        div[role="listbox"] div,
        div[role="listbox"] p {
            background-color: #2E2E2E !important;
            color: #FFFFFF !important;
        }
        
        /* Target all text in dropdown options - most aggressive */
        [data-baseweb="option"] *,
        [data-baseweb="option"] span,
        [data-baseweb="option"] div,
        [data-baseweb="option"] p {
            color: #FFFFFF !important;
        }
        
        /* Popover container - all text white */
        [data-baseweb="popover"] *,
        [data-baseweb="popover"] span,
        [data-baseweb="popover"] div,
        [data-baseweb="popover"] p,
        [data-baseweb="popover"] li {
            color: #FFFFFF !important;
        }
        
        /* Universal selector for selectbox text */
        .stSelectbox [data-baseweb="select"] * {
            color: #FFFFFF !important;
        }
        
        /* Maximum specificity override - force white text everywhere in dropdown */
        .stSelectbox [data-baseweb="select"] [style*="color"] {
            color: #FFFFFF !important;
        }
        
        [data-baseweb="popover"] [style*="color"] {
            color: #FFFFFF !important;
        }
        
        [data-baseweb="option"] [style*="color"] {
            color: #FFFFFF !important;
        }
        
        /* Force text color using CSS custom properties if needed */
        .stSelectbox {
            --text-color: #FFFFFF !important;
        }
        
        .stSelectbox * {
            color: var(--text-color, #FFFFFF) !important;
        }
        
        /* Additional aggressive selectors for BaseWeb components */
        [data-baseweb="base-select"] *,
        [data-baseweb="base-select"] span,
        [data-baseweb="base-select"] div {
            color: #FFFFFF !important;
        }
        
        /* Target any element with text in the selectbox area */
        .stSelectbox div[class*="select"],
        .stSelectbox div[class*="Select"],
        .stSelectbox div[class*="dropdown"] {
            color: #FFFFFF !important;
        }
        
        .stSelectbox div[class*="select"] *,
        .stSelectbox div[class*="Select"] *,
        .stSelectbox div[class*="dropdown"] * {
            color: #FFFFFF !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #F8F9FA;
            color: #000000 !important;
            font-weight: 500 !important;
            border: 1px solid #E0E0E0;
        }
        
        .streamlit-expanderContent {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* Info, success, warning, error boxes - enhanced contrast */
        .stAlert {
            background-color: #F8F9FA;
            border: 2px solid #CCCCCC;
        }
        
        .stInfo {
            background-color: #E3F2FD;
            color: #0D47A1 !important;
            border: 2px solid #2196F3 !important;
        }
        
        .stSuccess {
            background-color: #E8F5E9;
            color: #1B5E20 !important;
            border: 2px solid #4CAF50 !important;
        }
        
        .stWarning {
            background-color: #FFF3E0;
            color: #E65100 !important;
            border: 2px solid #FF9800 !important;
        }
        
        .stError {
            background-color: #FFEBEE;
            color: #B71C1C !important;
            border: 2px solid #F44336 !important;
        }
        
        /* Captions - darker for readability */
        .stCaption {
            color: #333333 !important;
            font-weight: 400 !important;
        }
        
        /* Markdown text */
        .stMarkdown {
            color: #000000 !important;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        
        /* Code blocks */
        code {
            background-color: #F5F5F5;
            color: #000000;
            border: 1px solid #E0E0E0;
            padding: 2px 4px;
        }
        
        /* Tables */
        table {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #E0E0E0;
        }
        
        table th {
            background-color: #F5F5F5;
            color: #000000;
            font-weight: 600;
            border: 1px solid #D0D0D0;
        }
        
        table td {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #E0E0E0;
        }
        
        /* Dividers */
        hr {
            border-color: #CCCCCC;
            border-width: 1px;
        }
        
        /* Links - darker blue for better visibility */
        a {
            color: #0066CC !important;
            font-weight: 500;
        }
        
        a:hover {
            color: #0052A3 !important;
            text-decoration: underline;
        }
        
        /* Columns */
        [data-testid="column"] {
            background-color: transparent;
        }
        
        /* Streamlit widgets */
        .stTextInput > div > div > input {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
        }
        
        /* Checkbox and radio */
        .stCheckbox label, .stRadio label {
            color: #000000 !important;
            font-weight: 400 !important;
        }
        
        /* Tooltips */
        [data-testid="stTooltip"] {
            background-color: #333333;
            color: #FFFFFF;
        }
        
        /* Multi-select */
        .stMultiSelect [data-baseweb="select"] {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* Number input */
        .stNumberInput > div > div > input {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #CCCCCC;
        }
        
        /* Slider */
        .stSlider {
            color: #000000;
        }
        
        /* Progress bar */
        .stProgress > div > div > div {
            background-color: #1F77B4;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-color: #1F77B4;
        }
        
        /* JSON viewer */
        .stJson {
            background-color: #F8F9FA;
            color: #000000;
        }
        
        /* Sidebar navigation */
        .css-1d391kg {
            background-color: #F8F9FA;
        }
        
        /* Main content blocks */
        .element-container {
            color: #000000;
        }
        
        /* Ensure all text in widgets is visible */
        .stWidget label {
            color: #000000 !important;
            font-weight: 500 !important;
        }
        
        /* Data editor */
        [data-testid="stDataEditor"] {
            background-color: #FFFFFF;
            color: #000000;
        }
        
        /* Charts and plots */
        .js-plotly-plot {
            background-color: #FFFFFF;
        }
        
        /* Additional text elements for maximum readability */
        .stText {
            color: #000000 !important;
        }
        
        .stMarkdownContainer {
            color: #000000 !important;
        }
        
        /* Strong emphasis on important text */
        strong, b {
            color: #000000 !important;
            font-weight: 700 !important;
        }
        
        /* Ensure subheader and title visibility */
        .stSubheader, .stTitle {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        </style>
        """
        st.markdown(light_mode_css, unsafe_allow_html=True)


def render_theme_toggle():
    """Render theme toggle button in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Theme")
    
    current_theme = st.session_state.theme
    theme_icon = "🌙" if current_theme == 'light' else "☀️"
    theme_label = "Dark Mode" if current_theme == 'light' else "Light Mode"
    
    if st.sidebar.button(f"{theme_icon} {theme_label}", use_container_width=True):
        st.session_state.theme = 'dark' if current_theme == 'light' else 'light'
        st.rerun()


# Apply theme CSS immediately (before any content is rendered)
apply_theme_css(st.session_state.theme)


# ─────────────────────────────
# Season helpers
# ─────────────────────────────
def get_current_nba_season():
    """
    Guess current NBA season like '2025-26'.
    If today is Oct or later, it's YEAR-(YEAR+1 short).
    Otherwise it's (YEAR-1)-(YEAR short).
    """
    now = datetime.now()
    yr = now.year
    mo = now.month
    if mo >= 10:
        return f"{yr}-{str(yr+1)[2:]}"
    else:
        return f"{yr-1}-{str(yr)[2:]}"


def get_prior_nba_season():
    cur = get_current_nba_season()
    start_year = int(cur.split('-')[0])
    return f"{start_year-1}-{str(start_year)[2:]}"


current_season = get_current_nba_season()
prior_season = get_prior_nba_season()


# ─────────────────────────────
# Model
# ─────────────────────────────
@st.cache_resource
def load_model():
    return PlayerPropModel(alpha=1.0)

model = load_model()


# ─────────────────────────────
# Stat options for dropdown
# ─────────────────────────────
STAT_OPTIONS = {
    "Points": "PTS",
    "Assists": "AST",
    "Rebounds": "REB",
    "Three-Pointers Made": "FG3M",
    "Points + Rebounds + Assists (PRA)": "PRA",
    "Double-Double Probability": "DD",
}


# ─────────────────────────────
# Utility helpers for sportsbook + display
# ─────────────────────────────
def normalize_name(name):
    """Normalize player name for better matching"""
    if not name:
        return ""
    # Remove periods, apostrophes, and extra spaces
    name = re.sub(r"[.'’]", "", name.lower().strip())
    # Remove common suffixes like Jr., Sr., III, etc.
    name = re.sub(r'\s+(jr|sr|ii|iii|iv|v)$', '', name)
    return name

def names_match(name1, name2):
    """Check if two player names match with flexible comparison"""
    if not name1 or not name2:
        return False
        
    # Normalize both names
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    # Check for direct match after normalization
    if norm1 == norm2:
        return True
    
    # Check if one name is contained in the other (e.g., "James Harden" and "Harden")
    if norm1 in norm2 or norm2 in norm1:
        return True
    
    # Check for same last name and first initial match (e.g., "J. Smith" and "John Smith")
    parts1 = norm1.split()
    parts2 = norm2.split()
    
    if parts1 and parts2:
        # Check if last names match
        if parts1[-1] == parts2[-1]:
            # Check if first names share the same first letter
            if parts1[0][0] == parts2[0][0]:
                return True
    
    # Use sequence matcher for fuzzy matching
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    return ratio > 0.8  # Threshold for considering names a match

def defense_emoji(rank_num: int) -> str:
    """
    Visual difficulty emoji:
    - rank <=10 : tough defense (red)
    - rank <=20 : middling (yellow/orange)
    - else      : soft / target (green)
    """
    if rank_num <= 10:
        return "🔴"
    elif rank_num <= 20:
        return "🟡"
    else:
        return "🟢"

def calc_hit_rate(game_logs: pd.DataFrame, stat_col: str, line_value: float, window: int = 10):
    """
    Calculate the percentage of recent games where the player exceeded the line value.
    
    Args:
        game_logs: DataFrame containing the player's game logs
        stat_col: The statistic column to analyze (e.g., 'PTS', 'REB', 'AST')
        line_value: The line value to check against
        window: Number of most recent games to consider (5, 10, or 0 for all games)
    
    Returns:
        float: Hit percentage (0-100) or None if not enough data
    """
    if game_logs is None or game_logs.empty:
        return None
    if line_value is None:
        return None

    try:
        # Create a copy to avoid SettingWithCopyWarning
        logs = game_logs.copy()
        
        # Filter to only include games where they played (MIN > 0)
        relevant_games = logs[logs["MIN"] > 0]
        
        # Sort by date (newest first)
        relevant_games = relevant_games.sort_values("GAME_DATE", ascending=False)
        
        # If window is greater than 0, limit to that many games
        if window and window > 0:
            relevant_games = relevant_games.head(window)
        
        if len(relevant_games) < 1:
            return None
            
        # Calculate hit rate
        hits = (relevant_games[stat_col] > line_value).sum()
        hit_pct = (hits / len(relevant_games)) * 100
        
        return round(hit_pct, 1)
        
    except Exception as e:
        st.error(f"Error calculating hit rate: {str(e)}")
        return None


def calc_edge(prediction: float, line_value: float):
    """
    Compare model projection to sportsbook line.
    Returns (edge_str, rec_text, ou_short)
    edge_str ~ "+2.1 (+9.4%)"
    rec_text ~ "✅ OVER looks good" / "❌ UNDER looks good" / "⚪ No clear edge"
    ou_short ~ "OVER", "UNDER", or "—"
    """
    if line_value is None:
        return ("—", "No line", "—")

    if line_value == 0:
        diff = prediction
        pct = 0.0
    else:
        diff = prediction - line_value
        pct = (diff / line_value) * 100.0

    if abs(diff) < 1.5:
        rec_text = "⚪ No clear edge"
        ou_short = "—"
    elif diff > 1.5:
        rec_text = "✅ OVER looks good"
        ou_short = "OVER"
    else:
        rec_text = "❌ UNDER looks good"
        ou_short = "UNDER"

    edge_str = f"{diff:+.1f} ({pct:+.1f}%)"
    return (edge_str, rec_text, ou_short)


# ─────────────────────────────
# Detailed Player View Renderer
# (used inside each expander)
# ─────────────────────────────
def render_player_detail_body(pdata, cur_season, prev_season):
    """
    The deep dive panel for a single player.
    Called inside each expander, after we build pdata in the loop.
    """
    player_id = pdata.get("player_id", "unknown")  # Get player_id for unique keys
    render_index = pdata.get("render_index", 0)  # Get render index for unique keys
    player_name = pdata["player_name"]
    team_abbrev = pdata["team_abbrev"]
    player_pos = pdata["player_pos"]
    opponent_abbrev = pdata["opponent_abbrev"]
    current_logs = pdata["current_logs"]
    prior_logs = pdata["prior_logs"]
    h2h_history = pdata["h2h_history"]
    opp_def_rank = pdata["opp_def_rank"]
    features = pdata["features"]
    prediction = pdata["prediction"]
    stat_code = pdata["stat_code"]
    stat_display = pdata["stat_display"]

    # sportsbook extras we calculated in build loop
    fd_line_val = pdata["fd_line_val"]           # may be None
    hit_pct_val = pdata["hit_pct_val"]           # may be None
    edge_str = pdata["edge_str"]                 # string or "—"
    rec_text = pdata["rec_text"]                 # recommendation string

    # games played info
    has_current = not current_logs.empty
    has_prior = not prior_logs.empty
    current_games = len(current_logs) if has_current else 0
    prior_games = len(prior_logs) if has_prior else 0
    h2h_games = 0 if h2h_history is None or h2h_history.empty else len(h2h_history)

    # ---- Header metrics
    st.subheader(f"📊 Projections for {player_name} ↩")

    colA, colB, colC = st.columns(3)
    with colA:
        st.metric(f"{cur_season} Games", current_games)
    with colB:
        st.metric(f"{prev_season} Games", prior_games)
    with colC:
        st.metric(f"vs {opponent_abbrev} History", h2h_games)

    if current_games < 5:
        st.info(
            f"Only {current_games} games in {cur_season}. "
            f"We're leaning more on {prev_season} + head-to-head."
        )

    # ---- Opponent defense vs position
    st.markdown("---")

    position_desc = {
        'G': 'Guards (PG/SG)',
        'F': 'Forwards (SF/PF)',
        'C': 'Centers (C)',
    }.get(player_pos, f'{player_pos} Position')

    st.subheader(f"🛡️ {opponent_abbrev} Defense vs {position_desc}")

    col1, col2, col3 = st.columns(3)

    rank_val = opp_def_rank.get("rank", 15)
    rating_text = opp_def_rank.get("rating", "Average")
    percentile = opp_def_rank.get("percentile", 50.0)

    rating_lower = str(rating_text).lower()
    if "elite" in rating_lower or "above" in rating_lower:
        diff_emoji = "🔴"
    elif "average" in rating_lower and "above" not in rating_lower:
        diff_emoji = "🟡"
    else:
        diff_emoji = "🟢"

    with col1:
        st.metric(
            "Defensive Rank vs Position",
            f"{diff_emoji} #{rank_val} of 30",
            help=f"How {opponent_abbrev} guards this archetype ({player_pos})"
        )
    with col2:
        st.metric(
            "Matchup Difficulty",
            rating_text,
            help="Elite / Above Avg = tough. Below Avg = soft / target spot."
        )
    with col3:
        st.metric(
            "Defense Percentile",
            f"{percentile:.0f}%",
            help="Higher percentile = stronger defense overall."
        )

    if "elite" in rating_lower or "above" in rating_lower:
        st.info(
            f"🔴 Tough matchup: {opponent_abbrev} defends {player_pos} well. "
            "Unders / caution."
        )
    elif "below" in rating_lower:
        st.success(
            f"🟢 Favorable matchup: {opponent_abbrev} struggles "
            f"vs {player_pos}. Overs become more viable."
        )

    # ---- Projection / performance / context
    st.markdown("---")
    colP, colR, colCxt = st.columns([2, 2, 1])

    # Projection panel
    with colP:
        st.subheader("🎯 Model Projection")
        if stat_code == "DD":
            st.metric("Double-Double Probability", f"{prediction:.1f}%")
        else:
            st.metric(
                f"Projected {stat_display}",
                f"{prediction:.1f}"
            )

        if "pts_allowed" in opp_def_rank:
            st.caption(
                f"🛡️ Opp vs {player_pos}: "
                f"{opp_def_rank['pts_allowed']:.1f} pts allowed"
            )
        else:
            st.caption("🛡️ Opponent defense data unavailable")

        if h2h_games > 0 and stat_code != "DD":
            h2h_avg = features.get(f"h2h_{stat_code}_avg", 0)
            st.caption(
                f"📊 vs {opponent_abbrev} Avg: {h2h_avg:.1f} "
                f"({h2h_games} games)"
            )

    # Recent performance
    with colR:
        st.subheader("📈 Recent Performance")
        season_avg = features.get(f"{stat_code}_avg", 0)
        last5 = features.get(f"{stat_code}_last5", season_avg)
        last10 = features.get(f"{stat_code}_last10", season_avg)

        if stat_code != "DD":
            st.write(f"**Season Average:** {season_avg:.1f}")
            st.write(f"**Last 5 Games:** {last5:.1f}")
            st.write(f"**Last 10 Games:** {last10:.1f}")

            wc = features.get("weight_current", 0)
            wp = features.get("weight_prior", 1)
            st.caption(
                f"Blend: {wc*100:.0f}% {cur_season}, "
                f"{wp*100:.0f}% {prev_season}"
            )
        else:
            st.write(f"Chance at DD: {prediction:.1f}% (model)")

    # Context
    with colCxt:
        st.subheader("🏀 Context")
        rest_days = features.get("rest_days", 3)
        is_b2b = features.get("is_back_to_back", 0)
        st.write(f"**Rest Days:** {rest_days}")
        st.write(f"**Back-to-Back:** {'Yes' if is_b2b else 'No'}")
        st.write(f"**Opponent:** {opponent_abbrev}")

    # ---- Sportsbook Line / Hit Rate section
    st.markdown("---")
    st.subheader("📊 Sportsbook Line & Hit Rate")

    colL, colH, colBet = st.columns([2, 2, 1])

    with colL:
        st.markdown("**Line / Edge**")
        if stat_code == "DD":
            st.write("Most books don't post DD props here, so no line.")
        else:
            if fd_line_val is None:
                st.write("Line: —")
                st.write("Edge vs Line: —")
                st.caption("No line available for this player/stat.")
            else:
                st.write(f"Line: **{fd_line_val}**")
                st.write(f"Edge vs Line: **{edge_str}**")
                st.caption(rec_text)

    with colH:
        st.markdown("**Hit Rate (Last 10 Games)**")
        if stat_code == "DD":
            st.write("Hit%: —")
            st.caption("N/A for DD market here.")
        else:
            if hit_pct_val is None:
                st.write("Hit%: —")
                st.caption("We only compute this if we have a line.")
            else:
                st.write(f"Hit%: **{hit_pct_val:.0f}%**")
                st.caption(
                    "Hit% = % of recent games over that line. "
                    "Historical only."
                )
    
    with colBet:
        st.markdown("**Action**")
        # Add to Bet Sheet button
        if st.button("Add to Bet Sheet", key=f"add_{pdata['player_id']}_{stat_code}"):
            # Get the line value, defaulting to projection if no line is available
            line_to_use = fd_line_val if fd_line_val is not None else prediction
            
            # Prepare game logs for hit rate calculation
            game_logs = []
            if 'game_logs' in pdata and pdata['game_logs'] is not None:
                # Convert game logs to list of dicts for serialization
                game_logs = pdata['game_logs'].to_dict('records')
            
            # Add to bet sheet
            success = add_to_bet_sheet(
                player_name=pdata['player_name'],
                team=pdata['team_abbrev'],
                stat_display=stat_display,
                line_value=line_to_use,
                hit_rate=hit_pct_val if hit_pct_val is not None else None,
                projection=prediction,
                edge_str=edge_str,
                opponent=opponent_abbrev,
                game_logs=game_logs
            )
            
            if success:
                st.toast(f"Added {pdata['player_name']} ({stat_display}) to bet sheet!")
            else:
                st.toast(f"{pdata['player_name']} is already in your bet sheet!", icon="⚠️")
        elif stat_code == "DD":
            st.info("DD market not available in bet sheet")
        else:
            st.info("No line available for this player")
        if stat_code != "DD":
            # Check if already in bet sheet
            bet_id = f"{player_name}_{stat_display}"
            already_added = bet_id in [bet.get('id') for bet in st.session_state.bet_sheet]
            
            if already_added:
                st.success("✅ Added")
            else:
                # Format projection display
                if stat_code == "DD":
                    proj_display = f"{prediction:.1f}%"
                else:
                    proj_display = f"{prediction:.1f}"
                
                # Show button with different text based on line availability
                button_text = "➕ Add to Bet Sheet" if fd_line_val is not None else "➕ Add (No Line)"
                
                # Use player_id and render_index for unique key to avoid duplicates
                if st.button(button_text, key=f"add_bet_{player_id}_{stat_code}_{render_index}", use_container_width=True):
                    success = add_to_bet_sheet(
                        player_name=player_name,
                        team=team_abbrev,
                        stat_display=stat_display,
                        line_value=fd_line_val if fd_line_val is not None else "N/A",
                        hit_rate=hit_pct_val,
                        projection=proj_display,
                        edge_str=edge_str if edge_str else "—",
                        opponent=opponent_abbrev
                    )
                    if success:
                        st.rerun()
        else:
            st.caption("DD not supported")

    # ---- Head to head deep dive
    if h2h_games > 0 and stat_code != "DD":
        st.markdown("---")
        st.subheader(f"🔥 Head-to-Head vs {opponent_abbrev}")

        h2h_avg = features.get(f"h2h_{stat_code}_avg", 0)
        h2h_trend = features.get(f"h2h_{stat_code}_trend", 0)

        colH2H1, colH2H2 = st.columns(2)
        with colH2H1:
            st.markdown("**Average vs Opponent**")
            st.markdown(f"### Avg: {h2h_avg:.1f} ({h2h_games} games)")
            diff = h2h_avg - features.get(f"{stat_code}_avg", 0)
            clr = "green" if diff > 0 else "red"
            st.markdown(f":{clr}[{diff:+.1f} vs season avg]")

        with colH2H2:
            st.markdown("**Recent Trend**")
            if abs(h2h_trend) > 1:
                trending_up = (h2h_trend > 0)
                trend_text = "📈 Trending UP" if trending_up else "📉 Trending DOWN"
                st.markdown(f"### {trend_text}")
                st.markdown(
                    f":{('green' if trending_up else 'red')}[{h2h_trend:+.1f}]"
                )
            else:
                st.markdown("### ➡️ Consistent")

        if not h2h_history.empty:
            st.markdown("**Recent Games vs Opponent:**")
            base_cols = ["GAME_DATE","MATCHUP","PTS","REB","AST","FG3M"]
            show_cols = [c for c in base_cols if c in h2h_history.columns]
            if show_cols:
                h2h_recent = h2h_history.head(5)[show_cols].copy()
                if {"PTS","REB","AST"}.issubset(h2h_recent.columns):
                    h2h_recent["PRA"] = (
                        h2h_recent["PTS"] +
                        h2h_recent["REB"] +
                        h2h_recent["AST"]
                    )
                st.dataframe(h2h_recent, use_container_width=True)

    # ---- Recent game log (last 10)
    st.markdown("---")
    st.subheader("📋 Recent Game Log (Last 10 Games)")

    # stitch 10 most recent between current and prior
    if has_current and len(current_logs) >= 10:
        last10_logs = current_logs.head(10)
        label_season = cur_season
    elif has_current and len(current_logs) < 10:
        need = 10 - len(current_logs)
        last10_logs = pd.concat(
            [current_logs, prior_logs.head(need)], ignore_index=True
        ).head(10)
        label_season = f"{cur_season} + {prev_season}"
    elif has_prior:
        last10_logs = prior_logs.head(10)
        label_season = prev_season
    else:
        last10_logs = pd.DataFrame()
        label_season = "N/A"

    st.caption(f"Showing games from: {label_season}")

    if not last10_logs.empty:
        display_cols = [
            "GAME_DATE","MATCHUP","MIN","PTS","REB","AST",
            "FG3M","FGA","FG_PCT"
        ]
        cols_avail = [c for c in display_cols if c in last10_logs.columns]
        if cols_avail:
            preview_df = last10_logs[cols_avail].copy()
            if {"PTS","REB","AST"}.issubset(preview_df.columns):
                preview_df["PRA"] = (
                    preview_df["PTS"] +
                    preview_df["REB"] +
                    preview_df["AST"]
                )
            st.dataframe(preview_df, use_container_width=True)


# ─────────────────────────────
# Build matchup table + live expanders
# ─────────────────────────────
def build_matchup_view(
    selected_game: dict,
    stat_code: str,
    stat_display: str,
    cur_season: str,
    prev_season: str,
    model_obj: PlayerPropModel,
):
    # Validate selected_game structure
    if not selected_game or not isinstance(selected_game, dict):
        st.warning("No valid game selected. Please select a game from the sidebar.")
        return
        
    # Standardize field names - support both 'home'/'away' and 'home_team'/'away_team'
    home_team = selected_game.get('home_team') or selected_game.get('home')
    away_team = selected_game.get('away_team') or selected_game.get('away')
    
    if not home_team or not away_team:
        st.warning("Incomplete game data. Missing team information.")
        print(f"Debug - Invalid game data: {selected_game}")
        return
        
    # Create a standardized game data structure
    game_data = {
        'home_team': home_team,
        'away_team': away_team,
        'game_date': selected_game.get('game_date', selected_game.get('date', '')),
        'game_time': selected_game.get('game_time', selected_game.get('time', '')),
        'game_id': selected_game.get('game_id', '')
    }
    """
    Stream the matchup board IF we have a selected game.
    If there's no game selected yet, show landing / instructions.
    """

    # If user hasn't picked a game yet
    if not selected_game:
        st.title("🏀 NBA Player Props Projection Model")
        st.markdown(
            "Advanced predictions using historical data, matchup analysis, "
            "and head-to-head history"
        )
        st.markdown("---")
        st.subheader("👋 How to use this tool")
        st.markdown(
            """
1. **Pick a matchup** on the left sidebar under *Select Upcoming Game*  
2. **Pick a stat** (*Points*, *Rebounds*, *3PM*, etc.)  
3. Watch the **Matchup Board** fill in player by player  
4. Scroll down and **expand any player** to see the full deep dive (model projection, line vs projection edge, rest days, head-to-head, etc.)

No game is selected yet — choose one in the sidebar to start.
            """
        )
        return

    # Use the standardized game_data dictionary
    home_team = game_data['home_team']
    away_team = game_data['away_team']

    # Title / description
    st.title("🏀 NBA Player Props Projection Model")
    st.markdown(f"### {away_team} @ {home_team}")
    
    if game_data.get('game_date'):
        game_time = f" at {game_data['game_time']}" if game_data.get('game_time') else ""
        st.caption(f"{game_data['game_date']}{game_time}")
    
    st.markdown("---")
    
    st.subheader("🏟 Matchup Board")
    st.caption(
        "Quick view of projections, sportsbook line, model edge, hit rate, and "
        "defensive matchup for everyone in this game."
    )

    # shared data we reuse for all players
    def_vs_pos_df = scrape_defense_vs_position_cached_db()
    team_stats = get_team_stats_cached_db(season=prev_season)

    # fetch rosters
    home_roster = get_players_by_team(home_team, season=cur_season)
    if home_roster.empty:
        home_roster = get_players_by_team(home_team, season=prev_season)
    if not home_roster.empty:
        home_roster["team_abbrev"] = home_team

    away_roster = get_players_by_team(away_team, season=cur_season)
    if away_roster.empty:
        away_roster = get_players_by_team(away_team, season=prev_season)
    if not away_roster.empty:
        away_roster["team_abbrev"] = away_team

    if home_roster.empty and away_roster.empty:
        st.error("Couldn't load rosters for this matchup.")
        return

    combined_roster = pd.concat([home_roster, away_roster], ignore_index=True)
    combined_roster = combined_roster.drop_duplicates(subset=["player_id"])
    
    # Ensure starter column exists (in case it's missing)
    if "starter" not in combined_roster.columns:
        combined_roster["starter"] = False
    
    total_players = len(combined_roster)
    starter_count = len(combined_roster[combined_roster["starter"] == True]) if "starter" in combined_roster.columns else 0

    # Get event ID for the game using standardized team names
    event_id = get_event_id_for_game(game_data['home_team'], game_data['away_team'])
    
    # Fetch odds data if we have an event ID
    odds_data = {}
    if event_id:
        safe_print(f"Fetching odds for event ID: {event_id}")
        odds_data = fetch_fanduel_lines(event_id)
        safe_print(f"Fetched odds for {len(odds_data)} players")
        
        # Debug: Print sample of odds data
        if odds_data:
            sample_player = next(iter(odds_data))
            safe_print(f"Sample player data for '{sample_player}': {odds_data[sample_player]}")
        else:
            safe_print("Warning: No odds data returned from API")
    else:
        safe_print(f"No event ID found for game: {away_team} @ {home_team}")

    # Show player count with starter info and add search bar
    st.markdown("---")
    
    # Initialize session state for search if not exists
    if 'player_search' not in st.session_state:
        st.session_state.player_search = ""
    
    # Add player search bar with columns for better layout
    col_search, col_clear = st.columns([4, 1])
    
    with col_search:
        search_query = st.text_input(
            "🔍 Search Player", 
            value=st.session_state.player_search,
            placeholder="Type to filter players by name...",
            help="Filter players by name (case-insensitive, partial match)",
            key="player_search_input"
        )
        st.session_state.player_search = search_query
    
    with col_clear:
        st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
        if st.button("🔄 Clear", help="Clear search filter", use_container_width=True):
            st.session_state.player_search = ""
            st.rerun()
    
    # Apply search filter if query exists
    if search_query and search_query.strip():
        # Filter players based on search query (case-insensitive partial match)
        search_lower = search_query.strip().lower()
        combined_roster = combined_roster[
            combined_roster["full_name"].str.lower().str.contains(search_lower, na=False, regex=False)
        ]
        total_players = len(combined_roster)
        starter_count = len(combined_roster[combined_roster["starter"] == True]) if "starter" in combined_roster.columns else 0
    
    # Update player count display
    if search_query and search_query.strip():
        if total_players == 0:
            st.warning(f"⚠️ No players match '{search_query}'. Try a different name or clear the search.")
        else:
            st.success(f"✅ Found {total_players} player(s) matching '{search_query}' ({starter_count} starters ⭐)")
    else:
        if starter_count > 0:
            st.info(f"👥 Showing all {total_players} players ({starter_count} starters marked with ⭐)")

    # placeholders for streaming UI
    table_placeholder = st.empty()         # board table so far
    status_placeholder = st.empty()        # "Loaded X/Y"
    st.markdown("---")
    st.subheader("📂 Player Breakdowns (click any name below to expand)")
    st.caption(
        f"You can start opening players right away. "
        f"We'll keep adding more below as they finish loading. "
        f"({cur_season} vs {prev_season}, matchup context, line edge, trends, etc.)"
    )
    expanders_placeholder = st.empty()     # list of expanders so far

    table_rows = []
    player_payloads = []

    # If no players match the search, show a message and return early
    if len(combined_roster) == 0:
        st.warning("No players match your search. Try a different name.")
        return
        
    # stream each player
    for _, prow in combined_roster.iterrows():
        player_name = prow["full_name"]
        pid = prow["player_id"]
        team_abbrev = prow["team_abbrev"]
        opponent_abbrev = away_team if team_abbrev == home_team else home_team

        # position
        player_pos = get_player_position(pid, season=prev_season)

        # logs
        current_logs = get_player_game_logs_cached_db(
            pid, player_name, season=cur_season
        )
        prior_logs = get_player_game_logs_cached_db(
            pid, player_name, season=prev_season
        )

        # opponent recent form
        opponent_recent = get_opponent_recent_games(
            opponent_abbrev,
            season=prev_season,
            last_n=10
        )

        # head-to-head
        h2h_history = get_head_to_head_history(
            pid,
            opponent_abbrev,
            seasons=[prev_season, "2023-24"]
        )

        # defense rank vs position
        opp_def_rank_info = get_team_defense_rank_vs_position(
            opponent_abbrev,
            player_pos,
            def_vs_pos_df
        )

        # features for model
        feat = build_enhanced_feature_vector(
            current_logs,
            opponent_abbrev,
            team_stats,
            prior_season_logs=prior_logs,
            opponent_recent_games=opponent_recent,
            head_to_head_games=h2h_history,
            player_position=player_pos
        )

        # model projection (stat-based)
        if stat_code == "DD":
            pred_val = model_obj.predict_double_double(feat) * 100.0  # %
            proj_display = f"{pred_val:.1f}%"
        else:
            pred_val = model_obj.predict(feat, stat_code)
            proj_display = f"{pred_val:.1f}"

            # sportsbook line for THIS player/stat from FanDuel odds
            if stat_code == "DD":
                fd_line_val = None
            else:
                # Look up player's line with detailed logging
                safe_print(f"\nLooking up line for player: {player_name} ({stat_code})")
                fd_info = get_player_fanduel_line(player_name, stat_code, odds_data)
                
                # Debug logging
                if fd_info:
                    safe_print(f"  Found line: {fd_info.get('line')}")
                    safe_print(f"  Over price: {fd_info.get('over_price')}")
                    safe_print(f"  Under price: {fd_info.get('under_price')}")
                else:
                    safe_print(f"  No line found for {player_name} ({stat_code})")
                    # Debug: Print all available players in odds data
                    if odds_data:
                        safe_print("  Available players in odds data:")
                        for i, name in enumerate(odds_data.keys()):
                            if i < 5:  # Only show first 5 to avoid log spam
                                safe_print(f"    - {name}: {list(odds_data[name].keys())}")
                
                fd_line_val = fd_info.get('line') if fd_info else None

            # compute edge + hit rate
            if stat_code == "DD":
                hit_pct_val = None
                edge_str = "—"
                rec_text = "Most books don't post DD lines"
                ou_short = "—"
            else:
                if fd_line_val is not None:
                    # Calculate hit rate based on selected range
                    # Get the window size based on selected range
                    window_size = {
                        "last_5": 5,
                        "last_10": 10,
                        "season": 0  # 0 means use all available games
                    }.get(st.session_state.hit_rate_range, 10)
                    
                    # Calculate hit rate with the selected window
                    hit_pct_val = calc_hit_rate(
                        current_logs if not current_logs.empty else prior_logs,
                        stat_code,
                        fd_line_val,
                        window=window_size
                    )
                    edge_str, rec_text, ou_short = calc_edge(pred_val, fd_line_val)
                else:
                    hit_pct_val = None
                    edge_str, rec_text, ou_short = ("—", "No line", "—")

            # Opp Def Rank vs Position w/ emoji color
            rank_num = opp_def_rank_info.get("rank", 15)
            rating_txt = opp_def_rank_info.get("rating", "Average")
            d_emoji = defense_emoji(rank_num)
            opp_def_display = f"{d_emoji} #{rank_num} ({rating_txt})"

        # Check if player is a starter and add indicator
        is_starter = prow.get("starter", False) if "starter" in prow else False
        starter_indicator = "⭐" if is_starter else ""
        player_display_name = f"{starter_indicator} {player_name}".strip() if is_starter else player_name

        # add row for this player into table
        table_rows.append({
            "Player": player_display_name,
            "Team/Pos": f"{team_abbrev} · {player_pos}",
            "Proj": proj_display,
            "Line": "—" if fd_line_val is None else f"{float(fd_line_val):.1f}",
            "O/U": ou_short,
            "Hit%": "—" if hit_pct_val is None else f"{hit_pct_val:.0f}%" + (
                " 🔥" if hit_pct_val and hit_pct_val >= 60 else 
                " ❄️" if hit_pct_val and hit_pct_val <= 40 else ""
            ),
            "Opp Def Rank vs Position": opp_def_display,
        })

        # prepare data for expander
        pdata = {
            "player_id": pid,  # Add player_id for unique keys
            "player_name": player_name,
            "team_abbrev": team_abbrev,
            "player_pos": player_pos,
            "opponent_abbrev": opponent_abbrev,
            "current_logs": current_logs,
            "prior_logs": prior_logs,
            "h2h_history": h2h_history,
            "opp_def_rank": opp_def_rank_info,
            "features": feat,
            "prediction": pred_val,
            "stat_code": stat_code,
            "stat_display": stat_display,

            # sportsbook stuff to show in detail view
            "fd_line_val": fd_line_val,
            "hit_pct_val": hit_pct_val,
            "edge_str": edge_str,
            "rec_text": rec_text,
            "render_index": len(player_payloads),  # Add unique index for each render
        }
        player_payloads.append(pdata)

        # re-render table so far
        running_df = pd.DataFrame(table_rows)
        table_placeholder.dataframe(running_df, use_container_width=True)

        # status line
        status_placeholder.write(
            f"Loaded {len(table_rows)}/{total_players} players..."
        )

        # tiny delay so UI visibly streams
        time.sleep(0.05)

    # final status
    status_placeholder.success("✅ Done.")
    
    # Render ALL expanders ONCE after all data is loaded
    with expanders_placeholder.container():
        for info in player_payloads:
            with st.expander(
                f"{info['player_name']} ({info['team_abbrev']} · {info['player_pos']})",
                expanded=False
            ):
                render_player_detail_body(info, cur_season, prev_season)


# ─────────────────────────────
# Bet Sheet Functions
# ─────────────────────────────
def add_to_bet_sheet(player_name, team, stat_display, line_value, hit_rate, projection, edge_str, opponent, game_logs=None):
    """Add a player to the bet sheet with duplicate prevention
    
    Args:
        player_name: Name of the player
        team: Player's team
        stat_display: The stat being tracked (e.g., 'PTS', 'REB')
        line_value: The original line value
        hit_rate: Initial hit rate
        projection: Projected stat value
        edge_str: Edge calculation string
        opponent: Opposing team
        game_logs: List of game logs for hit rate calculation (optional)
    """
    if 'bet_sheet' not in st.session_state:
        st.session_state.bet_sheet = []
        
    # Create a more readable ID without timestamp for better duplicate checking
    base_id = f"{player_name}_{stat_display}"
    
    # Check if already in bet sheet (same player and stat)
    existing_ids = [f"{bet['player_name']}_{bet['stat']}".lower() for bet in st.session_state.bet_sheet]
    if base_id.lower() in existing_ids:
        return False  # Already exists
    
    # Add to bet sheet with timestamp for unique ID but use base_id for checking
    bet_id = f"{base_id}_{int(time.time())}"
    
    # Safely convert values to float, handling 'N/A' strings and None values
    def safe_float(value):
        if value is None or value == 'N/A':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    line_float = safe_float(line_value)
    
    # Format the bet entry with all necessary details
    bet_entry = {
        'id': bet_id,
        'player_name': player_name,
        'team': team,
        'stat': stat_display,
        'line': line_float,
        'adjusted_line': line_float,  # Initialize adjusted_line same as original line
        'hit_rate': safe_float(hit_rate),
        'adjusted_hit_rate': None,  # Will be calculated when needed
        'projection': safe_float(projection),
        'edge': edge_str if edge_str != 'N/A' else None,
        'opponent': opponent if opponent != 'N/A' else None,
        'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'base_id': base_id.lower(),  # For easier duplicate checking
        'game_logs': game_logs or []  # Store game logs for hit rate recalculation
    }
    st.session_state.bet_sheet.append(bet_entry)
    return True  # Successfully added

def remove_from_bet_sheet(bet_id):
    """Remove a specific bet from the sheet"""
    if 'bet_sheet' in st.session_state:
        st.session_state.bet_sheet = [bet for bet in st.session_state.bet_sheet if bet['id'] != bet_id]
    st.rerun()

def clear_bet_sheet():
    """Clear all bets from the sheet"""
    if 'bet_sheet' in st.session_state:
        st.session_state.bet_sheet = []
    st.rerun()

def calculate_hit_rate(game_logs, stat, line_value, window=10):
    """
    Calculate hit rate based on game logs and line value
    
    Args:
        game_logs: List of game log dictionaries
        stat: The stat to check (e.g., 'PTS', 'REB', 'AST')
        line_value: The line value to compare against
        window: Number of recent games to consider (default: 10)
        
    Returns:
        float: Hit rate as a percentage (0-100) or None if not enough data
    """
    if not game_logs or not line_value:
        return None
        
    # Get the most recent games up to the window size
    recent_games = game_logs[-window:]
    
    # Count how many times the player exceeded the line
    hits = 0
    total = 0
    
    for game in recent_games:
        stat_value = game.get(stat)
        if stat_value is not None and stat_value != 'N/A':
            try:
                stat_float = float(stat_value)
                if stat_float > line_value:
                    hits += 1
                total += 1
            except (ValueError, TypeError):
                continue
    
    # Return hit rate as percentage if we have enough data
    return (hits / total * 100) if total >= 3 else None

def update_line_value(bet_id, increment):
    """Update the adjusted line value for a bet"""
    if 'bet_sheet' in st.session_state:
        for bet in st.session_state.bet_sheet:
            if bet['id'] == bet_id:
                current_line = bet.get('adjusted_line', bet.get('line', 0))
                new_line = current_line + increment
                # Ensure line doesn't go below 0.5
                new_line = max(0.5, new_line)
                bet['adjusted_line'] = round(new_line * 2) / 2  # Round to nearest 0.5
                
                # Recalculate hit rate if we have game logs
                if bet.get('game_logs') and bet.get('stat'):
                    bet['adjusted_hit_rate'] = calculate_hit_rate(
                        bet['game_logs'], 
                        bet['stat'], 
                        bet['adjusted_line']
                    )
                break
    st.rerun()

def render_bet_sheet_page():
    """Render the full bet sheet page with detailed player and bet information"""
    if 'bet_sheet' not in st.session_state or not st.session_state.bet_sheet:
        st.warning("Your bet sheet is empty. Add players from the main page.")
        if st.button("← Back to Main Page"):
            st.session_state.current_page = 'main'
            st.rerun()
        return
        
    # Add custom CSS for better bet sheet styling
    st.markdown("""
    <style>
    .bet-card {
        background-color: #1E1E1E;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #FFFFFF;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .line-adjust {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 4px;
    }
    .line-adjust button {
        min-width: 30px;
        padding: 2px 0;
        font-size: 0.9em;
    }
    .line-value {
        font-weight: bold;
        min-width: 40px;
        text-align: center;
        display: inline-block;
    }
    .bet-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .bet-card-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #FFFFFF;
        margin: 0;
    }
    .bet-card-subtitle {
        font-size: 0.9em;
        color: #B0B0B0;
        margin: 4px 0 0 0;
    }
    .bet-card-stats {
        display: flex;
        justify-content: space-between;
        margin: 12px 0;
        padding: 8px 0;
        border-top: 1px solid #2E2E2E;
        border-bottom: 1px solid #2E2E2E;
    }
    .stat-item {
        text-align: center;
    }
    .stat-label {
        font-size: 0.8em;
        color: #B0B0B0;
        margin-bottom: 4px;
    }
    .stat-value {
        font-size: 1.1em;
        font-weight: 600;
    }
    .edge-badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.9em;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📋 My Bet Sheet")
    
    # Add JavaScript for line adjustment
    st.markdown("""
    <script>
    function adjustLine(betId, increment) {
        fetch(`/_stcore/stream`,
            {method: "POST",
             headers: {"Content-Type": "application/json"},
             body: JSON.stringify({
                data: {
                    betId: betId,
                    increment: increment
                },
                sessionId: window.location.pathname.split('/').pop()
             })
            });
    }
    
    function resetLine(betId) {
        fetch(`/_stcore/stream`,
            {method: "POST",
             headers: {"Content-Type": "application/json"},
             body: JSON.stringify({
                data: {
                    betId: betId,
                    reset: true
                },
                sessionId: window.location.pathname.split('/').pop()
             })
            });
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to Main Page"):
        st.session_state.current_page = 'main'
        st.rerun()
    
    st.write("---")
    
    # Handle line adjustment callbacks
    if 'data' in st.query_params:
        data = st.query_params['data']
        if 'betId' in data and 'increment' in data:
            update_line_value(data['betId'], float(data['increment']))
        elif 'betId' in data and data.get('reset', False):
            # Reset to original line
            if 'bet_sheet' in st.session_state:
                for bet in st.session_state.bet_sheet:
                    if bet['id'] == data['betId'] and 'line' in bet:
                        bet['adjusted_line'] = bet['line']
                        if bet.get('game_logs') and bet.get('stat'):
                            bet['adjusted_hit_rate'] = calculate_hit_rate(
                                bet['game_logs'], 
                                bet['stat'], 
                                bet['line']
                            )
                        break
                st.rerun()
    
    # Bet sheet content with enhanced display
    for bet in st.session_state.bet_sheet:
        # Get values with proper defaults and type conversion
        try:
            line_val = float(bet.get('line')) if bet.get('line') is not None else None
            proj_val = float(bet.get('projection')) if bet.get('projection') is not None else None
            hit_rate = float(bet.get('hit_rate')) if bet.get('hit_rate') is not None else None
            
            # Calculate edge if we have both line and projection
            if line_val is not None and proj_val is not None and line_val > 0:
                edge = ((proj_val - line_val) / line_val * 100)
                edge_text = f"{edge:+.1f}%"
                edge_color = "#4CAF50" if edge >= 0 else "#F44336"
                edge_direction = "▲" if edge >= 0 else "▼"
            else:
                edge_text = bet.get('edge', '—')
                edge_color = "#2196F3"
                edge_direction = ""
                
        except (ValueError, TypeError) as e:
            line_val = bet.get('line')
            proj_val = bet.get('projection')
            hit_rate = bet.get('hit_rate')
            edge_text = bet.get('edge', '—')
            edge_color = "#2196F3"
            edge_direction = ""
        
        # Create columns for bet card and remove button
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            # Use st.container() to create a card-like container
            with st.container():
                # Create a styled container with border and padding
                st.markdown(
                    f"""
                    <div style="
                        background-color: #1E1E1E;
                        border-radius: 8px;
                        padding: 16px;
                        margin-bottom: 12px;
                        border-left: 4px solid {edge_color};
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        color: #FFFFFF;
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div>
                                <h3 style="margin: 0 0 4px 0; color: #FFFFFF; font-size: 1.2em;">
                                    {bet.get('player_name', 'N/A')}
                                </h3>
                                <p style="margin: 0; color: #B0B0B0; font-size: 0.9em;">
                                    {bet.get('team', '')} @ {bet.get('opponent', '')} • {bet.get('stat', 'N/A')}
                                </p>
                            </div>
                            <div>
                                <span style="
                                    background-color: {edge_color};
                                    color: white;
                                    padding: 4px 10px;
                                    border-radius: 12px;
                                    font-size: 0.9em;
                                    font-weight: 500;
                                ">
                                    {edge_text} {edge_direction}
                                </span>
                            </div>
                        </div>
                        
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            margin: 12px 0;
                            padding: 8px 0;
                            border-top: 1px solid #2E2E2E;
                            border-bottom: 1px solid #2E2E2E;
                        ">
                            <div style="text-align: center; flex: 1;">
                                <div style="font-size: 0.8em; color: #B0B0B0; margin-bottom: 4px;">Line (Adjusted)</div>
                                <div style="font-size: 1.1em; font-weight: 600; color: #FFFFFF;">
                                    {bet.get('adjusted_line', line_val) if line_val is not None else '—'}
                                </div>
                                <div class="line-adjust">
                                    <button onclick="adjustLine('{bet['id']}', -0.5)">-0.5</button>
                                    <button onclick="adjustLine('{bet['id']}', 0.5)">+0.5</button>
                                    <button onclick="resetLine('{bet['id']}')" style="margin-left: 4px;">Reset</button>
                                </div>
                            </div>
                            <div style="text-align: center; flex: 1;">
                                <div style="font-size: 0.8em; color: #B0B0B0; margin-bottom: 4px;">Projection</div>
                                <div style="font-size: 1.1em; font-weight: 600; color: #4CAF50;">
                                    {f"{proj_val:.1f}" if proj_val is not None else '—'}
                                </div>
                            </div>
                            <div style="text-align: center; flex: 1;">
                                <div style="font-size: 0.8em; color: #B0B0B0; margin-bottom: 4px;">Hit % (Adj.)</div>
                                <div style="font-size: 1.1em; font-weight: 600; color: #FFC107;">
                                    {f"{bet.get('adjusted_hit_rate', hit_rate):.0f}%" if bet.get('adjusted_hit_rate', hit_rate) is not None else '—'}
                                </div>
                                <div style="font-size: 0.7em; color: #888; margin-top: 2px;">
                                    {f"({hit_rate:.0f}% orig)" if hit_rate is not None else ''}
                                </div>
                            </div>
                        </div>
                        
                        <div style="font-size: 0.8em; color: #888; text-align: right;">
                            Added: {bet.get('added_at', '')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        with col2:
            # Remove button with confirmation
            if st.button("❌", 
                        key=f"remove_{bet['id']}", 
                        help=f"Remove {bet['player_name']}'s {bet['stat']} bet",
                        use_container_width=True):
                remove_from_bet_sheet(bet['id'])
                st.rerun()
    
    # Clear all button at the bottom
    st.write("---")
    if st.button("🗑️ Clear All Bets", type="primary", use_container_width=True):
        clear_bet_sheet()
    
    # Add some space at the bottom
    st.write("")
    st.write("")
    
    # Back to top button
    st.markdown("""
    <div style='text-align: center; margin-top: 20px;'>
        <a href='#top' style='color: #4CAF50; text-decoration: none;'>↑ Back to Top</a>
    </div>
    """, unsafe_allow_html=True)

def render_bet_sheet_button():
    """Render the bet sheet button in the sidebar"""
    if 'bet_sheet' not in st.session_state:
        st.session_state.bet_sheet = []
    
    bet_count = len(st.session_state.bet_sheet)
    button_label = f"📋 View Bet Sheet ({bet_count})" if bet_count > 0 else "📋 View Bet Sheet"
    
    if st.sidebar.button(button_label, use_container_width=True):
        st.session_state.current_page = 'bet_sheet'
        st.rerun()

# ─────────────────────────────
# Sidebar Controls
# ─────────────────────────────
st.sidebar.header("⚙️ Settings")

# Theme toggle button
render_theme_toggle()

# Cache stats block
with st.sidebar.expander("💾 Cache Stats"):
    cache_stats = get_cache_stats()
    st.write(f"**Players cached:** {cache_stats.get('total_players', 0)}")
    st.write(f"**Games cached:** {cache_stats.get('total_games', 0):,}")
    st.write(f"**DB Size:** {cache_stats.get('db_size_mb', 0):.1f} MB")

    if st.button("🗑️ Clear Old Seasons"):
        clear_old_seasons([current_season, prior_season])
        st.success("Old seasons cleared!")
        st.rerun()

# Upcoming games dropdown with a default "Select" option
st.sidebar.subheader("📅 Select Upcoming Game")

# Get today, tomorrow, and day after tomorrow's games (3 days total)
upcoming_games = get_upcoming_games(days=2)
selected_game = None
game_map = {}

# Generate date range display (e.g., "Nov 7 - Nov 9")
def get_date_range_display():
    """Generate clean date range display for today, tomorrow, and day after"""
    today = datetime.now()
    day_after = today + timedelta(days=2)
    
    today_str = today.strftime("%b %d")
    day_after_str = day_after.strftime("%b %d")
    
    return f"{today_str} - {day_after_str}"

date_range_display = get_date_range_display()

if upcoming_games:
    sidebar_options = ["-- Select a Game --"]
    for g in upcoming_games:
        # Ensure the game has required fields
        if not all(k in g for k in ['home', 'away']):
            print(f"Skipping invalid game data: {g}")
            continue
            
        date_disp = g.get("date_display", "")
        tm = f" ({g['time_display']})" if g.get("time_display") else ""
        label = f"{date_disp} - {g['away']} @ {g['home']}{tm}"
        sidebar_options.append(label)
        
        # Ensure we have all required fields in the game data
        game_data = {
            'home_team': g['home'],
            'away_team': g['away'],
            'game_date': g.get('date_display', ''),
            'game_time': g.get('time_display', ''),
            'game_id': g.get('game_id', '')
        }
        game_map[label] = game_data

    if len(sidebar_options) > 1:  # If we have valid games
        picked_label = st.sidebar.selectbox(
            f"Upcoming games ({date_range_display}) - {len(sidebar_options)-1} found",
            options=sidebar_options,
            index=0,  # default to instruction line
        )

        if picked_label != "-- Select a Game --":
            selected_game = game_map[picked_label]
            st.sidebar.info(
                f"Matchup: {selected_game['away_team']} @ {selected_game['home_team']}"
            )
    else:
        st.sidebar.warning("No valid upcoming games found in the data.")
        selected_game = None
else:
    st.sidebar.warning(f"⚠️ No upcoming games for {date_range_display}.")
    selected_game = None

# Which stat to predict on the board
st.sidebar.subheader("📊 Stat to Project")
stat_display_list = list(STAT_OPTIONS.keys())
stat_display_choice = st.sidebar.selectbox(
    "Choose stat to preview on the board",
    options=stat_display_list,
    index=0,
)
stat_code_choice = STAT_OPTIONS[stat_display_choice]

# Render bet sheet in sidebar
render_bet_sheet_button()

# ─────────────────────────────
# Main render call
# ─────────────────────────────
# Initialize session state for page navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'  # 'main' or 'bet_sheet'

if st.session_state.current_page == 'bet_sheet':
    render_bet_sheet_page()
else:
    st.title("🏀 NBA Player Props Model")
    
    # Main content
    if not selected_game or selected_game == "-- Select a Game --" or not isinstance(selected_game, dict):
        st.info("👈 Select a game from the sidebar to get started!")
    else:
        print(f"\n=== DEBUG: Selected Game Data ===")
        print(f"Type: {type(selected_game)}")
        print(f"Keys: {list(selected_game.keys())}")
        print(f"Home Team: {selected_game.get('home_team', 'Not found')}")
        print(f"Away Team: {selected_game.get('away_team', 'Not found')}")
        print("============================\n")
        
        build_matchup_view(
            selected_game,
            stat_code_choice,
            stat_display_choice,
            current_season,
            prior_season,
            model
        )

# footer
st.markdown("---")
st.markdown(
    "**Data Sources:** NBA.com (via nba_api) | "
    "**Model:** Enhanced Ridge Regression  \n"
    "**Features:** Season blending, H2H history, opponent recent form, "
    "positional defense  \n"
    "**Sportsbook Lines:** FanDuel via The Odds API  \n"
    "**Note:** Projections are informational only. "
    "Always verify lines and context."
)
