"""
应用启动与依赖装配
"""

from app.container import ServiceContainer
from app.bootstrap import Application, create_app

__all__ = ["ServiceContainer", "Application", "create_app"]
