import unittest
from novelcast.dub.translator import ScriptTranslator
from novelcast.dub.transcriber import AudioTranscriber

class TestDubbingModules(unittest.TestCase):
    def test_script_translator_build(self):
        translator = ScriptTranslator()
        raw_segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello world, this is a test.", "speaker": "Narrator"},
            {"start": 3.0, "end": 5.0, "text": "What are you doing here?!", "speaker": "Subaru"}
        ]
        script = translator.build_chapter_script(
            chapter_title="Test Chapter",
            chapter_id="test_01",
            segments=raw_segments,
            from_lang="en",
            to_lang="es"
        )
        self.assertEqual(len(script.segments), 2)
        self.assertEqual(script.segments[0].speaker, "Narrator")
        self.assertEqual(script.segments[1].speaker, "Subaru")
        self.assertIsNotNone(script.segments[1].instruct)
        self.assertTrue(script.segments[0].pause_after_ms > 0)

    def test_transcriber_initialization(self):
        transcriber = AudioTranscriber(model_size="base")
        self.assertEqual(transcriber.model_size, "base")

if __name__ == '__main__':
    unittest.main()
