import importlib.util
from pathlib import Path


MODULE_PATH = Path(r"C:\Users\user\Projects\MorphIQ\Product\portal_new\seed_admin.py")


def load_seed_admin():
    spec = importlib.util.spec_from_file_location("seed_admin_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_demo_user_seed_requires_explicit_password(monkeypatch):
    seed_admin = load_seed_admin()

    monkeypatch.delenv("MORPHIQ_DEMO_PASSWORD", raising=False)

    config = seed_admin.get_demo_user_seed()

    assert config is None


def test_demo_user_seed_uses_env_configuration(monkeypatch):
    seed_admin = load_seed_admin()

    monkeypatch.setenv("MORPHIQ_DEMO_PASSWORD", "top-secret")
    monkeypatch.setenv("MORPHIQ_DEMO_EMAIL", "demo@example.test")
    monkeypatch.setenv("MORPHIQ_DEMO_NAME", "Portal Demo")

    config = seed_admin.get_demo_user_seed()

    assert config == {
        "email": "demo@example.test",
        "password": "top-secret",
        "full_name": "Portal Demo",
        "role": "manager",
        "client_id": 1,
    }
