import io
import json
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


class GeminiResponseUsageTests(unittest.TestCase):
    def _fake_response(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        cm = mock.MagicMock()
        cm.__enter__.return_value = io.BytesIO(body)
        cm.__exit__.return_value = False
        return cm

    def test_generate_gemini_response_returns_text_and_usage(self):
        from portal_new import ai_runtime

        payload = {
            "candidates": [{"content": {"parts": [{"text": "Gas Safety Certificate"}]}}],
            "usageMetadata": {
                "promptTokenCount": 1234,
                "candidatesTokenCount": 7,
                "totalTokenCount": 1241,
            },
        }
        fake_key = "test-key"
        with mock.patch.object(ai_runtime.urllib.request, "urlopen",
                               return_value=self._fake_response(payload)):
            result = ai_runtime.generate_gemini_response(
                api_key=fake_key, model="gemini-2.5-flash", prompt="hi"
            )

        self.assertEqual(result.text, "Gas Safety Certificate")
        self.assertEqual(result.usage["promptTokenCount"], 1234)
        self.assertEqual(result.usage["totalTokenCount"], 1241)

    def test_generate_gemini_text_delegates_to_response(self):
        from portal_new import ai_runtime

        payload = {"candidates": [{"content": {"parts": [{"text": "EICR"}]}}]}
        fake_key = "test-key"
        with mock.patch.object(ai_runtime.urllib.request, "urlopen",
                               return_value=self._fake_response(payload)):
            text = ai_runtime.generate_gemini_text(
                api_key=fake_key, model="gemini-2.5-flash", prompt="hi"
            )
        # Backward-compatible: returns the plain string, usage absent is fine.
        self.assertEqual(text, "EICR")


if __name__ == "__main__":
    unittest.main()
