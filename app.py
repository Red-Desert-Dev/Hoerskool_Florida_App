import ast
import contextlib
import hashlib
import hmac
import html
import io
import base64
import json
import os
import random
import re
import secrets
import sqlite3
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


DB_FILE = "school_app.db"
JSON_BACKUP_FILE = "db.json"
SCHOOL_NAME = "Hoërskool Florida"
SCHOOL_CREST_FILE = os.path.join("assets", "hoerskool_florida_wapen.png")
APP_TAGLINE = "Bou vaardighede in wiskunde, tale en leesbegrip - een kort oefensessie op 'n slag."
PBKDF2_ITERATIONS = 260_000
DEFAULT_TEACHER_NAME = "Onderwyser"
DEFAULT_TEACHER_PASSWORD = "admin123"
QUESTIONS_PER_LEVEL = 5
INCORRECT_HINT_PENALTY = 2
GRADE_OPTIONS = list(range(2, 13))
READING_UNTIMED_LEVELS = 4
TETRIS_DAILY_BONUS_CAP = 100
TETRIS_PERSONAL_BEST_BONUS = 10
TETRIS_GRADE_BEST_BONUS = 25
TETRIS_SCHOOL_BEST_BONUS = 50
READING_PREVIEW_SECONDS_BY_LEVEL = {
    1: 60,
    2: 60,
    3: 50,
    4: 45,
    5: 40,
    6: 35,
    7: 30,
    8: 25,
    9: 20,
    10: 20,
}

AVATAR_OPTIONS = {
    "astronaut": {"label": "Astronaut", "face": "#ffd7a8", "hair": "#3b2b25", "accent": "#f2cf4a", "symbol": "👨‍🚀"},
    "robot": {"label": "Robot", "face": "#b8c7d9", "hair": "#516070", "accent": "#007a3d", "symbol": "🤖"},
    "ninja": {"label": "Ninja", "face": "#f0b98d", "hair": "#10131c", "accent": "#c7252e", "symbol": "🥷"},
    "wizard": {"label": "Wizard", "face": "#ffd1bd", "hair": "#6f4bd8", "accent": "#b76cff", "symbol": "🧙‍♂️"},
    "scientist": {"label": "Scientist", "face": "#f4c7a1", "hair": "#e8edf5", "accent": "#007a3d", "symbol": "👨‍🔬"},
    "gamer": {"label": "Gamer", "face": "#d8a47f", "hair": "#1c2638", "accent": "#f2cf4a", "symbol": "🎮"},
    "pilot": {"label": "Pilot", "face": "#c98f6a", "hair": "#2d211d", "accent": "#007a3d", "symbol": "👨‍✈️"},
    "artist": {"label": "Artist", "face": "#e9b384", "hair": "#ff8a3d", "accent": "#ff4b9b", "symbol": "👨‍🎨"},
    "coder": {"label": "Coder", "face": "#c48d67", "hair": "#16202f", "accent": "#f2cf4a", "symbol": "👨‍💻"},
    "captain": {"label": "Captain", "face": "#f2c09d", "hair": "#263047", "accent": "#f2cf4a", "symbol": "🧑‍✈️"},
    "alien": {"label": "Alien", "face": "#9dffb0", "hair": "#2f6b4a", "accent": "#f2cf4a", "symbol": "👽"},
    "explorer": {"label": "Explorer", "face": "#d49a73", "hair": "#7a4d2b", "accent": "#007a3d", "symbol": "🧭"},
}


def school_crest_img_html(css_class="school-crest"):
    if not os.path.exists(SCHOOL_CREST_FILE):
        return ""
    with open(SCHOOL_CREST_FILE, "rb") as crest_file:
        encoded = base64.b64encode(crest_file.read()).decode("ascii")
    return f'<img class="{css_class}" src="data:image/png;base64,{encoded}" alt="{SCHOOL_NAME} wapen" />'


def school_brand_html(compact=False):
    crest_class = "school-crest-small" if compact else "school-crest"
    text_class = "school-brand-compact" if compact else "school-brand"
    return (
        f'<div class="{text_class}">'
        f'{school_crest_img_html(crest_class)}'
        f'<div><span>{SCHOOL_NAME}</span><strong>Akademie-Kampioen</strong></div>'
        "</div>"
    )


def learner_intro_html():
    return f"""
    <div class="helper-panel">
        <h3>Welkom by jou oefenruimte</h3>
        <p>{APP_TAGLINE}</p>
        <div class="feature-grid">
            <div class="feature-card"><strong>1. Registreer</strong><span>Kies jou graad en avatar.</span></div>
            <div class="feature-card"><strong>2. Oefen</strong><span>Werk deur vrae volgens jou vlak.</span></div>
            <div class="feature-card"><strong>3. Groei</strong><span>Verdien punte, sien ranglyste en verbeter.</span></div>
        </div>
    </div>
    """


def reading_pane_html(text):
    safe_text = html.escape(str(text or "")).replace("\n", "<br>")
    return f'<div class="reading-pane">{safe_text}</div>'


