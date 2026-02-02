import json
import os
from datetime import datetime, timedelta
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Простий файловий кеш для графіків"""

    def __init__(self, cache_dir: str = "cache", ttl_minutes: int = 30):
        """
        Args:
            cache_dir: Директорія для кешу
            ttl_minutes: Час життя кешу в хвилинах
        """
        self.cache_dir = cache_dir
        self.ttl = timedelta(minutes=ttl_minutes)

        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """Отримати шлях до файлу кешу"""
        safe_key = key.replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def get(self, key: str) -> Optional[Any]:
        """Отримати значення з кешу"""
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            logger.debug(f"Cache miss for key: {key}")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Check if cache is still valid
            cached_at = datetime.fromisoformat(cached_data['cached_at'])
            if datetime.now() - cached_at > self.ttl:
                logger.debug(f"Cache expired for key: {key}")
                os.remove(cache_path)
                return None

            logger.debug(f"Cache hit for key: {key}")
            return cached_data['data']

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Invalid cache file for key {key}: {e}")
            # Remove corrupted cache file
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return None

    def set(self, key: str, value: Any) -> None:
        """Зберегти значення в кеш"""
        cache_path = self._get_cache_path(key)

        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': value
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Cached data for key: {key}")

        except Exception as e:
            logger.error(f"Failed to cache data for key {key}: {e}")

    def clear(self, key: Optional[str] = None) -> None:
        """Очистити кеш (конкретний ключ або весь кеш)"""
        if key:
            cache_path = self._get_cache_path(key)
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.info(f"Cleared cache for key: {key}")
        else:
            # Clear all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            logger.info("Cleared all cache")

    def get_cache_info(self) -> dict:
        """Отримати інформацію про кеш"""
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]

        info = {
            'total_files': len(cache_files),
            'files': []
        }

        for filename in cache_files:
            cache_path = os.path.join(self.cache_dir, filename)
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cached_at = datetime.fromisoformat(data['cached_at'])
                    age = datetime.now() - cached_at
                    is_valid = age <= self.ttl

                    info['files'].append({
                        'key': filename.replace('.json', ''),
                        'cached_at': data['cached_at'],
                        'age_minutes': int(age.total_seconds() / 60),
                        'is_valid': is_valid
                    })
            except Exception as e:
                logger.warning(f"Error reading cache file {filename}: {e}")

        return info
