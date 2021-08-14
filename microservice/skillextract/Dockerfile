FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor python3-dev curl g++ -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/skillextract/supervisor/conf.d/skillextract.conf /etc/supervisor/conf.d/skillextract.conf
COPY ./microservice/skillextract/supervisor/conf.d/index.conf /etc/supervisor/conf.d/index.conf

RUN truncate -s 0 /workspace/logs/skillextract*.log

RUN pip install pika
RUN pip install --no-binary :all: nmslib
RUN pip install pymongo
RUN pip install scipy
RUN pip install gensim===3.8.3
RUN pip install spacy===2.3.5
RUN python -m spacy download en
RUN pip install redis

RUN apt-get install -y debconf-utils
ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone
# RUN rm /etc/localtime
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
RUN export DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get clean

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates gnupg2 -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

COPY ./gcp-service-account.json /workspace/app/RecruitAI.json
COPY ./gcp-service-account.json /workspace/RecruitAI.json

RUN gcloud auth activate-service-account --key-file=/workspace/RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gsutil ls


RUN mkdir /workspace/word2vec

RUN pip install pymemcache redis

CMD ["/usr/bin/supervisord"]