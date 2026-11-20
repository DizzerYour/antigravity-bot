import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "bot_token": "",
    "gemini_api_key": "",
    "allowed_user_id": 0,
    "gemini_model": "gemini-3.5-flash-lite",
    "proxy": ""
}

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key, val in DEFAULT_CONFIG.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception as e:
        print(f"[!] Ошибка чтения config.json: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config_data: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Не удалось сохранить config.json: {e}")

def set_allowed_user(user_id: int) -> None:
    config = load_config()
    config["allowed_user_id"] = user_id
    save_config(config)

def get_bot_token() -> str:
    return os.environ.get("BOT_TOKEN") or load_config().get("bot_token", "").strip()

def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY") or load_config().get("gemini_api_key", "").strip()

def get_allowed_user_id() -> int:
    val = os.environ.get("ALLOWED_USER_ID")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return int(load_config().get("allowed_user_id", 0))

def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL") or load_config().get("gemini_model", "gemini-3.5-flash-lite").strip()

def get_proxy() -> str:
    return os.environ.get("PROXY") or load_config().get("proxy", "").strip()
