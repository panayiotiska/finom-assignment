import config

def get_date_anomaly_query(target_date: str) -> str:
    """Get anomaly status for a specific date using moving average + (multiplier × std_dev)"""
    return f'''
    -- Count registrations per day per country
    WITH daily_counts AS (
        SELECT
            country,
            strftime('%Y-%m-%d', reg_timestamp) as day_timestamp,
            COUNT(*) as registrations
        FROM registrations
        GROUP BY country, strftime('%Y-%m-%d', reg_timestamp)
    ),

    -- Get target date data for all countries
    target_day AS (
        SELECT
            dc.country,
            dc.day_timestamp,
            dc.registrations
        FROM daily_counts dc
        WHERE dc.day_timestamp = '{target_date}'
    )

    -- Calculate window stats and detect anomalies for target date
    SELECT
        td.country,
        CASE
            -- No data for this country on target date
            WHEN td.registrations IS NULL THEN false
            -- No previous data available for comparison
            WHEN window_stats.moving_avg IS NULL THEN false
            -- Not enough data points for reliable std_dev calculation
            WHEN window_stats.std_dev IS NULL OR window_stats.std_dev = 0 THEN
                CASE WHEN td.registrations > (window_stats.moving_avg * 1.5) THEN true ELSE false END
            -- Z-score based anomaly detection: |z| > threshold
            WHEN ABS((td.registrations - window_stats.moving_avg) / window_stats.std_dev) > {config.MULTIPLIER} THEN true
            ELSE false
        END as is_anomaly,
        COALESCE(td.registrations, 0) as registrations_cnt
    FROM (
        -- Get all countries that exist in the data
        SELECT DISTINCT country FROM daily_counts
    ) all_countries
    LEFT JOIN target_day td ON all_countries.country = td.country

    -- Calculate stats for the previous X days window (excluding target date)
    LEFT JOIN (
        SELECT
            country,
            AVG(registrations) as moving_avg,
            SQRT(AVG(POWER(registrations - sub.avg_window, 2))) as std_dev
        FROM (
            -- Get previous days before target date (up to WINDOW_DAYS, minimum 1)
            SELECT
                dc.country,
                dc.registrations
            FROM daily_counts dc
            WHERE dc.day_timestamp < '{target_date}'
            AND dc.day_timestamp >= (
                SELECT datetime('{target_date}', '-{config.WINDOW_DAYS} days')
            )
            AND dc.day_timestamp >= (
                SELECT MIN(day_timestamp) FROM daily_counts
            )
        ) window_data
        -- Calculate window average for std dev
        CROSS JOIN (
            SELECT AVG(registrations) as avg_window
            FROM daily_counts
            WHERE day_timestamp < '{target_date}'
            AND day_timestamp >= (
                SELECT datetime('{target_date}', '-{config.WINDOW_DAYS} days')
            )
            AND day_timestamp >= (
                SELECT MIN(day_timestamp) FROM daily_counts
            )
        ) sub -- sub is the window average
        GROUP BY country
    ) window_stats ON all_countries.country = window_stats.country

    ORDER BY all_countries.country
    '''


def get_country_date_anomaly_query(country: str, target_date: str) -> str:
    """Get anomaly status for a specific country on a specific date using moving average + (multiplier × std_dev)"""
    return f'''
    -- Count registrations per day for the specific country
    WITH daily_counts AS (
        SELECT
            country,
            strftime('%Y-%m-%d', reg_timestamp) as day_timestamp,
            COUNT(*) as registrations
        FROM registrations
        WHERE country = '{country}'
        GROUP BY country, strftime('%Y-%m-%d', reg_timestamp)
    ),

    -- Get target date data for the country
    target_day AS (
        SELECT
            dc.country,
            dc.day_timestamp,
            dc.registrations
        FROM daily_counts dc
        WHERE dc.day_timestamp = '{target_date}'
    )

    -- Calculate window stats and detect anomaly for the specific country and date
    SELECT
        CASE
            -- No data for this country on target date
            WHEN td.registrations IS NULL THEN false
            -- No previous data available for comparison
            WHEN window_stats.moving_avg IS NULL THEN false
            -- Not enough data points for reliable std_dev calculation
            WHEN window_stats.std_dev IS NULL OR window_stats.std_dev = 0 THEN
                CASE WHEN COALESCE(td.registrations, 0) > (window_stats.moving_avg * 1.5) THEN true ELSE false END
            -- Z-score based anomaly detection: |z| > threshold
            WHEN ABS((COALESCE(td.registrations, 0) - window_stats.moving_avg) / window_stats.std_dev) > {config.MULTIPLIER} THEN true
            ELSE false
        END as is_anomaly,
        COALESCE(td.registrations, 0) as registrations_cnt
    FROM (
        -- We know we're looking for exactly one country
        SELECT '{country}' as country
    ) target_country
    LEFT JOIN target_day td ON target_country.country = td.country

    -- Calculate stats for the previous X days window (excluding target date)
    LEFT JOIN (
        SELECT
            country,
            AVG(registrations) as moving_avg,
            SQRT(AVG(POWER(registrations - sub.avg_window, 2))) as std_dev
        FROM (
            -- Get previous days before target date (up to WINDOW_DAYS, minimum 1)
            SELECT
                dc.country,
                dc.registrations
            FROM daily_counts dc
            WHERE dc.day_timestamp < '{target_date}'
            AND dc.day_timestamp >= (
                SELECT datetime('{target_date}', '-{config.WINDOW_DAYS} days')
            )
            AND dc.day_timestamp >= (
                SELECT MIN(day_timestamp) FROM daily_counts
            )
        ) window_data
        -- Calculate window average for std dev
        CROSS JOIN (
            SELECT AVG(registrations) as avg_window
            FROM daily_counts
            WHERE day_timestamp < '{target_date}'
            AND day_timestamp >= (
                SELECT datetime('{target_date}', '-{config.WINDOW_DAYS} days')
            )
            AND day_timestamp >= (
                SELECT MIN(day_timestamp) FROM daily_counts
            )
        ) sub -- sub is the window average
        GROUP BY country
    ) window_stats ON target_country.country = window_stats.country
    '''
