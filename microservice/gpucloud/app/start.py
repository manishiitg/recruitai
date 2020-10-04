from sendgrid.helpers.mail import *
import requests
from requests.auth import HTTPBasicAuth
from app.logging import logger as LOGGER
import subprocess
import time
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import shlex
from datetime import datetime, timezone, timedelta
import random
import sendgrid


amqp_url_base = os.getenv('RABBIT_API_URL')
RabbitMQLOGIN = os.getenv("RABBIT_LOGIN")


running_instance_check = {}
running_computes = []

max_instances_to_run_together = 1

run_combined_gpu = True

min_run_gpu = 50 #50min running

is_process_running = False
last_process_running_time = 0

use_gpu = False # if false will start instance with cpu only

def queue_process():
    LOGGER.critical("processing queues")
    global is_process_running
    global running_instance_check
    global running_computes
    global last_process_running_time
    global run_combined_gpu

    if is_process_running:
        if (time.time() - last_process_running_time) < 1 * 60 * 60:
            LOGGER.critical("already running process so returnning")
            return

    is_process_running = True
    last_process_running_time = time.time()

    min_process_to_start_gpu = 500
    max_process_to_kill_gpu = 10

    now = datetime.now()

    print(now.hour)

    if now.hour > 21 or now.hour < 8:
        LOGGER.critical("its non working hours so will start gpu only if more than 500 process pending")
        min_process_to_start_gpu = 1000

    if not use_gpu:
        min_process_to_start_gpu = 100

    try:
        queues = get_queues()
        # sometimes i restart rabbitmq and this crashes
    except Exception as e:
        return
    

    for queue_type in ["all", "summary", "picture", "resume"]:
        if run_combined_gpu:
            if queue_type != "all":
                
                if int(queues[queue_type]['in_process']) < 3000:
                    continue
        else:
            if queue_type == "all":
                continue

        if queue_type in queues:

            type_instance_name = "torch" + queue_type
            if not use_gpu:
                type_instance_name = "torch-cpu" + queue_type
            LOGGER.critical("checking for queue type %s", type_instance_name)
            if int(queues[queue_type]['in_process']) > min_process_to_start_gpu:

                instance_status = check_compute_running(type_instance_name)
                LOGGER.critical("number of running %s instances %s",
                                queue_type,  len(instance_status))

                if int(queues[queue_type]['in_process']) > 3000 and queue_type != "all" and False:
                    instance_count = 0
                    for instance in instance_status:
                        running_instance_name = instance["running_instance_name"]
                        if queue_type in running_instance_name:
                            instance_count += 1

                    if instance_count == 0:
                        LOGGER.critical("need to start another gpu as more than 3k jobs pending")
                        slack_message("need to start another gpu as more than 3k jobs pending" + str(queues[queue_type]['in_process']) + "for queue type " + queue_type)
                        start_compute_preementable(type_instance_name, queue_type , len(instance_status) + 1)
                        instance_status = check_compute_running(type_instance_name)
                        

                if len(instance_status) >= 1:
                    if int(queues[queue_type]['in_process']) < 1000:
                        instance = instance_status[-1]
                        is_any_torch_running = instance["is_any_torch_running"]
                        is_torch_responding = instance["is_torch_responding"]
                        running_instance_name = instance["running_instance_name"]
                        running_instance_zone = instance["zone"]
                        created_at = instance['created_at']
                        if created_at > min_run_gpu * 60:
                            LOGGER.critical("killing second running gpus as no need")
                            slack_message(f"killing second running gpus as no need: {queues[queue_type]['in_process']}")
                            delete_instance(running_instance_name,
                                            running_instance_zone, "work completed")
                            if running_instance_name in running_instance_check:
                                del running_instance_check[running_instance_name]


                if len(instance_status) > 0:
                    for instance in instance_status:
                        is_any_torch_running = instance["is_any_torch_running"]
                        is_torch_responding = instance["is_torch_responding"]
                        running_instance_name = instance["running_instance_name"]
                        running_instance_zone = instance["zone"]

                        LOGGER.critical("instance status for type %s is_any_torch_running %s is_torch_responding %s, running_instance_name %s ",
                                        type_instance_name, is_any_torch_running, is_torch_responding, running_instance_name)
                        if is_any_torch_running:
                            if not is_torch_responding:
                                if running_instance_name not in running_instance_check:
                                    LOGGER.critical(
                                        "picking starting %s", instance["created_at"])
                                    running_instance_check[running_instance_name] = time.time(
                                    ) - instance["created_at"]

                                if running_instance_name in running_instance_check:
                                    prev_check_time = running_instance_check[running_instance_name]
                                    time_passed = time.time() - prev_check_time
                                    # it takes 5-10min for gpu to start its processing
                                    LOGGER.critical(
                                        "time passed %s for instance %s", time_passed, running_instance_name)

                                    max_time_passed = 60 * 10
                                    if queue_type == "picture":
                                        max_time_passed = 60 * 15
                                    if queue_type == "all" or queue_type == "resume":
                                        max_time_passed = 60 * 20

                                    if time_passed > max_time_passed:
                                        slack_message(f"some wrong majorly so deleting instance {running_instance_name} as time passed {time_passed}")
                                        LOGGER.critical(
                                            "some wrong majorly so deleting instance %s as time passed %s", running_instance_name, time_passed)
                                        delete_instance(
                                            running_instance_name, running_instance_zone, "vm not responding even after " + str(max_time_passed))
                                        del running_instance_check[running_instance_name]

                                else:
                                    LOGGER.critical(
                                        "its running but not responsive which is not good! check again")
                                    running_instance_check[running_instance_name] = time.time(
                                    )
                            else:
                                # if running_instance_name in running_instance_check:
                                # del running_instance_check[running_instance_name]
                                running_instance_check[running_instance_name] = time.time() - 10 * 60  # if gpu doesn't respond for 1sec, something it justs deleted it
                                LOGGER.critical(
                                    "already gpu %s running so nothing else to do", running_instance_name)
                else:
                    LOGGER.critical("not gpu running need to start")
                    start_compute_preementable(type_instance_name, queue_type)
            else:

                # slack_message(f"{queue_type} has less than {min_process_to_start_gpu} no need to start gpu {queues["summary"]}")
                LOGGER.critical("%s has less than %s no need to start gpu %s",
                                queue_type, min_process_to_start_gpu, queues["summary"])

                instance_status = check_compute_running(type_instance_name)
                LOGGER.critical("number of running instances %s",
                                len(instance_status))
                if len(instance_status) > 0:
                    if int(queues[queue_type]['in_process']) <= max_process_to_kill_gpu:
                        for instance in instance_status:
                            is_any_torch_running = instance["is_any_torch_running"]
                            is_torch_responding = instance["is_torch_responding"]
                            running_instance_name = instance["running_instance_name"]
                            running_instance_zone = instance["zone"]
                            created_at = instance["created_at"]

                            LOGGER.critical("instance status for type %s is_any_torch_running %s is_torch_responding %s, running_instance_name %s ",
                                                type_instance_name, is_any_torch_running, is_torch_responding, running_instance_name)
                            if created_at > min_run_gpu * 60:
                                LOGGER.critical("killing running gpus as no need")
                                slack_message(f"killing running gpus as no need: {queues[queue_type]['in_process']}")
                                delete_instance(running_instance_name,
                                                running_instance_zone, "work completed")
                                if running_instance_name in running_instance_check:
                                    del running_instance_check[running_instance_name]
                            else:
                                LOGGER.critical("not killing instance and running minimum of %s minutes", min_run_gpu)
                    else:
                        LOGGER.critical("not killing running gpu")

        else:
            LOGGER.critical("%s not found in queues", queue_type)

    is_process_running = False


