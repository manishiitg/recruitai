FROM  pytorch/pytorch
LABEL maintainer="Manish Prakash<manish@excellencetechnologies.in"


WORKDIR /workspace

COPY requirements.txt /workspace/


# update the repository sources list
# and install dependencies
RUN apt-get update \
    && apt-get install -y curl software-properties-common gnupg


RUN pip install --upgrade cython
RUN pip install 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'
RUN pip install 'git+https://github.com/facebookresearch/detectron2.git'
RUN pip install transformers
RUN pip uninstall -y tokenizers
RUN pip install tokenizers
RUN pip install google-cloud-storage


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


RUN pip install flask Flask-PyMongo Flask-Cors Flask-JWT-Extended pytest apscheduler redis rq elasticsearch \
    numpy gensim flair opencv-python pdfminer.six pdf2image tesserocr fuzzywuzzy
# RUN pip install -r requirements.txt

ADD app /workspace/app
COPY RecruitAI.json /workspace/

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN apt-get install apt-transport-https ca-certificates -y
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
RUN apt-get update && apt-get install google-cloud-sdk -y

RUN gcloud auth activate-service-account --key-file=RecruitAI.json
RUN gcloud config set project recruitai-266705
RUN gcloud auth list
RUN gsutil ls

RUN mkdir -p /workspace/pretrained
# -n to prevent redownloading should be removed in production
RUN gsutil -m cp -r -n gs://recruitaiwork/ /workspace/pretrained/ 

RUN pip install gunicorn 

RUN apt-get update && \
	apt-get install supervisor && \
    apt-get -y autoclean && \
	rm -rf /var/cache/apk/*