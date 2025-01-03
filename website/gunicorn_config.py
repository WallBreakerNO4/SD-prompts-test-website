workers = 4  # 建议设置为CPU核心数量的2-4倍
bind = "127.0.0.1:8080"
timeout = 120
keepalive = 5
errorlog = "logs/gunicorn-error.log"
accesslog = "logs/gunicorn-access.log"
loglevel = "info"
# 自定义访问日志格式，使用X-Forwarded-For header获取真实IP
access_log_format = '%(h)s %({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' 