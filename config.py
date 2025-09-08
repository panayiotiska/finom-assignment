# Configuration for anomaly detection
WINDOW_DAYS = 4  # Moving average window size (days to look back)
MULTIPLIER = 2  # Standard deviation multiplier for anomaly threshold (z-score)
PERCENTILE_THRESHOLD = 0.05  # Percentile threshold for percentiles-based detection (0.05 = 95th percentile)
