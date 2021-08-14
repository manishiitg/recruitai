FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/gender/supervisor/conf.d/gender.conf /etc/supervisor/conf.d/gender.conf

COPY ./gcp-service-account.json /workspace/app/RecruitAI.json
COPY ./gcp-service-account.json /workspace/RecruitAI.json

RUN truncate -s 0 /workspace/logs/gender*.log

RUN pip install pika
RUN pip install flair 

RUN apt-get install -y debconf-utils
ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone
# RUN rm /etc/localtime
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
RUN export DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get clean


CMD ["/usr/bin/supervisord"]