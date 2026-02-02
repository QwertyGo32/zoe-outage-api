import requests
import json
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_wordpress_api():
    base_url = "https://www.zoe.com.ua"
    wp_json_url = f"{base_url}/wp-json"

    print("=" * 60)
    print("Checking WordPress REST API")
    print("=" * 60)

    try:
        # Get API index
        print("\n[1] Getting API index...")
        response = requests.get(wp_json_url, verify=False, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Save full response
            with open("wp_api_index.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("[OK] API index saved to wp_api_index.json")

            # Look for interesting routes
            if 'routes' in data:
                print("\n[2] Available routes:")
                routes = data['routes']
                if isinstance(routes, dict):
                    for route in routes.keys():
                        if 'outage' in route.lower() or 'schedule' in route.lower():
                            print(f"  [INTERESTING] {route}")
                elif isinstance(routes, list):
                    for route in routes:
                        if isinstance(route, str) and ('outage' in route.lower() or 'schedule' in route.lower()):
                            print(f"  [INTERESTING] {route}")

        # Try to get posts of type 'outage_schedules'
        print("\n[3] Trying to fetch outage schedules...")

        possible_endpoints = [
            "/wp-json/wp/v2/outage_schedules",
            "/wp-json/wp/v2/outage",
            "/wp-json/wp/v2/posts?post_type=outage_schedules",
        ]

        for endpoint in possible_endpoints:
            try:
                url = f"{base_url}{endpoint}"
                print(f"\n  Testing: {endpoint}")
                r = requests.get(url, verify=False, timeout=5)

                if r.status_code == 200:
                    print(f"    [OK] Status {r.status_code}")
                    data = r.json()

                    # Save response
                    filename = endpoint.split('/')[-1].replace('?', '_') + '.json'
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"    [OK] Saved to {filename}")

                    # Print first item structure
                    if isinstance(data, list) and len(data) > 0:
                        print(f"    Found {len(data)} items")
                        print(f"    First item keys: {list(data[0].keys())}")

                        if 'title' in data[0]:
                            print(f"    First title: {data[0]['title'].get('rendered', 'N/A')[:80]}")
                        if 'date' in data[0]:
                            print(f"    Date: {data[0]['date']}")
                        if 'content' in data[0]:
                            content = data[0]['content'].get('rendered', '')
                            print(f"    Content length: {len(content)} chars")

                else:
                    print(f"    Status {r.status_code}")

            except Exception as e:
                print(f"    Error: {e}")

        # Try pagination
        print("\n[4] Checking pagination...")
        url = f"{base_url}/wp-json/wp/v2/outage_schedules?per_page=10&page=1"
        try:
            r = requests.get(url, verify=False, timeout=10)
            if r.status_code == 200:
                data = r.json()
                print(f"  [OK] Got {len(data)} schedules")

                # Check headers for total count
                total = r.headers.get('X-WP-Total')
                total_pages = r.headers.get('X-WP-TotalPages')
                if total:
                    print(f"  Total schedules available: {total}")
                if total_pages:
                    print(f"  Total pages: {total_pages}")

                # Save first page
                with open("outage_schedules_page1.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print("  [OK] Saved to outage_schedules_page1.json")

        except Exception as e:
            print(f"  Error: {e}")

        print("\n" + "=" * 60)
        print("API check complete!")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_wordpress_api()
