import requests
from requests.auth import HTTPBasicAuth
from app.logging import logger as LOGGER
import subprocess
import time
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import shlex


amqp_url_base = os.getenv('RABBIT_API_URL')
RabbitMQLOGIN = os.getenv("RABBIT_LOGIN")


running_instance_check = {}
running_computes = []

def queue_process():

    LOGGER.critical("processing queues")
    global running_instance_check
    global running_computes

    min_process_to_start_gpu = 3400
    max_process_to_kill_gpu = 1

    queues = get_queues()
    
    for queue_type in ["summary", "picture"]:
        if queue_type in queues:

            type_instance_name = "torch" + queue_type
            if int(queues[queue_type]['in_process']) > min_process_to_start_gpu:
                

                instance_status = check_compute_running(type_instance_name)
                
                LOGGER.critical("number of running %s instances %s", queue_type,  len(instance_status))
                if len(instance_status) > 0:
                    for instance in instance_status:
                        is_any_torch_running = instance["is_any_torch_running"]
                        is_torch_responding = instance["is_torch_responding"]
                        running_instance_name = instance["running_instance_name"]
                        running_instance_zone = instance["zone"]

                        LOGGER.critical("instance status for type %s is_any_torch_running %s is_torch_responding %s, running_instance_name %s ", type_instance_name, is_any_torch_running, is_torch_responding, running_instance_name)
                        if is_any_torch_running:    
                            if not is_torch_responding:

                                if running_instance_name in running_instance_check:
                                    prev_check_time = running_instance_check[running_instance_name]
                                    time_passed = time.time() - prev_check_time
                                    LOGGER.critical("time passed %s for instance %s", time_passed, running_instance_name)
                                    if time_passed > 60 * 10:
                                        LOGGER.critical("some wrong majorly so deleting instance %s as time passed %s", running_instance_name, time_passed)
                                        delete_instance(running_instance_name, running_instance_zone)
                                        del running_instance_check[running_instance_name]

                                else:
                                    LOGGER.critical("its running but not responsive which is not good! check again")
                                    running_instance_check[running_instance_name] = time.time()
                            else:
                                if running_instance_name in running_instance_check:
                                    del running_instance_check[running_instance_name]
                                LOGGER.critical("already gpu %s running so nothing else to do", running_instance_name)
                else:
                    LOGGER.critical("not gpu running need to start")
                    start_compute_preementable(type_instance_name, queue_type)
            else:
                LOGGER.critical("%s has less than %s no need to start gpu %s", queue_type, min_process_to_start_gpu ,queues["summary"])

                instance_status = check_compute_running(type_instance_name)
                LOGGER.critical("number of running instances %s", len(instance_status))
                if len(instance_status) > 0:
                    LOGGER.critical("killing running gpus as no need")
                    for instance in instance_status:
                        is_any_torch_running = instance["is_any_torch_running"]
                        is_torch_responding = instance["is_torch_responding"]
                        running_instance_name = instance["running_instance_name"]
                        running_instance_zone = instance["zone"]
                        LOGGER.critical("instance status for type %s is_any_torch_running %s is_torch_responding %s, running_instance_name %s ", summary_instance_name, is_any_torch_running, is_torch_responding, running_instance_name)
                        delete_instance(running_instance_name, running_instance_zone)
        else:
            LOGGER.critical("%s not found in queues", queue_type)



def get_queues():
    res = requests.get(amqp_url_base + "/api/queues", verify=False,
                       auth=HTTPBasicAuth(RabbitMQLOGIN.split(":")[0], RabbitMQLOGIN.split(":")[1]))
    queues = res.json()
    # LOGGER(json.dumps(queues, indent=True))

    mq_status = {}
    running_process = 0
    for queue in queues:
        if queue["name"] == "resume" or queue["name"] == "picture" or queue["name"] == "summary":

            # print(queue)
            if "consumers" in queue.keys():
                mq_status[queue["name"]] = {
                    "consumers": queue["consumers"],
                    "in_process": queue["messages_unacknowledged_ram"] + queue["messages_ready"]
                }
                running_process += int(queue["messages_unacknowledged_ram"])

    LOGGER.critical(mq_status)
    # print(running_process)

    return mq_status


def get_connections():
    res = requests.get(amqp_url_base + "/api/connections", verify=False,
                       auth=HTTPBasicAuth(RabbitMQLOGIN.split(":")[0], RabbitMQLOGIN.split(":")[1]))
    connections = res.json()
    return connections


def get_compute_list():
    LOGGER.critical("getting instance list")
    result = subprocess.run(['gcloud', 'compute', 'instances',
                             'list', '--format="json"'], stdout=subprocess.PIPE)
    # print(result.stdout)
    vm_list = json.loads(result.stdout)
    # print(json.dumps(vm_list, indent=True))
    return vm_list


