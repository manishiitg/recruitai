# brief overview all the microservices we have their purpose

1. API

This is the flask api's. This microservice/api doesn't have any business logic at all except exposting api end points 
and then publishing data to microservices

2. imagemq

When resume parsing starts first we convert docx, doc to pdf
and then save the pdf to image.
This is done in imagemq. This service saves data to db mongo and redis.
This service passes data to resumemq queue


2. resumemq

This is the most important microservice and this parses resume data full.
This is the most time taking one and take about 1min per resume on average.
This needs to be optmized for sure. 

Also in experments its been found that scaling instances using docker or incraese prefetch and scaling this make this parsing slower and not faster per cv. 

So as of now its been kept at 1 resume at a time and no parallel processing. 

Resume microservice does this 
a) first it saves the detectron predictions of images (this takes most amount of time) and this doesn't like parallel processing
b) next the predictions are converted to text using ocr. (this also takes time and i think doesn't like parallel)
c) next we convert ocr to text lines (this is custom code and logic)
d) next we do ner
f) next we do cv parts classify to classify lines
g) next we add to search the resume lines
h) next we save data to mongo
i) next we extract skills
j) next we extract gender
j) next we classify candidate according to label
k) next we pass to datasyncmq

3. candidatemq

This is to classify candidate to labels like softwaredevelpoer, hr, sales etc

this is called only internally via resumemq

4. classifymq

this is to classify cv lines/parts to their lables 
this is called only internally via resumemq

5. datasyncmq

this is to basically keep our internal redis cache updated.
this internally sends data to searchmq and filtermq
full datasycn every one on hour via cron

this is called internally via resumemq and also api.
API is mainly for update when candidate moved between job profile and labels

6. filtermq

this takes data from redis only and generates filter json for job profiles, candidate labels
this is called internally 



7. gendermq

this to predict gender from name

8. searchmq

to add data to elastic search

right now this is called from api as well and interally.

api can add to es index and also update meta data

its called internally via resumemq as well

need to correct its flow 

9. skillmq

this is only called via api.
this basically return skills which are closeby using word2vec model

10. skillextractmq

this will extract skills for candidate from resume data


11. statsmq

== not used yet