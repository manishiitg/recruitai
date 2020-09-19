#!/bin/bash

gcloud auth activate-service-account --key-file=/workspace/java-ref-7a9117277dda.json >&1
gcloud config set project java-ref >&1

echo "$1" >&1
echo "x$2x" >&1

gcloud beta compute instances create $1 --zone=$2 --image-family=common-cu101 --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-4 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_summary.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json >&1