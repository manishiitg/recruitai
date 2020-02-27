FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/skill.conf /etc/supervisor/conf.d/skill.conf

RUN truncate -s 0 /workspace/logs/skill*.log

RUN pip install gensim 
RUN pip install pika

CMD ["/usr/bin/supervisord"]