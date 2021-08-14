FROM  pytorch/pytorch:1.7.0-cuda11.0-cudnn8-runtime
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg git build-essential

RUN pip install --upgrade cython
RUN pip install 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'
# RUN pip install 'git+https://github.com/facebookresearch/detectron2.git'
RUN python -m pip install detectron2 -f \
  https://dl.fbaipublicfiles.com/detectron2/wheels/cu110/torch1.7/index.html

RUN pip install google-cloud-storage
RUN pip install pika

RUN add-apt-repository ppa:libreoffice/ppa -y
RUN apt-get update && apt-get -y autoclean && apt-get install --fix-missing
RUN apt-get install libreoffice -y
RUN apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config -y
RUN apt-get install python-poppler poppler-utils -y \
    && apt-get -y autoclean

RUN curl -sL https://deb.nodesource.com/setup_14.x  | bash -
RUN apt-get -y install nodejs

RUN node --version
RUN npm --version

RUN npm install -g pdf-text-extract


RUN pip install numpy opencv-python pdfminer.six pdf2image tesserocr fuzzywuzzy[speedup] pytest flair
# RUN pip install -r requirements.txt

VOLUME ["/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

RUN pip install gunicorn

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./microservice/resume/supervisor/conf.d/resume.conf /etc/supervisor/conf.d/resume.conf

RUN truncate -s 0 /workspace/logs/resume*.log

COPY ./gcp-service-account.json /workspace/RecruitAI.json
COPY ./gcp-service-account.json /workspace/app/RecruitAI.json

RUN gcloud auth activate-service-account --key-file=/workspace/RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gsutil ls

RUN pip install transformers==3.5.1 beautifulsoup4 redis pymongo

RUN apt-get install default-jdk -y
# ADD app /workspace/app, using volume instead

RUN apt-get install -y debconf-utils
ENV TZ=Asia/Kolkata
RUN echo $TZ > /etc/timezone
# RUN rm /etc/localtime
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime
RUN export DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata
RUN apt-get clean


RUN mkdir /workspace/recruit-tags-flair-roberta-word2vec
RUN mkdir /workspace/detectron4_5000_fpn

RUN pip install pymemcache redis
RUN pip install PyMuPDF
RUN npm install -g pdf2json
RUN apt-get install imagemagick -y
RUN sed -i_bak 's/rights="none" pattern="PDF"/rights="read | write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml
CMD ["/usr/bin/supervisord"]