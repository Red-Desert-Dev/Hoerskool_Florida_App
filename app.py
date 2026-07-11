import hashlib
import hmac
import base64
import json
import os
import random
import secrets
import sqlite3
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st


DB_FILE = "school_app.db"
JSON_BACKUP_FILE = "db.json"
SCHOOL_NAME = "Hoerskool Florida"
SCHOOL_CREST_FILE = os.path.join("assets", "hoerskool_florida_wapen.png")
APP_TAGLINE = "Bou vaardighede in wiskunde, tale en leesbegrip - een kort oefensessie op 'n slag."
PBKDF2_ITERATIONS = 260_000
DEFAULT_TEACHER_NAME = "Onderwyser"
DEFAULT_TEACHER_PASSWORD = "admin123"
QUESTIONS_PER_LEVEL = 5
INCORRECT_HINT_PENALTY = 2
GRADE_OPTIONS = list(range(4, 13))
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
    "astronaut": {"label": "Astronaut", "face": "#ffd7a8", "hair": "#3b2b25", "accent": "#f2cf4a", "symbol": "★"},
    "robot": {"label": "Robot", "face": "#b8c7d9", "hair": "#516070", "accent": "#007a3d", "symbol": "●"},
    "ninja": {"label": "Ninja", "face": "#f0b98d", "hair": "#10131c", "accent": "#c7252e", "symbol": "◆"},
    "wizard": {"label": "Wizard", "face": "#ffd1bd", "hair": "#6f4bd8", "accent": "#b76cff", "symbol": "✦"},
    "scientist": {"label": "Scientist", "face": "#f4c7a1", "hair": "#e8edf5", "accent": "#007a3d", "symbol": "⚗"},
    "gamer": {"label": "Gamer", "face": "#d8a47f", "hair": "#1c2638", "accent": "#f2cf4a", "symbol": "▶"},
    "pilot": {"label": "Pilot", "face": "#c98f6a", "hair": "#2d211d", "accent": "#007a3d", "symbol": "▲"},
    "artist": {"label": "Artist", "face": "#e9b384", "hair": "#ff8a3d", "accent": "#ff4b9b", "symbol": "✎"},
    "coder": {"label": "Coder", "face": "#c48d67", "hair": "#16202f", "accent": "#f2cf4a", "symbol": "</>"},
    "captain": {"label": "Captain", "face": "#f2c09d", "hair": "#263047", "accent": "#f2cf4a", "symbol": "⚡"},
    "alien": {"label": "Alien", "face": "#9dffb0", "hair": "#2f6b4a", "accent": "#f2cf4a", "symbol": "◉"},
    "explorer": {"label": "Explorer", "face": "#d49a73", "hair": "#7a4d2b", "accent": "#007a3d", "symbol": "⌖"},
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


st.set_page_config(page_title=f"{SCHOOL_NAME} Akademie", layout="wide", page_icon="HF")

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

BASIC_MATH_QUESTIONS = [
    {
        "id": f"math_alg_{level}_{index:02d}",
        "subject": "Wiskunde",
        "topic": "Algebra",
        "grade": 6,
        "level": level,
        "prompt": prompt,
        "answer": answer,
        "points": 8 + (level * 2),
        "time_limit": 15 + min(level, 5) * 3,
    }
    for level, questions in BASIC_MATH_LEVELS.items()
    for index, (prompt, answer) in enumerate(questions, start=1)
]

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


