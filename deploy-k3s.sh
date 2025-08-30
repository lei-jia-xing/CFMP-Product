#!/bin/bash

# ProductService K3s 部署脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数定义
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查K3s是否安装
check_k3s() {
    if ! command -v k3s &> /dev/null; then
        log_error "K3s 未安装，请先安装K3s"
        echo "安装命令: curl -sfL https://get.k3s.io | sh -"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_warn "kubectl 未找到，使用 k3s kubectl"
        alias kubectl='k3s kubectl'
    fi
}

# 检查Docker镜像
check_docker_image() {
    log_step "检查Docker镜像..."
    
    if [[ -f "productservice-backend.tar.gz" ]]; then
        log_info "发现Docker镜像文件，正在导入到K3s..."
        sudo k3s ctr images import productservice-backend.tar.gz
    elif ! docker images | grep -q "productservice-backend"; then
        log_info "构建Docker镜像..."
        docker build -t productservice-backend:latest .
        
        # 导入镜像到K3s
        log_info "导入镜像到K3s..."
        docker save productservice-backend:latest | sudo k3s ctr images import -
    else
        log_info "Docker镜像已存在，导入到K3s..."
        docker save productservice-backend:latest | sudo k3s ctr images import -
    fi
}

# 部署数据库
deploy_database() {
    log_step "部署PostgreSQL数据库..."
    
    # 应用PVC
    kubectl apply -f k8s/postgres-data-persistentvolumeclaim.yaml
    
    # 部署数据库
    kubectl apply -f k8s/db-deployment.yaml
    kubectl apply -f k8s/db-service.yaml
    
    # 等待数据库就绪
    log_info "等待数据库启动..."
    kubectl wait --for=condition=ready pod -l io.kompose.service=db --timeout=300s || {
        log_error "数据库启动超时"
        kubectl logs -l io.kompose.service=db --tail=50
        exit 1
    }
    
    log_info "数据库部署完成"
}

# 部署后端服务
deploy_backend() {
    log_step "部署ProductService后端..."
    
    # 部署后端服务
    kubectl apply -f k8s/backend-deployment.yaml
    kubectl apply -f k8s/backend-service.yaml
    
    # 等待后端服务就绪
    log_info "等待后端服务启动..."
    kubectl wait --for=condition=ready pod -l io.kompose.service=backend --timeout=300s || {
        log_error "后端服务启动超时"
        kubectl logs -l io.kompose.service=backend --tail=50
        exit 1
    }
    
    log_info "后端服务部署完成"
}

# 健康检查
health_check() {
    log_step "执行健康检查..."
    
    # 获取NodePort
    NODE_PORT=$(kubectl get service backend -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30800")
    
    # 等待服务完全启动
    sleep 30
    
    # 检查健康端点
    for i in {1..10}; do
        if curl -f http://localhost:$NODE_PORT/health/ > /dev/null 2>&1; then
            log_info "健康检查通过！"
            break
        elif [ $i -eq 10 ]; then
            log_warn "健康检查失败，但服务可能仍在启动中"
            kubectl logs -l io.kompose.service=backend --tail=20
        else
            log_info "等待服务启动... ($i/10)"
            sleep 10
        fi
    done
}

# 显示部署信息
show_deployment_info() {
    log_step "部署信息:"
    
    echo -e "${GREEN}集群状态:${NC}"
    kubectl get nodes
    
    echo -e "${GREEN}Pod状态:${NC}"
    kubectl get pods -o wide
    
    echo -e "${GREEN}Service状态:${NC}"
    kubectl get services
    
    # 获取访问信息
    NODE_PORT=$(kubectl get service backend -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30800")
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
    
    echo -e "${GREEN}访问信息:${NC}"
    echo -e "  内部访问: http://backend.default.svc.cluster.local:8000"
    echo -e "  外部访问: http://$NODE_IP:$NODE_PORT"
    echo -e "  本地访问: http://localhost:$NODE_PORT"
    echo -e "  健康检查: http://localhost:$NODE_PORT/health/"
}

# 主函数
main() {
    log_info "开始部署 ProductService 到 K3s 集群..."
    
    check_k3s
    check_docker_image
    deploy_database
    deploy_backend
    health_check
    show_deployment_info
    
    log_info "ProductService 部署完成！"
}

# 处理中断信号
trap 'log_error "部署被中断"; exit 1' INT TERM

# 执行主函数
main "$@"