def get_queues():
    res = requests.get(amqp_url_base + "/api/queues", verify=False,
                       auth=HTTPBasicAuth(RabbitMQLOGIN.split(":")[0], RabbitMQLOGIN.split(":")[1]))
    queues = res.json()
    # LOGGER(json.dumps(queues, indent=True))

    mq_status = {}
    running_process = 0
    total = 0
    for queue in queues:
        if queue["name"] == "resume" or queue["name"] == "picture" or queue["name"] == "summary":

            # print(queue)
            if "consumers" in queue.keys():
                mq_status[queue["name"]] = {
                    "consumers": queue["consumers"],
                    "in_process": queue["messages_unacknowledged_ram"] + queue["messages_ready"]
                }
                running_process += int(queue["messages_unacknowledged_ram"])
                total += int(queue["messages_unacknowledged_ram"]) + int(queue["messages_ready"])

    LOGGER.critical(mq_status)
    # print(running_process)

    mq_status["all"] = {
        "consumers": 0,
        "in_process": total
    }

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

    # global running_computes
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
        is_any_torch_running = False
        is_torch_responding = False
        running_instance_name = ""
        LOGGER.info("name %s, status %s", vm['name'], vm['status'])

        if instance_name in vm['name']:
            is_any_torch_running = True

            # print(json.dumps(vm, indent=True))

            # "creationTimestamp": "2020-09-19T00:41:59.148-07:00

            actual_time_stamp = vm["creationTimestamp"][:-6]
            # print(actual_time_stamp)

            created_at = datetime.strptime(
                vm["creationTimestamp"], '%Y-%m-%dT%H:%M:%S.%f%z')
            print("created_at", created_at)
            now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
            difference = now - created_at
            print("now", now)
            print("difference", difference.total_seconds())
            # process.exit()

            running_instance_name = vm['name']
            LOGGER.critical("running vm found %s", running_instance_name)

            print(json.dumps(vm["networkInterfaces"], indent=True))
            ip = ""
            if isinstance(vm["networkInterfaces"], list):
                vminstance = vm["networkInterfaces"][0]
            else:
                vminstance = vm["networkInterfaces"]

            if "accessConfigs" in vminstance:

                if isinstance(vminstance['accessConfigs'], list):
                    accessConfig = vminstance['accessConfigs'][0]
                else:
                    accessConfig = vminstance['accessConfigs']

                if "natIP" in accessConfig:
                    ip = accessConfig["natIP"]
            # print()

            for connection in connections:
                LOGGER.critical("%s == %s", connection["peer_host"],ip)
                if connection["peer_host"] == ip:
                    LOGGER.critical("host found so torch vm is working")
                    is_torch_responding = True
                    break

            LOGGER.critical("vm ip %s is_any_torch_running %s is_torch_responding %s",
                            ip, is_any_torch_running, is_torch_responding)
            compute = {
                "is_any_torch_running": is_any_torch_running,
                "is_torch_responding": is_torch_responding,
                "running_instance_name": running_instance_name,
                "zone": vm["zone"],
                "created_at": difference.total_seconds()
            }
            instance_status.append(compute)
            # running_computes.append(compute)

    return instance_status  # is_any_torch_running, is_torch_responding, instance_name


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