st.set_page_config(
    page_title=f"{SCHOOL_NAME} Akademie",
    layout="wide",
    page_icon="HF",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Orbitron:wght@700;800&display=swap');

    :root {
        --school-bg: #062d20;
        --school-panel: #0b3b2a;
        --school-panel-2: #125437;
        --school-line: #d5b03a;
        --school-green: #007a3d;
        --school-deep-green: #064226;
        --school-yellow: #f2cf4a;
        --school-red: #c7252e;
        --school-text: #fff8df;
        --school-muted: #e7dcae;
        --school-shadow: rgba(0, 0, 0, 0.32);
    }

    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        box-shadow: none !important;
    }

    div[data-testid="stToolbar"] {
        background: transparent !important;
    }

    div[data-testid="stToolbar"] div[data-testid="stDeployButton"],
    div[data-testid="stToolbar"] button[aria-label="Deploy"],
    div[data-testid="stToolbar"] button[title="Deploy"] {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp {
        background:
            linear-gradient(180deg, rgba(199, 37, 46, 0.12) 0%, transparent 18%),
            linear-gradient(135deg, #06351f 0%, #0d5c35 48%, #052719 100%);
        color: var(--school-text);
        font-family: Inter, system-ui, sans-serif;
    }

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #073820 0%, #0a2b1d 100%);
        border-right: 1px solid rgba(242, 207, 74, 0.34);
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--school-text);
    }

    h1, h2, h3 {
        font-family: Inter, system-ui, sans-serif;
        letter-spacing: 0;
    }

    .school-brand,
    .school-brand-compact {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        color: var(--school-text);
    }

    .school-brand-compact {
        justify-content: flex-start;
        gap: 10px;
        margin-bottom: 12px;
    }

    .school-brand span,
    .school-brand-compact span {
        display: block;
        color: var(--school-yellow);
        font-size: 0.82rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .school-brand strong {
        display: block;
        font-size: clamp(1.6rem, 4vw, 2.3rem);
        line-height: 1.05;
    }

    .school-brand-compact strong {
        display: block;
        font-size: 0.98rem;
        line-height: 1.1;
    }

    .school-crest {
        width: 92px;
        height: 92px;
        object-fit: contain;
        flex: 0 0 auto;
        filter: drop-shadow(0 10px 20px rgba(0,0,0,0.35));
    }

    .school-crest-small {
        width: 44px;
        height: 44px;
        object-fit: contain;
        flex: 0 0 auto;
    }

    .helper-panel,
    .empty-state,
    .practice-guide {
        background: rgba(8, 49, 29, 0.78);
        border: 1px solid rgba(242, 207, 74, 0.32);
        border-radius: 8px;
        padding: 18px 20px;
        margin: 12px 0 18px 0;
        box-shadow: 0 12px 30px rgba(0,0,0,0.18);
    }

    .helper-panel h3,
    .empty-state h3,
    .practice-guide h3 {
        margin: 0 0 8px 0;
        color: var(--school-yellow);
    }

    .helper-panel p,
    .empty-state p,
    .practice-guide p {
        margin: 0;
        color: var(--school-muted);
        line-height: 1.5;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-top: 14px;
    }

    .feature-card {
        background: rgba(15, 87, 52, 0.78);
        border: 1px solid rgba(242, 207, 74, 0.22);
        border-radius: 8px;
        padding: 12px;
        min-height: 86px;
    }

    .feature-card strong,
    .feature-card span {
        display: block;
    }

    .feature-card strong {
        color: var(--school-text);
        margin-bottom: 5px;
    }

    .feature-card span {
        color: var(--school-muted);
        font-size: 0.92rem;
        line-height: 1.35;
    }

    .subject-pill {
        display: inline-block;
        background: rgba(242, 207, 74, 0.16);
        border: 1px solid rgba(242, 207, 74, 0.38);
        border-radius: 999px;
        color: var(--school-yellow);
        font-weight: 800;
        margin: 3px 5px 3px 0;
        padding: 5px 10px;
        font-size: 0.88rem;
    }

    @media (max-width: 760px) {
        .feature-grid {
            grid-template-columns: 1fr;
        }

        .school-brand {
            gap: 10px;
        }

        .school-crest {
            width: 78px;
            height: 78px;
        }
    }

    .hoof-kaart {
        background:
            linear-gradient(135deg, rgba(242,207,74,0.18), rgba(199,37,46,0.12)),
            linear-gradient(180deg, #0f5a35 0%, #07381f 100%);
        padding: 30px;
        border-radius: 10px;
        border: 1px solid rgba(242, 207, 74, 0.58);
        box-shadow: 0 0 0 1px rgba(199,37,46,0.18), 0 20px 60px var(--school-shadow);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 18px;
        flex-wrap: wrap;
        text-align: center;
        font-size: 28px;
        margin-bottom: 20px;
    }

    .wetenskap-teks {
        color: var(--school-yellow);
        font-family: Inter, system-ui, sans-serif;
        font-weight: 800;
        text-shadow: 0 2px 10px rgba(0,0,0,0.34);
    }

    .question-box {
        background:
            linear-gradient(180deg, rgba(16,83,50,0.96), rgba(7,49,29,0.98));
        border: 1px solid rgba(242, 207, 74, 0.38);
        border-left: 5px solid var(--school-yellow);
        border-radius: 8px;
        padding: 26px;
        margin: 12px 0 20px 0;
        box-shadow: 0 14px 38px var(--school-shadow);
    }

    .question-box h3 {
        margin: 0;
        color: var(--school-text);
        font-size: 1.55rem;
    }

    .reading-pane {
        background: #176b65;
        border-radius: 8px;
        color: #43a3ff;
        font-size: clamp(1.45rem, 2.6vw, 2rem);
        font-weight: 500;
        line-height: 1.55;
        margin: 18px 0;
        padding: 26px 28px;
        box-shadow: inset 0 0 0 1px rgba(67, 163, 255, 0.08);
    }

    .coding-hero {
        background:
            linear-gradient(135deg, rgba(242,207,74,0.18), rgba(67,163,255,0.16)),
            linear-gradient(180deg, #0f5734 0%, #07381f 100%);
        border: 1px solid rgba(242, 207, 74, 0.45);
        border-radius: 10px;
        margin-bottom: 18px;
        padding: 24px;
    }

    .coding-hero h2 {
        color: var(--school-yellow);
        margin: 0 0 8px 0;
    }

    .coding-hero p {
        color: var(--school-muted);
        line-height: 1.5;
        margin: 0;
    }

    .code-card {
        background: #071912;
        border: 1px solid rgba(67, 163, 255, 0.32);
        border-radius: 8px;
        color: #d8fff0;
        font-family: Consolas, "Courier New", monospace;
        font-size: 1rem;
        line-height: 1.55;
        margin: 12px 0;
        padding: 16px;
        white-space: pre-wrap;
    }

    .code-card::before {
        content: "Missieplan";
        color: var(--school-yellow);
        display: block;
        font-family: Inter, system-ui, sans-serif;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .mission-card {
        background: rgba(15, 87, 52, 0.86);
        border: 1px solid rgba(242, 207, 74, 0.30);
        border-radius: 8px;
        min-height: 190px;
        padding: 16px;
    }

    .mission-card strong {
        color: var(--school-yellow);
        display: block;
        margin-bottom: 8px;
    }

    .mission-card span {
        color: var(--school-text);
        display: block;
        font-size: 0.98rem;
        line-height: 1.48;
    }

    .small-muted { color: var(--school-muted); font-size: 14px; }

    .avatar-img {
        width: 54px;
        height: 54px;
        border-radius: 50%;
        vertical-align: middle;
        margin-right: 10px;
        border: 2px solid var(--school-yellow);
        background: #0f3d2a;
        box-shadow: 0 0 20px rgba(242,207,74,0.22);
    }

    .avatar-small {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        vertical-align: middle;
        margin-right: 6px;
        border: 1px solid rgba(242,207,74,0.58);
    }

    div[data-testid="stMetric"] {
        background:
            linear-gradient(180deg, rgba(17,87,53,0.96), rgba(8,55,32,0.96));
        border: 1px solid rgba(242, 207, 74, 0.36);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 12px 28px var(--school-shadow);
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"] {
        color: var(--school-muted) !important;
        font-weight: 700;
    }

    div[data-testid="stMetricValue"] {
        color: var(--school-yellow);
        font-family: Inter, sans-serif;
        font-weight: 800;
        text-shadow: 0 2px 10px rgba(0,0,0,0.34);
    }

    .stButton > button,
    .stDownloadButton > button,
    button[kind="primary"] {
        background: linear-gradient(135deg, var(--school-yellow), #f7e07a) !important;
        color: #06351f !important;
        border: 0 !important;
        border-radius: 7px !important;
        font-weight: 800 !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.22);
        transition: transform 120ms ease, box-shadow 120ms ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 26px rgba(242,207,74,0.28);
    }

    div[data-baseweb="select"] > div,
    input,
    textarea,
    div[data-testid="stNumberInput"] input {
        background-color: #082f1d !important;
        border-color: rgba(242,207,74,0.38) !important;
        color: var(--school-text) !important;
        border-radius: 7px !important;
    }

    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.12);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #0a3a24;
        border: 1px solid rgba(242,207,74,0.28);
        border-radius: 7px;
        color: var(--school-muted);
        padding: 8px 14px;
    }

    .stTabs [aria-selected="true"] {
        color: var(--school-yellow) !important;
        border-color: rgba(242,207,74,0.68);
        box-shadow: inset 0 -2px 0 var(--school-red);
    }

    table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: rgba(8,49,29,0.92);
        border: 1px solid rgba(242,207,74,0.28);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 14px 38px rgba(0,0,0,0.24);
    }

    th {
        background: #0f5734;
        color: var(--school-yellow);
        font-family: Inter, sans-serif;
        font-size: 0.78rem;
        text-transform: uppercase;
        padding: 10px;
        border-bottom: 1px solid rgba(242,207,74,0.24);
    }

    td {
        padding: 9px 10px;
        color: var(--school-text);
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    tr:nth-child(even) td {
        background: rgba(255,255,255,0.025);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid rgba(242,207,74,0.30);
        border-radius: 8px;
        overflow: hidden;
    }

    hr {
        border-color: rgba(242,207,74,0.24);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


BASIC_MATH_LEVELS = {
    1: [
        ("8 + 5 = ?", "13"),
        ("14 - 6 = ?", "8"),
        ("23 + 12 = ?", "35"),
        ("30 - 17 = ?", "13"),
        ("45 + 9 = ?", "54"),
    ],
    2: [
        ("125 + 38 = ?", "163"),
        ("200 - 76 = ?", "124"),
        ("349 + 125 = ?", "474"),
        ("500 - 237 = ?", "263"),
        ("78 + 96 = ?", "174"),
    ],
    3: [
        ("6 x 7 = ?", "42"),
        ("8 x 9 = ?", "72"),
        ("56 / 7 = ?", "8"),
        ("81 / 9 = ?", "9"),
        ("12 x 4 = ?", "48"),
    ],
    4: [
        ("15 x 6 = ?", "90"),
        ("144 / 12 = ?", "12"),
        ("18 x 7 = ?", "126"),
        ("96 / 8 = ?", "12"),
        ("25 x 4 = ?", "100"),
    ],
    5: [
        ("(2 x 3) + (5 x 2) = ?", "16"),
        ("(4 x 6) - 8 = ?", "16"),
        ("7 + (3 x 5) = ?", "22"),
        ("(20 / 4) + 9 = ?", "14"),
        ("(6 x 6) + 12 = ?", "48"),
    ],
    6: [
        ("(18 / 3) + (4 x 5) = ?", "26"),
        ("(9 x 8) - (24 / 6) = ?", "68"),
        ("(7 x 5) + 15 - 10 = ?", "40"),
        ("60 - (6 x 7) = ?", "18"),
        ("(45 / 5) + (3 x 9) = ?", "36"),
    ],
    7: [
        ("12 + 6 x 4 = ?", "36"),
        ("50 - 18 / 3 = ?", "44"),
        ("8 x (7 + 3) = ?", "80"),
        ("(36 / 6) x 9 = ?", "54"),
        ("100 - (5 x 12) = ?", "40"),
    ],
    8: [
        ("(14 + 6) x 3 = ?", "60"),
        ("(80 - 32) / 4 = ?", "12"),
        ("(9 + 7) x (12 - 8) = ?", "64"),
        ("(6 x 8) + (72 / 9) = ?", "56"),
        ("150 - (25 x 4) = ?", "50"),
    ],
    9: [
        ("((5 + 7) x 3) - 10 = ?", "26"),
        ("(96 / 8) + (11 x 4) = ?", "56"),
        ("(14 x 6) - (9 x 5) = ?", "39"),
        ("(120 - 45) / 5 = ?", "15"),
        ("(8 x 8) + (7 x 6) - 20 = ?", "86"),
    ],
    10: [
        ("((18 + 12) x 4) / 5 = ?", "24"),
        ("(15 x 8) - (96 / 4) = ?", "96"),
        ("(200 - (7 x 15)) / 5 = ?", "19"),
        ("((9 x 9) + (6 x 7)) - 50 = ?", "73"),
        ("(144 / 12) + (13 x 7) - 30 = ?", "73"),
    ],
}

FOUNDATION_MATH_LEVELS = {
    2: {
        1: [("2 + 3 = ?", "5"), ("4 + 1 = ?", "5"), ("5 - 2 = ?", "3"), ("6 - 1 = ?", "5"), ("Tel aan: 2, 3, 4, __", "5")],
        2: [("7 + 2 = ?", "9"), ("8 - 3 = ?", "5"), ("10 - 4 = ?", "6"), ("5 + 4 = ?", "9"), ("Tel terug: 9, 8, 7, __", "6")],
        3: [("10 + 5 = ?", "15"), ("12 - 2 = ?", "10"), ("11 + 3 = ?", "14"), ("15 - 5 = ?", "10"), ("Watter getal is groter: 13 of 9?", "13")],
        4: [("20 - 7 = ?", "13"), ("14 + 6 = ?", "20"), ("18 - 8 = ?", "10"), ("9 + 8 = ?", "17"), ("Dubbel van 4 is?", "8")],
        5: [("2 x 2 = ?", "4"), ("3 x 2 = ?", "6"), ("10 / 2 = ?", "5"), ("Halwe van 8 is?", "4"), ("5 + 5 + 5 = ?", "15")],
        6: [("25 + 5 = ?", "30"), ("30 - 10 = ?", "20"), ("12 + 8 = ?", "20"), ("16 - 9 = ?", "7"), ("Dubbel van 6 is?", "12")],
        7: [("2 x 5 = ?", "10"), ("4 x 2 = ?", "8"), ("12 / 2 = ?", "6"), ("3 groepe van 3 is?", "9"), ("20 - 11 = ?", "9")],
        8: [("35 + 10 = ?", "45"), ("40 - 15 = ?", "25"), ("6 x 2 = ?", "12"), ("18 / 2 = ?", "9"), ("Tel aan in 5e: 5, 10, 15, __", "20")],
        9: [("50 - 25 = ?", "25"), ("24 + 6 = ?", "30"), ("3 x 4 = ?", "12"), ("20 / 4 = ?", "5"), ("Dubbel van 9 is?", "18")],
        10: [("45 + 12 = ?", "57"), ("60 - 18 = ?", "42"), ("5 x 5 = ?", "25"), ("30 / 5 = ?", "6"), ("Tel aan in 10e: 10, 20, 30, __", "40")],
    },
    3: {
        1: [("12 + 8 = ?", "20"), ("15 - 6 = ?", "9"), ("24 + 5 = ?", "29"), ("30 - 7 = ?", "23"), ("Watter getal is kleiner: 18 of 21?", "18")],
        2: [("35 + 14 = ?", "49"), ("48 - 16 = ?", "32"), ("27 + 9 = ?", "36"), ("40 - 18 = ?", "22"), ("Dubbel van 12 is?", "24")],
        3: [("3 x 4 = ?", "12"), ("5 x 3 = ?", "15"), ("18 / 3 = ?", "6"), ("20 / 4 = ?", "5"), ("4 groepe van 5 is?", "20")],
        4: [("6 x 5 = ?", "30"), ("7 x 3 = ?", "21"), ("24 / 6 = ?", "4"), ("30 / 5 = ?", "6"), ("Halwe van 26 is?", "13")],
        5: [("(4 + 3) x 2 = ?", "14"), ("20 - (5 + 4) = ?", "11"), ("3 x (2 + 4) = ?", "18"), ("(18 / 3) + 5 = ?", "11"), ("10 + 10 - 6 = ?", "14")],
        6: [("125 + 10 = ?", "135"), ("100 - 35 = ?", "65"), ("45 + 27 = ?", "72"), ("90 - 48 = ?", "42"), ("Dubbel van 25 is?", "50")],
        7: [("8 x 4 = ?", "32"), ("6 x 6 = ?", "36"), ("36 / 6 = ?", "6"), ("42 / 7 = ?", "6"), ("9 groepe van 3 is?", "27")],
        8: [("(6 x 4) + 5 = ?", "29"), ("50 - (3 x 8) = ?", "26"), ("(30 / 5) + 12 = ?", "18"), ("7 + (4 x 5) = ?", "27"), ("100 - 25 - 25 = ?", "50")],
        9: [("150 + 25 = ?", "175"), ("200 - 75 = ?", "125"), ("9 x 5 = ?", "45"), ("56 / 7 = ?", "8"), ("Tel aan in 25e: 25, 50, 75, __", "100")],
        10: [("(8 x 5) - 10 = ?", "30"), ("(60 / 6) + 18 = ?", "28"), ("90 - (7 x 8) = ?", "34"), ("45 + 35 - 20 = ?", "60"), ("Dubbel van 48 is?", "96")],
    },
}


def math_levels_for_grade(grade):
    return FOUNDATION_MATH_LEVELS.get(int(grade), BASIC_MATH_LEVELS)


def build_basic_math_questions():
    questions = []
    for grade in GRADE_OPTIONS:
        for level, items in math_levels_for_grade(grade).items():
            for index, (prompt, answer) in enumerate(items, start=1):
                questions.append(
                    {
                        "id": f"math_alg_g{grade}_{level}_{index:02d}",
                        "subject": "Wiskunde",
                        "topic": "Algebra",
                        "grade": grade,
                        "level": level,
                        "prompt": prompt,
                        "answer": answer,
                        "accepted": [answer],
                        "points": 6 + int(grade) + level,
                        "time_limit": 18 + min(level, 5) * 3,
                    }
                )
    return questions


BASIC_MATH_QUESTIONS = build_basic_math_questions()

def build_questions(prefix, subject, topic, levels, grade=6, base_points=10, base_time=18):
    questions = []
    for level, items in levels.items():
        for index, item in enumerate(items, start=1):
            if len(item) == 2:
                prompt, answer = item
                accepted = [answer]
                passage = None
            elif len(item) == 3:
                prompt, answer, accepted = item
                passage = None
            else:
                passage, prompt, answer, accepted = item
            questions.append(
                {
                    "id": f"{prefix}_{level}_{index:02d}",
                    "subject": subject,
                    "topic": topic,
                    "grade": grade,
                    "level": level,
                    "passage": passage,
                    "prompt": prompt,
                    "answer": answer,
                    "accepted": accepted,
                    "points": base_points + level,
                    "time_limit": base_time + min(level, 5) * 2,
                }
            )
    return questions


def geometry_items_for_grade_level(grade, level):
    if int(grade) <= 3:
        side = level + 1
        length = level + 3
        width = level + 1
        return [
            (f"Hoeveel hoeke het 'n driehoek?", "3", ["3", "drie"]),
            (f"Hoeveel sye het 'n vierkant?", "4", ["4", "vier"]),
            (f"Wat is die omtrek van 'n vierkant met sye van {side} cm?", str(side * 4), [str(side * 4), f"{side * 4} cm", f"{side * 4}cm"]),
            (f"Wat is die oppervlakte van 'n reghoek met lengte {length} cm en breedte {width} cm?", str(length * width), [str(length * width), f"{length * width} cm2", f"{length * width}cm2"]),
            ("Watter vorm het geen hoeke nie?", "sirkel", ["sirkel", "kring"]),
        ]
    return [
        (f"Wat is die omtrek van 'n vierkant met sye van {level + 3} cm?", str((level + 3) * 4)),
        (
            f"Wat is die oppervlakte van 'n reghoek met lengte {level + 5} cm en breedte {level + 2} cm?",
            str((level + 5) * (level + 2)),
        ),
        (
            f"'n Reghoek het 'n omtrek van {2 * ((level + 4) + (level + 1))} cm. Die lengte is {level + 4} cm. Wat is die breedte?",
            str(level + 1),
        ),
        (
            f"Wat is die volume van 'n blok met lengte {level + 2} cm, breedte {level + 1} cm en hoogte 2 cm?",
            str((level + 2) * (level + 1) * 2),
        ),
        (
            f"'n Reguit lyn is 180 grade. Een hoek is {level * 10 + 30} grade. Hoe groot is die ander hoek?",
            str(180 - (level * 10 + 30)),
        ),
    ]


def build_meetkunde_questions():
    questions = []
    for grade in GRADE_OPTIONS:
        for level in range(1, 11):
            items = geometry_items_for_grade_level(grade, level)
            for index, item in enumerate(items, start=1):
                prompt, answer = item[:2]
                accepted = item[2] if len(item) > 2 else [answer, f"{answer}cm", f"{answer} cm", f"{answer}cm2", f"{answer} cm2"]
                questions.append(
                    {
                        "id": f"math_geo_g{grade}_{level}_{index:02d}",
                        "subject": "Wiskunde",
                        "topic": "Meetkunde",
                        "grade": grade,
                        "level": level,
                        "prompt": prompt,
                        "answer": answer,
                        "accepted": accepted,
                        "points": 7 + int(grade) + level,
                        "time_limit": 18 + min(level, 5) * 3,
                    }
                )
    return questions


AFRIKAANS_TAAL_LEVELS = {
    1: [("Gee die meervoud van 'kat'.", "katte"), ("Gee die meervoud van 'boek'.", "boeke"), ("Gee die antoniem van 'warm'.", "koud"), ("Gee die antoniem van 'groot'.", "klein"), ("Spel korrek: 'huis toe'.", "huis toe")],
    2: [("Gee die verkleining van 'kat'.", "katjie"), ("Gee die verkleining van 'boom'.", "boompie"), ("Gee 'n sinoniem vir 'vinnig'.", "gou", ["gou", "rats", "snel"]), ("Gee 'n sinoniem vir 'bly'.", "gelukkig", ["gelukkig", "vrolik"]), ("Spel korrek: 'onmidelik'.", "onmiddellik")],
    3: [("Kies die regte woord: Ek ___ skool toe.", "gaan"), ("Kies die regte woord: Sy ___ 'n boek.", "lees"), ("Gee die verlede tyd: Ek speel.", "Ek het gespeel", ["ek het gespeel", "het gespeel"]), ("Gee die toekomende tyd: Ek lees.", "Ek sal lees", ["ek sal lees", "sal lees"]), ("Spel korrek: 'interesant'.", "interessant")],
    4: [("Gee die trappe van vergelyking: mooi, mooier, ___.", "mooiste"), ("Gee die trappe van vergelyking: vinnig, vinniger, ___.", "vinnigste"), ("Wat is die onderwerp in die sin: Die hond blaf hard.", "Die hond", ["die hond", "hond"]), ("Wat is die werkwoord in die sin: Sara skryf netjies.", "skryf"), ("Spel korrek: 'veras'.", "verras")],
    5: [("Gee die direkte rede: Jan se dat hy moeg is.", "Jan se: \"Ek is moeg.\"", ["jan se: ek is moeg", "jan se ek is moeg"]), ("Gee die indirekte rede: Ana se: Ek is bly.", "Ana se dat sy bly is", ["ana se dat sy bly is"]), ("Verbind die sinne met 'want': Ek bly tuis. Ek is siek.", "Ek bly tuis want ek is siek", ["ek bly tuis want ek is siek"]), ("Gee die basisvorm van 'hardloop'.", "hardloop"), ("Spel korrek: 'akkommodasie'.", "akkommodasie")],
    6: [("Gee die meervoud van 'stad'.", "stede"), ("Gee die meervoud van 'dag'.", "dae"), ("Gee die verkleining van 'glas'.", "glasie"), ("Gee die antoniem van 'moedig'.", "bang", ["bang", "lafhartig"]), ("Spel korrek: 'defenitief'.", "definitief")],
    7: [("Watter woordsoort is 'vinnig' in: Die seun hardloop vinnig?", "bywoord"), ("Watter woordsoort is 'groen' in: Die groen boom groei?", "byvoeglike naamwoord"), ("Skryf in die verlede tyd: Hulle eet kos.", "Hulle het kos geeet", ["hulle het kos geeet", "hulle het kos geëet"]), ("Skryf in die toekomende tyd: Sy sing mooi.", "Sy sal mooi sing", ["sy sal mooi sing"]), ("Spel korrek: 'paralel'.", "parallel")],
    8: [("Gee die intensiewe vorm van 'wit'.", "spierwit"), ("Gee die intensiewe vorm van 'koud'.", "yskoud"), ("Gee 'n samestelling met 'son' en 'bril'.", "sonbril"), ("Gee 'n samestelling met 'skool' en 'tas'.", "skooltas"), ("Spel korrek: 'biblioteek'.", "biblioteek")],
    9: [("Verander na 'n vraag: Jy gaan vandag skool toe.", "Gaan jy vandag skool toe?", ["gaan jy vandag skool toe"]), ("Verander na 'n bevel: Jy moet stil wees.", "Wees stil", ["wees stil"]), ("Gee die ontkennende vorm: Ek het iets gesien.", "Ek het niks gesien nie", ["ek het niks gesien nie"]), ("Gee die ontkennende vorm: Iemand klop.", "Niemand klop nie", ["niemand klop nie"]), ("Spel korrek: 'professioneel'.", "professioneel")],
    10: [("Ontleed die sin: Die meisie lees die boek. Wat is die voorwerp?", "die boek", ["boek", "die boek"]), ("Ontleed die sin: Pa maak kos. Wat is die onderwerp?", "Pa", ["pa"]), ("Gee die lydende vorm: Die seun skop die bal.", "Die bal word deur die seun geskop", ["die bal word deur die seun geskop"]), ("Gee die bedrywende vorm: Die brief word deur Mia geskryf.", "Mia skryf die brief", ["mia skryf die brief"]), ("Spel korrek: 'verantwoordelikheid'.", "verantwoordelikheid")],
}


ENGLISH_TAAL_LEVELS = {
    1: [("Choose the correct word: I ___ happy.", "am"), ("Choose the correct word: She ___ a book.", "reads"), ("Give the opposite of 'hot'.", "cold"), ("Give the plural of 'dog'.", "dogs"), ("Spell correctly: 'freind'.", "friend")],
    2: [("Give the plural of 'box'.", "boxes"), ("Give the plural of 'baby'.", "babies"), ("Give a synonym for 'quick'.", "fast", ["fast", "speedy", "rapid"]), ("Give the opposite of 'early'.", "late"), ("Spell correctly: 'becuase'.", "because")],
    3: [("Change to past tense: I walk.", "I walked", ["i walked"]), ("Change to past tense: They play.", "They played", ["they played"]), ("Choose the correct word: He ___ to school.", "goes"), ("Choose the correct word: We ___ soccer.", "play"), ("Spell correctly: 'wich'.", "which")],
    4: [("Give the comparative form of 'big'.", "bigger"), ("Give the superlative form of 'small'.", "smallest"), ("Identify the verb: The cat sleeps.", "sleeps"), ("Identify the noun: The girl laughs.", "girl"), ("Spell correctly: 'seperate'.", "separate")],
    5: [("Add punctuation: where are you", "Where are you?", ["where are you?"]), ("Add punctuation: i like apples", "I like apples.", ["i like apples."]), ("Choose: Their/There house is big.", "Their"), ("Choose: Your/You're late.", "You're", ["you're", "you are"]), ("Spell correctly: 'adress'.", "address")],
    6: [("Change to future tense: I read.", "I will read", ["i will read"]), ("Change to future tense: She sings.", "She will sing", ["she will sing"]), ("Give the opposite of 'brave'.", "afraid", ["afraid", "scared"]), ("Give a synonym for 'happy'.", "glad", ["glad", "joyful", "pleased"]), ("Spell correctly: 'definately'.", "definitely")],
    7: [("Choose the adjective: The red car stopped.", "red"), ("Choose the adverb: He ran quickly.", "quickly"), ("Change to past tense: They write a test.", "They wrote a test", ["they wrote a test"]), ("Change to plural: The child laughs.", "The children laugh", ["the children laugh"]), ("Spell correctly: 'tomorow'.", "tomorrow")],
    8: [("Join with 'because': I stayed home. I was sick.", "I stayed home because I was sick", ["i stayed home because i was sick"]), ("Join with 'but': I tried. I failed.", "I tried but I failed", ["i tried but i failed"]), ("Choose: much/many books", "many"), ("Choose: much/many water", "much"), ("Spell correctly: 'beautiful'.", "beautiful")],
    9: [("Change to a question: You are ready.", "Are you ready?", ["are you ready"]), ("Make negative: I saw something.", "I saw nothing", ["i saw nothing", "i did not see anything"]), ("Identify the subject: The teacher smiled.", "The teacher", ["teacher", "the teacher"]), ("Identify the object: Sam kicked the ball.", "the ball", ["ball", "the ball"]), ("Spell correctly: 'necessary'.", "necessary")],
    10: [("Change to passive voice: The boy kicked the ball.", "The ball was kicked by the boy", ["the ball was kicked by the boy"]), ("Change to active voice: The cake was eaten by Tom.", "Tom ate the cake", ["tom ate the cake"]), ("Choose the correct tense: Yesterday I ___ home.", "went"), ("Choose the correct tense: Tomorrow we ___ early.", "will leave", ["will leave", "leave"]), ("Spell correctly: 'responsibility'.", "responsibility")],
}


AFRIKAANS_READING_DATA = [
    ("Mia plant boontjies in 'n klein tuin. Sy gee elke oggend water en skryf neer hoe hoog die plant groei.", [("Wat plant Mia?", "boontjies", ["boontjies"]), ("Wanneer gee sy water?", "elke oggend", ["oggend", "elke oggend"]), ("Waar plant Mia?", "tuin", ["tuin", "klein tuin"]), ("Wat skryf sy neer?", "hoe hoog die plant groei", ["hoogte", "hoe hoog die plant groei"]), ("Hoekom gee sy water?", "sodat die plant kan groei", ["plant kan groei", "groei"])]),
    ("Thabo oefen elke middag sokker. Hy wil sy span help om die finaal te wen.", [("Wat oefen Thabo?", "sokker", ["sokker"]), ("Wanneer oefen hy?", "elke middag", ["middag", "elke middag"]), ("Wie wil hy help?", "sy span", ["span", "sy span"]), ("Wat wil hy wen?", "die finaal", ["finaal", "die finaal"]), ("Hoekom oefen hy?", "om beter te speel", ["beter speel", "sy span help"])]),
    ("Die klas besoek die biblioteek. Hulle leer hoe om boeke volgens onderwerp te soek.", [("Waarheen gaan die klas?", "biblioteek", ["biblioteek", "die biblioteek"]), ("Wat leer hulle soek?", "boeke", ["boeke"]), ("Hoe word die boeke gesoek?", "volgens onderwerp", ["onderwerp", "volgens onderwerp"]), ("Wie besoek die biblioteek?", "die klas", ["klas", "die klas"]), ("Waarom is die besoek nuttig?", "hulle leer om boeke te soek", ["boeke te soek", "leer soek"])]),
    ("Lina maak 'n plakkaat oor herwinning. Sy gebruik ou tydskrifte, gom en kleurpotlode.", [("Waaroor gaan Lina se plakkaat?", "herwinning", ["herwinning"]), ("Wat gebruik sy?", "ou tydskrifte", ["tydskrifte", "ou tydskrifte"]), ("Noem een ander item wat sy gebruik.", "gom", ["gom", "kleurpotlode"]), ("Wie maak die plakkaat?", "Lina", ["lina"]), ("Wat beteken herwinning in hierdie konteks?", "om ou goed weer te gebruik", ["weer gebruik", "ou goed weer gebruik"])]),
    ("Die skool hou 'n leeskompetisie. Elke leerder probeer vyf boeke in 'n maand lees.", [("Wat hou die skool?", "leeskompetisie", ["leeskompetisie"]), ("Hoeveel boeke probeer elke leerder lees?", "vyf", ["5", "vyf"]), ("In hoe lank moet hulle lees?", "een maand", ["maand", "een maand"]), ("Wie neem deel?", "elke leerder", ["leerder", "elke leerder"]), ("Wat is die doel van die kompetisie?", "om meer te lees", ["meer te lees", "lees"])]),
    ("Sipho bou 'n modelbrug met roomysstokkies. Hy toets of dit 'n klein boek kan dra.", [("Wat bou Sipho?", "modelbrug", ["brug", "modelbrug"]), ("Waarmee bou hy dit?", "roomysstokkies", ["roomysstokkies"]), ("Wat toets hy?", "of dit 'n klein boek kan dra", ["boek kan dra", "klein boek"]), ("Wie bou die brug?", "Sipho", ["sipho"]), ("Waarom toets hy die brug?", "om te sien of dit sterk is", ["sterk", "of dit sterk is"])]),
    ("Emma spaar geld vir 'n nuwe woordeboek. Sy sit elke week tien rand in haar spaarbussie.", [("Waarvoor spaar Emma?", "woordeboek", ["woordeboek"]), ("Hoe gereeld spaar sy?", "elke week", ["week", "elke week"]), ("Hoeveel geld sit sy weg?", "tien rand", ["10 rand", "tien rand"]), ("Waar sit sy die geld?", "spaarbussie", ["spaarbussie"]), ("Wat wys dit van Emma?", "sy beplan vooruit", ["beplan", "spaar"])]),
    ("Die wind waai sterk by die sportveld. Die afrigter skuif die wedstryd na die saal.", [("Waar waai die wind sterk?", "sportveld", ["sportveld"]), ("Wie skuif die wedstryd?", "afrigter", ["afrigter", "die afrigter"]), ("Waarheen word dit geskuif?", "die saal", ["saal", "die saal"]), ("Hoekom word dit geskuif?", "die wind waai sterk", ["wind", "sterk wind"]), ("Wat is 'n afrigter?", "iemand wat 'n span oefen", ["span oefen", "oefen"])]),
    ("Nadia lees 'n resep voordat sy muffins bak. Sy meet meel, suiker en melk versigtig af.", [("Wat lees Nadia?", "resep", ["resep"]), ("Wat bak sy?", "muffins", ["muffins"]), ("Noem een bestanddeel.", "meel", ["meel", "suiker", "melk"]), ("Hoe meet sy die bestanddele?", "versigtig", ["versigtig"]), ("Waarom lees sy die resep eerste?", "sodat sy weet wat om te doen", ["weet wat om te doen", "instruksies"])]),
    ("Die gemeenskap plant bome langs die straat. Oor 'n paar jaar sal daar meer skaduwee wees.", [("Wie plant bome?", "die gemeenskap", ["gemeenskap", "die gemeenskap"]), ("Waar plant hulle bome?", "langs die straat", ["straat", "langs die straat"]), ("Wat sal daar later meer wees?", "skaduwee", ["skaduwee"]), ("Wanneer sal die skaduwee meer wees?", "oor 'n paar jaar", ["paar jaar", "oor 'n paar jaar"]), ("Waarom is bome nuttig?", "dit gee skaduwee", ["skaduwee", "gee skaduwee"])]),
]


ENGLISH_READING_DATA = [
    ("Ben packs his school bag before breakfast. He checks his books, pencil case, and lunch box.", [("When does Ben pack his bag?", "before breakfast", ["before breakfast"]), ("What does he check first?", "his books", ["books", "his books"]), ("Name one thing in the bag.", "pencil case", ["books", "pencil case", "lunch box"]), ("Who packs the bag?", "Ben", ["ben"]), ("Why does he check the bag?", "to be ready for school", ["ready", "ready for school"])]),
    ("A small bird builds a nest in the tree. It carries dry grass and soft leaves.", [("What builds a nest?", "a small bird", ["bird", "a small bird"]), ("Where is the nest?", "in the tree", ["tree", "in the tree"]), ("What does it carry?", "dry grass", ["dry grass", "soft leaves"]), ("Name one soft material.", "soft leaves", ["soft leaves", "leaves"]), ("Why does the bird build a nest?", "to live in it", ["live", "eggs", "home"])]),
    ("Lebo rides his bicycle to the shop. He buys bread and milk for his grandmother.", [("How does Lebo travel?", "bicycle", ["bicycle", "bike"]), ("Where does he go?", "shop", ["shop", "the shop"]), ("What does he buy?", "bread and milk", ["bread", "milk", "bread and milk"]), ("Who is it for?", "his grandmother", ["grandmother", "his grandmother"]), ("What kind of person is Lebo?", "helpful", ["helpful", "kind"])]),
    ("The class watches dark clouds gather. Soon, rain begins to fall on the playground.", [("What does the class watch?", "dark clouds", ["clouds", "dark clouds"]), ("What begins to fall?", "rain", ["rain"]), ("Where does rain fall?", "playground", ["playground", "the playground"]), ("What might happen next?", "the learners go inside", ["go inside", "inside"]), ("What tells us rain is coming?", "dark clouds", ["dark clouds", "clouds"])]),
    ("Sara writes a letter to her cousin. She tells him about her new puppy.", [("What does Sara write?", "letter", ["letter", "a letter"]), ("Who gets the letter?", "her cousin", ["cousin", "her cousin"]), ("What does she write about?", "new puppy", ["puppy", "new puppy"]), ("Who is the writer?", "Sara", ["sara"]), ("Why might her cousin enjoy it?", "he learns her news", ["news", "puppy"])]),
    ("The children clean the park on Saturday. They pick up paper, bottles, and plastic bags.", [("When do they clean?", "Saturday", ["saturday"]), ("Where do they clean?", "park", ["park", "the park"]), ("Name one thing they pick up.", "paper", ["paper", "bottles", "plastic bags"]), ("Who cleans the park?", "children", ["children", "the children"]), ("Why is this helpful?", "the park becomes cleaner", ["cleaner", "park clean"])]),
    ("Tom saves coins in a jar. He wants to buy a soccer ball at the end of the month.", [("What does Tom save?", "coins", ["coins"]), ("Where does he save them?", "jar", ["jar", "a jar"]), ("What does he want to buy?", "soccer ball", ["soccer ball", "ball"]), ("When will he buy it?", "end of the month", ["end of the month", "month"]), ("What does this show about Tom?", "he plans ahead", ["plans", "saves"])]),
    ("The baker wakes early to make fresh bread. By seven o'clock, the shop smells warm and sweet.", [("Who wakes early?", "baker", ["baker", "the baker"]), ("What does the baker make?", "fresh bread", ["bread", "fresh bread"]), ("When does the shop smell warm?", "seven o'clock", ["seven", "seven o'clock"]), ("How does the shop smell?", "warm and sweet", ["warm", "sweet", "warm and sweet"]), ("Why wake early?", "to make fresh bread", ["make bread", "fresh bread"])]),
    ("Nina studies a map before the hike. She marks the river, hill, and picnic spot.", [("What does Nina study?", "map", ["map", "a map"]), ("Why does she study it?", "before the hike", ["hike", "before the hike"]), ("Name one place she marks.", "river", ["river", "hill", "picnic spot"]), ("Who studies the map?", "Nina", ["nina"]), ("How does the map help?", "it shows the route", ["route", "places"])]),
    ("The team practises every afternoon. They pass, run, and listen carefully to the coach.", [("When does the team practise?", "every afternoon", ["afternoon", "every afternoon"]), ("Name one action they practise.", "pass", ["pass", "run", "listen"]), ("Who do they listen to?", "coach", ["coach", "the coach"]), ("Who practises?", "team", ["team", "the team"]), ("Why practise often?", "to improve", ["improve", "get better"])]),
]


def build_reading_questions(prefix, subject, data, grade=6):
    levels = {}
    for level, (passage, items) in enumerate(data, start=1):
        levels[level] = [(passage, prompt, answer, accepted) for prompt, answer, accepted in items]
    return build_questions(prefix, subject, "Lees", levels, grade=grade, base_points=10 + int(grade), base_time=25)


def coding_items_for_grade_level(grade, level):
    a = level + 2
    b = grade - 1
    if grade <= 5:
        return [
            ("In coding, what do we call a step-by-step list of instructions?", "algorithm", ["algorithm", "an algorithm"]),
            (f"Python command to show text on the screen: ___('Level {level}')", "print", ["print", "print()"]),
            (f"What is the value of x after: x = {a} + {b}", str(a + b), [str(a + b)]),
            ("What symbol starts a comment in Python?", "#", ["#", "hash", "hashtag"]),
            ("A repeated instruction is called a ___.", "loop", ["loop"]),
        ]
    if grade <= 7:
        word = ["Hi", "Code", "Python", "School", "Robot", "Loop", "Debug", "Data", "Logic", "Create"][level - 1]
        return [
            (f"What will Python print? print('{word}')", word, [word, word.lower()]),
            (f"What is stored in score after: score = {a} * 2?", str(a * 2), [str(a * 2)]),
            ("Which Python keyword starts a repeat loop over a list: for or if?", "for", ["for"]),
            ("Complete the Python condition: if age >= 10___", ":", [":", "colon"]),
            ("Java also uses variables. Which type stores whole numbers: int or String?", "int", ["int"]),
        ]
    if grade <= 9:
        values = [level, level + 1, level + 2]
        return [
            (f"What is the output of Python: print({a} * {level})", str(a * level), [str(a * level)]),
            ("Which Python type stores True or False values?", "bool", ["bool", "boolean"]),
            (f"Complete the Python list access: marks = {values}; marks[0] is ___", str(values[0]), [str(values[0])]),
            ("Which keyword creates a Python function?", "def", ["def"]),
            ("In Java, which symbol ends most statements?", ";", [";", "semicolon"]),
        ]
    if grade <= 11:
        items_count = level + 2
        method_name = "main" if level < 6 else "toString"
        return [
            (f"What is returned by len(list(range({items_count}))) in Python?", str(items_count), [str(items_count)]),
            ("Which Python keyword handles an error after try?", "except", ["except"]),
            ("What does a function normally use to send a value back?", "return", ["return"]),
            ("In object-oriented programming, a class is a blueprint for an ___.", "object", ["object", "objects"]),
            (f"In Java, identify the method name in: public String {method_name}()", method_name, [method_name]),
        ]
    complexity = "O(n)" if level <= 5 else "O(n^2)"
    loop_hint = "single loop" if level <= 5 else "nested loop"
    return [
        (f"Which Big O notation usually describes a {loop_hint} through n items?", complexity, [complexity.lower(), complexity, "linear" if level <= 5 else "quadratic"]),
        ("Which Python structure maps keys to values?", "dictionary", ["dictionary", "dict"]),
        ("What does SQL usually stand for?", "structured query language", ["structured query language", "sql"]),
        ("In Java, which keyword creates a subclass relationship?", "extends", ["extends"]),
        ("Which testing style checks one small function or method at a time?", "unit test", ["unit test", "unit testing", "unit"]),
    ]


def build_coding_questions():
    questions = []
    for grade in GRADE_OPTIONS:
        for level in range(1, 11):
            level_items = coding_items_for_grade_level(grade, level)
            for index, (prompt, answer, accepted) in enumerate(level_items, start=1):
                language_note = "Python"
                if "Java" in prompt:
                    language_note = "Java"
                if grade >= 8 and level >= 7:
                    language_note = "Python / Java"
                questions.append(
                    {
                        "id": f"coding_g{grade}_l{level}_{index:02d}",
                        "subject": "Kodering",
                        "topic": "Python & Java",
                        "grade": grade,
                        "level": level,
                        "prompt": f"{language_note}: {prompt}",
                        "answer": answer,
                        "accepted": accepted,
                        "points": 7 + grade + level,
                        "time_limit": 20 + min(level, 6) * 3 + max(0, grade - 7),
                    }
                )
    return questions


def build_grade_module_questions():
    questions = build_meetkunde_questions()
    for grade in GRADE_OPTIONS:
        questions.extend(
            build_questions(
                f"afr_lang_g{grade}",
                "Afrikaans",
                "Taal",
                AFRIKAANS_TAAL_LEVELS,
                grade=grade,
                base_points=7 + int(grade),
                base_time=18,
            )
        )
        questions.extend(build_reading_questions(f"afr_read_g{grade}", "Afrikaans", AFRIKAANS_READING_DATA, grade=grade))
        questions.extend(
            build_questions(
                f"eng_lang_g{grade}",
                "Engels",
                "Taal",
                ENGLISH_TAAL_LEVELS,
                grade=grade,
                base_points=7 + int(grade),
                base_time=18,
            )
        )
        questions.extend(build_reading_questions(f"eng_read_g{grade}", "Engels", ENGLISH_READING_DATA, grade=grade))
    return questions


GRADE_MODULE_QUESTIONS = build_grade_module_questions()


LEGACY_QUESTION_BANK = [
    {
        "id": "math_geo_1_01",
        "subject": "Wiskunde",
        "topic": "Meetkunde",
        "grade": 8,
        "level": 1,
        "prompt": "Wat is die oppervlakte van 'n vierkant met sye van 5 cm?",
        "answer": "25",
        "accepted": ["25", "25cm2", "25 cm2"],
        "points": 12,
        "time_limit": 20,
    },
    {
        "id": "math_geo_1_02",
        "subject": "Wiskunde",
        "topic": "Meetkunde",
        "grade": 8,
        "level": 1,
        "prompt": "'n Reghoek is 6 cm lank en 4 cm breed. Wat is die oppervlakte?",
        "answer": "24",
        "accepted": ["24", "24cm2", "24 cm2"],
        "points": 12,
        "time_limit": 20,
    },
    {
        "id": "math_geo_2_01",
        "subject": "Wiskunde",
        "topic": "Meetkunde",
        "grade": 8,
        "level": 2,
        "prompt": "'n Driehoek het 'n basis van 4 cm en 'n hoogte van 5 cm. Wat is die oppervlakte?",
        "answer": "10",
        "accepted": ["10", "10cm2", "10 cm2"],
        "points": 15,
        "time_limit": 24,
    },
    {
        "id": "afr_lang_1_01",
        "subject": "Afrikaans",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Gee die meervoud van 'kind'.",
        "answer": "kinders",
        "points": 10,
        "time_limit": 18,
    },
    {
        "id": "afr_lang_1_02",
        "subject": "Afrikaans",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Gee 'n antoniem vir 'koud'.",
        "answer": "warm",
        "points": 10,
        "time_limit": 18,
    },
    {
        "id": "afr_lang_1_03",
        "subject": "Afrikaans",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Spel die woord korrek: 'onmidelik'.",
        "answer": "onmiddellik",
        "points": 10,
        "time_limit": 20,
    },
    {
        "id": "afr_lang_2_01",
        "subject": "Afrikaans",
        "topic": "Taal",
        "grade": 8,
        "level": 2,
        "prompt": "Skryf die verkleining van 'boek'.",
        "answer": "boekie",
        "points": 12,
        "time_limit": 20,
    },
    {
        "id": "afr_read_1_01",
        "subject": "Afrikaans",
        "topic": "Lees",
        "grade": 8,
        "level": 1,
        "passage": "Daar was eenmaal 'n vinnige jakkals wat oor die lui hond gespring het.",
        "prompt": "Oor wie het die jakkals gespring?",
        "answer": "hond",
        "accepted": ["hond", "die hond", "lui hond", "die lui hond"],
        "points": 15,
        "time_limit": 25,
    },
    {
        "id": "afr_read_1_02",
        "subject": "Afrikaans",
        "topic": "Lees",
        "grade": 8,
        "level": 1,
        "passage": "Lerato lees elke aand tien bladsye sodat haar woordeskat kan groei.",
        "prompt": "Hoekom lees Lerato elke aand?",
        "answer": "woordeskat",
        "accepted": ["woordeskat", "haar woordeskat kan groei", "om haar woordeskat te laat groei"],
        "points": 15,
        "time_limit": 30,
    },
    {
        "id": "eng_lang_1_01",
        "subject": "Engels",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Choose the correct word: She ___ to school every day.",
        "answer": "walks",
        "points": 10,
        "time_limit": 18,
    },
    {
        "id": "eng_lang_1_02",
        "subject": "Engels",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Give a synonym for 'quick'.",
        "answer": "fast",
        "accepted": ["fast", "speedy", "rapid"],
        "points": 10,
        "time_limit": 18,
    },
    {
        "id": "eng_lang_1_03",
        "subject": "Engels",
        "topic": "Taal",
        "grade": 8,
        "level": 1,
        "prompt": "Spell the word correctly: 'becuase'.",
        "answer": "because",
        "points": 10,
        "time_limit": 20,
    },
    {
        "id": "eng_lang_2_01",
        "subject": "Engels",
        "topic": "Taal",
        "grade": 8,
        "level": 2,
        "prompt": "Change to past tense: 'They write a test.'",
        "answer": "they wrote a test",
        "accepted": ["they wrote a test", "they wrote a test."],
        "points": 12,
        "time_limit": 22,
    },
    {
        "id": "eng_read_1_01",
        "subject": "Engels",
        "topic": "Lees",
        "grade": 8,
        "level": 1,
        "passage": "The quick brown fox jumps over the lazy dog.",
        "prompt": "Who did the fox jump over?",
        "answer": "dog",
        "accepted": ["dog", "the dog", "lazy dog", "the lazy dog"],
        "points": 15,
        "time_limit": 25,
    },
    {
        "id": "eng_read_1_02",
        "subject": "Engels",
        "topic": "Lees",
        "grade": 8,
        "level": 1,
        "passage": "Amina practises reading aloud because it helps her speak more clearly.",
        "prompt": "Why does Amina practise reading aloud?",
        "answer": "speak more clearly",
        "accepted": ["speak more clearly", "it helps her speak more clearly", "to speak more clearly"],
        "points": 15,
        "time_limit": 30,
    },
]


CODING_QUESTIONS = build_coding_questions()


QUESTION_BANK = BASIC_MATH_QUESTIONS + GRADE_MODULE_QUESTIONS + LEGACY_QUESTION_BANK + CODING_QUESTIONS


CATEGORIES = {
    "Wiskunde - Algebra": ("Wiskunde", "Algebra"),
    "Wiskunde - Meetkunde": ("Wiskunde", "Meetkunde"),
    "Afrikaans - Taal": ("Afrikaans", "Taal"),
    "Afrikaans - Begripstoets": ("Afrikaans", "Lees"),
    "Engels - Comprehension": ("Engels", "Taal"),
    "Engels - Lees": ("Engels", "Lees"),
}

ADMIN_CATEGORIES = {
    **CATEGORIES,
    "Kodering - Python & Java": ("Kodering", "Python & Java"),
}


def now_iso():
    return datetime.now().replace(microsecond=0).isoformat()


def normalize_avatar_key(value):
    key = str(value or "").strip().lower()
    legacy_map = {
        "alien": "alien",
        "robot": "robot",
        "towenaar": "wizard",
        "wizard": "wizard",
        "ninja": "ninja",
        "student": "gamer",
    }
    return key if key in AVATAR_OPTIONS else legacy_map.get(key, "gamer")


def avatar_data_uri(avatar_key):
    avatar = AVATAR_OPTIONS[normalize_avatar_key(avatar_key)]
    symbol = avatar["symbol"]
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="{avatar['accent']}"/>
          <stop offset="1" stop-color="#151b2f"/>
        </linearGradient>
      </defs>
      <circle cx="48" cy="48" r="46" fill="url(#bg)"/>
      <circle cx="48" cy="50" r="29" fill="{avatar['face']}"/>
      <path d="M22 44c5-18 18-27 36-24 10 2 17 8 20 20-13-8-35-9-56 4z" fill="{avatar['hair']}"/>
      <circle cx="37" cy="50" r="4" fill="#10131c"/>
      <circle cx="59" cy="50" r="4" fill="#10131c"/>
      <path d="M37 66c7 6 15 6 22 0" fill="none" stroke="#10131c" stroke-width="4" stroke-linecap="round"/>
      <circle cx="72" cy="25" r="13" fill="#0e1117" opacity="0.85"/>
      <text x="72" y="31" text-anchor="middle" font-size="18" font-family="Arial, sans-serif" font-weight="700" fill="{avatar['accent']}">{symbol}</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def avatar_img_html(avatar_key, css_class="avatar-img"):
    avatar = AVATAR_OPTIONS[normalize_avatar_key(avatar_key)]
    return f'<img class="{css_class}" src="{avatar_data_uri(avatar_key)}" alt="{avatar["label"]}" />'


def avatar_display_label(avatar_key):
    return AVATAR_OPTIONS[normalize_avatar_key(avatar_key)]["label"]


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(digest, expected)


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                avatar TEXT NOT NULL,
                grade INTEGER NOT NULL DEFAULT 6,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
                account_type TEXT NOT NULL CHECK(account_type IN ('student', 'teacher')),
                account_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (account_type, account_id)
            );

            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subject_progress (
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                grade INTEGER NOT NULL DEFAULT 6,
                level INTEGER NOT NULL DEFAULT 1,
                score INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                current_streak INTEGER NOT NULL DEFAULT 0,
                best_streak INTEGER NOT NULL DEFAULT 0,
                last_seen_at TEXT,
                PRIMARY KEY (user_id, subject, topic),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                grade INTEGER NOT NULL,
                level INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_given TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                correct INTEGER NOT NULL,
                timed_out INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                points_awarded INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                game TEXT NOT NULL,
                grade INTEGER NOT NULL,
                score INTEGER NOT NULL,
                bonus_awarded INTEGER NOT NULL DEFAULT 0,
                personal_best INTEGER NOT NULL DEFAULT 0,
                grade_best INTEGER NOT NULL DEFAULT 0,
                school_best INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                grade INTEGER NOT NULL DEFAULT 6,
                level INTEGER NOT NULL DEFAULT 1,
                prompt TEXT NOT NULL,
                answer TEXT NOT NULL,
                accepted TEXT NOT NULL DEFAULT '[]',
                passage TEXT,
                hint TEXT,
                input_mode TEXT NOT NULL DEFAULT 'text',
                points INTEGER NOT NULL DEFAULT 10,
                time_limit INTEGER NOT NULL DEFAULT 20,
                active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                scope_value TEXT NOT NULL,
                user_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                level INTEGER NOT NULL,
                improvement INTEGER NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
    ensure_default_teacher()
    ensure_user_grade_column()
    ensure_question_columns()
    migrate_json_once()
    seed_question_bank()


def ensure_user_grade_column():
    with get_conn() as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "grade" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN grade INTEGER NOT NULL DEFAULT 6")


def ensure_question_columns():
    with get_conn() as conn:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(questions)").fetchall()]
        if "hint" not in columns:
            conn.execute("ALTER TABLE questions ADD COLUMN hint TEXT")
        if "input_mode" not in columns:
            conn.execute("ALTER TABLE questions ADD COLUMN input_mode TEXT NOT NULL DEFAULT 'text'")
        rows = conn.execute(
            "SELECT id, answer, input_mode FROM questions WHERE input_mode IS NULL OR input_mode = '' OR input_mode = 'text'"
        ).fetchall()
        for row in rows:
            if is_numeric_answer(row["answer"]):
                conn.execute("UPDATE questions SET input_mode = 'number' WHERE id = ?", (row["id"],))


def ensure_default_teacher():
    with get_conn() as conn:
        teacher = conn.execute("SELECT id FROM teachers WHERE id = 'teacher-1'").fetchone()
        if teacher is None:
            conn.execute(
                "INSERT INTO teachers (id, name, created_at) VALUES (?, ?, ?)",
                ("teacher-1", DEFAULT_TEACHER_NAME, now_iso()),
            )
            conn.execute(
                "INSERT INTO credentials (account_type, account_id, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("teacher", "teacher-1", hash_password(DEFAULT_TEACHER_PASSWORD), now_iso()),
            )


def serialize_accepted(question):
    accepted = question.get("accepted", [question.get("answer", "")])
    if isinstance(accepted, str):
        accepted = [item.strip() for item in accepted.split(",") if item.strip()]
    return json.dumps(accepted)


def deserialize_accepted(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = [item.strip() for item in str(value).split(",") if item.strip()]
    return parsed if isinstance(parsed, list) else []


def default_hint_for(question):
    subject = question.get("subject", "")
    topic = question.get("topic", "")
    prompt = question.get("prompt", "")
    answer = question.get("answer", "")
    if subject == "Wiskunde":
        return (
            "Werk van binne die hakies na buite. Doen eers maal en deel, dan plus en minus. "
            f"Kontroleer jou finale antwoord teen {answer}."
        )
    if topic == "Lees":
        return "Lees die stuk weer en soek die sin wat direk oor die vraag praat. Die antwoord staan gewoonlik daar naby."
    if subject == "Afrikaans":
        return "Kyk na die taalreel in die vraag: meervoud, verkleining, antoniem, tydsvorm of spelling. Probeer dan weer met die korrekte vorm."
    if subject == "Engels":
        return "Look at the grammar clue in the question: tense, plural, synonym, opposite, spelling, subject, verb, or object."
    if subject == "Kodering":
        return (
            "Lees die kode van links na regs en bo na onder. Kyk eers na veranderlikes, dan na berekeninge, "
            "voorwaardes of lusse. Python gebruik eenvoudige woorde soos print, for en def; Java gebruik dikwels int, main en kommapunte."
        )
    return "Lees die vraag stadig, merk die sleutelwoorde, en werk stap vir stap na die antwoord."


def is_numeric_answer(answer):
    value = str(answer or "").strip().replace(",", ".")
    if not value:
        return False
    try:
        float(value)
    except ValueError:
        return False
    return True


def default_input_mode_for(question):
    return "number" if is_numeric_answer(question.get("answer")) else "text"


def seed_question_bank():
    with get_conn() as conn:
        for question in QUESTION_BANK:
            conn.execute(
                """
                INSERT OR IGNORE INTO questions
                    (id, subject, topic, grade, level, prompt, answer, accepted, passage, hint, input_mode,
                     points, time_limit, active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    question["id"],
                    question["subject"],
                    question["topic"],
                    int(question.get("grade", 6)),
                    int(question["level"]),
                    question["prompt"],
                    question["answer"],
                    serialize_accepted(question),
                    question.get("passage"),
                    question.get("hint") or default_hint_for(question),
                    question.get("input_mode") or default_input_mode_for(question),
                    int(question.get("points", 10)),
                    int(question.get("time_limit", 20)),
                    now_iso(),
                ),
            )
    seed_missing_grade_starter_banks()


def seed_missing_grade_starter_banks():
    with get_conn() as conn:
        modules = conn.execute(
            """
            SELECT DISTINCT subject, topic
            FROM questions
            WHERE grade = 6 AND active = 1
            ORDER BY subject, topic
            """
        ).fetchall()
        for grade in GRADE_OPTIONS:
            if grade == 6:
                continue
            for module in modules:
                subject = module["subject"]
                topic = module["topic"]
                existing = conn.execute(
                    """
                    SELECT COUNT(1)
                    FROM questions
                    WHERE grade = ? AND subject = ? AND topic = ?
                    """,
                    (grade, subject, topic),
                ).fetchone()[0]
                if existing >= QUESTIONS_PER_LEVEL * 10:
                    continue

                source_questions = conn.execute(
                    """
                    SELECT *
                    FROM questions
                    WHERE grade = 6 AND subject = ? AND topic = ?
                    ORDER BY level, id
                    """,
                    (subject, topic),
                ).fetchall()
                for source in source_questions:
                    new_id = f"{source['id']}_g{grade}"
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO questions
                            (id, subject, topic, grade, level, prompt, answer, accepted, passage, hint,
                             input_mode, points, time_limit, active, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_id,
                            source["subject"],
                            source["topic"],
                            grade,
                            source["level"],
                            source["prompt"],
                            source["answer"],
                            source["accepted"],
                            source["passage"],
                            source["hint"],
                            source["input_mode"],
                            source["points"],
                            source["time_limit"],
                            source["active"],
                            now_iso(),
                        ),
                    )


def question_row_to_dict(row):
    accepted = deserialize_accepted(row["accepted"])
    if not accepted:
        accepted = [row["answer"]]
    question = {
        "id": row["id"],
        "subject": row["subject"],
        "topic": row["topic"],
        "grade": int(row["grade"]),
        "level": int(row["level"]),
        "prompt": row["prompt"],
        "answer": row["answer"],
        "accepted": accepted,
        "hint": row["hint"] or default_hint_for(dict(row)),
        "input_mode": row["input_mode"] or default_input_mode_for(dict(row)),
        "points": int(row["points"]),
        "time_limit": int(row["time_limit"]),
    }
    if row["passage"]:
        question["passage"] = row["passage"]
    return question


def generate_question_id(subject, topic, grade, level):
    prefix = f"{subject[:3]}_{topic[:3]}_g{grade}_l{level}".lower()
    prefix = "".join(ch if ch.isalnum() else "_" for ch in prefix)
    return f"{prefix}_{secrets.token_hex(4)}"


def migrate_json_once():
    if not os.path.exists(JSON_BACKUP_FILE):
        return
    with get_conn() as conn:
        migrated = conn.execute(
            "SELECT value FROM app_metadata WHERE key = 'json_migrated'"
        ).fetchone()
        if migrated:
            return
        existing_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing_count:
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('json_migrated', ?)",
                (now_iso(),),
            )
            return
    try:
        with open(JSON_BACKUP_FILE, "r", encoding="utf-8") as f:
            old_db = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    for uid, user in old_db.get("users", {}).items():
        name = user.get("name") or f"Student {uid}"
        avatar = normalize_avatar_key(user.get("avatar") or "Student")
        grade = int(user.get("grade", 6) or 6)
        password = user.get("password") or secrets.token_urlsafe(8)
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, name, avatar, grade, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uid), name, avatar, grade, now_iso()),
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO credentials
                    (account_type, account_id, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                ("student", str(uid), hash_password(password), now_iso()),
            )
            seed_progress = int(user.get("score", 0) or 0)
            level = int(user.get("level", 1) or 1)
            ensure_progress(conn, str(uid), "Wiskunde", "Algebra", grade)
            conn.execute(
                """
                UPDATE subject_progress
                SET score = ?, level = ?, correct_count = ?, attempt_count = ?, best_streak = ?, last_seen_at = ?
                WHERE user_id = ? AND subject = ? AND topic = ?
                """,
                (seed_progress, level, seed_progress // 10, seed_progress // 10, seed_progress // 10, now_iso(), str(uid), "Wiskunde", "Algebra"),
            )
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('json_migrated', ?)",
            (now_iso(),),
        )


def ensure_progress(conn, user_id, subject, topic, grade=6):
    conn.execute(
        """
        INSERT OR IGNORE INTO subject_progress
            (user_id, subject, topic, grade, level, score, correct_count, attempt_count, current_streak, best_streak, last_seen_at)
        VALUES (?, ?, ?, ?, 1, 0, 0, 0, 0, 0, ?)
        """,
        (user_id, subject, topic, grade, now_iso()),
    )
    conn.execute(
        """
        UPDATE subject_progress
        SET grade = ?
        WHERE user_id = ? AND subject = ? AND topic = ?
        """,
        (grade, user_id, subject, topic),
    )


def ensure_all_progress(user_id):
    with get_conn() as conn:
        user = conn.execute("SELECT grade FROM users WHERE id = ?", (user_id,)).fetchone()
        grade = int(user["grade"]) if user else 6
        for subject, topic in CATEGORIES.values():
            ensure_progress(conn, user_id, subject, topic, grade)


def get_student_by_name(name):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE lower(name) = lower(?)", (name.strip(),)).fetchone()


def get_teacher_by_name(name):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM teachers WHERE lower(name) = lower(?)", (name.strip(),)).fetchone()


def get_credential(account_type, account_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM credentials WHERE account_type = ? AND account_id = ?",
            (account_type, account_id),
        ).fetchone()
    return row["password_hash"] if row else None


def create_student(name, password, avatar, grade):
    user_id = secrets.token_hex(6)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, name, avatar, grade, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, name.strip(), avatar, int(grade), now_iso()),
        )
        conn.execute(
            "INSERT INTO credentials (account_type, account_id, password_hash, created_at) VALUES (?, ?, ?, ?)",
            ("student", user_id, hash_password(password), now_iso()),
        )
        for subject, topic in CATEGORIES.values():
            ensure_progress(conn, user_id, subject, topic, int(grade))
    return user_id


def load_student_context(user_id):
    ensure_all_progress(user_id)
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        progress = conn.execute(
            "SELECT * FROM subject_progress WHERE user_id = ? ORDER BY subject, topic", (user_id,)
        ).fetchall()
    if not user:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "avatar": normalize_avatar_key(user["avatar"]),
        "grade": int(user["grade"]),
        "progress": progress,
    }


def get_progress(user_id, subject, topic):
    with get_conn() as conn:
        user = conn.execute("SELECT grade FROM users WHERE id = ?", (user_id,)).fetchone()
        grade = int(user["grade"]) if user else 6
        ensure_progress(conn, user_id, subject, topic, grade)
        return conn.execute(
            "SELECT * FROM subject_progress WHERE user_id = ? AND subject = ? AND topic = ?",
            (user_id, subject, topic),
        ).fetchone()


def correct_count_for_level(user_id, subject, topic, level):
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT COUNT(*)
            FROM attempts
            WHERE user_id = ? AND subject = ? AND topic = ? AND level = ? AND correct = 1
            """,
            (user_id, subject, topic, int(level)),
        ).fetchone()[0]


def available_questions(subject, topic, grade, level):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM questions
            WHERE subject = ? AND topic = ? AND grade = ? AND level = ? AND active = 1
            ORDER BY id
            """,
            (subject, topic, grade, level),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                """
                SELECT * FROM questions
                WHERE subject = ? AND topic = ? AND grade = ? AND level <= ? AND active = 1
                ORDER BY level DESC, id
                """,
                (subject, topic, grade, level),
            ).fetchall()
        if not rows:
            rows = conn.execute(
                """
                SELECT * FROM questions
                WHERE subject = ? AND topic = ? AND grade = ? AND active = 1
                ORDER BY level, id
                """,
                (subject, topic, grade),
            ).fetchall()
    return [question_row_to_dict(row) for row in rows]


def max_level_for(subject, topic, grade):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(level), 1) AS max_level FROM questions WHERE subject = ? AND topic = ? AND grade = ? AND active = 1",
            (subject, topic, grade),
        ).fetchone()
    return int(row["max_level"]) if row else 1


def choose_question(user_id, subject, topic, grade, level):
    key = f"recent_{user_id}_{subject}_{topic}_{grade}"
    recent = st.session_state.get(key, [])
    questions = available_questions(subject, topic, grade, level)
    if not questions:
        return None
    choices = [q for q in questions if q["id"] not in recent] or questions
    question = random.choice(choices)
    st.session_state[key] = (recent + [question["id"]])[-3:]
    return question


def normalize_answer(value):
    return " ".join(str(value or "").strip().lower().replace("²", "2").split())


def is_correct(question, answer):
    normalized = normalize_answer(answer)
    accepted = question.get("accepted", [question["answer"]])
    return normalized in {normalize_answer(item) for item in accepted}


def run_matrix_level_up(new_level):
    matrix_html = f"""
    <img src="matrix-level-up" style="display:none;" onerror="
        (function() {{
            if (document.getElementById('matrix-level-up-overlay')) return;
            const canvas = document.createElement('canvas');
            canvas.id = 'matrix-level-up-overlay';
            canvas.style.position = 'fixed';
            canvas.style.inset = '0';
            canvas.style.width = '100vw';
            canvas.style.height = '100vh';
            canvas.style.zIndex = '999999';
            canvas.style.background = 'black';
            document.body.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            const resize = function() {{
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }};
            resize();
            window.addEventListener('resize', resize);

            const characters = '01ABCDEFGHIJKLMNOPQRSTUVWXYZ+-*/=';
            const fontSize = 18;
            const drops = [];
            for (let i = 0; i < Math.ceil(window.innerWidth / fontSize); i++) drops[i] = 1;

            const interval = setInterval(function() {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.08)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = '#f2cf4a';
                ctx.font = fontSize + 'px monospace';

                for (let i = 0; i < drops.length; i++) {{
                    const text = characters[Math.floor(Math.random() * characters.length)];
                    ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                    if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                    drops[i]++;
                }}

                ctx.textAlign = 'center';
                ctx.fillStyle = '#FFFFFF';
                ctx.font = 'bold 64px monospace';
                ctx.fillText('LEVEL UP', canvas.width / 2, canvas.height / 2 - 20);
                ctx.fillStyle = '#f2cf4a';
                ctx.font = 'bold 42px monospace';
                ctx.fillText('VLAK {new_level}', canvas.width / 2, canvas.height / 2 + 48);
            }}, 33);

            setTimeout(function() {{
                clearInterval(interval);
                window.removeEventListener('resize', resize);
                canvas.remove();
            }}, 2800);
        }})();
    " />
    """
    st.markdown(matrix_html, unsafe_allow_html=True)
    time.sleep(3.0)


def render_countdown_timer(deadline, timer_key):
    remaining = max(0, int(deadline - time.time()))
    deadline_ms = int(deadline * 1000)
    safe_key = "".join(ch if ch.isalnum() else "_" for ch in str(timer_key))
    timer_html = f"""
    <div style="
        background:#08331f;
        border:1px solid #d5b03a;
        border-radius:8px;
        padding:10px 12px;
        min-height:74px;
        display:flex;
        flex-direction:column;
        justify-content:center;
    ">
        <div style="font-size:14px;color:#e7dcae;margin-bottom:4px;">Tyd oor</div>
        <div id="timer-{safe_key}" style="font-size:32px;font-weight:700;color:#f2cf4a;font-family:monospace;">
            {remaining}s
        </div>
    </div>
    <script>
        const deadline{safe_key} = {deadline_ms};
        const timer{safe_key} = document.getElementById("timer-{safe_key}");
        function updateTimer{safe_key}() {{
            const remaining = Math.max(0, Math.ceil((deadline{safe_key} - Date.now()) / 1000));
            timer{safe_key}.textContent = remaining + "s";
            if (remaining <= 5) {{
                timer{safe_key}.style.color = "#c7252e";
            }}
            if (remaining <= 0) {{
                timer{safe_key}.textContent = "Tyd is om";
            }}
        }}
        updateTimer{safe_key}();
        setInterval(updateTimer{safe_key}, 250);
    </script>
    """
    st.components.v1.html(timer_html, height=92)


def reading_preview_seconds(level):
    return READING_PREVIEW_SECONDS_BY_LEVEL.get(int(level), 20)


def is_early_reading_question(question):
    return bool(question.get("passage")) and int(question.get("level", 1)) <= READING_UNTIMED_LEVELS


def should_hide_passage_after_preview(question):
    return bool(question.get("passage")) and int(question.get("level", 1)) > READING_UNTIMED_LEVELS


def start_reading_preview_if_needed(user_id, subject, topic, question):
    key = f"reading_preview_{user_id}_{subject}_{topic}_{question['id']}"
    active = st.session_state.get(key)
    if active and active.get("question_id") == question["id"]:
        return active
    preview = {
        "question_id": question["id"],
        "started_at": time.time(),
        "deadline": time.time() + reading_preview_seconds(question["level"]),
    }
    st.session_state[key] = preview
    return preview


def clear_reading_preview(user_id, subject, topic, question):
    key = f"reading_preview_{user_id}_{subject}_{topic}_{question['id']}"
    st.session_state.pop(key, None)


def start_question_if_needed(user_id, subject, topic, grade, level):
    key = f"active_question_{user_id}_{subject}_{topic}"
    active = st.session_state.get(key)
    if active:
        return active
    question = choose_question(user_id, subject, topic, grade, level)
    if question is None:
        return None
    active = {
        "question": question,
        "started_at": None if should_hide_passage_after_preview(question) else time.time(),
        "deadline": None if (should_hide_passage_after_preview(question) or is_early_reading_question(question)) else time.time() + float(question["time_limit"]),
    }
    st.session_state[key] = active
    return active


def restart_active_question(user_id, subject, topic, question):
    key = f"active_question_{user_id}_{subject}_{topic}"
    st.session_state[key] = {
        "question": question,
        "started_at": None if should_hide_passage_after_preview(question) else time.time(),
        "deadline": None if (should_hide_passage_after_preview(question) or is_early_reading_question(question)) else time.time() + float(question["time_limit"]),
    }


def start_answer_phase(user_id, subject, topic, active):
    key = f"active_question_{user_id}_{subject}_{topic}"
    active["started_at"] = time.time()
    active["deadline"] = None if is_early_reading_question(active["question"]) else time.time() + float(active["question"]["time_limit"])
    st.session_state[key] = active
    clear_reading_preview(user_id, subject, topic, active["question"])


def clear_active_question(user_id, subject, topic):
    key = f"active_question_{user_id}_{subject}_{topic}"
    st.session_state.pop(key, None)


def record_attempt(user_id, question, answer, elapsed, timed_out):
    correct = (not timed_out) and is_correct(question, answer)
    points = int(question["points"]) if correct else (-INCORRECT_HINT_PENALTY if not timed_out else 0)
    with get_conn() as conn:
        ensure_progress(conn, user_id, question["subject"], question["topic"], question["grade"])
        progress = conn.execute(
            """
            SELECT * FROM subject_progress
            WHERE user_id = ? AND subject = ? AND topic = ?
            """,
            (user_id, question["subject"], question["topic"]),
        ).fetchone()
        new_correct_count = int(progress["correct_count"]) + int(correct)
        new_attempt_count = int(progress["attempt_count"]) + 1
        new_score = int(progress["score"]) + points
        new_streak = int(progress["current_streak"]) + 1 if correct else 0
        new_best_streak = max(int(progress["best_streak"]), new_streak)
        new_level = int(progress["level"])
        correct_at_current_level = (
            conn.execute(
                """
                SELECT COUNT(*)
                FROM attempts
                WHERE user_id = ?
                  AND subject = ?
                  AND topic = ?
                  AND level = ?
                  AND correct = 1
                """,
                (user_id, question["subject"], question["topic"], new_level),
            ).fetchone()[0]
            + int(correct)
        )
        if (
            correct
            and correct_at_current_level >= QUESTIONS_PER_LEVEL
            and new_level < max_level_for(question["subject"], question["topic"], question["grade"])
        ):
            new_level += 1

        conn.execute(
            """
            INSERT INTO attempts
                (user_id, subject, topic, grade, level, question_id, question, answer_given,
                 correct_answer, correct, timed_out, time_taken, points_awarded, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                question["subject"],
                question["topic"],
                int(question["grade"]),
                int(progress["level"]),
                question["id"],
                question["prompt"],
                str(answer or ""),
                question["answer"],
                int(correct),
                int(timed_out),
                float(elapsed),
                points,
                now_iso(),
            ),
        )
        conn.execute(
            """
            UPDATE subject_progress
            SET level = ?, score = ?, correct_count = ?, attempt_count = ?,
                current_streak = ?, best_streak = ?, last_seen_at = ?
            WHERE user_id = ? AND subject = ? AND topic = ?
            """,
            (
                new_level,
                new_score,
                new_correct_count,
                new_attempt_count,
                new_streak,
                new_best_streak,
                now_iso(),
                user_id,
                question["subject"],
                question["topic"],
            ),
        )
    return correct, points, new_level


def week_bounds():
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


def leaderboard_query(scope="weekly", subject=None, grade=None):
    start, end = week_bounds()
    params = [start.isoformat(), end.isoformat()]
    attempt_subject_filter = ""
    progress_subject_filter = ""
    if subject:
        attempt_subject_filter = "AND subject = ?"
        progress_subject_filter = "WHERE subject = ?"
        params.append(subject)
    progress_params = [subject] if subject else []
    user_grade_filter = ""
    user_params = []
    if grade is not None:
        user_grade_filter = "WHERE u.grade = ?"
        user_params.append(int(grade))
    with get_conn() as conn:
        return conn.execute(
            f"""
            WITH attempt_stats AS (
                SELECT
                    user_id,
                    SUM(points_awarded) AS score,
                    ROUND(100.0 * SUM(correct) / NULLIF(COUNT(id), 0), 1) AS accuracy,
                    SUM(CASE WHEN correct = 1 THEN 1 ELSE 0 END) AS correct_answers,
                    COUNT(id) AS attempts
                FROM attempts
                WHERE created_at >= ? AND created_at < ? {attempt_subject_filter}
                GROUP BY user_id
            ),
            game_bonus_stats AS (
                SELECT user_id, SUM(bonus_awarded) AS bonus
                FROM game_scores
                WHERE created_at >= ? AND created_at < ?
                GROUP BY user_id
            ),
            progress_stats AS (
                SELECT user_id, MAX(level) AS level
                FROM subject_progress
                {progress_subject_filter}
                GROUP BY user_id
            )
            SELECT
                u.id,
                u.avatar,
                u.name,
                u.grade,
                COALESCE(a.score, 0) + COALESCE(g.bonus, 0) AS score,
                COALESCE(a.accuracy, 0) AS accuracy,
                COALESCE(p.level, 1) AS level,
                COALESCE(a.correct_answers, 0) AS correct_answers,
                COALESCE(a.attempts, 0) AS attempts
            FROM users u
            LEFT JOIN attempt_stats a ON a.user_id = u.id
            LEFT JOIN game_bonus_stats g ON g.user_id = u.id
            LEFT JOIN progress_stats p ON p.user_id = u.id
            {user_grade_filter}
            ORDER BY score DESC, accuracy DESC, correct_answers DESC, name ASC
            LIMIT 10
            """,
            params + [start.isoformat(), end.isoformat()] + progress_params + user_params,
        ).fetchall()


def improvement_leaderboard(grade=None):
    start, end = week_bounds()
    previous_start = start - timedelta(days=7)
    user_grade_filter = ""
    user_params = []
    if grade is not None:
        user_grade_filter = "WHERE u.grade = ?"
        user_params.append(int(grade))
    with get_conn() as conn:
        return conn.execute(
            f"""
            WITH current_week AS (
                SELECT user_id, SUM(points_awarded) AS score
                FROM attempts
                WHERE created_at >= ? AND created_at < ?
                GROUP BY user_id
            ),
            previous_week AS (
                SELECT user_id, SUM(points_awarded) AS score
                FROM attempts
                WHERE created_at >= ? AND created_at < ?
                GROUP BY user_id
            )
            SELECT
                u.avatar,
                u.name,
                u.grade,
                COALESCE(c.score, 0) AS this_week,
                COALESCE(p.score, 0) AS last_week,
                COALESCE(c.score, 0) - COALESCE(p.score, 0) AS improvement
            FROM users u
            LEFT JOIN current_week c ON c.user_id = u.id
            LEFT JOIN previous_week p ON p.user_id = u.id
            {user_grade_filter}
            ORDER BY improvement DESC, this_week DESC, name ASC
            LIMIT 10
            """,
            (
                start.isoformat(),
                end.isoformat(),
                previous_start.isoformat(),
                start.isoformat(),
                *user_params,
            ),
        ).fetchall()


def accuracy_leaderboard(min_attempts=3, grade=None):
    start, end = week_bounds()
    user_grade_filter = ""
    user_params = []
    if grade is not None:
        user_grade_filter = "WHERE u.grade = ?"
        user_params.append(int(grade))
    with get_conn() as conn:
        return conn.execute(
            f"""
            WITH attempt_stats AS (
                SELECT
                    user_id,
                    SUM(points_awarded) AS score,
                    ROUND(100.0 * SUM(correct) / COUNT(id), 1) AS accuracy,
                    COUNT(id) AS attempts
                FROM attempts
                WHERE created_at >= ? AND created_at < ?
                GROUP BY user_id
                HAVING COUNT(id) >= ?
            ),
            progress_stats AS (
                SELECT user_id, MAX(level) AS level
                FROM subject_progress
                GROUP BY user_id
            )
            SELECT
                u.avatar,
                u.name,
                u.grade,
                a.score,
                a.accuracy,
                COALESCE(p.level, 1) AS level,
                a.attempts
            FROM attempt_stats a
            JOIN users u ON u.id = a.user_id
            LEFT JOIN progress_stats p ON p.user_id = u.id
            {user_grade_filter}
            ORDER BY accuracy DESC, score DESC, attempts DESC, name ASC
            LIMIT 10
            """,
            (start.isoformat(), end.isoformat(), min_attempts, *user_params),
        ).fetchall()


def language_leaderboard(grade=None):
    start, end = week_bounds()
    user_grade_filter = ""
    user_params = []
    if grade is not None:
        user_grade_filter = "WHERE u.grade = ?"
        user_params.append(int(grade))
    with get_conn() as conn:
        return conn.execute(
            f"""
            WITH attempt_stats AS (
                SELECT
                    user_id,
                    SUM(points_awarded) AS score,
                    ROUND(100.0 * SUM(correct) / NULLIF(COUNT(id), 0), 1) AS accuracy,
                    COUNT(id) AS attempts
                FROM attempts
                WHERE created_at >= ? AND created_at < ?
                  AND subject IN ('Afrikaans', 'Engels')
                GROUP BY user_id
            ),
            progress_stats AS (
                SELECT user_id, MAX(level) AS level
                FROM subject_progress
                WHERE subject IN ('Afrikaans', 'Engels')
                GROUP BY user_id
            )
            SELECT
                u.avatar,
                u.name,
                u.grade,
                COALESCE(a.score, 0) AS score,
                COALESCE(a.accuracy, 0) AS accuracy,
                COALESCE(p.level, 1) AS level,
                COALESCE(a.attempts, 0) AS attempts
            FROM users u
            LEFT JOIN attempt_stats a ON a.user_id = u.id
            LEFT JOIN progress_stats p ON p.user_id = u.id
            {user_grade_filter}
            ORDER BY score DESC, accuracy DESC, attempts DESC, name ASC
            LIMIT 10
            """,
            (start.isoformat(), end.isoformat(), *user_params),
        ).fetchall()


def refresh_leaderboard_snapshots():
    start, end = week_bounds()
    rows = leaderboard_query("weekly")
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM leaderboard_snapshots WHERE period_start = ? AND period_end = ?",
            (start.isoformat(), end.isoformat()),
        )
        for row in rows:
            conn.execute(
                """
                INSERT INTO leaderboard_snapshots
                    (scope, scope_value, user_id, score, accuracy, level, improvement, period_start, period_end, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "weekly",
                    "all",
                    row["id"],
                    int(row["score"]),
                    float(row["accuracy"]),
                    int(row["level"]),
                    0,
                    start.isoformat(),
                    end.isoformat(),
                    now_iso(),
                ),
            )


def rows_to_dataframe(rows):
    return pd.DataFrame([dict(row) for row in rows])


def today_bounds():
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def tetris_daily_bonus_used(user_id):
    start, end = today_bounds()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(bonus_awarded), 0) AS bonus
            FROM game_scores
            WHERE user_id = ? AND game = 'tetris' AND created_at >= ? AND created_at < ?
            """,
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchone()
    return int(row["bonus"] or 0)


def record_tetris_score(user_id, grade, score):
    score = int(score or 0)
    if score <= 0:
        return {"saved": False, "bonus": 0, "message": "Geen telling om te stoor nie."}

    with get_conn() as conn:
        personal_best_before = conn.execute(
            "SELECT COALESCE(MAX(score), 0) AS best FROM game_scores WHERE user_id = ? AND game = 'tetris'",
            (user_id,),
        ).fetchone()["best"]
        grade_best_before = conn.execute(
            "SELECT COALESCE(MAX(score), 0) AS best FROM game_scores WHERE game = 'tetris' AND grade = ?",
            (grade,),
        ).fetchone()["best"]
        school_best_before = conn.execute(
            "SELECT COALESCE(MAX(score), 0) AS best FROM game_scores WHERE game = 'tetris'",
        ).fetchone()["best"]

        personal_best = score > int(personal_best_before or 0)
        grade_best = score > int(grade_best_before or 0)
        school_best = score > int(school_best_before or 0)

        raw_bonus = 0
        if personal_best:
            raw_bonus += TETRIS_PERSONAL_BEST_BONUS
        if grade_best:
            raw_bonus += TETRIS_GRADE_BEST_BONUS
        if school_best:
            raw_bonus += TETRIS_SCHOOL_BEST_BONUS

        used_today = tetris_daily_bonus_used(user_id)
        bonus = max(0, min(raw_bonus, TETRIS_DAILY_BONUS_CAP - used_today))

        conn.execute(
            """
            INSERT INTO game_scores
                (user_id, game, grade, score, bonus_awarded, personal_best, grade_best, school_best, created_at)
            VALUES (?, 'tetris', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                int(grade),
                score,
                bonus,
                int(personal_best),
                int(grade_best),
                int(school_best),
                now_iso(),
            ),
        )

    messages = []
    if personal_best:
        messages.append("nuwe persoonlike beste")
    if grade_best:
        messages.append("nuwe graad rekord")
    if school_best:
        messages.append("nuwe skool rekord")
    if bonus:
        messages.append(f"+{bonus} bonuspunte")
    message = ", ".join(messages) if messages else "telling gestoor"
    return {"saved": True, "bonus": bonus, "message": message}


def tetris_leaderboard(grade=None):
    params = []
    grade_filter = ""
    if grade is not None:
        grade_filter = "WHERE gs.grade = ?"
        params.append(int(grade))
    with get_conn() as conn:
        return conn.execute(
            f"""
            SELECT u.avatar, u.name, gs.grade, MAX(gs.score) AS score, COALESCE(SUM(gs.bonus_awarded), 0) AS bonus
            FROM game_scores gs
            JOIN users u ON u.id = gs.user_id
            {grade_filter}
            GROUP BY u.id, u.avatar, u.name, gs.grade
            ORDER BY score DESC, bonus DESC, name ASC
            LIMIT 10
            """,
            params,
        ).fetchall()


def login_flow():
    st.markdown(
        f'<div class="hoof-kaart">{school_brand_html()}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(learner_intro_html(), unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["Leerder Teken In", "Nuwe Leerder", "Onderwyser"])

    with tab1:
        st.caption("Gebruik die naam en wagwoord waarmee jy geregistreer het.")
        login_user = st.text_input("Gebruikersnaam", placeholder="Byvoorbeeld: Mia van Wyk")
        login_pass = st.text_input("Wagwoord", type="password", placeholder="Jou wagwoord")
        if st.button("Teken In", type="primary", use_container_width=True):
            student = get_student_by_name(login_user)
            if student and verify_password(login_pass, get_credential("student", student["id"])):
                st.session_state.user = {
                    "id": student["id"],
                    "name": student["name"],
                    "avatar": normalize_avatar_key(student["avatar"]),
                    "grade": int(student["grade"]),
                    "role": "student",
                }
                st.rerun()
            st.error("Verkeerde besonderhede.")

    with tab2:
        st.caption("Nuwe leerders kan self begin. Onderwysers kan later name, grade en wagwoorde regmaak.")
        reg_name = st.text_input("Volle naam of gebruikersnaam", placeholder="Byvoorbeeld: Jan Botha")
        reg_pass = st.text_input("Kies 'n wagwoord", type="password", help="Gebruik iets wat jy sal onthou, maar nie jou naam alleen nie.")
        reg_pass_confirm = st.text_input("Tik wagwoord weer", type="password")
        reg_grade = st.selectbox("Graad", GRADE_OPTIONS, index=GRADE_OPTIONS.index(6), help="Kies jou huidige skoolgraad.")
        avatar_labels = {data["label"]: key for key, data in AVATAR_OPTIONS.items()}
        reg_avatar_label = st.selectbox("Kies avatar", list(avatar_labels.keys()))
        reg_avatar = avatar_labels[reg_avatar_label]
        st.markdown(
            f"{avatar_img_html(reg_avatar)} <strong>{reg_avatar_label}</strong>",
            unsafe_allow_html=True,
        )
        if st.button("Registreer Nou", type="primary", use_container_width=True):
            if not reg_name.strip() or not reg_pass:
                st.error("Naam en wagwoord is nodig.")
            elif reg_pass != reg_pass_confirm:
                st.error("Die twee wagwoorde stem nie ooreen nie.")
            elif len(reg_pass) < 4:
                st.error("Gebruik asseblief 'n wagwoord van minstens 4 karakters.")
            elif get_student_by_name(reg_name):
                st.error("Daardie naam bestaan reeds.")
            else:
                create_student(reg_name, reg_pass, reg_avatar, reg_grade)
                st.success("Geregistreer. Jy kan nou inteken.")

    with tab3:
        st.caption("Onderwyser toegang is vir vraagbank, ranglyste en studentbestuur.")
        teacher_name = st.text_input("Onderwyser naam", value=DEFAULT_TEACHER_NAME)
        teacher_pass = st.text_input("Onderwyser wagwoord", type="password")
        if st.button("Onderwyser Teken In", type="primary", use_container_width=True):
            teacher = get_teacher_by_name(teacher_name)
            if teacher and verify_password(teacher_pass, get_credential("teacher", teacher["id"])):
                st.session_state.user = {
                    "id": teacher["id"],
                    "name": teacher["name"],
                    "role": "admin",
                }
                st.rerun()
            st.error("Verkeerde onderwyser besonderhede.")


def render_leaderboard(title, rows):
    st.markdown(f"### {title}")
    df = rows_to_dataframe(rows)
    if df.empty:
        st.info("Nog geen pogings hierdie week nie.")
        return
    if "avatar" in df.columns:
        df["avatar"] = df["avatar"].apply(lambda value: avatar_img_html(value, "avatar-small"))
    columns = [
        col
        for col in ["avatar", "name", "grade", "score", "accuracy", "level", "attempts", "improvement"]
        if col in df.columns
    ]
    column_labels = {
        "avatar": "Avatar",
        "name": "Naam",
        "grade": "Graad",
        "score": "Telling",
        "accuracy": "Akkuraatheid",
        "level": "Vlak",
        "attempts": "Pogings",
        "improvement": "Verbetering",
    }
    display_df = df[columns].rename(columns=column_labels)
    st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)


def render_tetris_component():
    game_html = """
    <div style="background:#08331f;border:1px solid #d5b03a;border-radius:10px;padding:14px;color:#fff8df;font-family:system-ui;">
      <div style="display:flex;gap:16px;align-items:flex-start;justify-content:center;flex-wrap:wrap;">
        <canvas id="tetris-board" width="200" height="400" style="background:#052719;border:2px solid #f2cf4a;border-radius:6px;"></canvas>
        <div style="min-width:190px;">
          <div style="font-size:13px;color:#e7dcae;">Tetris Score</div>
          <div id="score" style="font-size:38px;font-weight:800;color:#f2cf4a;margin-bottom:10px;">0</div>
          <button id="startBtn" type="button" style="width:100%;padding:10px;border:0;border-radius:6px;background:#f2cf4a;color:#06351f;font-weight:800;cursor:pointer;">START</button>
          <button id="submitBtn" type="button" style="width:100%;padding:10px;border:1px solid #d5b03a;border-radius:6px;background:#0f5734;color:#fff8df;font-weight:700;margin-top:8px;cursor:pointer;">STOOR TELLING</button>
          <form id="scoreForm" method="GET" target="_parent" style="display:none;">
            <input id="scoreInput" name="tetris_score" value="0" />
            <input id="scoreNonceInput" name="tetris_score_nonce" value="0" />
          </form>
          <div style="display:grid;grid-template-columns:repeat(3,52px);gap:6px;margin-top:14px;justify-content:center;">
            <button type="button" data-action="left">&larr;</button><button type="button" data-action="rotate">&#8635;</button><button type="button" data-action="right">&rarr;</button>
            <button type="button" data-action="down" style="grid-column:1 / span 3;">&darr;</button>
          </div>
          <div style="font-size:12px;color:#e7dcae;margin-top:12px;line-height:1.35;">Keyboard: &larr; &rarr; move, &uarr; rotate, &darr; soft drop. Mobile buttons work too.</div>
          <div id="status" style="font-size:13px;color:#f2cf4a;margin-top:10px;"></div>
        </div>
      </div>
    </div>
    <style>
      button[data-action] { padding:10px;border:1px solid #d5b03a;border-radius:6px;background:#0f5734;color:#fff8df;font-weight:800;cursor:pointer; }
      button[data-action]:active, #startBtn:active, #submitBtn:active { transform: translateY(1px); }
    </style>
    <script>
    const canvas = document.getElementById('tetris-board');
    const ctx = canvas.getContext('2d');
    const scoreEl = document.getElementById('score');
    const statusEl = document.getElementById('status');
    const COLS = 10, ROWS = 20, BLOCK = 20;
    const START_DROP_INTERVAL = 850;
    const MIN_DROP_INTERVAL = 140;
    const SPEED_UP_PER_LINE = 45;
    const colors = [null, '#f2cf4a', '#007a3d', '#fff8df', '#c7252e', '#d5b03a', '#0f5734', '#e34b52'];
    const pieces = {
      T: [[0,1,0],[1,1,1],[0,0,0]],
      O: [[2,2],[2,2]],
      L: [[0,0,3],[3,3,3],[0,0,0]],
      J: [[4,0,0],[4,4,4],[0,0,0]],
      I: [[0,0,0,0],[5,5,5,5],[0,0,0,0],[0,0,0,0]],
      S: [[0,6,6],[6,6,0],[0,0,0]],
      Z: [[7,7,0],[0,7,7],[0,0,0]]
    };
    let board, player, score, dropCounter, dropInterval, lastTime, running, gameOver;

    function resetBoard() { board = Array.from({length: ROWS}, () => Array(COLS).fill(0)); }
    function randomPiece() {
      const keys = Object.keys(pieces);
      const matrix = pieces[keys[Math.floor(Math.random() * keys.length)]].map(r => r.slice());
      return { matrix, x: Math.floor(COLS / 2) - Math.ceil(matrix[0].length / 2), y: 0 };
    }
    function collide() {
      const m = player.matrix;
      for (let y=0; y<m.length; y++) for (let x=0; x<m[y].length; x++) {
        if (m[y][x] && (board[y + player.y] && board[y + player.y][x + player.x]) !== 0) return true;
      }
      return false;
    }
    function merge() {
      player.matrix.forEach((row, y) => row.forEach((value, x) => {
        if (value) board[y + player.y][x + player.x] = value;
      }));
    }
    function rotate(matrix) {
      for (let y=0; y<matrix.length; y++) for (let x=0; x<y; x++) [matrix[x][y], matrix[y][x]] = [matrix[y][x], matrix[x][y]];
      matrix.forEach(row => row.reverse());
    }
    function sweep() {
      let lines = 0;
      outer: for (let y=ROWS-1; y>=0; y--) {
        for (let x=0; x<COLS; x++) if (!board[y][x]) continue outer;
        board.splice(y, 1);
        board.unshift(Array(COLS).fill(0));
        lines++; y++;
      }
      if (lines) {
        score += [0, 100, 300, 500, 800][lines] || lines * 250;
        dropInterval = Math.max(MIN_DROP_INTERVAL, dropInterval - lines * SPEED_UP_PER_LINE);
        statusEl.textContent = lines === 1
          ? 'Mooi. Die volgende blok val vinniger.'
          : `Mooi. ${lines} lyne skoon. Die spel raak vinniger.`;
      }
    }
    function playerDrop() {
      player.y++;
      if (collide()) {
        player.y--;
        merge();
        sweep();
        player = randomPiece();
        if (collide()) {
          running = false; gameOver = true;
          statusEl.textContent = 'Game over. Stoor jou telling.';
        }
      }
      dropCounter = 0;
    }
    function move(dir) { player.x += dir; if (collide()) player.x -= dir; }
    function playerRotate() {
      const oldX = player.x;
      rotate(player.matrix);
      let offset = 1;
      while (collide()) {
        player.x += offset;
        offset = -(offset + (offset > 0 ? 1 : -1));
        if (Math.abs(offset) > player.matrix[0].length) { rotate(player.matrix); rotate(player.matrix); rotate(player.matrix); player.x = oldX; return; }
      }
    }
    function drawMatrix(matrix, offset) {
      matrix.forEach((row, y) => row.forEach((value, x) => {
        if (value) {
          ctx.fillStyle = colors[value];
          ctx.fillRect((x + offset.x) * BLOCK, (y + offset.y) * BLOCK, BLOCK - 1, BLOCK - 1);
        }
      }));
    }
    function draw() {
      ctx.fillStyle = '#052719'; ctx.fillRect(0,0,canvas.width,canvas.height);
      drawMatrix(board, {x:0,y:0});
      if (player) drawMatrix(player.matrix, player);
      scoreEl.textContent = score;
    }
    function update(time=0) {
      const delta = time - lastTime; lastTime = time; dropCounter += delta;
      if (dropCounter > dropInterval && running) playerDrop();
      draw();
      if (running) requestAnimationFrame(update);
    }
    function startGame() {
      resetBoard(); player = randomPiece(); score = 0; dropCounter = 0; dropInterval = START_DROP_INTERVAL; lastTime = 0; running = true; gameOver = false;
      statusEl.textContent = '';
      update();
    }
    function submitScore() {
      if (!score || score <= 0) {
        statusEl.textContent = "Speel eers om 'n telling te kry.";
        return;
      }
      document.getElementById('scoreInput').value = String(score);
      const nonce = String(Date.now());
      document.getElementById('scoreNonceInput').value = nonce;
      statusEl.textContent = 'Stoor telling...';
      try {
        const params = new URLSearchParams(window.parent.location.search);
        params.set('tetris_score', String(score));
        params.set('tetris_score_nonce', nonce);
        window.parent.location.search = params.toString();
      } catch (error) {
        document.getElementById('scoreForm').submit();
      }
    }
    document.getElementById('startBtn').onclick = startGame;
    document.getElementById('submitBtn').onclick = submitScore;
    document.querySelectorAll('button[data-action]').forEach(btn => btn.onclick = () => {
      if (!running) return;
      const action = btn.dataset.action;
      if (action === 'left') move(-1);
      if (action === 'right') move(1);
      if (action === 'rotate') playerRotate();
      if (action === 'down') playerDrop();
      draw();
    });
    document.addEventListener('keydown', e => {
      if (!running) return;
      if (e.key === 'ArrowLeft') move(-1);
      else if (e.key === 'ArrowRight') move(1);
      else if (e.key === 'ArrowUp') playerRotate();
      else if (e.key === 'ArrowDown') playerDrop();
      else return;
      e.preventDefault(); draw();
    });
    resetBoard(); score = 0; player = null; draw();
    </script>
    """
    st.components.v1.html(game_html, height=470)


def tetris_page():
    user = st.session_state.user
    user_id = user["id"]
    grade = int(user.get("grade", 6))

    pending_message = st.session_state.pop("tetris_save_message", None)
    if pending_message:
        message_type, message = pending_message
        if message_type == "success":
            st.success(message)
        else:
            st.info(message)

    if "tetris_score" in st.query_params:
        submit_nonce = str(st.query_params.get("tetris_score_nonce", ""))
        already_processed = submit_nonce and st.session_state.get("last_tetris_score_nonce") == submit_nonce
        try:
            submitted_score = int(st.query_params.get("tetris_score", 0))
        except (TypeError, ValueError):
            submitted_score = 0
        if already_processed:
            result = {"saved": False, "message": "Hierdie telling is reeds verwerk."}
        else:
            result = record_tetris_score(user_id, grade, submitted_score)
            if submit_nonce:
                st.session_state.last_tetris_score_nonce = submit_nonce
        remaining_params = {
            key: value
            for key, value in st.query_params.items()
            if key not in {"tetris_score", "tetris_score_nonce"}
        }
        st.query_params.clear()
        for key, value in remaining_params.items():
            st.query_params[key] = value
        if result["saved"]:
            st.session_state.tetris_save_message = (
                "success",
                f"Tetris telling gestoor: {submitted_score}. {result['message']}.",
            )
        else:
            st.session_state.tetris_save_message = ("info", result["message"])
        st.rerun()

    st.title("Mini Game - Tetris")
    used = tetris_daily_bonus_used(user_id)
    col1, col2, col3 = st.columns(3)
    with get_conn() as conn:
        personal_best = conn.execute(
            "SELECT COALESCE(MAX(score), 0) AS best FROM game_scores WHERE user_id = ? AND game = 'tetris'",
            (user_id,),
        ).fetchone()["best"]
        grade_best = conn.execute(
            "SELECT COALESCE(MAX(score), 0) AS best FROM game_scores WHERE game = 'tetris' AND grade = ?",
            (grade,),
        ).fetchone()["best"]
    col1.metric("Persoonlike beste", int(personal_best or 0))
    col2.metric(f"Graad {grade} beste", int(grade_best or 0))
    col3.metric("Vandag se bonus cap", f"{used}/{TETRIS_DAILY_BONUS_CAP}")

    st.caption("Bonus: nuwe persoonlike beste +10, graad rekord +25, skool rekord +50. Daaglikse bonus is beperk tot 100 punte.")
    render_tetris_component()
    render_leaderboard(f"Graad {grade} Tetris ranglys", tetris_leaderboard(grade=grade))


def coding_modules_for_grade(grade):
    if grade <= 7:
        return [
            {
                "title": "Robot Avontuur",
                "goal": "Gee 'n robot maklike instruksies om by die skat uit te kom.",
                "training": [
                    ("Stap vir stap", "Kodering begin soos 'n speletjie: gee een klein opdrag op 'n slag, soos vorentoe, draai links, tel op."),
                    ("Volgorde", "Die volgorde maak saak. As die robot eers draai en dan loop, beland hy op 'n ander plek."),
                    ("Toets", "Goeie koders toets hulle plan. As die robot verkeerd loop, verander net een stap en probeer weer."),
                ],
                "code": "Missie: Help die robot by die ster kom.\n\nBegin -> vorentoe -> vorentoe -> draai regs -> vorentoe -> tel ster op",
                "challenge": "Wat moet die robot doen net voor hy die ster optel?",
                "answer": "vorentoe",
                "options": ["draai links", "vorentoe", "stop"],
            },
            {
                "title": "Skatkis Geheue",
                "goal": "Leer dat 'n program dinge kan onthou.",
                "training": [
                    ("Houers", "Dink aan 'n variable soos 'n skatkis met 'n naam op. Jy sit iets daarin en kry dit later weer."),
                    ("Naamkaartjie", "As die skatkis 'telling' genoem word, weet almal dit hou punte of tellings."),
                    ("Verander", "Die inhoud kan verander. Jy kan begin met 0 punte en later 10 punte he."),
                ],
                "code": "Skatkis: telling\nBeginwaarde: 0\nKry muntstuk: +10\nNuwe telling: 10",
                "challenge": "Wat is die nuwe telling nadat jy een 10-punt muntstuk kry?",
                "answer": "10",
                "options": ["0", "10", "telling"],
            },
            {
                "title": "Dans Loop",
                "goal": "Gebruik herhaling om minder werk te doen.",
                "training": [
                    ("Herhaal", "As jy dieselfde danspassie drie keer doen, hoef jy dit nie drie keer uit te skryf nie."),
                    ("Korter plan", "Skryf: 'herhaal 3 keer' en sit die danspassie daarbinne."),
                    ("Patrone", "Rekenaars is baie goed met patrone. Sodra jy die patroon sien, kan jy dit laat herhaal."),
                ],
                "code": "Herhaal 3 keer:\n  klap\n  spring\n\nDie dans doen: klap, spring, klap, spring, klap, spring",
                "challenge": "Hoeveel keer gebeur 'spring'?",
                "answer": "3",
                "options": ["1", "2", "3"],
            },
        ]
    modules = [
        {
            "title": "Tetris Bouplan",
            "goal": "Sien die speletjie as klein dele: bord, blok, speler, telling en tyd.",
            "training": [
                ("Bord", "Tetris speel op 'n rooster. Elke blokkie is leeg of vol, amper soos 'n Excel-blad vir 'n speletjie."),
                ("Blok", "Elke vorm bestaan uit klein blokkies. 'n L-vorm, vierkant of lang lyn is net 'n patroon op die rooster."),
                ("Speler", "Die speler beheer die aktiewe blok: links, regs, draai en vinniger af."),
            ],
            "code": "Tetris dele:\n- bord: 10 kolomme x 20 rye\n- aktiewe blok: vorm + x-posisie + y-posisie\n- telling: begin by 0\n- tyd: elke paar millisekondes val die blok",
            "challenge": "Wat is die beste manier om die Tetris-bord voor te stel?",
            "answer": "rooster",
            "options": ["rooster", "lang paragraaf", "een groot prent"],
            "activity": "Mini-missie: Teken 'n 10 x 20 rooster op papier en kleur een T-blok in. Jy het pas die eerste data-model gebou.",
        },
        {
            "title": "Beweeg Die Blok",
            "goal": "Laat die aktiewe blok reageer op speler-invoer.",
            "training": [
                ("Invoer", "Die sleutelbord of selfoonknoppies stuur 'n aksie soos links, regs, draai of af."),
                ("Posisie", "Links en regs verander die x-posisie. Af verander die y-posisie."),
                ("Toets", "Na elke beweging toets die speletjie of die blok nog binne die bord is."),
            ],
            "code": "As speler druk links:\n  skuif blok x - 1\nAs speler druk regs:\n  skuif blok x + 1\nAs speler druk af:\n  skuif blok y + 1",
            "challenge": "Watter posisie verander as die blok links of regs beweeg?",
            "answer": "x-posisie",
            "options": ["x-posisie", "telling", "bordhoogte"],
            "activity": "Speel-speel taak: Kies 'n blok op die bord en voorspel sy nuwe x-posisie nadat hy twee keer regs beweeg.",
        },
        {
            "title": "Botsing Speurder",
            "goal": "Keer dat blokke deur mure of ander blokke beweeg.",
            "training": [
                ("Botsing", "Botsing beteken die blok probeer op 'n plek wees waar hy nie mag wees nie."),
                ("Mure", "As x kleiner as 0 of buite die bord is, tref die blok 'n muur."),
                ("Vaste blokke", "As die aktiewe blok aan 'n bestaande blok raak, moet hy stop en deel van die bord word."),
            ],
            "code": "Probeer skuif\nAs nuwe plek bots:\n  skuif terug\nAnders:\n  hou nuwe plek",
            "challenge": "Wat moet gebeur as 'n blok teen 'n muur bots?",
            "answer": "skuif terug",
            "options": ["skuif terug", "kry 1000 punte", "verwyder die bord"],
            "activity": "Debug-missie: Vind een skuif wat onwettig is en verduidelik hoekom die spel dit moet blokkeer.",
        },
    ]
    if grade >= 9:
        modules.extend([
            {
                "title": "Volle Lyn = Punte",
                "goal": "Maak vol rye skoon en gee punte wanneer die speler slim bou.",
                "training": [
                    ("Ry lees", "Die program kyk deur elke ry en vra: is elke blokkie vol?"),
                    ("Skoonmaak", "Wanneer 'n ry vol is, word hy uitgevee en 'n nuwe leë ry kom bo in."),
                    ("Beloning", "Die speler kry punte. Meer lyne op een slag gee 'n groter beloning."),
                ],
                "code": "Vir elke ry in bord:\n  as al die blokkies vol is:\n    verwyder ry\n    sit leë ry bo\n    tel punte by",
                "challenge": "Wanneer moet Tetris punte bytel?",
                "answer": "as 'n ry vol is",
                "options": ["as 'n ry vol is", "as die speler wag", "as die bord leeg is"],
                "activity": "Punt-missie: Bou 'n ry met net een oop blokkie. Watter blok sal die lyn voltooi?",
            },
            {
                "title": "Spoed Wat Groei",
                "goal": "Maak die spel opwindender deur blokke vinniger te laat val wanneer lyne voltooi word.",
                "training": [
                    ("Valtyd", "Die game loop wag 'n kort tyd voordat die blok een stap af beweeg."),
                    ("Vinniger", "As 'n lyn skoon is, maak ons die wagtyd kleiner. Kleiner tyd beteken vinniger spel."),
                    ("Limiet", "Daar moet 'n minimum wagtyd wees sodat die spel moeilik maar nog speelbaar bly."),
                ],
                "code": "As lyne_skoon > 0:\n  telling = telling + punte\n  valtyd = valtyd - 45\n  as valtyd < 140:\n    valtyd = 140",
                "challenge": "Wat gebeur as die valtyd kleiner word?",
                "answer": "die blok val vinniger",
                "options": ["die blok val vinniger", "die telling word nul", "die bord verdwyn"],
                "activity": "Tempo-toets: Begin met 850 ms. Na twee lyne, hoeveel vinniger voel die spel as elke lyn 45 ms aftrek?",
            },
        ])
    if grade >= 10:
        modules.extend([
            {
                "title": "Game Loop",
                "goal": "Bou die hartklop van die spel: update, teken, herhaal.",
                "training": [
                    ("Update", "Update verander die spel: blok val, botsing word getoets, lyne word skoongemaak."),
                    ("Teken", "Draw wys die nuwe toestand op die skerm."),
                    ("Herhaal", "Die loop hardloop weer en weer totdat die game over is."),
                ],
                "code": "Terwyl spel loop:\n  meet tyd sedert laaste raam\n  as genoeg tyd verby is:\n    laat blok val\n  teken bord en blok",
                "challenge": "Wat is die game loop se werk?",
                "answer": "update en teken herhaal",
                "options": ["update en teken herhaal", "net wag", "net die naam wys"],
                "activity": "Loop-lab: Sit drie kaartjies in volgorde: Update, Draw, Repeat. Skuif hulle tot die spelvloei sin maak.",
            },
            {
                "title": "Funksies Vir Elke Taak",
                "goal": "Breek die Tetris-kode in klein funksies wat maklik is om te toets.",
                "training": [
                    ("Klein take", "Een funksie moet een duidelike werk doen, soos rotate, collide, sweep of draw."),
                    ("Herbruikbaar", "Dieselfde funksie kan elke keer gebruik word wanneer 'n blok beweeg."),
                    ("Minder chaos", "Klein funksies maak foute makliker om te vind."),
                ],
                "code": "funksies:\n- move(direction)\n- rotate(block)\n- collide(block, board)\n- sweepLines(board)\n- draw(board, block)",
                "challenge": "Watter funksie toets of 'n blok teen iets raak?",
                "answer": "collide",
                "options": ["collide", "draw", "score"],
                "activity": "Naam-uitdaging: Kies goeie funksiename vir links skuif, draai en lyn skoonmaak.",
            },
        ])
    if grade >= 11:
        modules.extend([
            {
                "title": "Data-Strukture Vir Vorms",
                "goal": "Stoor elke Tetris-vorm as data wat Python, Java of JavaScript kan lees.",
                "training": [
                    ("Matrix", "'n Vorm kan 'n klein 2D-lys wees: 0 beteken leeg, 1 beteken vol."),
                    ("Rotasie", "Om 'n blok te draai, verander jy die matrix se rye en kolomme."),
                    ("Tale", "Python gebruik lyste, Java gebruik arrays of lyste, JavaScript gebruik arrays. Die idee bly dieselfde."),
                ],
                "code": "T-vorm as data:\n0 1 0\n1 1 1\n0 0 0\n\nPython: [[0,1,0],[1,1,1],[0,0,0]]",
                "challenge": "Wat beteken 0 in die vorm-matrix?",
                "answer": "leeg",
                "options": ["leeg", "vol", "game over"],
                "activity": "Matrix-missie: Ontwerp jou eie 3 x 3 vorm met 0's en 1's en voorspel hoe dit sal lyk.",
            },
            {
                "title": "Debug Soos 'n Game Dev",
                "goal": "Gebruik klein toetse om Tetris-foute vinnig op te spoor.",
                "training": [
                    ("Reproduce", "Kry 'n fout wat jy weer kan laat gebeur. Dan kan jy hom regtig regmaak."),
                    ("Log", "Wys x, y, telling of valtyd terwyl jy toets."),
                    ("Een verandering", "Maak net een verandering op 'n slag, anders weet jy nie wat die fout reggemaak het nie."),
                ],
                "code": "Debug plan:\n1. Speel tot die fout gebeur\n2. Skryf neer wat jy gedoen het\n3. Wys x, y en valtyd\n4. Verander een ding\n5. Toets weer",
                "challenge": "Wat is die veiligste manier om 'n fout reg te maak?",
                "answer": "een verandering op 'n slag",
                "options": ["een verandering op 'n slag", "alles gelyk verander", "die fout ignoreer"],
                "activity": "Fout-speurder: As 'n blok deur die vloer val, watter twee waardes sal jy eerste log?",
            },
        ])
    if grade >= 12:
        modules.extend([
            {
                "title": "Stoor Telling En Ranglys",
                "goal": "Koppel die speletjie aan die app sodat tellings gestoor en vergelyk kan word.",
                "training": [
                    ("Submit", "Die speletjie stuur die telling na die hoof app wanneer die speler Stoor Telling druk."),
                    ("Databasis", "Die app stoor user_id, graad, telling, bonus en tyd in 'n tabel."),
                    ("Ranglys", "Die scoreboard vra die databasis vir die beste tellings en sorteer dit van hoog na laag."),
                ],
                "code": "Wanneer speler stoor:\n  stuur score na app\n  app skryf score in databasis\n  ranglys lees beste score per leerder\n  wys hoogste tellings eerste",
                "challenge": "Waar moet die Tetris-telling bly sodat die ranglys dit later kan wys?",
                "answer": "databasis",
                "options": ["databasis", "net op die skerm", "in die speler se kop"],
                "activity": "Produk-missie: Besluit watter velde jy in 'n game_scores tabel nodig het vir 'n skoolranglys.",
            },
            {
                "title": "Maak Dit Jou Eie",
                "goal": "Ontwerp 'n uitbreiding wat die Tetris-spel meer Hoërskool Florida laat voel.",
                "training": [
                    ("Tema", "Kleure, klanke en boodskappe kan die spel soos die skool se handelsmerk laat voel."),
                    ("Balans", "Bonusreëls moet motiverend wees sonder om akademiese punte onregverdig te maak."),
                    ("Verbeter", "Goeie ontwikkelaars kyk hoe mense speel en verbeter dan die ervaring."),
                ],
                "code": "Uitbreidingsidees:\n- Hoërskool Florida kleurtema\n- Graad-rekord badge\n- Moeilikheid per vlak\n- Weeklikse uitdaging\n- Veilige bonuslimiet",
                "challenge": "Waarom moet bonuspunte 'n limiet he?",
                "answer": "sodat dit regverdig bly",
                "options": ["sodat dit regverdig bly", "sodat niemand speel nie", "sodat die app stadiger is"],
                "activity": "Pitch-missie: Skryf een nuwe Tetris-feature neer en verduidelik hoe dit leerders sal motiveer.",
            },
        ])
    return modules


def coding_modules_for_grade(grade):
    return [
        {
            "title": "Betree die Kode-oerwoud",
            "goal": "Verstaan wat programmering is en skryf jou eerste program.",
            "character": "Kode-App",
            "lessons": [
                ("Missie", "Kode-App wil die rekenaar laat praat. Jou werk is om vir die rekenaar presiese instruksies te gee."),
                ("Wat is programmering?", "Programmering is 'n lys instruksies wat 'n rekenaar stap vir stap uitvoer."),
                ("Program vs toepassing", "'n Program is die kode wat werk doen. 'n Toepassing is die produk wat mense gebruik."),
                ("Sintaksis", "Sintaksis is die reels van kode: hakies, aanhalingstekens, kommapunte en inkeping."),
            ],
            "python_code": 'print("Hallo, programmeerder!")',
            "java_code": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hallo, programmeerder!");\n    }\n}',
            "challenge": "Wat doen print()?",
            "answer": "Dit wys inligting",
            "options": ["Dit vee 'n program uit", "Dit wys inligting", "Dit skakel die rekenaar aan", "Dit skep 'n wagwoord"],
            "explanation": "print() wys teks of inligting op die skerm.",
            "activity": "Skryf 'n program wat drie reels oor jouself vertoon.",
            "victory": "Uitstekend. Jy het pas 'n rekenaar instruksies gegee. Volgende leer jy hoe om inligting te onthou.",
        },
        {
            "title": "Die Veranderlike-kluis",
            "goal": "Leer hoe rekenaars inligting bere.",
            "character": "Veranderlike-kluisbewaarder",
            "lessons": [
                ("Missie", "Jy moet 'n speler se naam, telling en vlak onthou."),
                ("Veranderlike", "'n Veranderlike is 'n naam vir 'n stukkie inligting."),
                ("Verander", "Die waarde kan later verander, soos telling wat groter word."),
                ("Python vs Java", "Python raai die tipe makliker. Java vra dat jy die tipe duidelik noem."),
            ],
            "python_code": 'naam = "Mia"\ntelling = 95\nprint(naam)\nprint(telling)',
            "java_code": 'String naam = "Mia";\nint telling = 95;\nSystem.out.println(naam);\nSystem.out.println(telling);',
            "challenge": "Watter kode bere die getal 42?",
            "answer": "telling = 42",
            "options": ["42 = telling", "telling = 42", "bere telling 42", "getal(telling)"],
            "explanation": "Die veranderlike se naam kom links en die waarde kom regs.",
            "activity": "Skep veranderlikes vir 'n speler se naam, telling en vlak.",
            "victory": "Mooi. Jou kode kan nou onthou. Volgende kyk ons watter tipe data in die kluis kan wees.",
        },
        {
            "title": "Die Dieretuin van Datatipes",
            "goal": "Identifiseer teks, heelgetalle, desimale getalle en waar/onwaar-waardes.",
            "character": "Kode-App",
            "lessons": [
                ("String", "Teks soos \"Hallo\" word 'n string genoem."),
                ("Integer", "Heelgetalle soos 25 word vir tel gebruik."),
                ("Double/float", "Desimale getalle soos 3.14 hou breuke."),
                ("Boolean", "True of False help programme besluit."),
            ],
            "python_code": 'naam = "Alex"\nouderdom = 15\nlengte = 1.72\nhet_huisdier = True\n\nprint(naam)\nprint(ouderdom)\nprint(lengte)\nprint(het_huisdier)',
            "java_code": 'String naam = "Alex";\nint ouderdom = 15;\ndouble lengte = 1.72;\nboolean hetHuisdier = true;\n\nSystem.out.println(naam);\nSystem.out.println(ouderdom);\nSystem.out.println(lengte);\nSystem.out.println(hetHuisdier);',
            "challenge": "Watter datatipe verteenwoordig False?",
            "answer": "Boolean",
            "options": ["String", "Heelgetal", "Boolean", "Desimale getal"],
            "explanation": "False is 'n boolean, want dit beteken onwaar.",
            "activity": "Skep 'n profiel vir 'n superheld met naam, ouderdom, kragvlak en isHeld.",
            "victory": "Goed gedoen. Jy ken nou die diere in die data-dieretuin.",
        },
        {
            "title": "Invoer: Praat met die Rekenaar",
            "goal": "Maak programme interaktief deur gebruiker-invoer te lees.",
            "character": "Robot Rex",
            "lessons": [
                ("Vra", "Die program kan die gebruiker 'n vraag vra."),
                ("Lees", "Invoer kom dikwels as teks in."),
                ("Omskakel", "As jy wiskunde wil doen, verander teks na 'n getal."),
                ("Gebruik", "Gebruik die invoer in 'n boodskap of berekening."),
            ],
            "python_code": 'naam = input("Wat is jou naam? ")\nprint("Welkom, " + naam + "!")',
            "java_code": 'import java.util.Scanner;\nScanner invoer = new Scanner(System.in);\nSystem.out.print("Wat is jou naam? ");\nString naam = invoer.nextLine();\nSystem.out.println("Welkom, " + naam + "!");',
            "challenge": "Waarom moet invoer soms na 'n heelgetal verander word?",
            "answer": "Invoer word dikwels as teks behandel",
            "options": ["Rekenaars hou nie van getalle nie", "Invoer word dikwels as teks behandel", "Heelgetalle verwyder alle foute", "Dit maak die skerm helderder"],
            "explanation": "input() gee gewoonlik teks terug, selfs wanneer die gebruiker 15 tik.",
            "activity": "Bou 'n program wat bereken hoe oud iemand volgende jaar sal wees.",
            "victory": "Nou praat jou program terug. Volgende gebruik ons wiskunde-magie.",
        },
        {
            "title": "Wiskunde-magie",
            "goal": "Gebruik rekenkundige operatore in programme.",
            "character": "Funksie-towenaar",
            "lessons": [
                ("Plus en minus", "Gebruik + en - vir optelling en aftrekking."),
                ("Maal en deel", "Gebruik * en / vir vermenigvuldiging en deling."),
                ("Oorblyfsel", "% gee wat oorbly nadat jy deel."),
                ("Sakrekenaar", "Kombineer invoer en operatore om 'n klein sakrekenaar te bou."),
            ],
            "python_code": "appels = 17\nvriende = 5\noorblyfsel = appels % vriende\nprint(oorblyfsel)",
            "java_code": "int appels = 17;\nint vriende = 5;\nint oorblyfsel = appels % vriende;\nSystem.out.println(oorblyfsel);",
            "challenge": "Wat is die resultaat van 17 % 5?",
            "answer": "2",
            "options": ["2", "3", "5", "15"],
            "explanation": "17 gedeel deur 5 los 2 oor.",
            "activity": "Bou 'n program wat versnaperinge gelykop tussen vriende verdeel.",
            "victory": "Knap. Jou kode kan nou somme doen sonder om moeg te word.",
        },
        {
            "title": "Die Besluitberg",
            "goal": "Gebruik if, else en elif om keuses te maak.",
            "character": "Kode-App",
            "lessons": [
                ("if", "if toets of iets waar is."),
                ("else", "else gebeur wanneer die if-toets vals is."),
                ("elif", "elif gee nog 'n moontlike pad."),
                ("Vergelyk", "Gebruik >=, <=, == en != om waardes te vergelyk."),
            ],
            "python_code": 'telling = 82\nif telling >= 50:\n    print("Jy slaag!")\nelse:\n    print("Probeer weer!")',
            "java_code": 'int telling = 82;\nif (telling >= 50) {\n    System.out.println("Jy slaag!");\n} else {\n    System.out.println("Probeer weer!");\n}',
            "challenge": "Wat gebeur wanneer die voorwaarde in 'n if-stelling vals is?",
            "answer": "Die if-blok word oorgeslaan",
            "options": ["Die rekenaar breek", "Die if-blok word oorgeslaan", "Die program herhaal vir altyd", "Die waarde verander outomaties"],
            "explanation": "Wanneer die toets vals is, loop die if-blok nie.",
            "activity": "Skep 'n program wat bepaal of 'n leerder geslaag het.",
            "victory": "Jy het die besluitberg geklim. Volgende kombineer ons voorwaardes.",
        },
        {
            "title": "Die Logika-laboratorium",
            "goal": "Kombineer voorwaardes met logiese operatore.",
            "character": "Gogga-speurder",
            "lessons": [
                ("Gelyk", "== toets of twee waardes dieselfde is."),
                ("Nie gelyk", "!= toets of waardes verskil."),
                ("and", "and beteken albei voorwaardes moet waar wees."),
                ("or/not", "or vra vir ten minste een waar; not draai waar en vals om."),
            ],
            "python_code": 'ouderdom = 16\nhet_kaartjie = True\nif ouderdom >= 13 and het_kaartjie:\n    print("Jy mag ingaan.")',
            "java_code": 'int ouderdom = 16;\nboolean hetKaartjie = true;\nif (ouderdom >= 13 && hetKaartjie) {\n    System.out.println("Jy mag ingaan.");\n}',
            "challenge": "Wat beteken and?",
            "answer": "Albei voorwaardes moet waar wees",
            "options": ["Ten minste een voorwaarde moet waar wees", "Albei voorwaardes moet waar wees", "Geen voorwaarde is belangrik nie", "Die program herhaal"],
            "explanation": "and is streng: links en regs moet waar wees.",
            "activity": "Bou 'n program wat bepaal of iemand 'n konsert mag binnegaan.",
            "victory": "Logika ontsluit. Nou kan jou program slimmer besluit.",
        },
        {
            "title": "Die Lus-strandmeer",
            "goal": "Herhaal instruksies met for-lusse.",
            "character": "Kaptein Lus",
            "lessons": [
                ("Waarom lusse?", "Lusse herhaal werk sonder dat jy dieselfde kode oor en oor skryf."),
                ("Python for", "range() help Python om deur getalle te stap."),
                ("Java for", "Java se for-lus wys begin, toets en verandering."),
                ("Tel", "Lusse is uitstekend vir aftel, optel en patrone."),
            ],
            "python_code": "for getal in range(1, 6):\n    print(getal)",
            "java_code": "for (int getal = 1; getal <= 5; getal++) {\n    System.out.println(getal);\n}",
            "challenge": "Waarom gebruik programmeerders lusse?",
            "answer": "Om instruksies doeltreffend te herhaal",
            "options": ["Om instruksies doeltreffend te herhaal", "Om veranderlikes te verwyder", "Om alle kode te stop", "Om wagwoorde te skep"],
            "explanation": "Lusse maak herhaling korter en netjieser.",
            "activity": "Skep 'n aftelprogram vir 'n vuurpylansering.",
            "victory": "Kaptein Lus salueer. Jy kan nou herhaal sonder kopieer-en-plak.",
        },
        {
            "title": "Die while-lus-dwarrel",
            "goal": "Gebruik while-lusse en voorkom oneindige lusse.",
            "character": "Kaptein Lus",
            "lessons": [
                ("while", "while loop solank 'n voorwaarde waar is."),
                ("Verander", "Verander die lusveranderlike sodat die lus kan stop."),
                ("Oneindig", "'n Oneindige lus stop nooit vanself nie."),
                ("Aftelling", "while is goed vir energie, tyd en aftellings."),
            ],
            "python_code": 'energie = 3\nwhile energie > 0:\n    print("Energie oor:", energie)\n    energie -= 1',
            "java_code": 'int energie = 3;\nwhile (energie > 0) {\n    System.out.println("Energie oor: " + energie);\n    energie--;\n}',
            "challenge": "Wat veroorsaak 'n oneindige lus?",
            "answer": "Die voorwaarde word nooit vals nie",
            "options": ["Die voorwaarde word nooit vals nie", "Die program het 'n veranderlike", "Die lus loop net een keer", "Die kode gebruik getalle"],
            "explanation": "As die voorwaarde altyd waar bly, hou die lus aan loop.",
            "activity": "Skep 'n robotbattery-simulator.",
            "victory": "Jy het uit die dwarrel ontsnap. Volgende stap ons deur lyste.",
        },
        {
            "title": "Die Lys-oerwoud",
            "goal": "Bere verskeie waardes in lyste en skikkings.",
            "character": "Kode-App",
            "lessons": [
                ("Lys", "'n Lys hou meer as een waarde."),
                ("Indeks", "Die eerste item is gewoonlik by indeks 0."),
                ("Verander", "Jy kan items byvoeg, lees en verwyder."),
                ("Java skikkings", "Java arrays hou ook meer as een waarde."),
            ],
            "python_code": 'troeteldiere = ["kat", "hond", "hamster"]\nprint(troeteldiere[0])',
            "java_code": 'String[] troeteldiere = {"kat", "hond", "hamster"};\nSystem.out.println(troeteldiere[0]);',
            "challenge": "Wat is die indeks van die eerste item in die meeste programmeertale?",
            "answer": "0",
            "options": ["0", "1", "-1", "10"],
            "explanation": "Die meeste programmeertale begin lyste by 0 tel.",
            "activity": "Skep 'n digitale skooltas met vakke of items.",
            "victory": "Jy het jou pad deur die lys-oerwoud gevind.",
        },
        {
            "title": "Die String-safari",
            "goal": "Werk met teks in kode.",
            "character": "Kode-App",
            "lessons": [
                ("Bymekaar voeg", "Strings kan saamgevoeg word om boodskappe te bou."),
                ("Hoofletters", ".upper() maak letters hoofletters."),
                ("Lengte", "len() tel hoeveel karakters in teks is."),
                ("Vergelyk", "Programme kan teks soek en vergelyk."),
            ],
            "python_code": 'woord = "programmering"\nprint(woord.upper())\nprint(len(woord))',
            "java_code": 'String woord = "programmering";\nSystem.out.println(woord.toUpperCase());\nSystem.out.println(woord.length());',
            "challenge": "Wat doen .upper()?",
            "answer": "Dit verander letters na hoofletters",
            "options": ["Dit verwyder teks", "Dit verander letters na hoofletters", "Dit tel getalle", "Dit skep 'n lus"],
            "explanation": ".upper() verander teks soos hallo na HALLO.",
            "activity": "Skep 'n program wat geheime boodskappe verander.",
            "victory": "String-safari voltooi. Jou teks kan nou truuks doen.",
        },
        {
            "title": "Die Funksie-fabriek",
            "goal": "Skep herbruikbare blokke kode.",
            "character": "Funksie-towenaar",
            "lessons": [
                ("Funksie", "'n Funksie is 'n klein kode-masjien met 'n naam."),
                ("Roep", "Jy roep die funksie wanneer jy dit wil gebruik."),
                ("Parameters", "Parameters is inligting wat jy vir die funksie gee."),
                ("return", "return stuur 'n antwoord terug."),
            ],
            "python_code": 'def aanmoediging(naam):\n    return "Komaan, " + naam + "!"\n\nboodskap = aanmoediging("Sam")\nprint(boodskap)',
            "java_code": 'static String aanmoediging(String naam) {\n    return "Komaan, " + naam + "!";\n}',
            "challenge": "Waarom is funksies nuttig?",
            "answer": "Kode kan hergebruik word",
            "options": ["Kode kan hergebruik word", "Dit maak rekenaars stadiger", "Dit verwyder veranderlikes", "Dit voorkom invoer"],
            "explanation": "Funksies keer dat jy dieselfde oplossing oor en oor hoef te skryf.",
            "activity": "Skep 'n superheldnaam-generator.",
            "victory": "Die fabriek loop. Volgende voeg ons verrassing by.",
        },
        {
            "title": "Die Ewekansigheidsreaktor",
            "goal": "Voeg verrassing en onvoorspelbaarheid by programme.",
            "character": "Robot Rex",
            "lessons": [
                ("Random getalle", "random kan 'n getal kies wat jy nie vooraf weet nie."),
                ("Kies item", "Programme kan ewekansig uit 'n lys kies."),
                ("Speletjies", "Ewekansigheid maak speletjies minder voorspelbaar."),
                ("Toets", "Random programme moet meer as een keer getoets word."),
            ],
            "python_code": 'import random\ngetal = random.randint(1, 6)\nprint("Jy het gerol:", getal)',
            "java_code": 'import java.util.Random;\nRandom r = new Random();\nint getal = r.nextInt(6) + 1;\nSystem.out.println("Jy het gerol: " + getal);',
            "challenge": "Waarom is ewekansigheid nuttig in speletjies?",
            "answer": "Dit voeg verrassing en verskeidenheid by",
            "options": ["Dit maak elke resultaat voorspelbaar", "Dit voeg verrassing en verskeidenheid by", "Dit verwyder alle keuses", "Dit stop die program"],
            "explanation": "Random laat elke speelsessie anders voel.",
            "activity": "Bou 'n digitale dobbelsteen.",
            "victory": "Die reaktor zoem. Jou programme kan nou verras.",
        },
        {
            "title": "Gogga-speurder-hoofkwartier",
            "goal": "Leer om foute te vind en reg te stel.",
            "character": "Gogga-speurder",
            "lessons": [
                ("Sintaksisfout", "Die kode breek omdat die taalreels verkeerd is."),
                ("Logikafout", "Die program loop, maar die antwoord is verkeerd."),
                ("Looptydfout", "Die program begin, maar breek terwyl dit loop."),
                ("Lees foutboodskappe", "Foutboodskappe wys dikwels waar jy moet kyk."),
            ],
            "python_code": 'ouderdom = input("Hoe oud is jy? ")\nprint(ouderdom + 1)\n\n# Reg:\nouderdom = int(input("Hoe oud is jy? "))\nprint(ouderdom + 1)',
            "java_code": 'String ouderdom = "15";\n// Reg vir wiskunde:\nint ouderdomGetal = Integer.parseInt(ouderdom);\nSystem.out.println(ouderdomGetal + 1);',
            "challenge": "Wat is 'n logikafout?",
            "answer": "Die program loop, maar gee die verkeerde resultaat",
            "options": ["Die program kan glad nie begin nie", "Die program loop, maar gee die verkeerde resultaat", "Die sleutelbord is stukkend", "'n Veranderlike word geskep"],
            "explanation": "'n Logikafout is stil gevaarlik: die kode loop, maar dink verkeerd.",
            "activity": "Herstel drie programme wat doelbewus foute bevat.",
            "victory": "Gogga gevang. Jy debug nou soos 'n regte programmeerder.",
        },
        {
            "title": "Woordeboeke en Data-kaarte",
            "goal": "Stoor verwante inligting met sleutel-waarde-pare.",
            "character": "Veranderlike-kluisbewaarder",
            "lessons": [
                ("Woordeboek", "'n Woordeboek hou waardes met etikette."),
                ("Sleutel", "Die sleutel is die etiket waarmee jy die waarde kry."),
                ("Verander", "Jy kan waardes byvoeg of opdateer."),
                ("Java Map", "Java gebruik Map vir dieselfde idee."),
            ],
            "python_code": 'speler = {"naam": "Zara", "telling": 120, "vlak": 3}\nprint(speler["telling"])',
            "java_code": 'Map<String, Integer> speler = new HashMap<>();\nspeler.put("telling", 120);\nSystem.out.println(speler.get("telling"));',
            "challenge": "Wat is 'n sleutel in 'n woordeboek?",
            "answer": "'n Etiket waarmee 'n waarde gevind word",
            "options": ["'n Etiket waarmee 'n waarde gevind word", "'n Rekenaarwagwoord", "'n Lus", "'n Getalgenerator"],
            "explanation": "Die sleutel help jou om die regte waarde vinnig te kry.",
            "activity": "Skep 'n kaart met 'n speletjiespeler se besonderhede.",
            "victory": "Data-kaart oopgesluit. Jou kode kan nou beter organiseer.",
        },
        {
            "title": "Die Stad van Objekgeorienteerde Programmering",
            "goal": "Verstaan klasse en objekte.",
            "character": "Funksie-towenaar",
            "lessons": [
                ("Objek", "'n Objek stel iets in die regte wereld of speletjie voor."),
                ("Klas", "'n Klas is die bloudruk vir objekte."),
                ("Eienskappe", "Eienskappe beskryf die objek, soos naam of energie."),
                ("Metodes", "Metodes is aksies wat die objek kan doen."),
            ],
            "python_code": 'class Robot:\n    def __init__(self, naam):\n        self.naam = naam\n    def praat(self):\n        print(self.naam, "se: piep!")\n\nrobot = Robot("Rex")\nrobot.praat()',
            "java_code": 'class Robot {\n    String naam;\n    Robot(String naam) { this.naam = naam; }\n    void praat() { System.out.println(naam + " se: piep!"); }\n}',
            "challenge": "Wat is 'n objek?",
            "answer": "'n Werklike idee wat deur kode voorgestel word",
            "options": ["'n Werklike idee wat deur kode voorgestel word", "'n Sintaksisfout", "'n Lusvoorwaarde", "'n Kommentaar"],
            "explanation": "'n Objek is kode se weergawe van iets soos 'n robot, speler of troeteldier.",
            "activity": "Skep 'n virtuele troeteldierklas.",
            "victory": "Welkom in die objekstad. Nou kan jy groter programme bou.",
        },
        {
            "title": "Speletjieskepping-berg",
            "goal": "Kombineer veranderlikes, besluite, lusse, invoer en ewekansigheid.",
            "character": "Robot Rex",
            "lessons": [
                ("Ontwerp", "Begin met 'n eenvoudige speletjie-idee."),
                ("Keuses", "Laat die speler kies wat volgende gebeur."),
                ("Gesondheid en punte", "Gebruik veranderlikes om speltoestand te hou."),
                ("Wen of verloor", "Gebruik if-stellings vir eindes."),
            ],
            "python_code": 'gesondheid = 3\nskat = False\nif gesondheid > 0 and skat:\n    print("Jy wen!")\nelse:\n    print("Verken verder.")',
            "java_code": 'int gesondheid = 3;\nboolean skat = false;\nif (gesondheid > 0 && skat) {\n    System.out.println("Jy wen!");\n}',
            "challenge": "Watter konsep help om te besluit of 'n speler gewen het?",
            "answer": "'n if-stelling",
            "options": ["'n if-stelling", "'n Kommentaar", "Net 'n string", "Net 'n klasnaam"],
            "explanation": "Wen/verloor is 'n besluit, en if is vir besluite.",
            "activity": "Bou 'n teksavontuurspeletjie.",
            "victory": "Jy is op die bergtop. Jou konsepte werk nou saam.",
        },
        {
            "title": "Die Data-speurder",
            "goal": "Gebruik kode om data te ondersoek en op te som.",
            "character": "Gogga-speurder",
            "lessons": [
                ("Tellings", "Stoor baie tellings in 'n lys."),
                ("Hoogste", "max() kan die hoogste telling vind."),
                ("Gemiddeld", "Som gedeel deur aantal gee gemiddelde."),
                ("Besluite", "Data help mense beter besluite neem."),
            ],
            "python_code": 'tellings = [72, 88, 91, 65]\ngemiddeld = sum(tellings) / len(tellings)\nprint("Gemiddeld:", gemiddeld)',
            "java_code": 'int[] tellings = {72, 88, 91, 65};\nint totaal = 0;\nfor (int t : tellings) { totaal += t; }\nSystem.out.println(totaal / tellings.length);',
            "challenge": "Waarom is data-analise nuttig?",
            "answer": "Dit help ons om patrone te ontdek en besluite te neem",
            "options": ["Dit help ons om patrone te ontdek en besluite te neem", "Dit laat data verdwyn", "Dit voorkom berekeninge", "Dit werk net met speletjies"],
            "explanation": "Data-analise verander rou getalle in insig.",
            "activity": "Ontleed klasuitslae of sportstatistiek.",
            "victory": "Data-saak opgelos. Jy kan nou patrone raaksien.",
        },
        {
            "title": "Programmeringsmissies uit die Regte Wereld",
            "goal": "Sien hoe programmering alledaagse probleme oplos.",
            "character": "Kode-App",
            "lessons": [
                ("Probleem", "Goeie programme begin met 'n werklike probleem."),
                ("Gereedskap", "Voorbeelde: wagwoordtoetser, omskakelaar, studiebeplanner of kletsbot."),
                ("Gebruiker", "Dink aan wie die program gaan gebruik."),
                ("Waarde", "Die program moet iemand help om iets makliker te doen."),
            ],
            "python_code": 'wagwoord = "Skool2026!"\nif len(wagwoord) >= 8:\n    print("Sterker wagwoord")',
            "java_code": 'String wagwoord = "Skool2026!";\nif (wagwoord.length() >= 8) {\n    System.out.println("Sterker wagwoord");\n}',
            "challenge": "Wat maak 'n program nuttig?",
            "answer": "Dit los 'n probleem vir iemand op",
            "options": ["Dit los 'n probleem vir iemand op", "Dit bevat die meeste kode", "Dit gebruik moeilike woorde", "Dit aanvaar nooit invoer nie"],
            "explanation": "Nuttige kode dien 'n menslike behoefte.",
            "activity": "Bou 'n hulpmiddel wat 'n probleem in jou eie lewe oplos.",
            "victory": "Jy dink nou soos 'n bouer, nie net soos 'n leerder nie.",
        },
        {
            "title": "Kode-App se Finale Uitdaging",
            "goal": "Beplan, bou, toets en bied 'n finale projek aan.",
            "character": "Kode-App",
            "lessons": [
                ("Kies", "Kies 'n projekidee wat jou interesseer."),
                ("Beplan", "Skryf pseudokode voordat jy begin tik."),
                ("Bou", "Maak eers 'n klein weergawe wat werk."),
                ("Bied aan", "Verduidelik die probleem, oplossing, fout en volgende verbetering."),
            ],
            "python_code": '# Finale projek plan\nprojek = "Studiebeplanner"\nprobleem = "Ek vergeet wanneer om te leer"\nprint(projek, probleem)',
            "java_code": 'String projek = "Studiebeplanner";\nString probleem = "Ek vergeet wanneer om te leer";\nSystem.out.println(projek + ": " + probleem);',
            "challenge": "Wat moet programmeerders doen wanneer hul eerste weergawe nie werk nie?",
            "answer": "Toets, ontfout en verbeter dit",
            "options": ["Gee dadelik op", "Toets, ontfout en verbeter dit", "Vee die rekenaar uit", "Blameer die sleutelbord"],
            "explanation": "Die eerste weergawe is net die begin. Verbetering is deel van programmering.",
            "activity": "Kies een finale projek en verduidelik watter probleem dit oplos.",
            "victory": "Finale missie ontsluit. Jy is gereed om jou eie projek te bou en te wys.",
        },
    ]


def render_coding_module(module, index):
    lessons = module.get("lessons") or module.get("training", [])
    st.markdown(
        f"""
        <div class="coding-hero">
            <h2>Module {index}: {html.escape(module["title"])}</h2>
            <p>{html.escape(module["goal"])}</p>
            <p><strong>{html.escape(module.get("character", "Kode-App"))}</strong> lei hierdie missie.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for lesson_index in range(0, len(lessons), 3):
        cols = st.columns(min(3, len(lessons) - lesson_index))
        for col, (heading, explanation) in zip(cols, lessons[lesson_index:lesson_index + 3]):
            col.markdown(
                f"""
                <div class="mission-card">
                    <strong>{html.escape(heading)}</strong>
                    <span>{html.escape(explanation)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    code_tabs = []
    if module.get("python_code"):
        code_tabs.append(("Python", module["python_code"], "python"))
    if module.get("java_code"):
        code_tabs.append(("Java", module["java_code"], "java"))
    if code_tabs:
        tabs = st.tabs([label for label, _, _ in code_tabs])
        for tab, (_, code, language) in zip(tabs, code_tabs):
            with tab:
                st.code(code, language=language)
    elif module.get("code"):
        st.markdown(f'<div class="code-card">{html.escape(module["code"])}</div>', unsafe_allow_html=True)
    render_code_playground(module, index)
    st.markdown("### Kode-App-raaisel")
    st.markdown(f"**{module['challenge']}**")
    for option in module["options"]:
        st.markdown(f"- {html.escape(option)}")
    if module.get("explanation"):
        st.info(f"Antwoord: {module['answer']}. {module['explanation']}")
    if module.get("victory"):
        st.markdown(
            f"""
            <div class="practice-guide">
                <h3>Oorwinning</h3>
                <p>{html.escape(module["victory"])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def coding_module_quiz(module, grade, module_index):
    lessons = module.get("lessons") or module.get("training", [])
    first_heading, first_explanation = lessons[0]
    second_heading, _ = lessons[1] if len(lessons) > 1 else ("Volgende konsep", "")
    quiz_id_prefix = f"coding_course_m{module_index + 1}"
    return [
        {
            "id": f"{quiz_id_prefix}_concept",
            "prompt": f"Volgens hierdie module, wat leer jy by '{first_heading}'?",
            "options": [
                first_explanation,
                f"Dit beteken dieselfde as '{second_heading}'.",
                "Dit is net 'n moeilike woord wat ons later ignoreer.",
            ],
            "answer": first_explanation,
            "points": 10 + int(grade),
        },
        {
            "id": f"{quiz_id_prefix}_mission",
            "prompt": "Wat is die hoofdoel van hierdie module?",
            "options": [
                module["goal"],
                "Om 'n lang Python toets te skryf.",
                "Om die gewone skoolrooster te verander.",
            ],
            "answer": module["goal"],
            "points": 10 + int(grade),
        },
        {
            "id": f"{quiz_id_prefix}_challenge",
            "prompt": module["challenge"],
            "options": module["options"],
            "answer": module["answer"],
            "points": 12 + int(grade),
        },
    ]


def coding_quiz_question_for_attempt(quiz_item, grade, level):
    return {
        "id": quiz_item["id"],
        "subject": "Kodering",
        "topic": "Python & Java",
        "grade": int(grade),
        "level": int(level),
        "prompt": quiz_item["prompt"],
        "answer": quiz_item["answer"],
        "accepted": [quiz_item["answer"]],
        "points": int(quiz_item.get("points", 10)),
        "time_limit": 0,
    }


def stable_shuffled_options(options, seed, answer=None):
    unique_options = []
    for option in options:
        if option not in unique_options:
            unique_options.append(option)
    rng_seed = int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest()[:12], 16)
    shuffled = unique_options[:]
    random.Random(rng_seed).shuffle(shuffled)
    if answer is not None and len(shuffled) > 1 and normalize_answer(shuffled[0]) == normalize_answer(answer):
        swap_index = 1 + (rng_seed % (len(shuffled) - 1))
        shuffled[0], shuffled[swap_index] = shuffled[swap_index], shuffled[0]
    return shuffled


def completed_coding_quiz_ids(user_id, quiz_questions):
    question_ids = [question["id"] for question in quiz_questions]
    if not question_ids:
        return set()
    placeholders = ",".join("?" for _ in question_ids)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT question_id
            FROM attempts
            WHERE user_id = ?
              AND subject = 'Kodering'
              AND question_id IN ({placeholders})
            """,
            (user_id, *question_ids),
        ).fetchall()
    return {row["question_id"] for row in rows}


class SafeRandom:
    def randint(self, start, end):
        return random.randint(int(start), int(end))

    def choice(self, items):
        return random.choice(list(items))


def safe_python_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "random":
        return SafeRandom()
    raise ImportError(f"Die speelgrond laat nie import '{name}' toe nie.")


def validate_python_playground_code(code):
    allowed_nodes = (
        ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.Name, ast.Load, ast.Store,
        ast.Constant, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.If, ast.For,
        ast.While, ast.Break, ast.Continue, ast.List, ast.Tuple, ast.Dict, ast.Subscript,
        ast.Slice, ast.Call, ast.keyword, ast.Return, ast.FunctionDef, ast.arguments,
        ast.arg, ast.ClassDef, ast.Attribute, ast.Pass, ast.Import, ast.alias,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.And, ast.Or, ast.Not,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    )
    allowed_calls = {
        "print", "input", "int", "str", "float", "bool", "len", "sum", "max", "min",
        "range", "round", "abs", "list",
    }
    allowed_attributes = {
        "upper", "lower", "title", "strip", "replace", "append", "pop", "get",
        "put", "randint", "choice", "praat", "naam",
    }
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return None, f"Sintaksisfout op lyn {exc.lineno}: {exc.msg}"

    user_defined_calls = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("__")
    }
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            return None, f"Hierdie kode gebruik nog 'n gevorderde deel wat die speelgrond nie hardloop nie: {type(node).__name__}."
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            return None, "Name wat met __ begin word nie in die speelgrond toegelaat nie."
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return None, "Spesiale __ eienskappe word nie in die speelgrond toegelaat nie."
            if isinstance(node.ctx, ast.Load) and node.attr not in allowed_attributes:
                return None, f"Die metode of eienskap '.{node.attr}' word nie in die speelgrond toegelaat nie."
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in allowed_calls and node.func.id not in user_defined_calls:
                return None, f"Die funksie '{node.func.id}()' is nog nie in die speelgrond toegelaat nie."
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != "random":
                    return None, f"Net 'import random' word in die speelgrond toegelaat."
    return tree, None


def run_python_playground(code, mock_input="Leerling"):
    tree, error = validate_python_playground_code(code)
    if error:
        return "", error

    output = io.StringIO()
    safe_builtins = {
        "print": print,
        "input": lambda prompt="": mock_input,
        "int": int,
        "str": str,
        "float": float,
        "bool": bool,
        "len": len,
        "sum": sum,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "abs": abs,
        "list": list,
        "object": object,
        "__build_class__": __build_class__,
        "__import__": safe_python_import,
    }
    env = {"__builtins__": safe_builtins, "__name__": "kode_speelgrond", "random": SafeRandom()}
    line_budget = {"count": 0, "max": 500}

    def trace_lines(frame, event, arg):
        if event == "line":
            line_budget["count"] += 1
            if line_budget["count"] > line_budget["max"]:
                raise RuntimeError("Die speelgrond het gestop: te veel stappe. Kyk vir 'n oneindige lus.")
        return trace_lines

    try:
        compiled = compile(tree, "kode_speelgrond", "exec")
        with contextlib.redirect_stdout(output):
            previous_trace = sys.gettrace()
            sys.settrace(trace_lines)
            try:
                exec(compiled, env, env)
            finally:
                sys.settrace(previous_trace)
    except Exception as exc:
        return output.getvalue().strip(), f"{type(exc).__name__}: {exc}"
    return output.getvalue().strip() or "Kode het geloop, maar niks is met print() gewys nie.", None


def strip_java_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"//.*", "", code)


def extract_java_main_body(code):
    main_match = re.search(r"public\s+static\s+void\s+main\s*\([^)]*\)\s*\{", code)
    if not main_match:
        return code
    start = main_match.end()
    depth = 1
    for pos in range(start, len(code)):
        if code[pos] == "{":
            depth += 1
        elif code[pos] == "}":
            depth -= 1
            if depth == 0:
                return code[start:pos]
    return code[start:]


def split_java_top_level(source):
    parts = []
    start = 0
    depth = 0
    in_string = False
    escape = False
    paren_depth = 0
    for pos, char in enumerate(source):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                statement = source[start:pos + 1].strip()
                if statement:
                    parts.append(statement)
                start = pos + 1
        elif char == ";" and depth == 0 and paren_depth == 0:
            statement = source[start:pos].strip()
            if statement:
                parts.append(statement)
            start = pos + 1
    tail = source[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def split_java_plus(expr):
    parts = []
    start = 0
    in_string = False
    escape = False
    bracket_depth = 0
    paren_depth = 0
    for pos, char in enumerate(expr):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "+" and bracket_depth == 0 and paren_depth == 0:
            parts.append(expr[start:pos].strip())
            start = pos + 1
    parts.append(expr[start:].strip())
    return parts


def java_value_to_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def eval_java_atom(expr, env, mock_input):
    expr = expr.strip()
    if expr == "":
        return ""
    if expr in {"true", "false"}:
        return expr == "true"
    if expr.startswith('"') and expr.endswith('"'):
        return bytes(expr[1:-1], "utf-8").decode("unicode_escape")
    if expr.endswith(".length"):
        name = expr[:-7].strip()
        if name in env and isinstance(env[name], list):
            return len(env[name])
    index_match = re.fullmatch(r"([A-Za-z_]\w*)\s*\[\s*(.*?)\s*\]", expr)
    if index_match:
        name, index_expr = index_match.groups()
        if name not in env or not isinstance(env[name], list):
            raise ValueError(f"'{name}' is nie 'n lys/array nie.")
        return env[name][int(eval_java_expr(index_expr, env, mock_input))]
    if expr in env:
        return env[expr]
    if expr.endswith(".nextLine()"):
        return mock_input
    if expr.endswith(".nextInt()"):
        return int(mock_input.strip())
    if re.fullmatch(r"-?\d+", expr):
        return int(expr)
    if re.fullmatch(r"-?\d+\.\d+", expr):
        return float(expr)
    return eval_java_arithmetic(expr, env, mock_input)


def eval_java_arithmetic(expr, env, mock_input):
    transformed = expr.replace("&&", " and ").replace("||", " or ")
    transformed = re.sub(r"\btrue\b", "True", transformed)
    transformed = re.sub(r"\bfalse\b", "False", transformed)
    for name, value in sorted(env.items(), key=lambda item: len(item[0]), reverse=True):
        if isinstance(value, (int, float, bool)):
            transformed = re.sub(rf"\b{re.escape(name)}\b", repr(value), transformed)
    tree = ast.parse(transformed, mode="eval")
    allowed_nodes = (
        ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd,
        ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError("Hierdie Java-uitdrukking is nog te gevorderd vir die speelgrond.")
    return eval(compile(tree, "java_speelgrond", "eval"), {"__builtins__": {}}, {})


def eval_java_expr(expr, env, mock_input):
    parts = split_java_plus(expr)
    values = [eval_java_atom(part, env, mock_input) for part in parts]
    if any(isinstance(value, str) for value in values):
        return "".join(java_value_to_text(value) for value in values)
    total = values[0]
    for value in values[1:]:
        total += value
    return total


def parse_java_array(value_expr, env, mock_input):
    inner = value_expr.strip()
    inner = re.sub(r"^new\s+\w+\s*\[\]\s*", "", inner).strip()
    if not (inner.startswith("{") and inner.endswith("}")):
        raise ValueError("Gebruik asseblief 'n eenvoudige array soos {\"kat\", \"hond\"}.")
    item_source = inner[1:-1]
    items = []
    current = []
    in_string = False
    escape = False
    for char in item_source:
        if in_string:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            current.append(char)
        elif char == ",":
            items.append(eval_java_expr("".join(current).strip(), env, mock_input))
            current = []
        else:
            current.append(char)
    if "".join(current).strip():
        items.append(eval_java_expr("".join(current).strip(), env, mock_input))
    return items


def run_java_lines(source, env, output, mock_input, budget):
    for statement in split_java_top_level(source):
        budget["count"] += 1
        if budget["count"] > budget["max"]:
            raise RuntimeError("Die Java-speelgrond het gestop: te veel stappe.")
        statement = statement.strip()
        if not statement or statement.startswith("import "):
            continue
        if re.fullmatch(r"(Scanner|Random)\s+\w+\s*=\s*new\s+\w+\s*\([^)]*\)", statement):
            continue
        print_match = re.fullmatch(r"System\.out\.(println|print)\s*\((.*)\)", statement, flags=re.S)
        if print_match:
            value = eval_java_expr(print_match.group(2), env, mock_input)
            if print_match.group(1) == "println":
                output.append(java_value_to_text(value))
            elif output:
                output[-1] += java_value_to_text(value)
            else:
                output.append(java_value_to_text(value))
            continue
        if_match = re.fullmatch(r"if\s*\((.*?)\)\s*\{(.*?)\}(?:\s*else\s*\{(.*?)\})?", statement, flags=re.S)
        if if_match:
            condition, if_body, else_body = if_match.groups()
            run_java_lines(if_body if eval_java_expr(condition, env, mock_input) else (else_body or ""), env, output, mock_input, budget)
            continue
        for_match = re.fullmatch(r"for\s*\(\s*int\s+(\w+)\s*=\s*(.*?);\s*\1\s*([<>=!]+)\s*(.*?);\s*\1\s*(\+\+|--)\s*\)\s*\{(.*?)\}", statement, flags=re.S)
        if for_match:
            name, start_expr, operator, end_expr, step, body = for_match.groups()
            env[name] = int(eval_java_expr(start_expr, env, mock_input))
            iterations = 0
            while eval_java_expr(f"{name} {operator} {end_expr}", env, mock_input):
                iterations += 1
                if iterations > 100:
                    raise RuntimeError("Hierdie for-lus loop te lank vir die speelgrond.")
                run_java_lines(body, env, output, mock_input, budget)
                env[name] += 1 if step == "++" else -1
            continue
        declaration_match = re.fullmatch(r"(String|int|double|boolean)(\[\])?\s+(\w+)\s*=\s*(.*)", statement, flags=re.S)
        if declaration_match:
            value_type, is_array, name, value_expr = declaration_match.groups()
            env[name] = parse_java_array(value_expr, env, mock_input) if is_array else eval_java_expr(value_expr, env, mock_input)
            if value_type == "int" and not is_array:
                env[name] = int(env[name])
            elif value_type == "double" and not is_array:
                env[name] = float(env[name])
            elif value_type == "boolean" and not is_array:
                env[name] = bool(env[name])
            else:
                env[name] = env[name]
            continue
        assignment_match = re.fullmatch(r"(\w+)\s*(=|\+=)\s*(.*)", statement, flags=re.S)
        if assignment_match:
            name, operator, value_expr = assignment_match.groups()
            value = eval_java_expr(value_expr, env, mock_input)
            env[name] = env.get(name, 0) + value if operator == "+=" else value
            continue
        inc_match = re.fullmatch(r"(\w+)(\+\+|--)", statement)
        if inc_match:
            name, step = inc_match.groups()
            env[name] = env.get(name, 0) + (1 if step == "++" else -1)
            continue
        raise ValueError(f"Ek kan hierdie Java-lyn nog nie uitvoer nie: {statement[:80]}")


def run_java_playground(code, mock_input="Leerling"):
    risky_terms = (
        "Runtime", "ProcessBuilder", "System.exit", "File", "Files", "Socket",
        "exec", "ClassLoader", "reflection", "Thread", "while",
    )
    if any(term in code for term in risky_terms):
        return "", "Hierdie Java-deel is te gevorderd of nie veilig vir die speelgrond nie."
    source = extract_java_main_body(strip_java_comments(code))
    env = {}
    output = []
    try:
        run_java_lines(source, env, output, mock_input, {"count": 0, "max": 500})
    except Exception as exc:
        return "\n".join(output).strip(), f"Java-fout: {exc}"
    return "\n".join(output).strip() or "Kode het geloop, maar niks is met System.out.println() gewys nie.", None


def render_code_playground(module, index):
    if not module.get("python_code") and not module.get("java_code"):
        return
    st.markdown("### Kode Speelgrond")
    st.caption("Kies 'n taal, tik jou eie kode en toets dit. Die Java-kant is 'n beginner-emulator vir die lesvoorbeelde.")
    module_slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in module["title"]).strip("_")
    if module.get("activity"):
        st.markdown(
            f"""
            <div class="practice-guide">
                <h3>Mini-uitdaging</h3>
                <p>{html.escape(module["activity"])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    language_options = []
    if module.get("python_code"):
        language_options.append("Python")
    if module.get("java_code"):
        language_options.append("Java")
    language = st.radio(
        "Kies taal vir speelgrond",
        language_options,
        horizontal=True,
        key=f"coding_playground_language_{index}_{module_slug}",
    )
    language_key = language.lower()
    starter_key = f"coding_playground_starter_{index}_{module_slug}_{language_key}"
    code_key = f"coding_playground_code_{index}_{module_slug}_{language_key}"
    starter_code = module.get(f"{language_key}_code", "")
    if code_key not in st.session_state:
        st.session_state[starter_key] = starter_code
        st.session_state[code_key] = ""
    elif st.session_state.get(starter_key) != starter_code:
        st.session_state[starter_key] = starter_code
    mock_input = st.text_input(
        "Toets-invoer vir input() / Scanner",
        value="Mia",
        key=f"coding_playground_input_{index}_{module_slug}",
        help="As jou kode input() of Scanner gebruik, gee die speelgrond hierdie waarde terug.",
    )
    code = st.text_area(
        f"Skryf jou {language}-kode hier",
        key=code_key,
        height=190,
    )
    col1, col2 = st.columns([1, 1])
    run_clicked = col1.button("Run kode", type="primary", use_container_width=True, key=f"coding_playground_run_{index}_{language_key}")
    col2.button(
        "Maak leeg",
        use_container_width=True,
        key=f"coding_playground_reset_{index}_{language_key}",
        on_click=lambda key=code_key: st.session_state.update({key: ""}),
    )
    if run_clicked:
        if language == "Java":
            output, error = run_java_playground(code, mock_input=mock_input)
        else:
            output, error = run_python_playground(code, mock_input=mock_input)
        if error:
            st.error(error)
        if output:
            st.code(output, language="text")


def coding_page():
    user = st.session_state.user
    user_id = user["id"]
    grade = int(user.get("grade", 6))
    progress = get_progress(user_id, "Kodering", "Python & Java")
    modules = coding_modules_for_grade(grade)

    intro_text = (
        "Werk deur 'n 20-module Python- en Java-kursus met kort lesse, kodevoorbeelde, "
        "Kode-App-raaisels en mini-uitdagings. Leer teen jou eie pas en bou selfvertroue module vir module."
    )
    st.markdown(
        f"""
        <div class="coding-hero">
            <h2>Kodering Akademie</h2>
            <p>{html.escape(intro_text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Kursusmodules", len(modules))
    col2.metric("Kodering telling", progress["score"])
    col3.metric("Vlak", progress["level"])

    module_labels = [f"Module {idx + 1}: {module['title']}" for idx, module in enumerate(modules)]
    selected_label = st.selectbox("Kies jou kodering module", module_labels, key="coding_module_choice")
    module_index = module_labels.index(selected_label)
    module = modules[module_index]
    level_floor = (module_index * 3) + 1
    lesson_level = min(10, max(level_floor, int(progress["level"])))

    st.progress((module_index + 1) / len(modules))
    st.caption(f"Module {module_index + 1} van {len(modules)}. Werk rustig deur die les, raaisel en mini-uitdaging.")

    render_coding_module(module, module_index + 1)

    st.markdown("### Speel-speel voorspelling")
    prediction_options = stable_shuffled_options(
        module["options"],
        f"prediction_{module_index}_{module['title']}",
        module["answer"],
    )
    prediction = st.radio(
        module["challenge"],
        prediction_options,
        index=None,
        key=f"coding_prediction_{grade}_{module_index}",
    )
    if st.button("Toets my voorspelling", use_container_width=True):
        if prediction is None:
            st.warning("Kies eers 'n antwoord, dan toets ons jou voorspelling.")
        elif normalize_answer(prediction) == normalize_answer(module["answer"]):
            st.success("Mooi. Jy het die kode reg gelees.")
        else:
            st.warning(f"Naby. Die beste antwoord is: {module['answer']}")

    st.markdown("### Kort quiz na die module")
    quiz_questions = coding_module_quiz(module, grade, module_index)
    completed_ids = completed_coding_quiz_ids(user_id, quiz_questions)
    quiz_completed = len(completed_ids) == len(quiz_questions)
    if quiz_completed:
        st.success("Jy het hierdie module-quiz klaar voltooi. Jou punte is reeds gestoor.")

    with st.form(key=f"coding_quiz_{grade}_{module_index}"):
        answers = {}
        for idx, question in enumerate(quiz_questions, start=1):
            st.markdown(f"**Vraag {idx}:** {question['prompt']}")
            shuffled_options = stable_shuffled_options(
                question["options"],
                question["id"],
                question["answer"],
            )
            answers[question["id"]] = st.radio(
                "Kies jou antwoord",
                shuffled_options,
                index=None,
                key=f"coding_answer_{question['id']}",
                disabled=quiz_completed,
            )
        submitted = st.form_submit_button("Merk my quiz", use_container_width=True, disabled=quiz_completed)

    if submitted:
        completed_ids = completed_coding_quiz_ids(user_id, quiz_questions)
        if len(completed_ids) == len(quiz_questions):
            st.info("Hierdie module-quiz is reeds gemerk. Geen ekstra punte is bygevoeg nie.")
            st.stop()
        correct_count = 0
        total_points = 0
        unanswered = [question for question in quiz_questions if answers.get(question["id"]) is None]
        if unanswered:
            st.warning("Beantwoord asseblief al die quiz-vrae voordat jy merk.")
            st.stop()
        for question in quiz_questions:
            if question["id"] in completed_ids:
                continue
            answer = answers.get(question["id"], "")
            attempt_question = coding_quiz_question_for_attempt(question, grade, lesson_level)
            correct, points, new_level = record_attempt(user_id, attempt_question, answer, elapsed=0, timed_out=False)
            correct_count += int(correct)
            total_points += points
        if correct_count == len(quiz_questions):
            st.success(f"Fantasties. {correct_count}/{len(quiz_questions)} korrek en {total_points} punte.")
        elif correct_count:
            st.info(f"Goeie begin. {correct_count}/{len(quiz_questions)} korrek. Probeer weer vir volle punte.")
        else:
            st.warning("Nog nie daar nie. Lees die module weer en probeer weer.")
        time.sleep(1.2)
        st.rerun()


def front_page():
    user_id = st.session_state.user["id"]
    ctx = load_student_context(user_id)
    progress_df = rows_to_dataframe(ctx["progress"])
    student_grade = int(ctx["grade"])
    total_score = int(progress_df["score"].sum()) if not progress_df.empty else 0
    best_level = int(progress_df["level"].max()) if not progress_df.empty else 1

    st.markdown(
        f'<div class="hoof-kaart">{school_crest_img_html()}<div>Welkom terug, {avatar_img_html(ctx["avatar"])} <span class="wetenskap-teks">{ctx["name"]}</span></div></div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Totale telling", total_score)
    col2.metric("Beste vlak", best_level)
    col3.metric("Graad", student_grade)

    st.markdown(
        """
        <div class="practice-guide">
            <h3>Hoe om te begin</h3>
            <p>Kies 'n kategorie links in die kieslys, of spring in by Kodering Akademie vir Python en Java. Doen kort oefensessies, lees die wenke wanneer jy vasbrand, en kom terug na hierdie blad om jou vordering en ranglyste te sien.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not progress_df.empty:
        total_attempts = int(progress_df["attempt_count"].sum()) if "attempt_count" in progress_df else 0
        if total_attempts == 0:
            subject_links = '<span class="subject-pill">Kodering Akademie</span>' + "".join(f'<span class="subject-pill">{label}</span>' for label in CATEGORIES.keys())
            st.markdown(
                f"""
                <div class="empty-state">
                    <h3>Jou eerste oefening wag</h3>
                    <p>Begin met enige een van hierdie afdelings in die linkerkantse kieslys:</p>
                    <p>{subject_links}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("### Jou vordering per onderwerp")
        st.dataframe(
            progress_df[["subject", "topic", "level", "score", "correct_count", "attempt_count", "best_streak"]],
            use_container_width=True,
            hide_index=True,
        )

    refresh_leaderboard_snapshots()
    render_leaderboard(f"Weeklikse Graad {student_grade} ranglys", leaderboard_query("weekly", grade=student_grade))
    render_leaderboard(f"Graad {student_grade} Wiskunde ranglys", leaderboard_query("subject", "Wiskunde", grade=student_grade))
    render_leaderboard(f"Graad {student_grade} taal en lees ranglys", language_leaderboard(grade=student_grade))
    render_leaderboard(f"Graad {student_grade} akkuraatheid ranglys", accuracy_leaderboard(grade=student_grade))
    render_leaderboard(f"Graad {student_grade} meeste verbetering", improvement_leaderboard(grade=student_grade))


@st.dialog("Tyd is om")
def timeout_choice_dialog(user_id, subject, topic, active):
    question = active["question"]
    elapsed = max(float(question["time_limit"]), time.time() - (active.get("started_at") or time.time()))

    st.write("Jy kan dieselfde vraag weer probeer, of hierdie poging as tyd-uit merk en na die volgende vraag beweeg.")
    st.markdown(f"**Vraag:** {question['prompt']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Probeer weer", use_container_width=True):
            restart_active_question(user_id, subject, topic, question)
            clear_reading_preview(user_id, subject, topic, question)
            st.rerun()
    with col2:
        if st.button("Volgende vraag", use_container_width=True):
            record_attempt(user_id, question, "", elapsed, timed_out=True)
            clear_reading_preview(user_id, subject, topic, question)
            clear_active_question(user_id, subject, topic)
            st.rerun()


def module_practice(subject, topic):
    user_id = st.session_state.user["id"]
    student_grade = int(st.session_state.user.get("grade", 6))
    progress = get_progress(user_id, subject, topic)
    active = start_question_if_needed(user_id, subject, topic, student_grade, int(progress["level"]))
    if active is None:
        st.warning(
            f"Daar is nog geen aktiewe vrae vir Graad {student_grade}, {subject} - {topic} nie. "
            "Vra die onderwyser om dit in Admin op te stel."
        )
        return
    question = active["question"]
    needs_preview = should_hide_passage_after_preview(question) and active.get("started_at") is None

    st.markdown(
        f'### {subject} - {topic} <span class="wetenskap-teks">(Vlak {progress["level"]})</span>',
        unsafe_allow_html=True,
    )
    st.caption(f"Graad {student_grade}")
    correct_this_level = correct_count_for_level(user_id, subject, topic, int(progress["level"]))
    level_goal = min(correct_this_level, QUESTIONS_PER_LEVEL)
    st.progress(level_goal / QUESTIONS_PER_LEVEL)
    st.caption(f"{level_goal}/{QUESTIONS_PER_LEVEL} korrekte antwoorde nodig vir die volgende vlak.")

    if needs_preview:
        preview = start_reading_preview_if_needed(user_id, subject, topic, question)
        preview_remaining = max(0, int(preview["deadline"] - time.time()))
        st.markdown(reading_pane_html(question["passage"]), unsafe_allow_html=True)
        st.markdown("### Leesfase")
        st.write("Lees die stuk noukeurig. Wanneer jy gereed is, begin die vrae en word die leesstuk weggesteek.")
        render_countdown_timer(preview["deadline"], f"preview_{question['id']}")
        if preview_remaining > 0:
            st.caption("Jy kan vroeer begin as jy klaar gelees het, maar die timer wys hoeveel aanbevole leestyd oor is.")
        if st.button("Begin vrae", type="primary", use_container_width=True):
            start_answer_phase(user_id, subject, topic, active)
            st.rerun()
        st.stop()

    if active.get("started_at") is None:
        start_answer_phase(user_id, subject, topic, active)
        st.rerun()

    col1, col2, col3 = st.columns(3)
    col1.metric("Onderwerp telling", progress["score"])
    col2.metric("Akkuraatheid", f"{(100 * progress['correct_count'] / progress['attempt_count']) if progress['attempt_count'] else 0:.1f}%")
    if active.get("deadline") is None:
        col3.metric("Tyd", "Geen timer")
    else:
        remaining = max(0, int(active["deadline"] - time.time()))
        if remaining <= 0:
            col3.metric("Tyd oor", "Tyd is om")
            timeout_choice_dialog(user_id, subject, topic, active)
            st.stop()
        else:
            with col3:
                render_countdown_timer(active["deadline"], question["id"])
            if st.button("Tyd klaar? Wys opsies", use_container_width=True):
                st.rerun()

    if question.get("passage") and not should_hide_passage_after_preview(question):
        st.markdown(reading_pane_html(question["passage"]), unsafe_allow_html=True)
    elif question.get("passage"):
        st.info("Leesstuk is versteek. Beantwoord die vraag uit wat jy gelees het.")
    else:
        st.markdown(
            """
            <div class="practice-guide">
                <h3>Vat jou tyd</h3>
                <p>Lees die vraag mooi, tik jou antwoord in, en druk Enter of Dien In. As jy verkeerd is, wys die app vir jou 'n wenk.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f'<div class="question-box"><h3>{question["prompt"]}</h3></div>', unsafe_allow_html=True)

    with st.form(key=f"answer_form_{subject}_{topic}_{question['id']}", enter_to_submit=True):
        if question.get("input_mode") == "number":
            answer_value = st.number_input("Jou antwoord", value=None, step=1, format="%d")
            answer = "" if answer_value is None else str(int(answer_value))
        else:
            answer = st.text_input("Jou antwoord")
        st.caption("Wenk: Druk Enter op jou sleutelbord of selfoon, of gebruik die Dien In-knoppie.")
        submitted = st.form_submit_button("Dien In", use_container_width=True)

    if submitted:
        elapsed = time.time() - active["started_at"]
        timed_out = False if active.get("deadline") is None else elapsed > float(question["time_limit"])
        if timed_out:
            timeout_choice_dialog(user_id, subject, topic, active)
            st.stop()
        correct, points, new_level = record_attempt(user_id, question, answer, elapsed, timed_out)
        clear_reading_preview(user_id, subject, topic, question)
        clear_active_question(user_id, subject, topic)
        if correct:
            st.success(f"Korrek. {points} punte bygevoeg.")
            if new_level > int(progress["level"]):
                run_matrix_level_up(new_level)
            time.sleep(1.2)
            st.rerun()
        else:
            st.error(f"Verkeerd. Die korrekte antwoord was: {question['answer']}")
            st.warning(f"Wenk (-{INCORRECT_HINT_PENALTY} punte): {question.get('hint') or default_hint_for(question)}")
            st.info("Klik hieronder om aan te gaan wanneer jy die verduideliking gelees het.")
            if st.button("Volgende vraag", type="primary", use_container_width=True):
                st.rerun()

def admin_dashboard():
    st.title("Onderwyser Dashboard")
    grade_choice = st.selectbox("Wys graad", ["Alle grade", *GRADE_OPTIONS], key="teacher_dashboard_grade")
    selected_grade = None if grade_choice == "Alle grade" else int(grade_choice)
    user_where = "WHERE u.grade = ?" if selected_grade is not None else ""
    user_params = [selected_grade] if selected_grade is not None else []
    refresh_leaderboard_snapshots()

    with get_conn() as conn:
        students = conn.execute(
            f"""
            WITH academic AS (
                SELECT
                    user_id,
                    COALESCE(SUM(score), 0) AS academic_score,
                    COALESCE(MAX(level), 1) AS best_level,
                    COALESCE(SUM(correct_count), 0) AS correct_count,
                    COALESCE(SUM(attempt_count), 0) AS attempt_count
                FROM subject_progress
                GROUP BY user_id
            ),
            game_bonus AS (
                SELECT
                    user_id,
                    COALESCE(SUM(bonus_awarded), 0) AS game_bonus,
                    COALESCE(MAX(score), 0) AS tetris_best_score
                FROM game_scores
                GROUP BY user_id
            )
            SELECT u.id, u.name, u.avatar, u.created_at,
                   u.grade,
                   COALESCE(a.academic_score, 0) AS academic_score,
                   COALESCE(g.tetris_best_score, 0) AS tetris_best_score,
                   COALESCE(g.game_bonus, 0) AS game_bonus,
                   COALESCE(a.academic_score, 0) + COALESCE(g.game_bonus, 0) AS total_score,
                   COALESCE(a.best_level, 1) AS best_level,
                   COALESCE(a.correct_count, 0) AS correct_count,
                   COALESCE(a.attempt_count, 0) AS attempt_count
            FROM users u
            LEFT JOIN academic a ON a.user_id = u.id
            LEFT JOIN game_bonus g ON g.user_id = u.id
            {user_where}
            ORDER BY total_score DESC, name ASC
            """,
            user_params,
        ).fetchall()
        attempts = conn.execute(
            f"""
            SELECT a.created_at, u.name, u.grade, a.subject, a.topic, a.level, a.question,
                   a.answer_given, a.correct_answer, a.correct, a.timed_out,
                   ROUND(a.time_taken, 1) AS time_taken, a.points_awarded
            FROM attempts a
            JOIN users u ON u.id = a.user_id
            {user_where}
            ORDER BY a.created_at DESC
            LIMIT 250
            """,
            user_params,
        ).fetchall()
        game_scores = conn.execute(
            f"""
            SELECT gs.created_at, u.name, u.grade, gs.game, gs.score, gs.bonus_awarded,
                   gs.personal_best, gs.grade_best, gs.school_best
            FROM game_scores gs
            JOIN users u ON u.id = gs.user_id
            {user_where}
            ORDER BY gs.created_at DESC
            LIMIT 100
            """,
            user_params,
        ).fetchall()

    st.subheader("Studente")
    students_df = rows_to_dataframe(students)
    if not students_df.empty:
        total_students = len(students_df)
        total_attempts = int(students_df["attempt_count"].sum())
        avg_accuracy = (
            100 * students_df["correct_count"].sum() / total_attempts
            if total_attempts
            else 0
        )
        active_students = int((students_df["attempt_count"] > 0).sum())
        summary1, summary2, summary3, summary4 = st.columns(4)
        summary1.metric("Leerders", total_students)
        summary2.metric("Aktief", active_students)
        summary3.metric("Pogings", total_attempts)
        summary4.metric("Gem. akkuraatheid", f"{avg_accuracy:.1f}%")

        if "avatar" in students_df.columns:
            students_df["avatar"] = students_df["avatar"].apply(lambda value: avatar_img_html(value, "avatar-small"))
        students_df["accuracy"] = students_df.apply(
            lambda row: round((100 * row["correct_count"] / row["attempt_count"]), 1)
            if row["attempt_count"]
            else 0,
            axis=1,
        )
        st.markdown(students_df.to_html(escape=False, index=False), unsafe_allow_html=True)
        st.download_button(
            "Laai student opsomming af",
            data=students_df.to_csv(index=False).encode("utf-8"),
            file_name=f"student_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Nog geen studente nie.")

    st.subheader("Onlangse pogings")
    attempts_df = rows_to_dataframe(attempts)
    if not attempts_df.empty:
        st.dataframe(attempts_df, use_container_width=True, hide_index=True)
        st.download_button(
            "Laai pogings af",
            data=attempts_df.to_csv(index=False).encode("utf-8"),
            file_name=f"attempts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Nog geen pogings gestoor nie.")

    st.subheader("Mini Game Tellings")
    game_scores_df = rows_to_dataframe(game_scores)
    if not game_scores_df.empty:
        st.dataframe(game_scores_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nog geen mini game tellings nie.")

    title_suffix = "alle grade" if selected_grade is None else f"Graad {selected_grade}"
    render_leaderboard(f"Weeklikse ranglys ({title_suffix})", leaderboard_query("weekly", grade=selected_grade))
    render_leaderboard(f"Akkuraatheid ranglys ({title_suffix})", accuracy_leaderboard(grade=selected_grade))
    render_leaderboard(f"Meeste verbetering ({title_suffix})", improvement_leaderboard(grade=selected_grade))


def load_questions_for_admin(subject, topic, grade, level):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, subject, topic, grade, level, prompt, answer, accepted, passage, hint, input_mode,
                   points, time_limit, active
            FROM questions
            WHERE subject = ? AND topic = ? AND grade = ? AND level = ?
            ORDER BY id
            """,
            (subject, topic, grade, level),
        ).fetchall()

    data = []
    for row in rows:
        item = dict(row)
        item["accepted"] = ", ".join(deserialize_accepted(item["accepted"]))
        item["input_mode"] = item.get("input_mode") or "text"
        item["active"] = bool(item["active"])
        item["delete"] = False
        data.append(item)
    return pd.DataFrame(data)


def save_admin_questions(edited_df, subject, topic, grade, level):
    required_columns = ["id", "prompt", "answer", "accepted", "passage", "hint", "input_mode", "grade", "points", "time_limit", "active", "delete"]
    for column in required_columns:
        if column not in edited_df.columns:
            edited_df[column] = ""

    with get_conn() as conn:
        for _, row in edited_df.iterrows():
            def clean(value, default=""):
                if pd.isna(value):
                    return default
                return value

            question_id = str(clean(row.get("id"), "") or "").strip()
            delete_row = bool(clean(row.get("delete"), False))

            if delete_row and question_id:
                conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
                continue

            prompt = str(clean(row.get("prompt"), "") or "").strip()
            answer = str(clean(row.get("answer"), "") or "").strip()
            if not prompt or not answer:
                continue

            if not question_id:
                question_id = generate_question_id(subject, topic, grade, level)

            accepted_text = str(clean(row.get("accepted"), "") or "").strip()
            accepted = [item.strip() for item in accepted_text.split(",") if item.strip()] or [answer]
            passage = str(clean(row.get("passage"), "") or "").strip() or None
            hint = str(clean(row.get("hint"), "") or "").strip() or default_hint_for(
                {"subject": subject, "topic": topic, "prompt": prompt, "answer": answer}
            )
            input_mode = str(clean(row.get("input_mode"), "") or "").strip().lower()
            if input_mode not in {"text", "number"}:
                input_mode = default_input_mode_for({"answer": answer})
            grade = int(grade)
            points = int(clean(row.get("points"), 10) or 10)
            time_limit = int(clean(row.get("time_limit"), 20) or 20)
            active = 1 if bool(clean(row.get("active"), True)) else 0

            conn.execute(
                """
                INSERT INTO questions
                    (id, subject, topic, grade, level, prompt, answer, accepted, passage, hint, input_mode,
                     points, time_limit, active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    subject = excluded.subject,
                    topic = excluded.topic,
                    grade = excluded.grade,
                    level = excluded.level,
                    prompt = excluded.prompt,
                    answer = excluded.answer,
                    accepted = excluded.accepted,
                    passage = excluded.passage,
                    hint = excluded.hint,
                    input_mode = excluded.input_mode,
                    points = excluded.points,
                    time_limit = excluded.time_limit,
                    active = excluded.active,
                    updated_at = excluded.updated_at
                """,
                (
                    question_id,
                    subject,
                    topic,
                    grade,
                    level,
                    prompt,
                    answer,
                    json.dumps(accepted),
                    passage,
                    hint,
                    input_mode,
                    points,
                    time_limit,
                    active,
                    now_iso(),
                ),
            )


def admin_questions_page():
    st.title("Admin")
    st.subheader("Vraagbank")
    st.caption("Kies 'n kategorie en vlak, wysig die vrae in die tabel, en klik Stoor. Nuwe rye kan onderaan bygevoeg word.")

    grade = st.selectbox("Graad", GRADE_OPTIONS, index=GRADE_OPTIONS.index(6), key="admin_question_grade")
    category = st.selectbox("Kategorie", list(ADMIN_CATEGORIES.keys()), key="admin_question_category")
    subject, topic = ADMIN_CATEGORIES[category]

    level = st.number_input(
        "Vlak",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        key="admin_question_level",
        help="Kies 'n bestaande vlak om dit te wysig, of kies 'n vlak sonder vrae om dit op te stel.",
    )
    questions_df = load_questions_for_admin(subject, topic, int(grade), int(level))

    if questions_df.empty:
        questions_df = pd.DataFrame(
            columns=[
                "id",
                "subject",
                "topic",
                "grade",
                "level",
                "prompt",
                "answer",
                "accepted",
                "passage",
                "hint",
                "input_mode",
                "points",
                "time_limit",
                "active",
                "delete",
            ]
        )

    edited_df = st.data_editor(
        questions_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True),
            "subject": st.column_config.TextColumn("Vak", disabled=True),
            "topic": st.column_config.TextColumn("Onderwerp", disabled=True),
            "grade": st.column_config.NumberColumn("Graad", disabled=True),
            "level": st.column_config.NumberColumn("Vlak", disabled=True),
            "prompt": st.column_config.TextColumn("Vraag", width="large"),
            "answer": st.column_config.TextColumn("Korrekte antwoord"),
            "accepted": st.column_config.TextColumn("Aanvaar ook", help="Gebruik kommas vir alternatiewe antwoorde."),
            "passage": st.column_config.TextColumn("Leesstuk", width="large"),
            "hint": st.column_config.TextColumn("Wenk", width="large"),
            "input_mode": st.column_config.SelectboxColumn(
                "Input tipe",
                options=["text", "number"],
                help="Gebruik 'number' vir somme sodat selfone die nommer-sleutelbord wys.",
            ),
            "points": st.column_config.NumberColumn("Punte", min_value=0, max_value=100, step=1),
            "time_limit": st.column_config.NumberColumn("Sekondes", min_value=5, max_value=300, step=1),
            "active": st.column_config.CheckboxColumn("Aktief"),
            "delete": st.column_config.CheckboxColumn("Verwyder"),
        },
        key=f"question_editor_{subject}_{topic}_{level}",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Stoor vrae", type="primary", use_container_width=True):
            edited_df["subject"] = subject
            edited_df["topic"] = topic
            edited_df["grade"] = int(grade)
            edited_df["level"] = int(level)
            save_admin_questions(edited_df, subject, topic, int(grade), int(level))
            st.success("Vraagbank gestoor.")
            st.rerun()
    with col2:
        st.info("Wenk: vir leesbegrip, vul die leesstuk-kolom in. Vir gewone somme of taalvrae kan dit leeg bly.")


def admin_students_page():
    st.title("Studente")
    st.subheader("Redigeer student data")
    st.caption("Wysig naam, graad en avatar hier. Wagwoorde word apart onderaan herstel sodat dit veilig gehash bly.")

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, grade, avatar, created_at
            FROM users
            ORDER BY grade, name
            """
        ).fetchall()

    students_df = rows_to_dataframe(rows)
    if students_df.empty:
        st.info("Daar is nog geen studente nie.")
    else:
        students_df["avatar"] = students_df["avatar"].apply(normalize_avatar_key)
        edited_df = st.data_editor(
            students_df,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True),
                "name": st.column_config.TextColumn("Naam"),
                "grade": st.column_config.SelectboxColumn("Graad", options=GRADE_OPTIONS),
                "avatar": st.column_config.SelectboxColumn("Avatar", options=list(AVATAR_OPTIONS.keys())),
                "created_at": st.column_config.TextColumn("Geskep", disabled=True),
            },
            key="student_editor",
        )

        if st.button("Stoor student data", type="primary"):
            try:
                with get_conn() as conn:
                    for _, row in edited_df.iterrows():
                        student_id = str(row["id"])
                        name = str(row["name"]).strip()
                        grade = int(row["grade"])
                        avatar = normalize_avatar_key(row["avatar"])
                        if not name:
                            st.error("Elke student moet 'n naam he.")
                            return
                        conn.execute(
                            """
                            UPDATE users
                            SET name = ?, grade = ?, avatar = ?
                            WHERE id = ?
                            """,
                            (name, grade, avatar, student_id),
                        )
                        conn.execute(
                            "UPDATE subject_progress SET grade = ? WHERE user_id = ?",
                            (grade, student_id),
                        )
                st.success("Student data gestoor.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Daardie naam bestaan reeds. Gebruik unieke studentname.")

    st.markdown("---")
    st.subheader("Herstel student wagwoord")
    with get_conn() as conn:
        student_rows = conn.execute("SELECT id, name, grade FROM users ORDER BY grade, name").fetchall()
    if not student_rows:
        st.info("Geen studente beskikbaar vir wagwoord herstel nie.")
        return

    student_options = {f"Graad {row['grade']} - {row['name']}": row["id"] for row in student_rows}
    selected_label = st.selectbox("Kies student", list(student_options.keys()), key="password_reset_student")
    new_password = st.text_input("Nuwe wagwoord", type="password", key="password_reset_value")
    if st.button("Stel wagwoord", use_container_width=True):
        if not new_password:
            st.error("Tik eers 'n nuwe wagwoord in.")
        else:
            student_id = student_options[selected_label]
            with get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO credentials (account_type, account_id, password_hash, created_at)
                    VALUES ('student', ?, ?, ?)
                    ON CONFLICT(account_type, account_id) DO UPDATE SET
                        password_hash = excluded.password_hash,
                        created_at = excluded.created_at
                    """,
                    (student_id, hash_password(new_password), now_iso()),
                )
            st.success("Wagwoord is herstel.")


def logout():
    st.session_state.clear()
    st.rerun()


def main():
    init_db()
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        login_flow()
        return

    if st.session_state.user.get("role") == "admin":
        with st.sidebar:
            st.markdown(school_brand_html(compact=True), unsafe_allow_html=True)
            admin_page = st.selectbox("Bladsy", ["Dashboard", "Admin", "Studente"], key="admin_page")
            st.markdown("---")
            if st.button("Log Uit"):
                logout()
        if admin_page == "Admin":
            admin_questions_page()
        elif admin_page == "Studente":
            admin_students_page()
        else:
            admin_dashboard()
        return

    with st.sidebar:
        st.markdown(school_brand_html(compact=True), unsafe_allow_html=True)
        st.markdown(
            f"{avatar_img_html(st.session_state.user['avatar'])} **{st.session_state.user['name']}**",
            unsafe_allow_html=True,
        )
        category = st.selectbox(
            "Kies Kategorie",
            ["Voorblad (Stats & Leaderboard)", "Kodering Akademie", "Mini Game - Tetris", *CATEGORIES.keys()],
            key="main_navigation",
        )
        st.markdown("---")
        if st.button("Log Uit"):
            logout()

    if category == "Voorblad (Stats & Leaderboard)":
        front_page()
    elif category == "Kodering Akademie":
        coding_page()
    elif category == "Mini Game - Tetris":
        tetris_page()
    else:
        subject, topic = CATEGORIES[category]
        module_practice(subject, topic)


if __name__ == "__main__":
    main()
