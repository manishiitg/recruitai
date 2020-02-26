FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/classify.conf /etc/supervisor/conf.d/classify.conf

RUN truncate -s 0 /workspace/logs/classify*.log

RUN pip install transformers 
RUN pip install pika
RUN pip install beautifulsoup4

CMD ["/usr/bin/supervisord"]