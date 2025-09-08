import sqlite3
from fastapi import FastAPI, HTTPException
from typing import Dict
from pydantic import BaseModel
from queries import get_anomaly_query
from datetime import datetime

app = FastAPI(title="Anomaly Detection API")


class AnomalyCheckRequest(BaseModel):
    registration_dt: str


class CountryAnomalyInfo(BaseModel):
    is_anomaly: bool
    registrations_cnt: int


class CountryCheckRequest(BaseModel):
    country: str
    registration_dt: str


def validate_date(date_str: str) -> None:
    """Validate date format and raise HTTPException if invalid"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )


def check_anomalies(target_date: str, algorithm: str = "zscore", country: str = None):
    """
    Unified function to check anomalies for a date (and optionally country) using specified algorithm

    Args:
        target_date: Date string in YYYY-MM-DD format
        algorithm: Algorithm to use ('zscore', 'percentiles', etc.)
        country: Optional country code. If None, returns results for all countries

    Returns:
        Dict[str, CountryAnomalyInfo] if country is None, else CountryAnomalyInfo
    """
    conn = sqlite3.connect("registrations.db")
    cursor = conn.cursor()

    # Get the unified anomaly detection query
    query = get_anomaly_query(target_date, algorithm, country)

    if country:
        # Single country result
        result = cursor.execute(query).fetchone()
        if result:
            is_anomaly, registrations_cnt = result
            country_info = CountryAnomalyInfo(
                is_anomaly=bool(is_anomaly), registrations_cnt=int(registrations_cnt)
            )
        else:
            # No data for this country/date combination
            country_info = CountryAnomalyInfo(is_anomaly=False, registrations_cnt=0)
        conn.close()
        return country_info
    else:
        # All countries result
        results = {}
        for row in cursor.execute(query):
            country_code = row[0]
            results[country_code] = CountryAnomalyInfo(
                is_anomaly=bool(row[1]), registrations_cnt=int(row[2])
            )
        conn.close()
        return results


@app.post("/check_anomaly")
async def check_anomaly(
    request: AnomalyCheckRequest, algorithm: str = "zscore"
) -> Dict[str, CountryAnomalyInfo]:
    """Check for anomalies on a specific date (all countries)"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, algorithm)


@app.post("/check_anomaly/country")
async def check_country_anomaly(
    request: CountryCheckRequest, algorithm: str = "zscore"
) -> CountryAnomalyInfo:
    """Check anomaly for a specific country on a specific date"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, algorithm, request.country)


# Algorithm-specific endpoints (backward compatibility)
@app.post("/check_anomaly/zscore")
async def check_anomaly_zscore(
    request: AnomalyCheckRequest,
) -> Dict[str, CountryAnomalyInfo]:
    """Check anomalies using z-score algorithm (all countries)"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, "zscore")


@app.post("/check_anomaly/percentiles")
async def check_anomaly_percentiles(
    request: AnomalyCheckRequest,
) -> Dict[str, CountryAnomalyInfo]:
    """Check anomalies using percentiles algorithm (all countries)"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, "percentiles")


@app.post("/check_anomaly/country/zscore")
async def check_country_anomaly_zscore(
    request: CountryCheckRequest,
) -> CountryAnomalyInfo:
    """Check country anomaly using z-score algorithm"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, "zscore", request.country)


@app.post("/check_anomaly/country/percentiles")
async def check_country_anomaly_percentiles(
    request: CountryCheckRequest,
) -> CountryAnomalyInfo:
    """Check country anomaly using percentiles algorithm"""
    validate_date(request.registration_dt)
    return check_anomalies(request.registration_dt, "percentiles", request.country)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
