FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN apt-get update && \
	apt-get install supervisor python3-dev -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/gpucloud/supervisor/conf.d/gpu.conf /etc/supervisor/conf.d/gpu.conf

RUN truncate -s 0 /workspace/logs/gpu*.log

RUN pip install pika
RUN pip install pymongo
RUN pip install redis
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

RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg git build-essential

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

COPY ./gcp-compute-service-account.json /workspace/gcp-compute-service-account.json
COPY ./gcp-service-account.json /workspace/RecruitAI.json
# COPY ./app/gcloud_setup_summary.sh /workspace
# COPY ./app/start.sh /workspace
# RUN chmod +x /workspace/start.sh

RUN gcloud auth activate-service-account --key-file=/workspace/gcp-compute-service-account.json
RUN gcloud config set project java-ref
# RUN gcloud auth activate-service-account --key-file=/workspace/RecruitAI-full.json
# RUN gcloud config set project recruitai-266705
RUN  pip install --upgrade google-api-python-client

RUN pip install apscheduler
RUN pip install sendgrid
RUN pip install slackclient

RUN pip install pymemcache redis

CMD ["/usr/bin/supervisord"]