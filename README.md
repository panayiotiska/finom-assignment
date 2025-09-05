# Anomaly Detection App

Moving average based anomaly detection FastAPI service. Detects unusual registration spikes by country using the max available hour.

**Total time spent ~2 Hours

## Features

- Uses SQL for anomaly detection
- Calculates moving averages and standard deviation
- Docker containerized
- FastAPI endpoints for the current hour's results

## Files

- generate_sample_data.py -> Script to create and populate the sqlite database with sample registration data
- app.py -> Main FastAPI app and anomaly detection logic
- queries.py -> The SQL query logic for anomaly detection
- Dockerfile -> Docker configuration for containerizing the app

## Anomaly Detection Logic

1. Groups registrations by hour and country
2. Calculates moving average over last X hours (excluding current)
3. Computes standard deviation of the window
4. Flags anomalies when current hour > moving_avg + (multiplier × std_dev)

## Setup

### With Docker

```bash
docker build -t anomaly-detector .
docker run -p 8000:8000 anomaly-detector
```

### Local

```bash
pip install -r requirements.txt

# First, generate sample data
python generate_sample_data.py

# Then start the API server
python app.py
```

## API Endpoints

- `GET /anomalies` - Get max available hour anomaly detection results for all countries
- `GET /anomalies/{country}` - Get max available hour anomaly detection results for specific country

## Configuration

Edit `config.py` to adjust:
- `WINDOW_HOURS = 4` - Moving average window size
- `MULTIPLIER = 2` - Standard deviation multiplier for threshold

