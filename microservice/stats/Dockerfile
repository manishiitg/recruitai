FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor python3-dev -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/stats.conf /etc/supervisor/conf.d/stats.conf

RUN truncate -s 0 /workspace/logs/stats*.log

RUN pip install pika
RUN pip install pymongo
RUN pip install redis

CMD ["/usr/bin/supervisord"]