@echo off
REM Launches the Streamlit app. Run setup_windows.bat first (once).

call .venv\Scripts\activate.bat
streamlit run app.py
pause
