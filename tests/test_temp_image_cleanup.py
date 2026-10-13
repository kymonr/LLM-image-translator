import configparser
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import LLMtranslator


class TempImageCleanupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture.cleanup)
        self.root = Path(self.fixture.name)
        self.config_path = self.root / 'offline.ini'
        config = configparser.ConfigParser()
        config['Translator'] = {
            'api_key': 'offline-test-placeholder',
            'api_base': 'https://offline.invalid',
        }
        with self.config_path.open('w', encoding='utf-8') as config_file:
            config.write(config_file)
        self.image = Image.new('RGB', (4, 4), 'white')
        self.addCleanup(self.image.close)
        self.temp_paths = []
        named_temporary_file = tempfile.NamedTemporaryFile

        def create_temp_file(*args, **kwargs):
            kwargs['dir'] = self.root
            temporary_file = named_temporary_file(*args, **kwargs)
            self.temp_paths.append(Path(temporary_file.name))
            return temporary_file

        self.temp_patch = patch('tempfile.NamedTemporaryFile', side_effect=create_temp_file)
        self.temp_patch.start()
        self.addCleanup(self.temp_patch.stop)
        self.request_patch = patch('LLMtranslator.requests.post', side_effect=AssertionError('network forbidden'))
        self.request_patch.start()
        self.addCleanup(self.request_patch.stop)

    def run_translation(self, image=None):
        return LLMtranslator.process_image_translation(
            self.image if image is None else image, str(self.config_path)
        )

    def assert_temp_removed(self):
        self.assertEqual(len(self.temp_paths), 1)
        self.assertFalse(self.temp_paths[0].exists(), 'owned temporary image must be removed')
        self.assertEqual(self.image.getpixel((0, 0)), (255, 255, 255))

    def test_removes_temp_after_ocr_failure(self):
        with patch.object(LLMtranslator.VLTranslator, 'ocr_and_translate', side_effect=RuntimeError('offline OCR failure')):
            result = self.run_translation()
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'offline OCR failure')
        self.assert_temp_removed()

    def test_removes_temp_when_initial_image_save_fails(self):
        with patch.object(self.image, 'save', side_effect=OSError('offline save failure')):
            result = self.run_translation()
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'offline save failure')
        self.assert_temp_removed()

    def test_removes_temp_when_translator_initialization_fails(self):
        with patch('LLMtranslator.VLTranslator', side_effect=RuntimeError('offline initialization failure')):
            result = self.run_translation()
        self.assertFalse(result['success'])
        self.assert_temp_removed()

    def test_removes_temp_after_no_text_success(self):
        with patch.object(LLMtranslator.VLTranslator, 'ocr_and_translate', return_value=[]):
            result = self.run_translation()
        self.assertTrue(result['success'])
        self.assertEqual(result['detected_texts'], [])
        self.assertEqual(result['translated_image'].size, (4, 4))
        result['translated_image'].close()
        self.assert_temp_removed()

    def test_removes_temp_after_render_success_or_failure(self):
        texts = [{'text': 'offline', 'box': [0, 0, 4, 4]}]
        for fails in (False, True):
            with self.subTest(fails=fails):
                self.temp_paths.clear()
                with patch.object(LLMtranslator.VLTranslator, 'ocr_and_translate', return_value=texts), \
                     patch('LLMtranslator.replace_text_with_translation', side_effect=RuntimeError('offline render failure') if fails else None, return_value=self.image):
                    result = self.run_translation()
                self.assertEqual(result['success'], not fails)
                self.assert_temp_removed()

    def test_never_unlinks_caller_source_path(self):
        source_path = self.root / 'caller.png'
        self.image.save(source_path)
        source_bytes = source_path.read_bytes()
        for fails in (False, True):
            with self.subTest(fails=fails), Image.open(source_path) as source_image:
                with patch('LLMtranslator.Image.open', return_value=source_image), \
                     patch.object(LLMtranslator.VLTranslator, 'ocr_and_translate', side_effect=RuntimeError('offline OCR failure') if fails else None, return_value=[]), \
                     patch('LLMtranslator.os.unlink', wraps=os.unlink) as unlink:
                    result = self.run_translation(str(source_path))
                self.assertEqual(result['success'], not fails)
                unlink.assert_not_called()
                self.assertEqual(source_path.read_bytes(), source_bytes)
                if result['translated_image'] is not None:
                    result['translated_image'].close()
        self.assertEqual(self.temp_paths, [])

    def test_cleanup_oserror_preserves_original_success_or_failure(self):
        for fails in (False, True):
            with self.subTest(fails=fails):
                self.temp_paths.clear()
                with patch.object(LLMtranslator.VLTranslator, 'ocr_and_translate', side_effect=RuntimeError('offline OCR failure') if fails else None, return_value=[]), \
                     patch('LLMtranslator.os.unlink', side_effect=OSError('offline cleanup failure')):
                    result = self.run_translation()
                self.assertEqual(result['success'], not fails)
                self.assertEqual(result['error'], 'offline OCR failure' if fails else None)
                self.assertEqual(len(self.temp_paths), 1)
                self.assertTrue(self.temp_paths[0].exists())
                self.temp_paths[0].unlink()
                if result['translated_image'] is not None:
                    result['translated_image'].close()


if __name__ == '__main__':
    unittest.main()
