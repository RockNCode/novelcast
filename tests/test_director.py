import unittest
from novelcast.core.director import Director, sanitize_instruct

class TestDirector(unittest.TestCase):
    def test_sanitize_instruct(self):
        raw = "female, young adult, playful, high pitch, deadpan"
        cleaned = sanitize_instruct(raw)
        self.assertEqual(cleaned, "female, young adult, high pitch")

    def test_speaker_identification(self):
        director = Director()
        # Signature phrases
        self.assertEqual(director.identify_speaker("Barusu, no seas holgazán.", "", ""), "Ram")
        self.assertEqual(director.identify_speaker("Subaru-kun, buenos días.", "", ""), "Rem")
        self.assertEqual(director.identify_speaker("¡Betty es la más increíble, supongo!", "", ""), "Beatrice")
        self.assertEqual(director.identify_speaker("¡Emilia-tan es la más linda del mundo!", "", ""), "Subaru")

    def test_emotion_analysis(self):
        director = Director()
        formatted, instruct, speed, guidance = director.analyze_emotion_and_delivery(
            "¡Cuidado Subaru!",
            prev_text="Emilia gritó con desesperación.",
            next_text="El ataque se acercaba velozmente.",
            speaker="Emilia"
        )
        self.assertTrue(formatted.startswith("[gasp]"))
        self.assertIn("female, young adult, high pitch", instruct)

if __name__ == '__main__':
    unittest.main()
