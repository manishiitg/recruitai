#!/bin/sh

echo "Time: $(date). Some error info." >> /home/manish/cron.log
sudo docker-compose restart imagemq  >> /home/manish/cron.log 2>&1
sudo docker-compose restart resumemq >> /home/manish/cron.log 2>&1
sudo docker-compose restart summarymq >> /home/manish/cron.log 2>&1
#sleep 10
#curl -q https://aiapi-1.exweb.in/datasync/full?account-name=devrecruit
#curl -q https://aiapi-1.exweb.in/datasync/full?account-name=excellencerecruit
#curl -q https://aiapi-1.exweb.in/datasync/full?account-name=rocketrecruit
#sudo docker-compose restart searchindexmq
echo "Time: $(date). Some error info." >> /home/manish/cron.log
#sudo docker-compose restart
sudo docker-compose restart searchindexmq
sudo docker-compose restart statsdatamq
