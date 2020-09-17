#!/bin/sh
# <!-- nano id_rsa.pub -->
# <!-- nano id_rsa -->

sudo su
sudo mkdir -p /home/jupyter/drive
sudo mount -o discard,defaults /dev/sdb /home/jupyter/drive
sudo chmod a+w /home/jupyter/drive

cd /home/jupyter/drive
cp /home/jupyter/drive/id_rsa ~/.ssh/id_rsa
cp /home/jupyter/drive/id_rsa.pub ~/.ssh/id_rsa.pub
sudo chmod 600 ~/.ssh/id_rsa
sudo chmod 600 ~/.ssh/id_rsa.pub
eval $(ssh-agent -s)
ssh-add ~/.ssh/id_rsa
sudo apt-get update
sudo apt-get install curl git
echo -e "Host github.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config
git clone git@github.com:manishiitg/recruitai.git
cd recruitai
sudo chown -R manis:manis .git
git pull

gcloud auth activate-service-account --key-file=RecruitAI.json
gcloud config set project recruitai-266705
gsutil ls
mkdir -p pretrained
gsutil -m cp -r -n gs://recruitaiwork/* pretrained/
mkdir -p cvreconstruction
sudo mkdir -p /var/log/recruitai

cd /home/jupyter/drive/

# sudo curl -L "https://github.com/docker/compose/releases/download/1.27.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
# sudo chmod +x /usr/local/bin/docker-compose
# sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

sudo pip3 install git+https://github.com/beehiveai/compose.git
sudo pip3 install -U six
cd /home/jupyter/drive/recruitai

sudo apt-get remove -y docker docker-engine docker.io containerd runc
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io


echo "116.202.234.182 rabbitmq" >> /etc/hosts
echo "116.202.234.182 redis" >> /etc/hosts

sudo docker-compose -f docker-compose-gpu.yml build
sudo docker-compose -f docker-compose-micro.yml up -d

