FROM  python:3
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/filter/supervisor/conf.d/filter.conf /etc/supervisor/conf.d/filter.conf
COPY ./microservice/filter/supervisor/conf.d/index.conf /etc/supervisor/conf.d/index.conf

RUN truncate -s 0 /workspace/logs/filter*.log

RUN pip install fuzzywuzzy[speedup]
RUN pip install pika
RUN pip install redis
RUN pip install apscheduler
RUN pip install pymongo

RUN apt-get install -y debconf-utils
ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone
# RUN rm /etc/localtime
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
RUN export DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get clean

RUN pip install pymemcache redis requests
RUN pip install email-validator

CMD ["/usr/bin/supervisord"]