===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.

Initial Data Copy
===================
https://cloud.google.com/sdk/docs/quickstart-debian-ubuntu

gcloud auth activate-service-account --key-file=RecruitAI.json

gcloud config set project recruitai-266705

gsutil ls

mkdir pretrained

gsutil -m cp -r gs://recruitaiwork/* pretrained/ 

mkdir cvreconstruction

sudo mkdir /var/log/recruitai


python -m app.main

http://144.76.110.170:5001/#/datasets

redis access
==========
http://116.202.234.182:8081/

To debug flask app
==================

open terimnal of microservice api and 
flask run -p 5001 -h 0.0.0.0

kibana
=======

http://116.202.234.182:5601/app/kibana



Docker
===========

sudo docker-compose build
sudo docker-compose up -d

docker exec -it recruit_ai_1 bash

sudo docker-compose  up -d --scale=resumemq=2 --scale=qamq=1 --scale=imagemq=4 --scale=picturemq=2
sudo docker-compose  up -d --scale=imagemq=4

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


http://116.202.234.182:9200/_cluster/health?pretty=true

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


NER Data
==========

http://144.76.110.170:8086/training/ner/convert_to_label_studio

this url will fetch data from ai errors collection and create version folder like v2, v3 etc.

files need to copied from these version folder to the main and label-studio project should be restarted for labelling data

e.g
cp -rf label-studio/ner/project/backup/v2/* label-studio/ner/project/
sudo docker-compose restart label-studio-ner

COCO Annotator
=================

http://144.76.110.170:8086/training/viz/convert_for_annotation

get cv's for annanotaion. manually download and copy the images


http://176.9.137.77:5000/#/datasets

its not part of this docker compse, its using orgianl docker-compose file itself 
https://github.com/jsbroks/coco-annotator/
itself and running as a seperate service


there is a dataset called resume/ which has all the images

there is a folder called trainig/coco which has all the trainig data.

this needs to be updated manually from time to time

current process for this to work

1. we open recruit system. go through the cv's there if we find issue we report it. the url gets saved in db
2. user needs to manually go into db. find the url open it on browser. see manually if the parsed was bad.
3. if parsing was bad, download the cv via browser and create a directly.
4. delete the data from db manually
5. upload it to server manually and do tagging there again



== INFO



export FLASK_APP=app && export FLASK_DEBUG=1 && export FLASK_ENV=development && flask run --host 0.0.0.0 --port 8085


 ps -aux | grep 8085

 ===

 curl --user elastic:DkIedPPSCb -XPUT -H "Content-Type: application/json" http://127.0.0.1:9200/_all/_settings -d '{"index.blocks.read_only_allow_delete": "false"}'

also check the disk usage if this error comes



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








QA System TODO
======================

a) i am getting different data from QA and which is good. its more specific to sections and questions asked.
==== done

b.1) so next steps is to combine QA and NER. NER should follow QA, so that if we get experiance say 2years from ner, we know if its from intership or projects or actual exp. This was not possible from pure QA.
b.2) from NER need to solve i.e showing better data section wise.
b.3) first is need to remove NER from current system and combine it with QA
b.4) this should affect skilexill extract also. now we whave specific lines to extract skill instead of entire resume
b.5) need to remove ner and candidate classify from resumemq

b.6. fix location based on correct section
b.7. skills score is not used at all. need to revist it .
b.8. tag for other sections except company are not used at all.... 


ideas from morning. 
can we improve just simple basic ner more. if yes, then we can get fast parsing as we are skipping detectron.
all is good in this mainly except work exp.

======

c) for proper display of a resume, i need to capture spacing as well. not just text. right now i am missing spacing fully.
this is a problem!



c.1) for fast parsing we can skip summary/detectron/ner etc and only do QA?
c.2) for full parsing we will do everything?


f) need to integrate with filters


g) can we match resume to a job based on this yet????
h) can we make candidate database better with this? we can remove detectron as such from candidata database and instead just do qa?

i) replace things like \u2022 \u25cf etc with actual bullet poitns


k) do longformer with ner

l) need to create edge cases for qa manual labelling further. like if qa model is able to return total work yers but unable to return company name its a problem. needd to see that. and also create similar questions or compare it with ner. or similar use score and generate docs with lowest score.

m) need to jobs overview with qa n  model as well and get data


p) should i ask questions like references/hobbies only if these text exist in the page content? as these are very rare.
and why do i event want reference? it come in orphans

# http://176.9.137.77:81/dashboard/candidate-details/candidate/ATOZZ/5fafefc410b05d00394b3609 tag this manually












































=========
OLD TODO

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
done)



=====
Statistics Setup
=====

