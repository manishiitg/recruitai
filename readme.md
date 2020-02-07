===== Recruit AI =====

Code for different models and predictions only (no training) to deploy on production env.


Few things to install
================================


sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev pkg-config
sudo apt-get install python-poppler poppler-utils

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