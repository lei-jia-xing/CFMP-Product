# ProductService K3s 部署指南

这个项目包含了用于在 K3s 集群中自动部署 ProductService 的工具和工作流。

## 🚀 快速开始

### 本地部署

使用提供的脚本可以快速在本地 K3s 集群中部署应用：

```bash
# 使用默认标签部署
./deploy-k3s.sh

# 使用特定标签部署
./deploy-k3s.sh v1.2.3
```

### 前置要求

1. **安装 K3s**
   ```bash
   curl -sfL https://get.k3s.io | sh -
   ```

2. **安装 Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io
   sudo usermod -aG docker $USER
   ```

3. **设置 kubectl 别名**（如果需要）
   ```bash
   alias kubectl='k3s kubectl'
   echo "alias kubectl='k3s kubectl'" >> ~/.bashrc
   ```

## 🔄 CI/CD 自动部署

### GitHub Actions 工作流

项目包含了 GitHub Actions 工作流，可以自动构建和部署到 K3s 集群：

- **触发方式**: 推送到 `main` 或 `master` 分支
- **手动触发**: 在 GitHub Actions 页面选择环境（staging/production）

### 配置 Secrets

在 GitHub 仓库设置中配置以下 Secrets：

```
K3S_HOST=your-k3s-server-ip
K3S_USER=your-ssh-username  
K3S_SSH_KEY=your-private-ssh-key
SLACK_WEBHOOK=your-slack-webhook-url (可选)
```

### 工作流功能

- ✅ 自动构建 Docker 镜像
- ✅ 部署到 K3s 集群
- ✅ 健康检查
- ✅ 失败时自动回滚
- ✅ Slack 通知（可选）

## 📊 部署后管理

### 常用命令

```bash
# 查看部署状态
kubectl get pods,svc

# 查看应用日志
kubectl logs -l io.kompose.service=backend

# 进入应用容器
kubectl exec -it $(kubectl get pods -l io.kompose.service=backend -o jsonpath='{.items[0].metadata.name}') -- bash

# 扩缩容
kubectl scale deployment backend --replicas=3

# 查看服务访问地址
kubectl get svc backend
```

### 数据库管理

```bash
# 执行数据库迁移
BACKEND_POD=$(kubectl get pods -l io.kompose.service=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec $BACKEND_POD -- python manage.py migrate

# 创建超级用户
kubectl exec -it $BACKEND_POD -- python manage.py createsuperuser

# 数据库备份
kubectl exec $BACKEND_POD -- python manage.py dumpdata > backup.json
```

## 🛠 故障排除

### 常见问题

1. **镜像拉取失败**
   - 确保镜像已正确导入到 K3s: `sudo k3s ctr images ls`
   - 检查 imagePullPolicy 设置为 `Never`

2. **Pod 无法启动**
   - 查看 Pod 日志: `kubectl logs <pod-name>`
   - 检查资源限制: `kubectl describe pod <pod-name>`

3. **数据库连接失败**
   - 确保数据库 Pod 正在运行: `kubectl get pods -l io.kompose.service=db`
   - 检查数据库服务: `kubectl get svc db`

4. **服务无法访问**
   - 检查 NodePort 服务: `kubectl get svc backend`
   - 确认防火墙设置允许相应端口

### 日志查看

```bash
# 应用日志
kubectl logs -f deployment/backend

# 数据库日志
kubectl logs -f deployment/db

# 系统事件
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 🔧 配置说明

### 环境变量

主要环境变量在 `k8s/backend-deployment.yaml` 中配置：

- `NACOS_SERVER`: Nacos 服务器地址
- `SERVICE_PORT`: 服务端口
- `ENVIRONMENT`: 运行环境
- `NACOS_USERNAME/PASSWORD`: Nacos 认证信息

### 资源配置

可以在部署文件中调整资源限制：

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

### 持久化存储

数据库数据通过 PersistentVolumeClaim 持久化：

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

## 📈 监控和维护

### 健康检查

应用提供健康检查端点：
- URL: `http://<service-ip>:<port>/health/`
- 检查内容: 数据库连接、服务状态

### 扩缩容

```bash
# 手动扩容到 3 个副本
kubectl scale deployment backend --replicas=3

# 设置自动扩缩容（需要 metrics-server）
kubectl autoscale deployment backend --cpu-percent=80 --min=2 --max=10
```

### 更新部署

```bash
# 滚动更新到新镜像
kubectl set image deployment/backend django-backend=productservice-backend:new-tag

# 查看更新状态
kubectl rollout status deployment/backend

# 回滚到上一版本
kubectl rollout undo deployment/backend
```
