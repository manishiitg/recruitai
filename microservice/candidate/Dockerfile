FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/candidate/supervisor/conf.d/candidate.conf /etc/supervisor/conf.d/candidate.conf

RUN truncate -s 0 /workspace/logs/candidate*.log

RUN pip install transformers 
RUN pip install pika
RUN pip install beautifulsoup4
RUN pip install pymongo
RUN pip install gensim===3.8.3
RUN pip install scipy
RUN pip install spacy===2.3.5
RUN python -m spacy download en

RUN apt-get install -y debconf-utils
ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone
# RUN rm /etc/localtime
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
RUN export DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get clean

RUN pip install pymemcache redis

CMD ["/usr/bin/supervisord"]