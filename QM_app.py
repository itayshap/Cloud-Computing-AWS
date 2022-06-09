import boto3
import http
import requests
import json
from flask import Flask, request, jsonify
import time 
import threading
from multiprocessing import Value
import queue
from datetime import datetime

AUTO_SCALE_TIME = 3
sem = threading.Semaphore()
work_id = Value('i', 0)
worker_counter = Value('i', 0)

config = {
    "DEBUG": True  # run app in debug mode
}

public_ip = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4").text

def spawn_worker():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    user_data = f'''#!/bin/bash
cat << EOF > /home/ubuntu/app.py
import requests
import os
import time
import http

def work(buffer, iterations):
    import hashlib
    output = hashlib.sha512(buffer).digest()
    for i in range(iterations - 1):
        output = hashlib.sha512(output).digest()
    return output

SECONDS_TO_TERMINATE = 5
start_time = time.time()

while True:
    response = requests.get("http://{public_ip}:5000/get_work")
    if response.status_code == http.HTTPStatus.NO_CONTENT:
        if int(time.time() - start_time) > SECONDS_TO_TERMINATE:
            requests.patch("http://{public_ip}:5000/worker_killed")
            break
        else:
            continue
    else:
        work_data = response.json()
        iterations = work_data["iterations"]
        buffer = work_data["work"].encode('utf-8')
        completed = work(buffer, iterations)
        response = requests.put("http://{public_ip}:5000/send_work", data=f'{{work_data["work_id"]}}: {{completed}}')
        start_time = time.time()
os.system('sudo shutdown -h now')
EOF

sudo apt update
cd /home/ubuntu/
python3 app.py
'''

    instance = ec2.run_instances(ImageId='ami-042e8287309f5df03', MinCount=1, MaxCount=1, UserData=user_data, 
    InstanceType='t2.micro', InstanceInitiatedShutdownBehavior = 'terminate')
   

def load_balancing():
    while True:
        sem.acquire()
        workers = work_queue.queue
        if len(workers) > 0:
            with worker_counter.get_lock():
                if worker_counter.value >= len(workers):
                    sem.release()
                    time.sleep(2)
                    continue
            middle_work = workers[int(len(workers) / 2)]
            if int(time.time() - middle_work['time']) > AUTO_SCALE_TIME:
                spawn_worker()
                with worker_counter.get_lock():
                    worker_counter.value += 1
        sem.release()                
        time.sleep(2)

app = Flask(__name__)
work_queue = queue.Queue()
completed_work = queue.Queue() 
app.config.from_mapping(config)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    work = request.get_data()
    with work_id.get_lock(): 
        new_work = {'work_id' :work_id.value, 'time': time.time(), 'work': work, 'iterations' : iterations}
    work_queue.put(new_work)
    with work_id.get_lock():
        work_id.value += 1
    return 'the work is in queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = int(request.args.get('top'))
    completed_jobs = []
    for _ in range(top):
        if completed_work.empty():
            break
        completed_jobs.append(completed_work.get())
    if len(completed_jobs) == 0:
        return "No completed work available"
    return ('\n').join(completed_jobs)


@app.route('/get_work')
def get_work():
    if work_queue.empty():
        return ('', http.HTTPStatus.NO_CONTENT)
    else:
        return jsonify(work_queue.get())

@app.route('/send_work', methods=['PUT'])
def send_work():
    work = request.get_data().decode('utf-8')
    completed_work.put(work)
    with worker_counter.get_lock():
        worker_counter.value -= 1
    return "work submitted"

@app.route('/worker_killed', methods=['PATCH'])
def worker_killed():
    with worker_counter.get_lock():
        worker_counter.value -= 1
    return "Message Received"

@app.route('/', methods=['GET'])
def status():
    return "QM_app is up"

if __name__ == "__main__":
    threading.Thread(target=load_balancing).start()
    app.run(host='0.0.0.0')
