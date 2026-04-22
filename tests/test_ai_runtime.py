import os
import unittest
from unittest import mock


class AiRuntimeTests(unittest.TestCase):
    def test_ai_runtime_requires_gemini_api_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            from portal_new import ai_runtime

            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                ai_runtime.get_required_env("GEMINI_API_KEY")

    def test_ai_runtime_uses_chat_and_prefill_model_defaults(self):
        with mock.patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL_CHAT": "",
                "GEMINI_MODEL_DETECTION": "",
                "GEMINI_MODEL_EXTRACTION": "",
            },
            clear=False,
        ):
            from portal_new import ai_runtime

            self.assertEqual(ai_runtime.get_chat_model_name(), "gemini-2.5-flash")
            self.assertEqual(ai_runtime.get_prefill_model_name("detection"), "gemini-2.5-flash")
            self.assertEqual(ai_runtime.get_prefill_model_name("extraction"), "gemini-2.5-flash")

    def test_ai_runtime_respects_explicit_model_overrides(self):
        with mock.patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL_CHAT": "gemini-chat",
                "GEMINI_MODEL_DETECTION": "gemini-detect",
                "GEMINI_MODEL_EXTRACTION": "gemini-extract",
            },
            clear=False,
        ):
            from portal_new import ai_runtime

            self.assertEqual(ai_runtime.get_chat_model_name(), "gemini-chat")
            self.assertEqual(ai_runtime.get_prefill_model_name("detection"), "gemini-detect")
            self.assertEqual(ai_runtime.get_prefill_model_name("extraction"), "gemini-extract")


if __name__ == "__main__":
    unittest.main()
