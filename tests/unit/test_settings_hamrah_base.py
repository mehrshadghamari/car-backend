from src.infrastructure.config import Settings


def test_settings_normalizes_hamrah_base_url_typo():
    settings = Settings(hamrah_mechanic_base_url="https://www.hamrah-mechanic.com/carpreice")
    assert settings.hamrah_mechanic_base_url == "https://www.hamrah-mechanic.com"
