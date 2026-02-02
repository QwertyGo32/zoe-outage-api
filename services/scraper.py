import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional, Tuple
import urllib3
from datetime import datetime
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ScraperService:
    """Сервіс для парсингу графіків відключень з ZOE.COM.UA"""

    BASE_URL = "https://www.zoe.com.ua/outage/"
    TIMEOUT = 30  # Increased from 10 to 30 seconds
    MAX_RETRIES = 3

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        # Add User-Agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })

    def fetch_schedules(self) -> List[Dict]:
        """Отримати всі графіки зі сторінки"""
        last_error = None

        # Retry logic with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    import time
                    wait_time = 2 ** attempt  # 2, 4, 8 seconds
                    logger.info(f"Retry attempt {attempt + 1}/{self.MAX_RETRIES} after {wait_time}s")
                    time.sleep(wait_time)

                logger.info(f"Fetching schedules from {self.BASE_URL} (attempt {attempt + 1})")
                response = self.session.get(self.BASE_URL, timeout=self.TIMEOUT)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('article')

                logger.info(f"Found {len(articles)} articles")

                schedules = []
                for idx, article in enumerate(articles):
                    schedule = self._parse_article(article, idx)
                    if schedule:
                        schedules.append(schedule)

                return schedules

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
                continue
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.error(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    break
                continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

        # All retries failed
        logger.error(f"Failed after {self.MAX_RETRIES} attempts. Last error: {last_error}")
        raise Exception(f"Failed to fetch schedules after {self.MAX_RETRIES} attempts: {str(last_error)}")

    def _parse_article(self, article, index: int) -> Optional[Dict]:
        """Парсинг окремої статті"""
        try:
            schedule_data = {
                'index': index,
                'title': '',
                'date': '',
                'content_text': '',
                'queues': [],
                'times': [],
                'parsed_at': datetime.now().isoformat()
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
                text = content_elem.get_text(separator='\n', strip=True)
                schedule_data['content_text'] = text

                # Find queue numbers (1.1, 1.2, etc.)
                queue_pattern = r'(\d+\.\d+)'
                queues_found = re.findall(queue_pattern, text)
                schedule_data['queues'] = list(set(queues_found))  # Unique

                # Find time ranges (00:00-04:30 or з 00:00 до 04:30)
                time_pattern = r'(\d{1,2}:\d{2})\s*[-–—до]\s*(\d{1,2}:\d{2})'
                times_found = re.findall(time_pattern, text)
                schedule_data['times'] = [[start, end] for start, end in times_found[:20]]

            return schedule_data

        except Exception as e:
            logger.warning(f"Failed to parse article {index}: {e}")
            return None

    def get_latest_schedule(self) -> Optional[Dict]:
        """Отримати найсвіжіший актуальний графік"""
        schedules = self.fetch_schedules()

        if not schedules:
            return None

        # Find first schedule with queues and times
        for schedule in schedules:
            if schedule.get('queues') and schedule.get('times'):
                # Check if it's not a cancellation notice
                title_lower = schedule.get('title', '').lower()
                if 'скасовано' not in title_lower and 'увага' not in title_lower:
                    return schedule

        # If no active schedule found, return first one with data
        for schedule in schedules:
            if schedule.get('queues') and schedule.get('times'):
                return schedule

        return schedules[0] if schedules else None

    def get_queue_schedule(self, queue_id: str) -> Optional[Dict]:
        """Отримати графік для конкретної черги"""
        latest = self.get_latest_schedule()

        if not latest:
            return None

        if queue_id not in latest.get('queues', []):
            return {
                'queue': queue_id,
                'title': latest.get('title', ''),
                'date': latest.get('date', ''),
                'outages': [],
                'status': 'no_data',
                'message': f'Черга {queue_id} не знайдена в поточному графіку'
            }

        # Extract times for this queue
        # Note: This is simplified - in real implementation you'd need to parse
        # the content more carefully to match times to specific queues
        outages = []
        for time_range in latest.get('times', [])[:10]:  # Limit to reasonable number
            if len(time_range) == 2:
                outages.append({
                    'start': time_range[0],
                    'end': time_range[1]
                })

        return {
            'queue': queue_id,
            'title': latest.get('title', ''),
            'date': latest.get('date', ''),
            'outages': outages,
            'status': 'active',
            'content_text': latest.get('content_text', '')[:500]
        }

    def parse_queue_specific_times(self, content: str, queue_id: str) -> List[Tuple[str, str]]:
        """
        Парсинг часів для конкретної черги з тексту
        Приклад: "1.1: 03:00 – 08:00, 12:00 – 17:00"
        """
        times = []

        # Pattern to find queue-specific times
        # Looking for "1.1: 03:00 – 08:00, 12:00 – 17:00"
        pattern = rf'{re.escape(queue_id)}:\s*((?:\d{{1,2}}:\d{{2}}\s*[-–—]\s*\d{{1,2}}:\d{{2}},?\s*)+)'

        match = re.search(pattern, content)
        if match:
            time_str = match.group(1)
            # Extract all time ranges from this string
            time_pattern = r'(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})'
            times = re.findall(time_pattern, time_str)

        return times

    def get_all_queues(self) -> List[str]:
        """Отримати список всіх доступних черг"""
        latest = self.get_latest_schedule()
        if latest and latest.get('queues'):
            return sorted(latest.get('queues', []))
        return ['1.1', '1.2', '2.1', '2.2', '3.1', '3.2', '4.1', '4.2', '5.1', '5.2', '6.1', '6.2']