def build_grade6_meetkunde_questions():
    questions = []
    for level in range(1, 11):
        items = [
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
        for index, (prompt, answer) in enumerate(items, start=1):
            questions.append(
                {
                    "id": f"math_geo_g6_{level}_{index:02d}",
                    "subject": "Wiskunde",
                    "topic": "Meetkunde",
                    "grade": 6,
                    "level": level,
                    "prompt": prompt,
                    "answer": answer,
                    "accepted": [answer, f"{answer}cm", f"{answer} cm", f"{answer}cm2", f"{answer} cm2"],
                    "points": 9 + level,
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


def build_reading_questions(prefix, subject, data):
    levels = {}
    for level, (passage, items) in enumerate(data, start=1):
        levels[level] = [(passage, prompt, answer, accepted) for prompt, answer, accepted in items]
    return build_questions(prefix, subject, "Lees", levels, grade=6, base_points=12, base_time=25)


GRADE6_MODULE_QUESTIONS = (
    build_grade6_meetkunde_questions()
    + build_questions("afr_lang_g6", "Afrikaans", "Taal", AFRIKAANS_TAAL_LEVELS, grade=6, base_points=9, base_time=18)
    + build_reading_questions("afr_read_g6", "Afrikaans", AFRIKAANS_READING_DATA)
    + build_questions("eng_lang_g6", "Engels", "Taal", ENGLISH_TAAL_LEVELS, grade=6, base_points=9, base_time=18)
    + build_reading_questions("eng_read_g6", "Engels", ENGLISH_READING_DATA)
)


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


QUESTION_BANK = BASIC_MATH_QUESTIONS + GRADE6_MODULE_QUESTIONS + LEGACY_QUESTION_BANK


CATEGORIES = {
    "Wiskunde - Algebra": ("Wiskunde", "Algebra"),
    "Wiskunde - Meetkunde": ("Wiskunde", "Meetkunde"),
    "Afrikaans - Taal": ("Afrikaans", "Taal"),
    "Afrikaans - Begripstoets": ("Afrikaans", "Lees"),
    "Engels - Comprehension": ("Engels", "Taal"),
    "Engels - Lees": ("Engels", "Lees"),
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
      <text x="72" y="30" text-anchor="middle" font-size="15" font-family="Arial" font-weight="700" fill="{avatar['accent']}">{symbol}</text>
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
    st.markdown(df[columns].to_html(escape=False, index=False), unsafe_allow_html=True)


def render_tetris_component():
    game_html = """
    <div style="background:#08331f;border:1px solid #d5b03a;border-radius:10px;padding:14px;color:#fff8df;font-family:system-ui;">
      <div style="display:flex;gap:16px;align-items:flex-start;justify-content:center;flex-wrap:wrap;">
        <canvas id="tetris-board" width="200" height="400" style="background:#052719;border:2px solid #f2cf4a;border-radius:6px;"></canvas>
        <div style="min-width:190px;">
          <div style="font-size:13px;color:#e7dcae;">Tetris Score</div>
          <div id="score" style="font-size:38px;font-weight:800;color:#f2cf4a;margin-bottom:10px;">0</div>
          <button id="startBtn" style="width:100%;padding:10px;border:0;border-radius:6px;background:#f2cf4a;color:#06351f;font-weight:800;cursor:pointer;">START</button>
          <button id="submitBtn" style="width:100%;padding:10px;border:1px solid #d5b03a;border-radius:6px;background:#0f5734;color:#fff8df;font-weight:700;margin-top:8px;cursor:pointer;">STOOR TELLING</button>
          <form id="scoreForm" method="GET" target="_parent" style="display:none;">
            <input id="scoreInput" name="tetris_score" value="0" />
          </form>
          <div style="display:grid;grid-template-columns:repeat(3,52px);gap:6px;margin-top:14px;justify-content:center;">
            <button data-action="left">&larr;</button><button data-action="rotate">&#8635;</button><button data-action="right">&rarr;</button>
            <button data-action="down" style="grid-column:1 / span 3;">&darr;</button>
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
        dropInterval = Math.max(180, dropInterval - lines * 20);
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
      resetBoard(); player = randomPiece(); score = 0; dropCounter = 0; dropInterval = 850; lastTime = 0; running = true; gameOver = false;
      statusEl.textContent = '';
      update();
    }
    function submitScore() {
      document.getElementById('scoreInput').value = String(score);
      document.getElementById('scoreForm').submit();
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

    if "tetris_score" in st.query_params:
        try:
            submitted_score = int(st.query_params.get("tetris_score", 0))
        except (TypeError, ValueError):
            submitted_score = 0
        result = record_tetris_score(user_id, grade, submitted_score)
        remaining_params = {key: value for key, value in st.query_params.items() if key != "tetris_score"}
        st.query_params.clear()
        for key, value in remaining_params.items():
            st.query_params[key] = value
        if result["saved"]:
            st.success(f"Tetris telling gestoor: {submitted_score}. {result['message']}.")
        else:
            st.info(result["message"])

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
            <p>Kies 'n kategorie links in die kieslys. Doen kort oefensessies, lees die wenke wanneer jy vasbrand, en kom terug na hierdie blad om jou vordering en ranglyste te sien.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not progress_df.empty:
        total_attempts = int(progress_df["attempt_count"].sum()) if "attempt_count" in progress_df else 0
        if total_attempts == 0:
            subject_links = "".join(f'<span class="subject-pill">{label}</span>' for label in CATEGORIES.keys())
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
        st.info(question["passage"])
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
        st.info(question["passage"])
    elif question.get("passage"):
        st.info("Leesstuk is versteek. Beantwoord die vraag uit wat jy gelees het.")
    else:
        st.markdown(
            """
            <div class="practice-guide">
                <h3>Vat jou tyd</h3>
                <p>Lees die vraag mooi, tik net jou antwoord in, en druk Dien In. As jy verkeerd is, wys die app vir jou 'n wenk.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f'<div class="question-box"><h3>{question["prompt"]}</h3></div>', unsafe_allow_html=True)

    with st.form(key=f"answer_form_{subject}_{topic}_{question['id']}"):
        if question.get("input_mode") == "number":
            answer_value = st.number_input("Jou antwoord", value=None, step=1, format="%d")
            answer = "" if answer_value is None else str(int(answer_value))
        else:
            answer = st.text_input("Jou antwoord")
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
    category = st.selectbox("Kategorie", list(CATEGORIES.keys()), key="admin_question_category")
    subject, topic = CATEGORIES[category]

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
            ["Voorblad (Stats & Leaderboard)", "Mini Game - Tetris", *CATEGORIES.keys()],
            key="category_selection",
        )
        st.markdown("---")
        if st.button("Log Uit"):
            logout()

    if category == "Voorblad (Stats & Leaderboard)":
        front_page()
    elif category == "Mini Game - Tetris":
        tetris_page()
    else:
        subject, topic = CATEGORIES[category]
        module_practice(subject, topic)


if __name__ == "__main__":
    main()
