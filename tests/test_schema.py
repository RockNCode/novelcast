import unittest
from novelcast.core.schema import Segment, ChapterScript, CharacterVoice, VoiceConfig

class TestSchema(unittest.TestCase):
    def test_segment_hash_generation(self):
        seg1 = Segment(id=1, speaker="Subaru", text="¡Hola Emilia!", speed=1.0, guidance_scale=2.8)
        hash1 = seg1.compute_hash()

        seg2 = Segment(id=1, speaker="Subaru", text="¡Hola Emilia!", speed=1.0, guidance_scale=2.8)
        hash2 = seg2.compute_hash()

        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 12)

        # Different text should produce different hash
        seg3 = Segment(id=1, speaker="Subaru", text="¡Hola Rem!", speed=1.0, guidance_scale=2.8)
        self.assertNotEqual(seg3.compute_hash(), hash1)

    def test_chapter_script_properties(self):
        script = ChapterScript(
            title="Chapter 1",
            chapter_id="01_cap",
            segments=[
                Segment(id=1, speaker="Narrador", text="Había una vez."),
                Segment(id=2, speaker="Emilia", text="Buenos días, Subaru.")
            ]
        )
        self.assertEqual(script.total_characters, len("Había una vez.") + len("Buenos días, Subaru."))
        self.assertEqual(script.dialogue_count, 1)

    def test_voice_config(self):
        cfg = VoiceConfig(
            default_narrator="Narrador",
            characters={
                "Subaru": CharacterVoice(gender="male", speed=1.05)
            }
        )
        self.assertIn("Subaru", cfg.characters)
        self.assertEqual(cfg.characters["Subaru"].speed, 1.05)

if __name__ == '__main__':
    unittest.main()
