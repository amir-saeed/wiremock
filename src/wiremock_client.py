from wiremock.constants import Config
from wiremock.client import Admin

def ping_admin() -> bool:
    try:
        return Admin.get_admin().get_root() is not None
    except Exception:
        return False

def set_admin_base_url(host: str = "localhost", port: int = 8080) -> None:
    Config.base_url = f"http://{host}:{port}/__admin"
