"""
Nacos 心跳管理 - 简化版本，专注于心跳功能
"""

import os
import time
import socket
import threading
import logging
from nacos import NacosClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class NacosHeartbeatManager:
    """Nacos 心跳管理器 - 专门处理服务心跳"""

    def __init__(self):
        self.service_name = "ProductService"
        self.nacos_client = None
        self.service_ip = None
        self.service_port = None  # 将在 _get_service_ip 中设置
        self.heartbeat_interval = int(
            os.getenv("NACOS_HEARTBEAT_INTERVAL", "5")
        )  # 默认5秒
        self.is_running = False
        self.heartbeat_thread = None
        self.cluster_name = "DEFAULT"

        self._init_nacos_client()
        self._get_service_ip()

    def _init_nacos_client(self):
        """初始化 Nacos 客户端"""
        try:
            nacos_server = os.getenv("NACOS_SERVER", "123.57.145.79:8848")
            nacos_username = os.getenv("NACOS_USERNAME")
            nacos_password = os.getenv("NACOS_PASSWORD")

            if nacos_username and nacos_password:
                self.nacos_client = NacosClient(
                    server_addresses=nacos_server,
                    namespace="public",
                    username=nacos_username,
                    password=nacos_password,
                )
            else:
                self.nacos_client = NacosClient(
                    server_addresses=nacos_server, namespace="public"
                )
            logger.info(
                f"💓 Nacos heartbeat client initialized: {nacos_server} (interval: {self.heartbeat_interval}s)"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize Nacos heartbeat client: {e}")

    def _get_service_ip(self):
        """获取服务IP地址"""
        try:
            self.service_ip = '101.132.163.45'
            self.service_port = 30800  # 使用NodePort端口
        except Exception as e:
            logger.error(f"Failed to get service IP: {e}")
            self.service_ip = "127.0.0.1"

    def register_service(self):
        """注册服务到 Nacos"""
        if not self.nacos_client:
            return False

        try:
            self.nacos_client.add_naming_instance(
                service_name=self.service_name,
                ip=self.service_ip,
                port=self.service_port,
                cluster_name=self.cluster_name,
            )
            logger.info(
                f"✅ Service registered to Nacos: {self.service_name} {self.service_ip}:{self.service_port}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register service: {e}")
            return False

    def send_heartbeat(self):
        """发送心跳到 Nacos"""
        if not self.nacos_client:
            return False

        try:
            self.nacos_client.send_heartbeat(
                service_name=self.service_name,
                ip=self.service_ip,
                port=self.service_port,
                cluster_name=self.cluster_name,
            )
            logger.debug(
                f" Heartbeat sent: {self.service_name} {self.service_ip}:{self.service_port}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send heartbeat: {e}")
            return False

    def heartbeat_loop(self):
        """心跳循环"""
        while self.is_running:
            try:
                success = self.send_heartbeat()
                if not success:
                    logger.warning("⚠️ Heartbeat failed, will retry")

                # 心跳周期建议小于 Nacos 配置的超时（默认 5s 一次）
                logger.info(f"⏳ Heartbeat interval: {self.heartbeat_interval}s")
                time.sleep(self.heartbeat_interval)

            except Exception as e:
                logger.error(f"💔 Heartbeat loop error: {e}")
                time.sleep(self.heartbeat_interval)

    def start_heartbeat(self):
        """启动心跳监控"""
        if self.is_running:
            logger.warning("Heartbeat monitoring is already running")
            return

        if not self.nacos_client:
            logger.error("Cannot start heartbeat: Nacos client not initialized")
            return

        # 先注册服务
        self.register_service()

        # 启动心跳线程
        self.is_running = True
        self.heartbeat_thread = threading.Thread(
            target=self.heartbeat_loop, daemon=True, name="NacosHeartbeat"
        )
        self.heartbeat_thread.start()
        logger.info(
            f"💓 Nacos heartbeat started (interval: {self.heartbeat_interval}s)"
        )

    def stop_heartbeat(self):
        """停止心跳监控"""
        self.is_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logger.info("💓 Nacos heartbeat stopped")

    def deregister_service(self):
        """从 Nacos 注销服务"""
        try:
            if self.nacos_client:
                self.nacos_client.remove_naming_instance(
                    service_name=self.service_name,
                    ip=self.service_ip,
                    port=self.service_port,
                    cluster_name=self.cluster_name,
                )
                logger.info(f"✅ Service deregistered from Nacos: {self.service_name}")
        except Exception as e:
            logger.error(f"❌ Failed to deregister service: {e}")


# 全局心跳管理器实例
_heartbeat_manager = None


def start_nacos_health_monitoring():
    """启动 Nacos 心跳监控"""
    global _heartbeat_manager

    if _heartbeat_manager is None:
        _heartbeat_manager = NacosHeartbeatManager()

    _heartbeat_manager.start_heartbeat()


def stop_nacos_health_monitoring():
    """停止 Nacos 心跳监控并注销服务"""
    global _heartbeat_manager

    if _heartbeat_manager:
        _heartbeat_manager.stop_heartbeat()
        _heartbeat_manager.deregister_service()
