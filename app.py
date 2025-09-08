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
    Includes caching to avoid recomputing results

    Args:
        target_date: Date string in YYYY-MM-DD format
        algorithm: Algorithm to use ('zscore', 'percentiles', etc.)
        country: Optional country code. If None, returns results for all countries

    Returns:
        Dict[str, CountryAnomalyInfo] if country is None, else CountryAnomalyInfo
    """
    conn = sqlite3.connect("registrations.db")
    cursor = conn.cursor()

    if country:
        # Check cache for single country
        cursor.execute(
            """
            SELECT is_anomaly, registrations_cnt FROM anomaly_results
            WHERE registration_dt = ? AND country = ? AND algorithm = ?
        """,
            (target_date, country, algorithm),
        )

        cached_result = cursor.fetchone()
        if cached_result:
            conn.close()
            is_anomaly, registrations_cnt = cached_result
            return CountryAnomalyInfo(
                is_anomaly=bool(is_anomaly), registrations_cnt=int(registrations_cnt)
            )

        # No cached result, run algorithm
        query = get_anomaly_query(target_date, algorithm, country)
        result = cursor.execute(query).fetchone()

        if result:
            is_anomaly, registrations_cnt = result
            country_info = CountryAnomalyInfo(
                is_anomaly=bool(is_anomaly), registrations_cnt=int(registrations_cnt)
            )
        else:
            # No data for this country/date combination
            country_info = CountryAnomalyInfo(is_anomaly=False, registrations_cnt=0)

        # Cache the result
        cursor.execute(
            """
            INSERT OR REPLACE INTO anomaly_results
            (registration_dt, country, is_anomaly, algorithm, registrations_cnt)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                target_date,
                country,
                bool(country_info.is_anomaly),
                algorithm,
                country_info.registrations_cnt,
            ),
        )

        conn.commit()
        conn.close()
        return country_info

    else:
        # Check cache for all countries
        cursor.execute(
            """
            SELECT country, is_anomaly, registrations_cnt FROM anomaly_results
            WHERE registration_dt = ? AND algorithm = ?
            ORDER BY country
        """,
            (target_date, algorithm),
        )

        cached_results = cursor.fetchall()

        # If we have cached results for all countries that exist in the database
        if cached_results:
            # Get all countries that should exist
            cursor.execute("SELECT DISTINCT country FROM registrations")
            all_countries = {row[0] for row in cursor.fetchall()}

            cached_countries = {row[0] for row in cached_results}

            # If we have results for all countries, return cached results
            if all_countries.issubset(cached_countries):
                results = {}
                for country_code, is_anomaly, registrations_cnt in cached_results:
                    results[country_code] = CountryAnomalyInfo(
                        is_anomaly=bool(is_anomaly),
                        registrations_cnt=int(registrations_cnt),
                    )
                conn.close()
                return results

        # Either no cached results or incomplete cache, run algorithm for all countries
        query = get_anomaly_query(target_date, algorithm, country)
        results = {}

        for row in cursor.execute(query):
            country_code = row[0]
            results[country_code] = CountryAnomalyInfo(
                is_anomaly=bool(row[1]), registrations_cnt=int(row[2])
            )

            # Cache each country's result
            cursor.execute(
                """
                INSERT OR REPLACE INTO anomaly_results
                (registration_dt, country, is_anomaly, algorithm, registrations_cnt)
                VALUES (?, ?, ?, ?, ?)
            """,
                (target_date, country_code, bool(row[1]), algorithm, int(row[2])),
            )

        conn.commit()
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
