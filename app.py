import sqlite3
from fastapi import FastAPI, HTTPException
from typing import Dict
from pydantic import BaseModel
import config
from queries import get_date_anomaly_query, get_country_date_anomaly_query

app = FastAPI(title="Anomaly Detection API")

class AnomalyCheckRequest(BaseModel):
    registration_dt: str


class CountryAnomalyInfo(BaseModel):
    is_anomaly: bool
    registrations_cnt: int


class CountryCheckRequest(BaseModel):
    country: str
    registration_dt: str


def check_date_anomalies(target_date: str) -> Dict[str, CountryAnomalyInfo]:
    """
    Check anomalies for a specific date using moving average + (multiplier × std_dev)

    Args:
        target_date: Date string in YYYY-MM-DD format

    Returns:
        Dict[str, CountryAnomalyInfo]: Dictionary mapping country codes to anomaly info
    """
    conn = sqlite3.connect('registrations.db')
    cursor = conn.cursor()

    # Get the date-specific anomaly detection query
    query = get_date_anomaly_query(target_date)

    results = {}
    for row in cursor.execute(query):
        country = row[0]
        results[country] = CountryAnomalyInfo(
            is_anomaly=bool(row[1]),
            registrations_cnt=int(row[2])
        )

    conn.close()
    return results




@app.post("/check_anomaly")
async def check_anomaly(request: AnomalyCheckRequest) -> Dict[str, CountryAnomalyInfo]:
    """
    Check for anomalies on a specific date

    Args:
        request: Contains the registration_dt field with date in YYYY-MM-DD format

    Returns:
        Dictionary mapping country codes to anomaly information
    """
    try:
        # Validate date format
        from datetime import datetime
        datetime.strptime(request.registration_dt, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    return check_date_anomalies(request.registration_dt)


def check_country_date_anomaly(country: str, target_date: str) -> CountryAnomalyInfo:
    """
    Check anomaly for a specific country on a specific date using moving average + (multiplier × std_dev)

    Args:
        country: Country code
        target_date: Date string in YYYY-MM-DD format

    Returns:
        CountryAnomalyInfo: Anomaly information for the country
    """
    conn = sqlite3.connect('registrations.db')
    cursor = conn.cursor()

    # Get the country-date specific anomaly detection query
    query = get_country_date_anomaly_query(country, target_date)

    result = cursor.execute(query).fetchone()
    if result:
        is_anomaly, registrations_cnt = result
        country_info = CountryAnomalyInfo(
            is_anomaly=bool(is_anomaly),
            registrations_cnt=int(registrations_cnt)
        )
    else:
        # No data for this country/date combination
        country_info = CountryAnomalyInfo(
            is_anomaly=False,
            registrations_cnt=0
        )

    conn.close()
    return country_info


@app.post("/check_anomaly/country")
async def check_country_anomaly(request: CountryCheckRequest) -> CountryAnomalyInfo:
    """
    Check anomaly for a specific country on a specific date

    Args:
        request: Contains country and registration_dt fields

    Returns:
        CountryAnomalyInfo: Anomaly information for the specific country
    """
    try:
        # Validate date format
        from datetime import datetime
        datetime.strptime(request.registration_dt, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    return check_country_date_anomaly(request.country, request.registration_dt)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
