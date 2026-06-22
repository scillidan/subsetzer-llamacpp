import unittest

from subsetzer.langs import normalise_lang


class LangTests(unittest.TestCase):
    def test_iso_639_1_codes(self):
        self.assertEqual(normalise_lang("en"), "en")
        self.assertEqual(normalise_lang("de"), "de")
        self.assertEqual(normalise_lang("fr"), "fr")
        self.assertEqual(normalise_lang("ja"), "ja")
        self.assertEqual(normalise_lang("ko"), "ko")

    def test_iso_639_2_codes(self):
        self.assertEqual(normalise_lang("eng"), "en")
        self.assertEqual(normalise_lang("deu"), "de")
        self.assertEqual(normalise_lang("fra"), "fr")
        self.assertEqual(normalise_lang("jpn"), "ja")

    def test_english_names(self):
        self.assertEqual(normalise_lang("English"), "en")
        self.assertEqual(normalise_lang("German"), "de")
        self.assertEqual(normalise_lang("French"), "fr")
        self.assertEqual(normalise_lang("Japanese"), "ja")
        self.assertEqual(normalise_lang("Chinese"), "zh-cn")
        self.assertEqual(normalise_lang("Korean"), "ko")
        self.assertEqual(normalise_lang("Spanish"), "es")

    def test_chinese_variants(self):
        self.assertEqual(normalise_lang("zh"), "zh-cn")
        self.assertEqual(normalise_lang("zh-cn"), "zh-cn")
        self.assertEqual(normalise_lang("zh-hans"), "zh-cn")
        self.assertEqual(normalise_lang("zh-tw"), "zh-tw")
        self.assertEqual(normalise_lang("zh-hant"), "zh-tw")
        self.assertEqual(normalise_lang("zho"), "zh-cn")
        self.assertEqual(normalise_lang("chi"), "zh-cn")

    def test_auto_preserved(self):
        self.assertEqual(normalise_lang("auto"), "auto")
        self.assertEqual(normalise_lang("Auto"), "auto")
        self.assertEqual(normalise_lang("AUTO"), "auto")

    def test_unknown_passthrough(self):
        self.assertEqual(normalise_lang("xyz-unknown"), "xyz-unknown")

    def test_case_insensitive(self):
        self.assertEqual(normalise_lang("GERMAN"), "de")
        self.assertEqual(normalise_lang("FrEnCh"), "fr")
