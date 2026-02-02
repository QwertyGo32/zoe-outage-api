import requests
from bs4 import BeautifulSoup
import re
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_outage_schedules():
    """Parse outage schedules from ZOE website"""
    base_url = "https://www.zoe.com.ua/outage/"

    print("=" * 60)
    print("Parsing Outage Schedules")
    print("=" * 60)

    try:
        response = requests.get(base_url, verify=False, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all articles/posts on the page
        articles = soup.find_all('article')

        print(f"\nFound {len(articles)} articles/posts on the page")

        schedules = []

        for idx, article in enumerate(articles):
            schedule_data = {
                'index': idx,
                'title': '',
                'date': '',
                'content_text': '',
                'queues': []
            }

            # Get title
            title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                schedule_data['title'] = title_elem.get_text(strip=True)

            # Get date
            date_elem = article.find('time')
            if date_elem:
                schedule_data['date'] = date_elem.get('datetime', date_elem.get_text(strip=True))

            # Get content
            content_elem = article.find(['div', 'section'], class_=re.compile(r'content|entry'))
            if content_elem:
                # Get text content
                text = content_elem.get_text(separator='\n', strip=True)
                schedule_data['content_text'] = text[:500]  # First 500 chars

                # Try to find queue information
                # Looking for patterns like "1.1", "1.2", "2.1", etc.
                queue_pattern = r'(\d+\.\d+)'
                queues_found = re.findall(queue_pattern, text)

                # Look for time patterns like "00:00-04:30" or "з 00:00 до 04:30"
                time_pattern = r'(\d{1,2}:\d{2})\s*[-–—до]\s*(\d{1,2}:\d{2})'
                times_found = re.findall(time_pattern, text)

                schedule_data['queues'] = list(set(queues_found))  # Unique queues
                schedule_data['times'] = times_found[:10]  # First 10 time ranges

            schedules.append(schedule_data)

            print(f"\n--- Schedule {idx + 1} ---")
            print(f"Title: {schedule_data['title'][:80]}")
            print(f"Date: {schedule_data['date']}")
            print(f"Queues found: {schedule_data['queues'][:10]}")
            if schedule_data.get('times'):
                print(f"Times: {schedule_data['times'][:5]}")

        # Save to JSON
        with open("parsed_schedules.json", "w", encoding="utf-8") as f:
            json.dump(schedules, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print(f"[OK] Parsed {len(schedules)} schedules")
        print("[OK] Saved to parsed_schedules.json")
        print("=" * 60)

        # Try to find individual schedule page
        if schedules and schedules[0]['title']:
            print("\n[Attempting to fetch individual schedule page...]")

            # Find first schedule link
            first_link = soup.find('a', href=re.compile(r'/outage-schedules/'))
            if not first_link:
                first_link = soup.find('article').find('a')

            if first_link:
                schedule_url = first_link.get('href')
                if not schedule_url.startswith('http'):
                    schedule_url = 'https://www.zoe.com.ua' + schedule_url

                print(f"Fetching: {schedule_url}")

                try:
                    schedule_response = requests.get(schedule_url, verify=False, timeout=10)
                    schedule_soup = BeautifulSoup(schedule_response.text, 'html.parser')

                    # Save the HTML
                    with open("single_schedule.html", "w", encoding="utf-8") as f:
                        f.write(schedule_response.text)

                    print("[OK] Individual schedule saved to single_schedule.html")

                    # Try to find structured data
                    json_ld = schedule_soup.find('script', type='application/ld+json')
                    if json_ld:
                        print("[OK] Found JSON-LD structured data")
                        with open("schedule_json_ld.json", "w", encoding="utf-8") as f:
                            f.write(json_ld.string)

                except Exception as e:
                    print(f"Error fetching individual schedule: {e}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parse_outage_schedules()
