FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/filter.conf /etc/supervisor/conf.d/filter.conf

RUN truncate -s 0 /workspace/logs/filter*.log

RUN pip install pika
RUN pip install redis
RUN pip install apscheduler
RUN pip install pymongo
RUN pip install fuzzywuzzy[speedup]

CMD ["/usr/bin/supervisord"]