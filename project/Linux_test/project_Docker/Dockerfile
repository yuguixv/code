# 1. 地基：基于 Python 3.9 的精简版 Linux (Alpine 或 Slim)
#    这意味着容器里已经预装了 Python，不需要你操心。
FROM python:3.9-slim

# 2. 只有在此目录干活：以后所有命令都默认在 /app 下执行
WORKDIR /app

# 3. 复制依赖：先把 txt 拿进来，方便利用缓存
COPY requirements.txt requirements.txt

# 4. 安装：在容器内部执行 pip，把 Flask 和 Redis 库装进容器里
RUN pip install -r requirements.txt

# 5. 搬家：把当前电脑目录下的所有代码，复制到容器的 /app 目录
COPY . .

# 6. 声明：这个容器打算用 5000 端口（这只是个标记，不代表对外开放）
EXPOSE 5000

# 7. 启动令：当容器跑起来时，执行这句话
CMD ["python", "app.py"]