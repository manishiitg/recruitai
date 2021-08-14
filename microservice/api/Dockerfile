FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"


WORKDIR /workspace

# COPY requirements.txt /workspace/


RUN pip install flask Flask-PyMongo Flask-Cors Flask-JWT-Extended===3.25.1 pytest apscheduler
# RUN pip install -r requirements.txt

RUN pip install gunicorn

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs","/workspace/app"]

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/api/supervisor/conf.d/recruitai.conf /etc/supervisor/conf.d/recruitai.conf
COPY ./microservice/api/supervisor/conf.d/queue.conf /etc/supervisor/conf.d/queue.conf

RUN truncate -s 0 /workspace/logs/flask*.log

# ADD app /workspace/app, using volume instead

RUN pip install pika

RUN pip install google-cloud-storage

RUN pip install jsonlines


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

EXPOSE 5000