FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg

RUN pip install --upgrade cython
RUN pip install 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'
RUN pip install 'git+https://github.com/facebookresearch/detectron2.git'

RUN pip install google-cloud-storage
RUN pip install pika

RUN add-apt-repository ppa:libreoffice/ppa -y
RUN apt-get update && apt-get -y autoclean
RUN apt-get install libreoffice-core --no-install-recommends -y
RUN apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config -y
RUN apt-get install python-poppler poppler-utils -y \
    && apt-get -y autoclean

RUN curl -sL https://deb.nodesource.com/setup_12.x  | bash -
RUN apt-get -y install nodejs

RUN node --version
RUN npm --version

RUN npm install -g pdf-text-extract


RUN pip install numpy opencv-python pdfminer.six pdf2image tesserocr fuzzywuzzy[speedup] pytest flair
# RUN pip install -r requirements.txt

VOLUME ["/workspace/pretrained","/workspace/batchprocessing","/workspace/cvreconstruction","/workspace/logs"]

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

RUN pip install gunicorn

RUN apt-get update && \
	apt-get install supervisor -y && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*

COPY ./supervisor/conf.d/resume.conf /etc/supervisor/conf.d/resume.conf

RUN truncate -s 0 /workspace/logs/resume*.log

COPY ./app/RecruitAI.json /workspace

RUN gcloud auth activate-service-account --key-file=/workspace/RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gsutil ls

RUN pip install transformers beautifulsoup4 redis pymongo

# ADD app /workspace/app, using volume instead

CMD ["/usr/bin/supervisord"]