FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/summary.conf /etc/supervisor/conf.d/summary.conf

RUN truncate -s 0 /workspace/logs/summary*.log

RUN curl -sL https://deb.nodesource.com/setup_12.x  | bash -
RUN apt-get -y install nodejs

RUN node --version
RUN npm --version

RUN npm install -g pdf-text-extract
RUN pip install pdfminer.six

RUN pip install transformers 
RUN pip install pika
RUN pip install beautifulsoup4
RUN pip install pymongo

CMD ["/usr/bin/supervisord"]