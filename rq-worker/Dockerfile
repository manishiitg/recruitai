FROM python:3.7

WORKDIR /usr/src/app

ENV TERM=xterm-256color
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV RQ_QUEUE=default
ENV LOG_LEVEL=DEBUG
ENV PIP_PACKAGES=none
ENV PIP_REQUIREMENTS=none
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get -q update >/dev/null \
    && apt-get install -y curl build-essential git supervisor \
    && pip install rq \
    && pip install Jinja2 \
    # Cleanup
    && apt-get clean autoclean \
    && apt-get autoremove --yes \
    && rm -rf /var/lib/{apt,dpkg,cache,log}/ 


COPY start_rq_worker.sh /usr/src/app/start_rq_worker.sh
COPY etc_supervisor_confd_rqworker.conf.j2 /etc/supervisor/conf.d/rqworker.conf.j2
VOLUME ["/pythonimports"]

ENTRYPOINT [ "sh","/usr/src/app/start_rq_worker.sh"]