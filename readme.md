===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.

Initial Data Copy
===================

gcloud auth activate-service-account --key-file=RecruitAI.json
gcloud config set project recruitai-266705
gsutil ls
mkdir pretrained
gsutil -m cp -r gs://recruitaiwork/* pretrained/ 
mkdir logs
mkdir batchprocessing
sudo mkdir /var/log/recruitai

Docker
===========

sudo docker-compose build
sudo docker-compose up -d

sudo docker image build -t recruitai .

sudo docker container run --name recruitai \
      -v $(pwd)/pretrained:/workspace/pretrained \
      -v $(pwd)/batchprocessing:/workspace/batchprocessing \
      -v $(pwd)/cvreconstruction:/workspace/cvreconstruction \
      -v $(pwd)/logs:/workspace/logs \
      -d -p 8086:5000 \
      recruitai 

# if need to debug via bash
sudo docker container run -it --rm \
      -v $(pwd)/pretrained:/workspace/pretrained \
      -v $(pwd)/batchprocessing:/workspace/batchprocessing \
      -v $(pwd)/cvreconstruction:/workspace/cvreconstruction \
      -v $(pwd)/logs:/workspace/logs \
      recruitai bash

docker container logs recruitai

docker container rm -f recruitai

# helper functions
https://stackoverflow.com/questions/47223280/docker-containers-can-not-be-stopped-or-removed-permission-denied-error

curl localhost:9200/_cat/health



Few things to install
================================

pip install torch torchvision


pip install --upgrade cython

pip install 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'

pip install numpy

pip install 'git+https://github.com/facebookresearch/detectron2.git'

pip install transformers
pip uninstall tokenizers
pip install  tokenizers

pip install google-cloud-storage
sudo apt-get install libreoffice

sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config
sudo apt-get install python-poppler poppler-utils

npm install -g pdf-text-extract

export FLASK_APP=app && export FLASK_DEBUG=1 && export FLASK_ENV=development && flask run --host 0.0.0.0 --port 8085

 ps -aux | grep 8085

 ===

 curl -XPUT -H "Content-Type: application/json" http://127.0.0.1:9200/_all/_settings -d '{"index.blocks.read_only_allow_delete": null}'


=== 
cloud sdk

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

sudo apt-get install apt-transport-https ca-certificates gnupg

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -


sudo apt-get install libreoffice

sudo apt-get update && sudo apt-get install google-cloud-sdk

apt-get install python-dev libxml2-dev libxslt1-dev antiword unrtf poppler-utils pstotext tesseract-ocr flac ffmpeg lame libmad0 libsox-fmt-mp3 sox libjpeg-dev swig
pip install textract


gcloud auth login
gcloud config set project recruitai-266705
mkdir pretrained
gsutil -m cp -r gs://recruitaiwork/detectron3_5000 pretrained/ 
gsutil -m cp -r gs://recruitaiwork/recruit-ner-flair-augment pretrained/
gsutil -m cp -r gs://recruitaiwork/recruit-ner-word2vec-flair pretrained/
gsutil -m cp -r gs://recruitaiwork/word2vec/word2vecrecruitskills.model	 pretrained/
gsutil -m cp -r gs://recruitaiwork/word2vec/word2vecfull.bin pretrained/
mkdir pretrained/emailclassification
gsutil -m cp -r gs://recruitaiwork/emailclassification/xlnet pretrained/emailclassification
mkdir pretrained/emailclassification/tokenizer
gsutil -m cp -r gs://recruitaiwork/emailclassification/tokenizer pretrained/emailclassification

gsutil -m cp -r gs://recruitaiwork/cvpartsclassification pretrained/


=====
supervisor commands

supervisorctl reread
supervisorctl update all
supervisorctl start recruitai
supervisorctl restart recruitai


###### Architecture ######

Object is that it should be easily be deployed as cloud functions or docker image on server.

Pipeline will contain different things

a) CV Process
   1. Extract picture
   2. Extract resume data
   3. NER
   4. Classify Lines
   5. Skill Extraction
   6. Final Data for frontend


   == Input will be a pdf file. This pdf file can come via a file upload, glcoud bucket,
   == Once i have the pdf file, next steps will start like saving the pages to images
   == extracting pic
   == extraing text and detectron
   == need to upload all this back to gcloud storage..... and also local folder
   == should i just use gsutil in this case
   == and database which db to use.mongo or some gcloud...
   == when entire process finishes, how to send response bcak to requester

b) Classification of emails (done)
c) Word2Vec skill api (done)

d) TBD. Semantic Search
e) TBD. Candidate Scoring
f) TBD. Male/Female based on name





TBD. small things
a) redis lock issue test (done)
b) take cv text from nodejs as well, but they say that can take text of full page only
or maybe try myself with textract same as nodejs
== done
3) delete file from filesystem when processing is done, as this is taking too much space (done)
