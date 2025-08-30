#!/bin/bash

# K3s 安装和配置脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查系统要求
check_system() {
    log_step "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测操作系统"
        exit 1
    fi
    
    source /etc/os-release
    log_info "操作系统: $PRETTY_NAME"
    
    # 检查内存
    MEMORY_GB=$(free -g | awk 'NR==2{printf "%.1f", $2}')
    if (( $(echo "$MEMORY_GB < 1.0" | bc -l) )); then
        log_warn "内存不足1GB，K3s可能运行不稳定"
    else
        log_info "内存: ${MEMORY_GB}GB"
    fi
    
    # 检查磁盘空间
    DISK_AVAILABLE=$(df / | awk 'NR==2{print $4}')
    if [[ $DISK_AVAILABLE -lt 2097152 ]]; then  # 2GB in KB
        log_warn "磁盘空间不足2GB"
    else
        log_info "磁盘空间: $(df -h / | awk 'NR==2{print $4}')可用"
    fi
}

# 安装依赖
install_dependencies() {
    log_step "安装系统依赖..."
    
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y curl wget
    elif command -v yum &> /dev/null; then
        yum install -y curl wget
    elif command -v dnf &> /dev/null; then
        dnf install -y curl wget
    else
        log_warn "未知的包管理器，请手动安装 curl 和 wget"
    fi
}

# 安装K3s
install_k3s() {
    log_step "安装K3s..."
    
    if command -v k3s &> /dev/null; then
        log_info "K3s 已安装，版本: $(k3s --version | head -n1)"
        return 0
    fi
    
    # 下载并安装K3s
    log_info "下载并安装K3s..."
    curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
    
    # 等待K3s启动
    log_info "等待K3s启动..."
    sleep 10
    
    # 检查K3s状态
    systemctl status k3s --no-pager
    
    # 配置kubectl
    if [[ ! -f ~/.kube/config ]]; then
        mkdir -p ~/.kube
        cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
        chmod 600 ~/.kube/config
        log_info "kubectl 配置完成"
    fi
    
    # 添加kubectl别名
    if ! grep -q "alias kubectl=" ~/.bashrc; then
        echo "alias kubectl='k3s kubectl'" >> ~/.bashrc
        log_info "kubectl 别名已添加到 ~/.bashrc"
    fi
}

# 验证安装
verify_installation() {
    log_step "验证K3s安装..."
    
    # 检查节点状态
    k3s kubectl get nodes
    
    # 检查系统Pod
    k3s kubectl get pods -n kube-system
    
    # 检查存储类
    k3s kubectl get storageclass
    
    log_info "K3s 安装验证完成"
}

# 配置防火墙（如果需要）
configure_firewall() {
    log_step "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        log_info "检测到 UFW 防火墙"
        ufw allow 6443/tcp  # K3s API server
        ufw allow 30000:32767/tcp  # NodePort range
        log_info "UFW 防火墙规则已配置"
    elif command -v firewall-cmd &> /dev/null; then
        log_info "检测到 firewalld"
        firewall-cmd --permanent --add-port=6443/tcp
        firewall-cmd --permanent --add-port=30000-32767/tcp
        firewall-cmd --reload
        log_info "firewalld 规则已配置"
    else
        log_warn "未检测到防火墙，请手动开放端口 6443 和 30000-32767"
    fi
}

# 主函数
main() {
    log_info "开始安装和配置 K3s..."
    
    # 检查是否为root用户
    if [[ $EUID -ne 0 ]]; then
        log_error "请以root用户运行此脚本"
        exit 1
    fi
    
    check_system
    install_dependencies
    install_k3s
    verify_installation
    configure_firewall
    
    log_info "K3s 安装配置完成！"
    log_info "现在可以使用以下命令："
    log_info "  k3s kubectl get nodes"
    log_info "  或者添加别名后: kubectl get nodes"
    log_info ""
    log_info "要卸载K3s，请运行: /usr/local/bin/k3s-uninstall.sh"
}

# 处理中断信号
trap 'log_error "安装被中断"; exit 1' INT TERM

# 执行主函数
main "$@"
