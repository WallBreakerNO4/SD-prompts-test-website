workers = 4  # 建议设置为CPU核心数量的2-4倍
bind = "127.0.0.1:8080"
timeout = 120
keepalive = 5
errorlog = "logs/gunicorn-error.log"
accesslog = "logs/gunicorn-access.log"
loglevel = "info" 