def start_compute_preementable(instance_name, queue_type, start_idx = -1):
    # LOGGER.critical("again starting!!!")
    # return
    global max_instances_to_run_together
    global running_instance_check
    zones = get_zone_list()
    max_attemps = 10
    started_instance = 0
    if use_gpu:
        email_subject = "gpu start compute preementable " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        email_subject = "cpu start compute preementable " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_content = ""
    for idx, zone in enumerate(zones):
        if idx <= start_idx:
            continue

        name = instance_name + str(idx)
        if use_gpu:
            log = f"trying to start gpu for instance name {name} for zone regision {zone['name']}"
        else:
            log = f"trying to start cpu for instance name {name} for zone regision {zone['name']}"
        slack_message(log)
        email_content += log + "\r\n"
        LOGGER.critical(log)
        start_compute(name, zone["name"], queue_type)

        instance_status = check_compute_running(name)
        
        if len(instance_status) > 0:

            if name in running_instance_check:
                del running_instance_check[name]

            email_content += "gpu started so breaking out " + name + "\r\n"
            LOGGER.critical("gpu started so breaking out")
            slack_message(f"gpu started so breaking out {name}")
            started_instance += 1
            if started_instance >= max_instances_to_run_together:
                email_content += "ran max instances to breaking out" + "\r\n"
                LOGGER.critical("ran max instances to breaking out")
                break
            else:
                LOGGER.critical("not breaking out")
                break
        if idx > max_attemps:
            slack_message("max attempts reached to start so breaking out")
            LOGGER.critical("max attempts reached to start so breaking out")
            break

    sendEmail(email_subject, email_content)


