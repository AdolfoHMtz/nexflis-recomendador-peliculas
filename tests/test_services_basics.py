import unittest

from services.cache_service import CacheService
from services.db_service import DatabaseService


class TestServicesBasics(unittest.TestCase):
    def test_cache_service_set_get_delete(self):
        cache = CacheService(ttl_segundos=60)
        cache.set('k1', {'value': 1})
        self.assertEqual(cache.get('k1'), {'value': 1})

        cache.delete('k1')
        self.assertIsNone(cache.get('k1'))

    def test_database_cache_key_is_deterministic(self):
        key_a = DatabaseService.cache_key('/movie/1', {'language': 'es-MX', 'page': 1})
        key_b = DatabaseService.cache_key('/movie/1', {'page': 1, 'language': 'es-MX'})
        key_c = DatabaseService.cache_key('/movie/2', {'language': 'es-MX', 'page': 1})

        self.assertEqual(key_a, key_b)
        self.assertNotEqual(key_a, key_c)


if __name__ == '__main__':
    unittest.main()
