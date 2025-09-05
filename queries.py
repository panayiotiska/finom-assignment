import config

def get_max_hour_anomaly_query() -> str:
    """Get anomaly status using moving average + (multiplier × std_dev) for max available hour"""
    return f'''
    -- Count registrations per hour per country
    WITH hourly_counts AS (
        SELECT
            country,
            strftime('%Y-%m-%d %H:00:00', reg_timestamp) as hour_timestamp,
            COUNT(*) as registrations
        FROM registrations
        GROUP BY country, strftime('%Y-%m-%d %H:00:00', reg_timestamp)
    ),

    -- Get max available hour data
    max_hour AS (
        SELECT
            country,
            MAX(hour_timestamp) as hour_timestamp,
            SUM(registrations) as registrations
        FROM hourly_counts
        GROUP BY country
    )

    -- Calculate window stats and detect anomalies
    SELECT
        mh.country,
        mh.hour_timestamp,
        CASE
            -- No previous data available
            WHEN window_stats.moving_avg IS NULL THEN false
            -- Max hour exceeds threshold: avg + (multiplier × std_dev)
            WHEN mh.registrations > window_stats.moving_avg + ({config.MULTIPLIER} * window_stats.std_dev) THEN true
            ELSE false
        END as is_anomaly
    FROM max_hour mh

    -- Calculate stats for the previous X hours window
    LEFT JOIN (
        SELECT
            country,
            AVG(registrations) as moving_avg,
            SQRT(AVG(POWER(registrations - sub.avg_window, 2))) as std_dev
        FROM (
            -- Get previous X hours for max hour
            SELECT
                hc.country,
                hc.registrations
            FROM hourly_counts hc
            WHERE hc.hour_timestamp <= (
                SELECT MAX(hour_timestamp) FROM max_hour
            )
            AND hc.hour_timestamp > (
                SELECT datetime(MAX(hour_timestamp), '-{config.WINDOW_HOURS} hours') FROM max_hour
            )
        ) window_data
        -- Calculate window average for std dev
        -- using CROSS JOIN instead of JOIN to avoid duplicate rows
        CROSS JOIN (
            SELECT AVG(registrations) as avg_window
            FROM hourly_counts
            WHERE hour_timestamp <= (
                SELECT MAX(hour_timestamp) FROM max_hour
            )
            AND hour_timestamp > (
                SELECT datetime(MAX(hour_timestamp), '-{config.WINDOW_HOURS} hours') FROM max_hour
            )
        ) sub -- sub is the window average
        GROUP BY country
    ) window_stats ON mh.country = window_stats.country

    ORDER BY mh.country
    '''
