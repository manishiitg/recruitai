===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.


Few things to install
================================


sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config
sudo apt-get install python-poppler poppler-utils

===

export FLASK_APP=app
export FLASK_DEBUG=1
flask run --port 8085

===

Api end point exposed 

http://176.9.137.77:8085/skill/reactjs+php+html-jquery
(to get similar skills or negative skils + means similar skills and - means negative skills)

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
gsutil -m cp -r gs://recruitaiwork/detectron3_5000 pretrained/ 
gsutil -m cp -r gs://recruitaiwork/recruit-ner-flair-augment pretrained/
gsutil -m cp -r gs://recruitaiwork/word2vec/word2vecrecruitskills.model	 pretrained/



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

b) Classification of emails 

c) TBD. Semantic Search
d) TBD. Candidate Scoring