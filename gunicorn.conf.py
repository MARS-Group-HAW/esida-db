# this file contains config params for gunicorn.
# see: https://docs.gunicorn.org/en/stable/settings.html

accesslog = "output/.logs/access.log"
errorlog = "output/.logs/error.log"

workers=3
