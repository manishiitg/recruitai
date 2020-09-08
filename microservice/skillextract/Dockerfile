FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor python3-dev -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/skillextract.conf /etc/supervisor/conf.d/skillextract.conf

RUN truncate -s 0 /workspace/logs/skillextract*.log

RUN pip install pika
RUN pip install --no-binary :all: nmslib
RUN pip install pymongo
RUN pip install scipy
RUN pip install gensim
RUN pip install spacy
RUN python -m spacy download en
RUN pip install redis

ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone && \
apt-get update && apt-get install -y tzdata && \
rm /etc/localtime && \
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
dpkg-reconfigure -f noninteractive tzdata && \
apt-get clean

CMD ["/usr/bin/supervisord"]