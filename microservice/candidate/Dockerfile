FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/candidate.conf /etc/supervisor/conf.d/candidate.conf

RUN truncate -s 0 /workspace/logs/candidate*.log

RUN pip install transformers 
RUN pip install pika
RUN pip install beautifulsoup4
RUN pip install pymongo
RUN pip install gensim
RUN pip install scipy
RUN pip install spacy
RUN python -m spacy download en

CMD ["/usr/bin/supervisord"]