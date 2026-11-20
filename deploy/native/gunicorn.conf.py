# gunicorn for the Treeline API: loopback only (Caddy is the only thing that talks to it).
bind = "127.0.0.1:8080"
workers = 1          # one process: the app keeps rate limits and the Asterisk client in memory
threads = 8
timeout = 30
graceful_timeout = 20
accesslog = "-"
errorlog = "-"
# No query strings, no tokens in the log (SECURITY.md R1-5): see controller/treeline/accesslog.py.
logger_class = "treeline.accesslog.Logger"
access_log_format = '%(h)s "%(m)s %(U)s" %(s)s %(b)s %(L)s'
# Import the app in the master before forking: a bad setting (see controller/treeline/prod.py) stops the service at once,
# instead of a worker that fails to boot while the service still looks "active".
preload_app = True
