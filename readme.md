===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.



Few things to install
================================


pip install --upgrade cython

pip install numpy

pip install 'git+https://github.com/facebookresearch/detectron2.git'

pip install transformers
pip uninstall tokenizers
pip install  tokenizers

pip install google-cloud-storage


sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config
sudo apt-get install python-poppler poppler-utils

export FLASK_APP=app
export FLASK_DEBUG=1
flask run --host 0.0.0.0 --port 8085

 ps -aux | grep 8085

===

Api end point exposed 

http://176.9.137.77:8085/skill/reactjs+php+html-jquery
(to get similar skills or negative skils + means similar skills and - means negative skills)


http://176.9.137.77:8085/emailclassify/i%20want%20to%20apply%20for%20a%20job%20as%20react%20developer/job%20application
(this to classify email as candidate or general)

http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/agency

####### need to work on this classifier more ###############
e.g
http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/thomas

returns
[
  {
    "ai": {
      "pipe1": {
        "other": 0.9968185424804688
      }
    }, 
    "body": "get studio benfies  asdf asfa sdfasd fasdf asdfasd fasdf asfd sdf s", 
    "subject": "thomas"
  }
]


http://176.9.137.77:8085/emailclassify/get%20studio%20benfies%20%20asdf%20asfa%20sdfasd%20fasdf%20asdfasd%20fasdf%20asfd%20sdf%20s/hello

[
  {
    "ai": {
      "pipe1": {
        "candidate": 0.9458337426185608
      }
    }, 
    "body": "get studio benfies  asdf asfa sdfasd fasdf asdfasd fasdf asfd sdf s", 
    "subject": "hello"
  }
]

so just the word "hello" has to be learnt as candidate. this is not correct.....




http://176.9.137.77:8086/resume/picture/102.pdf
get picture of candidate from resume


http://176.9.137.77:8086/resume/102.pdf

full parsing of a resume, getting all ner data and classiifcation and images

=== 
cloud sdk

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

sudo apt-get install apt-transport-https ca-certificates gnupg

curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -


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
   6. Final Data for frontend (TBD)


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
