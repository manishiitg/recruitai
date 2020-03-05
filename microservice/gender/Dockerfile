FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/gender.conf /etc/supervisor/conf.d/gender.conf

RUN truncate -s 0 /workspace/logs/gender*.log

RUN pip install pika
RUN pip install flair 

CMD ["/usr/bin/supervisord"]