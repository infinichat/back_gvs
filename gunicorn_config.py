import multiprocessing

bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1  # Adjust the number of workers based on your server's resources
worker_class = "gevent"
worker_connections = 1000
timeout = 360
keepalive = 2