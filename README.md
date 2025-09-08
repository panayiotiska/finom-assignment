# Anomaly Detection App

Statistical anomaly detection FastAPI service. Detects unusual registration spikes by country using z-score and percentiles algorithms.

**Total time spent ~2 Hours

## Features

- Uses SQL for anomaly detection
- Supports both z-score and percentiles-based algorithms
- Calculates z-scores with moving averages and standard deviation
- Docker containerized
- FastAPI endpoints for date-specific anomaly checking with algorithm selection

## Files

- scripts/generate_sample_data.py -> Script to create and populate the sqlite database with sample registration data
- app.py -> Main FastAPI app and anomaly detection logic
- queries.py -> The SQL query logic for anomaly detection
- Dockerfile -> Docker configuration for containerizing the app

## Anomaly Detection Logic

### Z-Score Algorithm
1. Groups registrations by day and country
2. Calculates moving average over last X days (excluding current)
3. Computes standard deviation of the window
4. Calculates z-score: (current - mean) / std_dev
5. Flags anomalies when |z-score| > threshold

### Percentiles Algorithm
1. Groups registrations by day and country
2. Calculates percentile thresholds from historical window data
3. Flags anomalies when current value exceeds the percentile threshold

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
python scripts/generate_sample_data.py

# Then start the API server
python app.py
```

## API Endpoints

### General Endpoints
- `POST /check_anomaly` - Check anomalies for all countries on a specific date
- `POST /check_anomaly/country` - Check anomaly for a specific country on a specific date

### Algorithm-Specific Endpoints
- `POST /check_anomaly/zscore` - Check anomalies using z-score algorithm (all countries)
- `POST /check_anomaly/percentiles` - Check anomalies using percentiles algorithm (all countries)
- `POST /check_anomaly/country/zscore` - Check country anomaly using z-score algorithm
- `POST /check_anomaly/country/percentiles` - Check country anomaly using percentiles algorithm

### Usage Examples

```bash
# Check all countries for a specific date (default z-score algorithm)
curl -X POST http://localhost:8000/check_anomaly \
  -H "Content-Type: application/json" \
  -d '{"registration_dt": "2025-08-31"}'

# Check specific country for a specific date (default z-score algorithm)
curl -X POST http://localhost:8000/check_anomaly/country \
  -H "Content-Type: application/json" \
  -d '{"country": "UK", "registration_dt": "2025-08-31"}'

# Check all countries using z-score algorithm
curl -X POST http://localhost:8000/check_anomaly/zscore \
  -H "Content-Type: application/json" \
  -d '{"registration_dt": "2025-08-31"}'

# Check all countries using percentiles algorithm
curl -X POST http://localhost:8000/check_anomaly/percentiles \
  -H "Content-Type: application/json" \
  -d '{"registration_dt": "2025-08-31"}'

# Check specific country using percentiles algorithm
curl -X POST http://localhost:8000/check_anomaly/country/percentiles \
  -H "Content-Type: application/json" \
  -d '{"country": "UK", "registration_dt": "2025-08-31"}'
```

## Configuration

Edit `config.py` to adjust:
- `WINDOW_DAYS = 4` - Moving average window size (days to look back)
- `MULTIPLIER = 2` - Z-score threshold (|z| > threshold is anomalous)
- `PERCENTILE_THRESHOLD = 0.05` - Percentile threshold for percentiles algorithm (0.05 = 95th percentile)

