import urllib.request
import json
import time
import subprocess
import sys
import sqlite3


def start_server():
    """Start the FastAPI server in background"""
    print("Starting server...")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)  # Wait for server to start
    return process


def test_endpoint(url, data, description):
    """Test an endpoint and return the result"""
    print(f"\nTesting: {description}")
    print(f"URL: {url}")
    print(f"Data: {data}")

    try:
        # Prepare the request
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result_data = response.read().decode("utf-8")
                result = json.loads(result_data)
                print(f"Status: {response.status}")
                print(f"Results: {len(result)} countries checked")
                # Show a few example results
                if result:
                    sample_country = list(result.keys())[0]
                    print(
                        f"Sample result for {sample_country}: {result[sample_country]}"
                    )
                return result
            else:
                print(f"Status: {response.status}")
                return None
    except urllib.error.URLError as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def test_caching(base_url, test_date, test_country):
    """Test basic caching functionality"""
    print("\nTesting caching...")

    # Clear existing cache for test date to ensure clean test
    conn = sqlite3.connect("registrations.db")
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM anomaly_results WHERE registration_dt = ?", (test_date,)
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM anomaly_results")
    initial_count = cursor.fetchone()[0]

    # Make first request
    result1 = test_endpoint(
        f"{base_url}/check_anomaly/zscore",
        {"registration_dt": test_date},
        "First request to cache results",
    )

    # Check if cache was populated
    cursor.execute("SELECT COUNT(*) FROM anomaly_results")
    after_first_count = cursor.fetchone()[0]

    # Make same request again
    result2 = test_endpoint(
        f"{base_url}/check_anomaly/zscore",
        {"registration_dt": test_date},
        "Second request to test cache reuse",
    )

    # Check if cache count stayed the same
    cursor.execute("SELECT COUNT(*) FROM anomaly_results")
    after_second_count = cursor.fetchone()[0]
    conn.close()

    # Test results
    cache_created = after_first_count > initial_count
    cache_reused = after_second_count == after_first_count
    results_identical = result1 == result2

    print(f"Cache created: {cache_created}")
    print(f"Cache reused: {cache_reused}")
    print(f"Results identical: {results_identical}")

    success = cache_created and cache_reused and results_identical
    print(f"Caching test: {'PASS' if success else 'FAIL'}")

    return success


def main():
    # Start the server
    server_process = start_server()

    try:
        base_url = "http://localhost:8000"

        # Test data
        test_date = "2025-09-08"
        test_country = "US"

        print("Testing Anomaly Detection API Endpoints")
        print("=" * 50)

        # Test 1: Z-score algorithm for all countries
        result1 = test_endpoint(
            f"{base_url}/check_anomaly/zscore",
            {"registration_dt": test_date},
            "Z-score algorithm (all countries)",
        )

        # Test 2: Percentiles algorithm for all countries
        result2 = test_endpoint(
            f"{base_url}/check_anomaly/percentiles",
            {"registration_dt": test_date},
            "Percentiles algorithm (all countries)",
        )

        # Test 3: Z-score algorithm for specific country
        result3 = test_endpoint(
            f"{base_url}/check_anomaly/country/zscore",
            {"country": test_country, "registration_dt": test_date},
            f"Z-score algorithm (country: {test_country})",
        )

        # Test 4: Percentiles algorithm for specific country
        result4 = test_endpoint(
            f"{base_url}/check_anomaly/country/percentiles",
            {"country": test_country, "registration_dt": test_date},
            f"Percentiles algorithm (country: {test_country})",
        )

        # Test 5: Backward compatibility - default algorithm
        result5 = test_endpoint(
            f"{base_url}/check_anomaly",
            {"registration_dt": test_date},
            "Backward compatibility (default algorithm)",
        )

        # Test 6: Caching behavior
        caching_test_result = test_caching(base_url, test_date, test_country)

        print("\n" + "=" * 50)
        print("SUMMARY")

        # Compare results between algorithms
        if result1 and result2:
            anomalies_zscore = sum(
                1 for country, info in result1.items() if info["is_anomaly"]
            )
            anomalies_percentiles = sum(
                1 for country, info in result2.items() if info["is_anomaly"]
            )

            print("\nAlgorithm Comparison:")
            print(f"Z-score detected {anomalies_zscore} anomalies")
            print(f"Percentiles detected {anomalies_percentiles} anomalies")

        # Check backward compatibility
        if result1 and result5:
            if result1 == result5:
                print("Backward compatibility maintained")
            else:
                print("Backward compatibility issue detected")

        # Report caching test results
        if caching_test_result:
            print("Caching system tests: PASSED")
        else:
            print("Caching system tests: FAILED")

        print("\nAll tests completed")
        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

    finally:
        server_process.terminate()
        server_process.wait()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
