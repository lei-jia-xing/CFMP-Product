"""
ProductService Django 应用配置
"""
from django.apps import AppConfig
import signal
import sys


class ProductServiceConfig(AppConfig):
    name = 'ProductService'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        """应用就绪时的初始化"""
        # 注册信号处理器用于优雅关闭
        signal.signal(signal.SIGTERM, self._graceful_shutdown)
        signal.signal(signal.SIGINT, self._graceful_shutdown)
    
    def _graceful_shutdown(self, signum, frame):
        """优雅关闭处理"""
        print(f"\n🔄 Received signal {signum}, starting graceful shutdown...")
        
        try:
            from .nacos_health import stop_nacos_health_monitoring
            stop_nacos_health_monitoring()
            print("✅ Nacos service deregistered")
        except ImportError:
            print("⚠️ Nacos health module not found")
        except Exception as e:
            print(f"❌ Error during Nacos deregistration: {e}")
        
        print("👋 ProductService shutdown complete")
        sys.exit(0)
