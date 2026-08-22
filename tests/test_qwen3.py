import unittest
from novelcast.engines import get_engine, Qwen3TTSEngine
from novelcast.core.schema import Segment

class TestQwen3Engine(unittest.TestCase):
    def test_engine_factory(self):
        engine = get_engine("qwen3", remote_url="http://192.168.0.180:9881/synthesize")
        self.assertIsInstance(engine, Qwen3TTSEngine)
        self.assertEqual(engine.name, "qwen3")
        self.assertEqual(engine.remote_url, "http://192.168.0.180:9881/synthesize")

    def test_cache_path_generation(self):
        engine = get_engine("qwen3", cache_dir="cache_qwen3")
        seg = Segment(id=1, speaker="Emilia", text="Hola Subaru.")
        cache_path = engine.get_cache_path(seg)
        self.assertTrue(cache_path.startswith("cache_qwen3"))
        self.assertTrue("emilia" in cache_path.lower())
        self.assertTrue(cache_path.endswith(".mp3"))

if __name__ == '__main__':
    unittest.main()
