FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"


WORKDIR /workspace

# COPY requirements.txt /workspace/


RUN pip install flask Flask-PyMongo Flask-Cors Flask-JWT-Extended pytest apscheduler
# RUN pip install -r requirements.txt

COPY RecruitAI.json /workspace/

RUN pip install gunicorn

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

RUN pip install google-cloud-storage
COPY ./RecruitAI.json /workspace

RUN pip install jsonlines

CMD ["/usr/bin/supervisord"]

ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone && \
apt-get update && apt-get install -y tzdata && \
rm /etc/localtime && \
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
dpkg-reconfigure -f noninteractive tzdata && \
apt-get clean

EXPOSE 5000