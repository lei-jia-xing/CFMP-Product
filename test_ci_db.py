#!/usr/bin/env python
"""
简单的数据库连接测试，用于验证CI环境下的数据库配置
"""

import os
import sys
import django
from pathlib import Path

# 设置项目路径和Django环境
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ProductService.settings')

django.setup()

def test_db_connection():
    """测试数据库连接"""
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        db_settings = connection.settings_dict
        print("✅ 数据库连接成功!")
        print(f"数据库: {db_settings['NAME']}")
        print(f"主机: {db_settings['HOST']}")
        print(f"端口: {db_settings['PORT']}")
        print(f"用户: {db_settings['USER']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print(f"DATABASE_URL: {os.getenv('DATABASE_URL', '未设置')}")
        return False

if __name__ == '__main__':
    if test_db_connection():
        sys.exit(0)
    else:
        sys.exit(1)