def start_compute(instance_name, zone, queue_type):

    # instance_name = "torchvm"
    # zone = "us-central1-a"

    # if not is_any_torch_running:
    try:

        vm_start = []

        # https://cloud.google.com/ai-platform/deep-learning-vm/docs/images

        # pytorch-latest-gpu # this is giving more errors with cuda docker

        image_family = ["common-cu101", "common-cu100"]

        # sometimes nvidia randomly fails
        image_family_name = random.choice(image_family)

        # result = subprocess.call(shlex.split(f"./start.sh {instance_name} {zone}"), cwd="/workspace/app")
        if use_gpu:
            if queue_type == "summary":
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-8 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_summary.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)
            elif queue_type == "picture":
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-4 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_picture.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)
            elif queue_type == "resume":
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-4 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_resume.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=100GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)
            else:
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --accelerator type=nvidia-tesla-t4,count=1 --metadata install-nvidia-driver=True --machine-type=n1-standard-8 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_all.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=200GB,type=pd-ssd,auto-delete=yes --preemptible --format=json"), stdout=subprocess.PIPE)
        else:
            image_family_name = "common-cpu"
            if queue_type == "picture":
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --machine-type=n1-standard-8 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_all_cpu_picture.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=200GB,type=pd-ssd,auto-delete=yes --network-interface=no-address --preemptible --format=json"), stdout=subprocess.PIPE)
            else:
                result = subprocess.call(shlex.split(f"gcloud beta compute instances create {instance_name} --zone={zone} --image-family={image_family_name} --image-project=deeplearning-platform-release --maintenance-policy=TERMINATE --machine-type=n1-standard-8 --boot-disk-type=pd-ssd --metadata-from-file startup-script=/workspace/app/gcloud_setup_all_cpu.sh --scopes=logging-write,compute-rw,cloud-platform --create-disk size=200GB,type=pd-ssd,auto-delete=yes --network-interface=no-address --preemptible --format=json"), stdout=subprocess.PIPE)
        # LOGGER.critical("stdout", result)

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


def delete_instance(instance_name, zone, reason):
    # if is_any_torch_running:
    LOGGER.critical("delete instance")
    return
    email_subject = "delete instance " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " + reason
    email_content = ""

    try:
        LOGGER.critical(" deleting instance")
        slack_message("deleting instance")
        

        result = subprocess.call(shlex.split(
            f"gcloud beta compute instances delete {instance_name} --zone={zone} --quiet --format=json"), stdout=subprocess.PIPE)
        # result = subprocess.run(['gcloud', 'compute', 'instances', 'delete', instance_name,
        #                          "--zone="+zone, '--quiet', '--format="json"'], stdout=subprocess.PIPE)

        # if result.stderr and len(result.stderr) > 0:
        #     LOGGER.critical("stderr %s", result.stderr)

        print(result)

        
        # if result.stdout and len(result.stdout) > 0:
        #     LOGGER.critical("stdout %s", result.stdout)
        #     email_content = result.stdout

        sendEmail(email_subject, email_content)
        slack_message(email_content)
        
        return True
    except Exception as e:
        LOGGER.critical("YYY %s", e)
        email_content = str(e)
        slack_message(str(e))
        sendEmail(email_subject, email_content)
        return False

    

# checkin_score_scheduler = BackgroundScheduler()
# checkin_score_scheduler.add_job(
#     queue_process, trigger='interval', seconds=1 * 60)
# checkin_score_scheduler.start()


from slack import WebClient
slack_web_client = WebClient(token='xoxb-98246795219-K2wljPXhhowEJoiT1Gua72C7')

def slack_message(message):
    slack_web_client.chat_postMessage(channel="product_recruit", 
                text=message, username='GPUCloud',
                icon_emoji=':robot_face:')
    

def sendEmail(subject, content):
    


    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("manish@excellencetechnologies.in")
    to_email = To("manisharies.iitg@gmail.com")
    subject = subject
    content = Content("text/plain", content)
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
    # print(response.status_code)
    # print(response.body)
    # print(response.headers)
