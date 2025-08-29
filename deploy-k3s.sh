#!/bin/bash

set -e

echo "🚀 启动 ProductService K3s 部署..."

# 检查 k3s 是否安装
if ! command -v k3s &> /dev/null; then
    echo "❌ K3s 未安装，请先安装 K3s"
    echo "安装命令: curl -sfL https://get.k3s.io | sh -"
    exit 1
fi

# 检查 kubectl 别名
if ! command -v kubectl &> /dev/null; then
    echo "设置 kubectl 别名..."
    alias kubectl='k3s kubectl'
fi

# 获取当前分支或使用默认标签
IMAGE_TAG=${1:-latest}
IMAGE_NAME="productservice-backend"

echo "构建 Docker 镜像..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "导入镜像到 k3s..."
docker save ${IMAGE_NAME}:${IMAGE_TAG} | sudo k3s ctr images import -

# 更新部署配置
echo "更新部署配置..."
cp k8s/backend-deployment.yaml k8s/backend-deployment.yaml.bak
sed -i "s|productservice-backend:latest|${IMAGE_NAME}:${IMAGE_TAG}|g" k8s/backend-deployment.yaml
sed -i "s|imagePullPolicy: IfNotPresent|imagePullPolicy: Never|g" k8s/backend-deployment.yaml

# 清理旧部署
echo "清理旧部署..."
sudo kubectl delete -f k8s/ --ignore-not-found=true
sleep 3

# 先部署持久化存储和数据库
echo "部署数据库服务..."
if [ -f k8s/postgres-data-persistentvolumeclaim.yaml ]; then
    sudo kubectl apply -f k8s/postgres-data-persistentvolumeclaim.yaml
fi

if [ -f k8s/db-service.yaml ]; then
    sudo kubectl apply -f k8s/db-service.yaml
fi

if [ -f k8s/db-deployment.yaml ]; then
    sudo kubectl apply -f k8s/db-deployment.yaml
fi

# 等待数据库服务就绪
echo "等待数据库服务启动..."
sleep 10

# 部署后端应用
echo "部署后端应用..."
sudo kubectl apply -f k8s/backend-deployment.yaml
sudo kubectl apply -f k8s/backend-service.yaml

# 等待应用启动
echo "等待应用启动..."
sudo kubectl wait --for=condition=ready pod -l io.kompose.service=backend --timeout=300s

# 检查数据库连接
echo "检查数据库连接..."
DB_POD=$(sudo kubectl get pods -l io.kompose.service=db -o jsonpath='{.items[0].metadata.name}')
if [ -n "$DB_POD" ]; then
    sudo kubectl wait --for=condition=ready pod -l io.kompose.service=db --timeout=300s
    echo "✅ 数据库服务就绪"
else
    echo "⚠️  未找到数据库 Pod"
fi

# 暴露服务
echo "配置服务访问..."
sudo kubectl patch service backend -p '{"spec":{"type":"NodePort"}}'

# 执行数据库迁移
echo "执行数据库迁移..."
BACKEND_POD=$(sudo kubectl get pods -l io.kompose.service=backend -o jsonpath='{.items[0].metadata.name}')
if [ -n "$BACKEND_POD" ]; then
    echo "在 Pod $BACKEND_POD 中执行迁移..."
    sudo kubectl exec $BACKEND_POD -- python manage.py migrate
    echo "✅ 数据库迁移完成"
fi

# 显示部署状态
echo ""
echo "📊 部署状态："
sudo kubectl get pods,svc
echo ""

# 显示访问地址
NODE_PORT=$(sudo kubectl get service backend -o jsonpath='{.spec.ports[0].nodePort}')
NODE_IP=$(hostname -I | awk '{print $1}')

echo "✅ 部署完成！"
echo ""
echo "🌐 访问地址："
echo "后端服务: http://$NODE_IP:$NODE_PORT"
echo "健康检查: http://$NODE_IP:$NODE_PORT/health/"
echo ""

# 恢复备份的部署配置
mv k8s/backend-deployment.yaml.bak k8s/backend-deployment.yaml

# 执行健康检查
echo "🔍 执行健康检查..."
sleep 10

for i in {1..5}; do
    if curl -f http://$NODE_IP:$NODE_PORT/health/ 2>/dev/null; then
        echo "✅ 健康检查通过！"
        break
    else
        echo "⏳ 健康检查失败，重试中... ($i/5)"
        sleep 5
    fi
    
    if [ $i -eq 5 ]; then
        echo "❌ 健康检查失败，请检查日志:"
        echo "kubectl logs -l io.kompose.service=backend"
    fi
done

echo ""
echo "🎉 ProductService 部署完成！"
echo ""
echo "常用命令："
echo "  查看 Pods: kubectl get pods"
echo "  查看日志: kubectl logs -l io.kompose.service=backend"
echo "  进入容器: kubectl exec -it \$(kubectl get pods -l io.kompose.service=backend -o jsonpath='{.items[0].metadata.name}') -- bash"
echo "  删除部署: kubectl delete -f k8s/"
