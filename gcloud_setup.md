<!-- nano id_rsa.pub -->
<!-- nano id_rsa -->

cp /home/jupyter/drive/id_rsa ~/.ssh/id_rsa
cp /home/jupyter/drive/id_rsa.pub ~/.ssh/id_rsa.pub
sudo chmod 600 ~/.ssh/id_rsa
sudo chmod 600 ~/.ssh/id_rsa.pub
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa
sudo apt-get update
sudo apt-get install curl git
git clone git@github.com:manishiitg/recruitai.git
cd recruitai
git pull

gcloud auth activate-service-account --key-file=RecruitAI.json
gcloud config set project recruitai-266705
gsutil ls
mkdir pretrained
gsutil -m cp -r gs://recruitaiwork/* pretrained/
mkdir cvreconstruction
sudo mkdir /var/log/recruitai

cd /home/jupyter/drive/

sudo curl -L "https://github.com/docker/compose/releases/download/1.27.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

sudo chmod +x /usr/local/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

cd /home/jupyter/drive/recruitai

sudo apt-get remove -y docker docker-engine docker.io containerd runc
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io


echo "116.202.234.182:15672 rabbitmq" >> /etc/hosts

sudo docker-compose -f docker-compose-micro.yml build
sudo docker-compose -f docker-compose-micro.yml up -d