import time
import redis
from flask import Flask

app = Flask(__name__)

# --- 关键点详解 ---
# cache = redis.Redis(host='redis', port=6379)
# 问：为什么 host 写 'redis'？我没在 hosts 文件里配置过这个域名啊？
# 答：这是 Docker Compose 的魔法。
#     在下面的 yaml 文件里，我们给数据库服务起名叫 'redis'。
#     Docker 会自动在内部 DNS 里把 'redis' 解析成那个容器的真实 IP。
cache = redis.Redis(host='redis', port=6379)

def get_hit_count():
    retries = 5
    while True:
        try:
            return cache.incr('hits') # 尝试让数据库里的 'hits' 数字加 1
        except redis.exceptions.ConnectionError as exc:
            # 问：为什么要重试？
            # 答：因为 Docker 启动时，Python 容器和 Redis 容器是同时启动的。
            #     有可能 Python 跑起来了，Redis 还没初始化好。
            #     所以如果连接失败，我们等 0.5 秒再试，一共试 5 次。
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.5)

@app.route('/')
def hello():
    count = get_hit_count()
    return f'Hello Ubuntu! 页面访问次数: {count}.\n'