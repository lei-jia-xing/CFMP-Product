#!/bin/bash

echo "🚀 启动 CFMP Kubernetes 应用..."

# 启动 minikube


# 配置 Docker 环境
eval $(minikube docker-env)

# 构建镜像
echo "构建后端镜像..."
cd 后端/cfmp && docker build -t backend . && cd ../..

echo "构建前端镜像..."
cd 前端/cfmp-front-end && docker build -t frontend . && cd ../..

# 部署应用
echo "部署应用..."
minikube kubectl -- delete -f k8s/ --ignore-not-found=true
sleep 3

# 先部署数据库服务
minikube kubectl -- create -f k8s/mysql-service.yaml
minikube kubectl -- create -f k8s/mysql-endpoint.yaml

# 等待数据库服务就绪
sleep 5

minikube kubectl -- create -f k8s/

# 等待启动
echo "等待应用启动..."
minikube kubectl -- wait --for=condition=ready pod -l io.kompose.service=backend --timeout=300s
minikube kubectl -- wait --for=condition=ready pod -l io.kompose.service=frontend --timeout=300s

# 暴露服务
minikube kubectl -- patch service frontend -p '{"spec":{"type":"NodePort"}}'
minikube kubectl -- patch service backend -p '{"spec":{"type":"NodePort"}}'

# 显示访问地址
echo ""
echo "✅ 部署完成！访问地址："
minikube service list | grep -E "(frontend|backend)"
echo ""
echo "前端: $(minikube service frontend --url)"
echo "后端: $(minikube service backend --url)"
