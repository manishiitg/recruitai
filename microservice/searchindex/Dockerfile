FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/searchindex.conf /etc/supervisor/conf.d/searchindex.conf

RUN truncate -s 0 /workspace/logs/searchindex*.log

RUN pip install pika
RUN pip install elasticsearch
RUN pip install redis

CMD ["/usr/bin/supervisord"]