def check_compute_running(instance_name):

    global running_computes
    LOGGER.critical("check compute running")

    instance_status = []

    is_any_torch_running = False
    is_torch_responding = False
    running_instance_name = ""
    connections = get_connections()
    LOGGER.info("number of connections on rabbit mq %s", len(connections))
    vm_list = get_compute_list()
    LOGGER.critical("number of compute running %s", len(vm_list))
    for vm in vm_list:
        LOGGER.info("name %s, status %s", vm['name'], vm['status'])
        if instance_name in vm['name']:
            is_any_torch_running = True

            # print(json.dumps(vm, indent=True))
            running_instance_name = vm['name']

            # print(json.dumps(vm["networkInterfaces"][0], indent=True))
            ip = vm["networkInterfaces"][0]['accessConfigs'][0]["natIP"]
            # print()
            
            for connection in connections:
                # LOGGER.critical("%s == %s", connection["peer_host"],ip)
                if connection["peer_host"] == ip:
                    LOGGER.critical("host found so torch vm is working")
                    is_torch_responding = True
                    break

            LOGGER.critical("vm ip %s", ip)
            compute = {
                "is_any_torch_running" : is_any_torch_running,
                "is_torch_responding" : is_torch_responding,
                "running_instance_name" : running_instance_name,
                "zone" : vm["zone"]
            }
            instance_status.append(compute)
            running_computes.append(compute)

    return instance_status  #is_any_torch_running, is_torch_responding, instance_name


def get_zone_list():
    result = subprocess.run(
        ['gcloud', 'compute', 'zones', 'list', '--filter=us-', '--format="json"'], stdout=subprocess.PIPE)
    zone_list = json.loads(result.stdout)
    # print(json.dumps(vm_list, indent=True))
    # for zone in zone_list:
    #     print(zone['name'], zone['region'])

    # zone_list = {
    #     "name" : "us-central1-a",
    #     "name" : "us-central1-b",
    #     "name" : "us-central1-c",
    #     "name" : "us-central1-f",
    #     "name" : "us-east-b",
    # }
    return zone_list

def start_compute_preementable(instance_name, queue_type):
    zones = get_zone_list()
    max_attemps = 10
    for idx, zone in enumerate(zones):

        name = instance_name+ str(idx)
        LOGGER.critical("trying to start gpu for instance name %s for zone regision %s", name , zone["name"])
        start_compute(name, zone["name"], queue_type)

        instance_status = check_compute_running(name)
        if len(instance_status) > 0:
            LOGGER.critical("gpu started so breaking out")
            break
        if idx > max_attemps:
            LOGGER.critical("max attempts reached to start so breaking out")
            break

def start_compute(instance_name, zone, queue_type):

    # instance_name = "torchvm"
    # zone = "us-central1-a"

    # if not is_any_torch_running:
    try:

        vm_start = []

        
        # result = subprocess.call(shlex.split(f"./start.sh {instance_name} {zone}"), cwd="/workspace/app")
        if queue_type == "summary":
            result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family=common-cu101 --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-4 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_summary.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)
        elif queue_type == "picture":
            result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family=common-cu101 --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-4 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_picture.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)

        LOGGER.critical("stdout", result)

        # if result.stderr and len(result.stderr) > 0:
        #     if "already exists" in result.stderr:
        #         LOGGER.critical("container already exists")
        #     else:
        #         LOGGER.critical("stderr", result.stderr)
        #     return False

        # if "stdout" in result:
        #     if len(result.stdout) > 0:
        #         vm_start = json.loads(result.stdout)
        #         LOGGER.critical(json.dumps(vm_start, indent=True))

        #         is_vm_started = False
        #         if len(vm_start) > 0:
        #             if "name" in vm_start[0]:
        #                 LOGGER.critical("vm started with name %s",
        #                                 vm_start[0]['name'])
        #                 is_vm_started = True
        #         return True

        # return False
    except Exception as e:
        # LOGGER.critical("XXX %s", e)
        # return False
        pass


def delete_instance(instance_name, zone):
    # if is_any_torch_running:
    try:
        LOGGER.critical(" deleting instance")

        result = subprocess.call(shlex.split(f"gcloud beta compute instances delete {instance_name} --zone={zone} --quiet --format=json"), stdout=subprocess.PIPE)
        # result = subprocess.run(['gcloud', 'compute', 'instances', 'delete', instance_name,
        #                          "--zone="+zone, '--quiet', '--format="json"'], stdout=subprocess.PIPE)

        # if result.stderr and len(result.stderr) > 0:
        #     LOGGER.critical("stderr %s", result.stderr)

        if result.stdout and len(result.stdout) > 0:
            LOGGER.critical("stdout %s", result.stdout)
        return True
    except Exception as e:
        LOGGER.critical("YYY %s", e)
        return False

checkin_score_scheduler = BackgroundScheduler()
checkin_score_scheduler.add_job(queue_process, trigger='interval', seconds=1 * 60)
checkin_score_scheduler.start()
