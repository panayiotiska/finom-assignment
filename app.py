import sqlite3
from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
import config
from queries import get_max_hour_anomaly_query

app = FastAPI(title="Anomaly Detection API")

class RegistrationOutput(BaseModel):
    country: str
    reg_timestamp: str
    is_anomaly: bool


def detect_max_hour_anomalies() -> List[RegistrationOutput]:
    """
    Detect anomalies for max available hour using moving average + (multiplier × std_dev)
    Needs to be run every hour at time XX:58

    Returns:
        List[RegistrationOutput]: List of registration outputs
    """
    conn = sqlite3.connect('registrations.db')
    cursor = conn.cursor()

    # Get the max hour anomaly detection query
    query = get_max_hour_anomaly_query()

    results = []
    for row in cursor.execute(query):
        results.append(RegistrationOutput(
            country=row[0],
            reg_timestamp=row[1],
            is_anomaly=bool(row[2])
        ))

    conn.close()
    return results


@app.get("/anomalies", response_model=List[RegistrationOutput])
async def get_anomalies():
    """Get max available hour anomaly detection results"""
    return detect_max_hour_anomalies()

@app.get("/anomalies/{country}", response_model=List[RegistrationOutput])
async def get_anomalies_by_country(country: str):
    """Get max available hour anomaly detection results for specific country"""
    all_results = detect_max_hour_anomalies()
    return [r for r in all_results if r.country == country]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
