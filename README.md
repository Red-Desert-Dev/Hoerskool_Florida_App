# Hoërskool Florida App

Streamlit learning app branded for Hoërskool Florida. The app helps learners practise skills in Wiskunde, Afrikaans, Engels, Leesbegrip, Kodering and a small Tetris game.

## Features

- Learner registration from Graad 2 to Graad 12.
- Hoërskool Florida colour theme with green, red and yellow branding.
- Practice modules for Wiskunde, Afrikaans, Engels and reading.
- Kodering Akademie with Python and Java examples.
- Interactive Kode Speelgrond for beginner Python and beginner Java lesson examples.
- Tetris mini game with score tracking and leaderboards.
- Teacher/Admin area for questions, learners, progress and rankings.

## Requirements

- Python 3.10 or newer.
- Windows PowerShell.
- Project dependencies from `requirements.txt`.

## Run Locally

Open PowerShell and run:

```powershell
cd "C:\Users\dekle\OneDrive\Desktop\SchoolApp"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens at:

```text
http://localhost:8501
```

## Start The Virtual Environment

If the virtual environment already exists, activate it first:

```powershell
cd "C:\Users\dekle\OneDrive\Desktop\SchoolApp"
.\.venv\Scripts\Activate.ps1
```

Your PowerShell prompt should then show `(.venv)` at the start.

After it is active, you can run Streamlit with:

```powershell
python -m streamlit run app.py
```

To leave the virtual environment:

```powershell
deactivate
```

## View On A Phone

Make sure your phone and computer are on the same Wi-Fi network.

Start the app so other devices can reach it:

```powershell
cd "C:\Users\dekle\OneDrive\Desktop\SchoolApp"
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Streamlit should show a `Network URL`, for example:

```text
http://192.168.1.25:8501
```

Open that URL on your phone browser.

If the phone cannot connect, check that Windows Firewall allows Python/Streamlit on private networks.

## Teacher Access

Default teacher login:

```text
Name: Onderwyser
Password: admin123
```

Change this before using the app with real learners.

## Data

The app stores local data in:

```text
school_app.db
```

Keep a backup of this file if you are testing with real learner accounts or scores.
