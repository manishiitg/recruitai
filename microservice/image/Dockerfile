FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace



RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg

RUN add-apt-repository ppa:libreoffice/ppa -y
RUN apt-get update && apt-get -y autoclean
RUN apt-get install libreoffice python-poppler default-jdk  poppler-utils -y \
    && apt-get -y autoclean


VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

RUN pip install gunicorn

RUN pip install pdfminer.six pdf2image
RUN pip install google-cloud-storage
RUN pip install pika

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/image/supervisor/conf.d/image.conf /etc/supervisor/conf.d/image.conf

RUN truncate -s 0 /workspace/logs/image*.log

COPY ./gcp-service-account.json /workspace/RecruitAI.json

RUN gcloud auth activate-service-account --key-file=/workspace/RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gsutil ls

RUN pip install redis pymongo


# ADD app /workspace/app, using volume instead

RUN pip install psutil

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