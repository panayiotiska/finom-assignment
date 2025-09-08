import config


def get_anomaly_query(
    target_date: str, algorithm: str = "zscore", country: str = None
) -> str:
    """
    Get anomaly status for a specific date (and optionally country) using specified algorithm

    Args:
        target_date: Date string in YYYY-MM-DD format
        algorithm: Algorithm to use ('zscore', 'percentiles', etc.)
        country: Optional country code. If None, returns results for all countries

    Returns:
        SQL query string for anomaly detection
    """
    if algorithm == "zscore":
        return get_zscore_anomaly_query(target_date, country)
    elif algorithm == "percentiles":
        return get_percentiles_anomaly_query(target_date, country)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def get_date_anomaly_query(target_date: str, algorithm: str = "zscore") -> str:
    """Backward compatibility wrapper"""
    return get_anomaly_query(target_date, algorithm)


def get_country_date_anomaly_query(
    country: str, target_date: str, algorithm: str = "zscore"
) -> str:
    """Backward compatibility wrapper"""
    return get_anomaly_query(target_date, algorithm, country)


def get_zscore_anomaly_query(target_date: str, country: str = None) -> str:
    """Get anomaly status for a specific date using z-score based anomaly detection"""
    country_filter = f"WHERE country = '{country}'" if country else ""
    country_select = (
        f"SELECT '{country}' as country"
        if country
        else "SELECT DISTINCT country FROM daily_counts"
    )
    country_join = (
        "target_country.country = td.country"
        if country
        else "all_countries.country = td.country"
    )
    country_group = (
        "target_country.country = window_stats.country"
        if country
        else "all_countries.country = window_stats.country"
    )
    country_order = "" if country else "ORDER BY all_countries.country"

    return f"""
    -- Count registrations per day per country
    WITH daily_counts AS (
        SELECT
            country,
            strftime('%Y-%m-%d', reg_timestamp) as day_timestamp,
            COUNT(*) as registrations
        FROM registrations
        {country_filter}
        GROUP BY country, strftime('%Y-%m-%d', reg_timestamp)
    ),

    -- Get target date data
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
        {"td.country," if not country else ""}
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
        -- Get countries to analyze
        {country_select}
    ) {"target_country" if country else "all_countries"}
    LEFT JOIN target_day td ON {country_join}

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
    ) window_stats ON {country_group}

    {country_order}
    """


def get_percentiles_anomaly_query(target_date: str, country: str = None) -> str:
    """Get anomaly status for a specific date using percentiles-based anomaly detection"""
    country_filter = f"WHERE country = '{country}'" if country else ""
    country_select = (
        f"SELECT '{country}' as country"
        if country
        else "SELECT DISTINCT country FROM daily_counts"
    )
    country_join = (
        "target_country.country = td.country"
        if country
        else "all_countries.country = td.country"
    )
    country_join_ps = (
        "target_country.country = ps.country"
        if country
        else "all_countries.country = ps.country"
    )
    country_order = "" if country else "ORDER BY all_countries.country"

    return f"""
    -- Count registrations per day per country
    WITH daily_counts AS (
        SELECT
            country,
            strftime('%Y-%m-%d', reg_timestamp) as day_timestamp,
            COUNT(*) as registrations
        FROM registrations
        {country_filter}
        GROUP BY country, strftime('%Y-%m-%d', reg_timestamp)
    ),

    -- Get target date data
    target_day AS (
        SELECT
            dc.country,
            dc.day_timestamp,
            dc.registrations
        FROM daily_counts dc
        WHERE dc.day_timestamp = '{target_date}'
    ),

    -- Calculate percentile-based thresholds
    percentile_stats AS (
        SELECT
            country,
            registrations as threshold_95
        FROM (
            SELECT
                country,
                registrations,
                ROW_NUMBER() OVER (PARTITION BY country ORDER BY registrations DESC) as row_num,
                COUNT(*) OVER (PARTITION BY country) as total_count
            FROM daily_counts
            WHERE day_timestamp < '{target_date}'
            AND day_timestamp >= (
                SELECT datetime('{target_date}', '-{config.WINDOW_DAYS} days')
            )
            AND day_timestamp >= (
                SELECT MIN(day_timestamp) FROM daily_counts
            )
        )
        WHERE CAST(row_num AS FLOAT) / total_count <= {config.PERCENTILE_THRESHOLD}
    )

    -- Detect anomalies using percentile thresholds
    SELECT
        {"td.country," if not country else ""}
        CASE
            -- No data for this country on target date
            WHEN td.registrations IS NULL THEN false
            -- No previous data available for comparison
            WHEN ps.threshold_95 IS NULL THEN false
            -- Check if target value exceeds the percentile threshold
            WHEN COALESCE(td.registrations, 0) > ps.threshold_95 THEN true
            ELSE false
        END as is_anomaly,
        COALESCE(td.registrations, 0) as registrations_cnt
    FROM (
        -- Get countries to analyze
        {country_select}
    ) {"target_country" if country else "all_countries"}
    LEFT JOIN target_day td ON {country_join}
    LEFT JOIN percentile_stats ps ON {country_join_ps}

    {country_order}
    """
