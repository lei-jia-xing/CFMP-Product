FROM python:3.12-slim

# 设置环境变量，防止生成 .pyc 文件，并确保 Python 输出直接发送到终端
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 在容器中创建工作目录
WORKDIR /app
RUN rm -rf /etc/apt/sources.list.d/* && \
    rm -f /etc/apt/sources.list

ADD sources.list /etc/apt/
# 安装系统依赖（包含 PostgreSQL 开发文件）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 将当前目录内容复制到容器的 /app 目录下
COPY . /app/

# 暴露端口
EXPOSE 8000

# 运行应用，包含数据迁移
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
