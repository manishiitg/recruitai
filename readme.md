===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.

Initial Data Copy
===================

gcloud auth activate-service-account --key-file=RecruitAI.json
gcloud config set project recruitai-266705
gsutil ls
mkdir pretrained
gsutil -m cp -r gs://recruitaiwork/* pretrained/ 
mkdir batchprocessing
sudo mkdir /var/log/recruitai

http://144.76.110.170:5001/#/datasets

Docker
===========

sudo docker-compose build
sudo docker-compose up -d

docker exec -it recruit_ai_1 bash

sudo docker-compose up -d --scale=resumemq=6

# running this multiple either via scale or prefetch queue is taking more time than running one at time


sudo docker exec -it recruitai_resumemq_1 bash

sudo docker image build -t recruitai .


sudo docker exec -it recruitai_rabbitmq_1 rabbitmqctl purge_queue image


sudo docker container run --name recruitai \
      -v $(pwd)/pretrained:/workspace/pretrained \
      -v $(pwd)/batchprocessing:/workspace/batchprocessing \
      -v $(pwd)/cvreconstruction:/workspace/cvreconstruction \
      -v $(pwd)/app:/workspace/app \
      -v /var/log/recruit:/workspace/logs \
      -d -p 8085:8085 \
      recruitai FLASK_APP=app && export FLASK_DEBUG=1 && export FLASK_ENV=development && flask run --host 0.0.--port 8085

sudo docker container run --name recruitai \
      -v $(pwd)/pretrained:/workspace/pretrained \
      -v $(pwd)/batchprocessing:/workspace/batchprocessing \
      -v $(pwd)/cvreconstruction:/workspace/cvreconstruction \
      -v $(pwd)/app:/workspace/app \
      -v /var/log/recruit:/workspace/logs \
      -d -p 8085:8085 \
      recruitai bash

sudo docker container run -it recruitai_resumemq_1 \
      -v $(pwd)/pretrained:/workspace/pretrained \
      -v $(pwd)/batchprocessing:/workspace/batchprocessing \
      -v $(pwd)/cvreconstruction:/workspace/cvreconstruction \
      -v $(pwd)/app:/workspace/app \
      -d \
      recruitai_resumemq_1 bash
      

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

localhost:9200 elastic search url
localhost:5601 for kibana and log viewer

setup filebeat dashboards 
./filebeat setup --dashboards --strict.perms=false -E setup.kibana.host=kibana:5601 -E output.elasticsearch.hosts=["elasticsearch:9200"]


# if elastic search is not running try this once
sudo sysctl -w vm.max_map_count=262144

sudo docker-compose logs -f

tail -f /var/log/recruitai/flask_out.log
tail -f /var/log/recruitai/flask_err.log

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
4) need to work on test cases
5) need to setup metricbeat




in the micro service(done)
a) store results in redis (done)
b) create another mq for elastic search?
c) directly write to mongodb of recruit (done)
d) we are not writing to elastic search (done)
f) make app also inta seperate api microservice (done)
g) fix the async exception in resume mq
f) move amqurl to config. small task (done)

h) for the micro services make input / output patterns so its configurable and not limited to just mongo (skipped)
== i think output should be on mongodb.
== because if we make expressapi, then need to worry about authentication, security, server going down etc.
== no need to create any api
== better to directly use mongodb access. 

i) create stats and proper log tracking across services

j) see api gateway like kong and see linkerd.io with kubernotes and open trace for logging

h) make recruit node and angular also docker based

g) there is an issue, suppose any micro service is down. but api is fired, even in microervice is started in next 5sec it doesn't repose. it only responds to new api request not old onces

h) need to look at candidate resume text data sync for faster processing and this can be used to update elastic search as well (done testing pending)


g) integrate candidate skill with add resume process (done but testing pending)


g) seperate pic/ner/ner classify into seperate micro services(postponed)
ner, nerclassify, picture. == i don't see much advantage of doing this except just to make code clean
== can do it later (not important)

h) need to put test for every micro service 
i) need to setup swagger for api
j) need to remove the doc to pdf code from resumemq as its part of imagemq now


g)
# data sync mq
 # this is very very slow for full job profile 
# need to add bulk to search or something

h) setup stats for ai, inclding time taken, pending etc how long it will take

j) make files common and reusable between microservices

l) delete job profile, etc won't update data sync right now. this is a problem.
when we do full datasync it should delete all previous keys and create new.
we can schedule this one or twice a day as well (completed)

m) need to make this muti account with priority & setup priority tasks for latest cvs













datasync neds to be faster. right now, there was bulk update of all tag_ids in a job profile.
this takes very very long