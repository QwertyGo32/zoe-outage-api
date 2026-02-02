import requests
import json
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def investigate_zoe_site():
    base_url = "https://www.zoe.com.ua/outage/"

    print("=" * 60)
    print("Investigating ZOE.COM.UA outage page")
    print("=" * 60)

    try:
        # Try to get the main page
        print("\n[1] Fetching main page...")
        response = requests.get(base_url, verify=False, timeout=10)
        print(f"Status Code: {response.status_code}")

        # Save HTML for inspection
        with open("outage_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("[OK] HTML saved to outage_page.html")

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for script tags
        print("\n[2] Looking for JavaScript files and API calls...")
        scripts = soup.find_all('script')

        api_patterns = [
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.[get|post]+\(["\']([^"\']+)["\']',
            r'\.get\(["\']([^"\']+)["\']',
            r'url:\s*["\']([^"\']+)["\']',
            r'api["\']:\s*["\']([^"\']+)["\']',
            r'/api/[^"\'\s]+',
        ]

        found_urls = set()

        for script in scripts:
            if script.string:
                for pattern in api_patterns:
                    matches = re.findall(pattern, script.string)
                    found_urls.update(matches)

            # Check src attributes
            if script.get('src'):
                src = script.get('src')
                print(f"  Script: {src}")

                # Try to fetch and analyze external scripts
                if src.startswith('http') or src.startswith('//'):
                    script_url = src if src.startswith('http') else 'https:' + src
                else:
                    script_url = urljoin(base_url, src)

                try:
                    script_response = requests.get(script_url, verify=False, timeout=5)
                    for pattern in api_patterns:
                        matches = re.findall(pattern, script_response.text)
                        found_urls.update(matches)
                except:
                    pass

        if found_urls:
            print("\n[3] Found potential API endpoints:")
            for url in found_urls:
                print(f"  - {url}")
        else:
            print("\n[3] No obvious API endpoints found in JavaScript")

        # Look for data attributes
        print("\n[4] Looking for data attributes...")
        elements_with_data = soup.find_all(attrs={"data-queue": True})
        elements_with_data += soup.find_all(attrs={"data-schedule": True})
        elements_with_data += soup.find_all(attrs={"data-outage": True})

        if elements_with_data:
            print(f"  Found {len(elements_with_data)} elements with data attributes")

        # Try common API endpoints
        print("\n[5] Testing common API endpoint patterns...")
        possible_endpoints = [
            "/api/outages",
            "/api/schedule",
            "/api/queues",
            "/outage/api",
            "/outage/data",
            "/outage.json",
            "/api/v1/outages",
            "/graphql",
        ]

        for endpoint in possible_endpoints:
            try:
                test_url = urljoin("https://www.zoe.com.ua", endpoint)
                r = requests.get(test_url, verify=False, timeout=3)
                if r.status_code == 200:
                    print(f"  [OK] {endpoint} - Status {r.status_code}")
                    try:
                        data = r.json()
                        print(f"    JSON Response: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
                    except:
                        print(f"    Response (first 200 chars): {r.text[:200]}")
            except:
                pass

        # Check network tab simulation - look for iframe or embedded content
        print("\n[6] Looking for iframes or embedded content...")
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            print(f"  iframe src: {iframe.get('src')}")

        print("\n" + "=" * 60)
        print("Investigation complete! Check outage_page.html for details.")
        print("=" * 60)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    investigate_zoe_site()
