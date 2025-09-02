#!/bin/bash

# ProductService 部署状态诊断脚本
echo "🔍 ProductService K3s 部署诊断..."

# 检查K3s状态
echo "1. 检查K3s集群状态:"
if command -v k3s &> /dev/null; then
    echo "✅ K3s已安装"
    if k3s kubectl get nodes; then
        echo "✅ K3s集群正常运行"
    else
        echo "❌ K3s集群无法访问"
        exit 1
    fi
else
    echo "❌ K3s未安装"
    exit 1
fi

echo ""

# 检查ProductService相关资源
echo "2. 检查ProductService部署状态:"

echo "PVC状态:"
k3s kubectl get pvc

echo ""
echo "Pod状态:"
k3s kubectl get pods -o wide

echo ""
echo "Service状态:"
k3s kubectl get svc

echo ""

# 检查具体的ProductService pod
echo "3. ProductService Pod详细信息:"
if k3s kubectl get pods -l io.kompose.service=backend > /dev/null 2>&1; then
    echo "后端Pod状态:"
    k3s kubectl get pods -l io.kompose.service=backend
    echo ""
    echo "后端Pod事件:"
    k3s kubectl describe pods -l io.kompose.service=backend
else
    echo "❌ 未找到后端Pod"
fi

echo ""
if k3s kubectl get pods -l io.kompose.service=db > /dev/null 2>&1; then
    echo "数据库Pod状态:"
    k3s kubectl get pods -l io.kompose.service=db
    echo ""
    echo "数据库Pod事件:"
    k3s kubectl describe pods -l io.kompose.service=db
else
    echo "❌ 未找到数据库Pod"
fi

echo ""

# 检查服务访问
echo "4. 检查服务访问:"
BACKEND_PORT=$(k3s kubectl get service backend -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "未找到")
if [ "$BACKEND_PORT" != "未找到" ]; then
    echo "✅ 后端服务端口: $BACKEND_PORT"
    echo "🌐 访问地址: http://localhost:$BACKEND_PORT"
    echo "🏥 健康检查: http://localhost:$BACKEND_PORT/health/"
    
    # 尝试访问健康检查端点
    if curl -f "http://localhost:$BACKEND_PORT/health/" > /dev/null 2>&1; then
        echo "✅ 健康检查通过"
    else
        echo "❌ 健康检查失败"
    fi
else
    echo "❌ 无法获取后端服务端口"
fi

echo ""

# 检查最近的日志
echo "5. 最近的Pod日志:"
echo "后端日志 (最近20行):"
k3s kubectl logs -l io.kompose.service=backend --tail=20 2>/dev/null || echo "无法获取后端日志"

echo ""
echo "数据库日志 (最近10行):"
k3s kubectl logs -l io.kompose.service=db --tail=10 2>/dev/null || echo "无法获取数据库日志"

echo ""
echo "🎯 诊断完成！"
