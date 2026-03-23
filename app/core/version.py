"""
IndiaShop Reseller Bot — Version
© 2026 All Rights Reserved.

Proprietary and Confidential.
"""

__version__ = "1.2.0"
__version_info__ = (1, 2, 0)
__build_date__ = "2026-03-23"
__status__ = "production"  # production, beta, dev
__copyright__ = "© 2026 IndiaShop. All Rights Reserved."


def get_version() -> str:
    """Получить версию в формате X.Y.Z"""
    return __version__


def get_version_info() -> dict:
    """Получить полную информацию о версии"""
    return {
        "version": __version__,
        "version_tuple": __version_info__,
        "build_date": __build_date__,
        "status": __status__,
        "copyright": __copyright__,
    }


def get_full_version() -> str:
    """Получить полную строку версии"""
    status_label = {
        "production": "",
        "beta": " (Beta)",
        "dev": " (Dev)"
    }.get(__status__, "")

    return f"v{__version__}{status_label}"
