import importlib
import os
import sys
import unittest
from unittest import mock


class PortalSecurityHelperTests(unittest.TestCase):
    def _import_app_module(self):
        from portal_new import ai_runtime

        sys.modules.pop("portal_new.app", None)
        with mock.patch.object(ai_runtime, "load_project_env", return_value=None):
            with mock.patch.dict(
                os.environ,
                {"PORTAL_SECRET_KEY": "secret", "GEMINI_API_KEY": "test-key"},
                clear=True,
            ):
                return importlib.import_module("portal_new.app")

    def _login_manager_session(self, app_module, client):
        manager = app_module.query_db(
            """
            SELECT id
            FROM users
            WHERE role = 'manager' AND is_active = 1 AND deleted_at IS NULL
            ORDER BY id
            LIMIT 1
            """,
            one=True,
        )
        self.assertIsNotNone(manager, "Expected at least one active manager user in portal.db")
        with client.session_transaction() as sess:
            sess["_user_id"] = str(manager["id"])
            sess["_fresh"] = True
            sess["_csrf_token"] = "test-csrf-token"
        return "test-csrf-token"

    def test_portal_import_fails_without_secret(self):
        from portal_new import ai_runtime

        sys.modules.pop("portal_new.app", None)
        with mock.patch.object(ai_runtime, "load_project_env", return_value=None):
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "PORTAL_SECRET_KEY"):
                    importlib.import_module("portal_new.app")

    def test_validate_model_output_blocks_obviously_unsafe_content(self):
        app_module = self._import_app_module()

        self.assertFalse(app_module.validate_chat_response_text("SELECT * FROM users;")[0])
        self.assertFalse(app_module.validate_chat_response_text("<script>alert(1)</script>")[0])
        self.assertFalse(app_module.validate_chat_response_text("Contact admin@example.com for access")[0])
        self.assertTrue(app_module.validate_chat_response_text("Property 1 is compliant.")[0])

    def test_logged_in_manager_can_fetch_properties(self):
        app_module = self._import_app_module()
        client = app_module.app.test_client()
        self._login_manager_session(app_module, client)

        properties = client.get("/api/properties")
        self.assertEqual(properties.status_code, 200)
        payload = properties.get_json()
        self.assertIn("properties", payload)

    def test_chat_requires_csrf_and_accepts_valid_token(self):
        app_module = self._import_app_module()
        client = app_module.app.test_client()
        csrf_token = self._login_manager_session(app_module, client)

        blocked = client.post("/api/chat", json={"message": "What is expiring soon?"})
        self.assertEqual(blocked.status_code, 403)

        with mock.patch.object(app_module, "generate_gemini_text", return_value="Sample response"):
            allowed = client.post(
                "/api/chat",
                json={"message": "What is expiring soon?"},
                headers={"X-CSRF-Token": csrf_token},
            )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.get_json()["response"], "Sample response")


if __name__ == "__main__":
    unittest.main()
