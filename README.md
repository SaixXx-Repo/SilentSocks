# Sales Data Analysis Tool

A local, portable Streamlit application for analyzing sales data from Excel files.

## Features
- **Data Import**: Upload Excel files for `Kundlista` (Customer List) and `Försäljningsstatistik` (Sales Statistics).
- **Dashboard**: Interactive filtering by date, country, customer group, type, and specific articles.
- **Visualizations**: View sales by country, trends over time, and top-performing articles/customers.
- **AI Analysis**: Connects to Google Gemini (requires API key) for automated insights and trend prediction.

## Installation

### Prerequisites
- Python 3.8+

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the App

### Windows
Run the `run_windows.bat` file or execute manually:
```bash
streamlit run app.py
```

### Mac/Linux
Run the `run.sh` script or execute manually:
```bash
streamlit run app.py
```

## Portable Version (Windows Only)
This project comes with a configured portable Python environment (if distributed as a bundle). Run `run_portable.bat` to launch without installing Python locally.

## Project Structure
- `app.py`: Main application entry point.
- `ai_service.py`: Handles logic for AI analysis and trend prediction.
- `data_processor.py`: Functions for parsing and cleaning Excel data.
- `database.py`: SQLite database interaction layer.
- `requirements.txt`: Python dependencies.
