FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"


WORKDIR /workspace

COPY requirements.txt /workspace/


RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg



RUN pip install transformers
RUN pip uninstall -y tokenizers
RUN pip install tokenizers
RUN pip install google-cloud-storage


RUN pip install flask Flask-PyMongo Flask-Cors Flask-JWT-Extended pytest apscheduler redis elasticsearch \
    numpy gensim flair fuzzywuzzy
# RUN pip install -r requirements.txt

COPY RecruitAI.json /workspace/

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

RUN gcloud auth activate-service-account --key-file=RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gsutil ls

RUN pip install gunicorn
RUN pip install -e git+https://github.com/nvie/rq.git@master#egg=rq

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs","/workspace/app"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/recruitai.conf /etc/supervisor/conf.d/recruitai.conf
COPY ./supervisor/conf.d/queue.conf /etc/supervisor/conf.d/queue.conf

RUN truncate -s 0 /workspace/logs/flask*.log

# ADD app /workspace/app, using volume instead


RUN pip install pika

CMD ["/usr/bin/supervisord"]

EXPOSE 5000