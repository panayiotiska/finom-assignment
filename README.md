# Anomaly Detection App

Z-score based anomaly detection FastAPI service. Detects unusual registration spikes by country using statistical analysis.

**Total time spent ~2 Hours

## Features

- Uses SQL for anomaly detection
- Calculates z-scores with moving averages and standard deviation
- Docker containerized
- FastAPI endpoints for date-specific anomaly checking

## Files

- generate_sample_data.py -> Script to create and populate the sqlite database with sample registration data
- app.py -> Main FastAPI app and anomaly detection logic
- queries.py -> The SQL query logic for anomaly detection
- Dockerfile -> Docker configuration for containerizing the app

## Anomaly Detection Logic

1. Groups registrations by day and country
2. Calculates moving average over last X days (excluding current)
3. Computes standard deviation of the window
4. Calculates z-score: (current - mean) / std_dev
5. Flags anomalies when |z-score| > threshold

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

- `POST /check_anomaly` - Check anomalies for all countries on a specific date
- `POST /check_anomaly/country` - Check anomaly for a specific country on a specific date

### Usage Examples

```bash
# Check all countries for a specific date
curl -X POST http://localhost:8000/check_anomaly \
  -H "Content-Type: application/json" \
  -d '{"registration_dt": "2025-08-31"}'

# Check specific country for a specific date
curl -X POST http://localhost:8000/check_anomaly/country \
  -H "Content-Type: application/json" \
  -d '{"country": "UK", "registration_dt": "2025-08-31"}'
```

## Configuration

Edit `config.py` to adjust:
- `WINDOW_DAYS = 4` - Moving average window size (days to look back)
- `MULTIPLIER = 2` - Z-score threshold (|z| > threshold is anomalous)

