
gcloud compute ssh --project java-ref --zone us-west1-b torch2-vm -- -L 8080:localhost:8080

gcloud compute project-info add-metadata \
    --metadata enable-oslogin=TRUE
# all os login to all instances

gcloud beta compute instances create torchvm3 \
  --zone=us-central1-f \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --machine-type="n1-standard-1" \
  --scopes storage-rw

gcloud beta compute disks create torch --zone us-central1-a --type pd-ssd
gcloud beta compute disks create torch --zone us-central1-a --type pd-ssd --source-snapshot=torchsnapshot

<!-- gcloud beta compute instances create torchvm3 --zone=us-central1-a --image-family=pytorch-latest-gpu --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator="type=nvidia-tesla-t4,count=1" --metadata="install-nvidia-driver=True" --machine-type="n1-standard-4" --scopes storage-rw --boot-disk-type=pd-ssd --preemptible -->


gcloud beta compute instances create torchvm3 --zone=us-central1-a --image-family=pytorch-latest-gpu --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type="n1-standard-4" --boot-disk-type=pd-ssd --metadata-from-file startup-script=gcloud_setup_summary.sh --scopes=logging-write,compute-rw,default --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible


gcloud beta compute instances create deep --zone=us-central1-a --image-family=pytorch-latest-gpu --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type="n1-standard-4" --boot-disk-type=pd-ssd --scopes=logging-write,compute-rw,default --create-disk size=100GB,type=pd-ssd,auto-delete=yes

#https://cloud.google.com/compute/docs/startupscript#gcloud

#n1 standard 4 



gcloud compute instances attach-disk deep --disk torch --zone us-central1-a

gcloud beta compute ssh --project java-ref --zone us-central1-a torchvm3

gcloud beta compute ssh --project java-ref --zone us-central1-b torchvm3 -- -L 8080:localhost:8080

sudo lsblk
sudo mkfs.ext4 -m 0 -F -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/sdb



sudo mkdir -p /home/jupyter/drive
sudo mount -o discard,defaults /dev/sdb /home/jupyter/drive
sudo chmod a+w /home/jupyter/drive

gcloud compute instances stop torchvm3 --zone=us-central1-a
gcloud compute instances delete torchvm3 --zone=us-central1-a



gcloud compute instances add-metadata torchvm3 --metadata-from-file startup-script=gcloud_setup.sh --zone=us-central1-a