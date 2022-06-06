import boto3
import requests
import json
from flask import Flask, request, jsonify
import time 
import threading
import queue
from datetime import datetime

AUTO_SCALE_TIME = 3
thread_lock = threading.Lock()
work_id = 0

config = {
    "DEBUG": True  # run app in debug mode
}

public_ip = requests.get("http://169.254.169.254/latest/meta-data/public-ipv4").text

def spawn_worker():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    user_data = f'''#!/bin/bash
    cat > /home/ubuntu/app.py<< EOF
    import requests
    import os
    import time
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
        if response is None and int(time.time() - start_time) > SECONDS_TO_TERMINATE:
            break
        else:
            work_data = response.get_json()
            iterations = work_data["iterations"]
            buffer = work_data["work"]
            completed_work = work(buffer, iterations)
            response = requests.put("http://{public_ip}:5000/send_work", data=completed_work.decode("utf-8"))
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
        with thread_lock:
            workers = work_queue.queue
            if len(workers) > 0:
                middle_work = workers[int(len(workers) / 2)]
                if int(time.time() - middle_work['time']) > AUTO_SCALE_TIME:
                    spawn_worker()
        time.sleep(5)

app = Flask(__name__)
work_queue = queue.Queue()
completed_work = queue.Queue() 
app.config.from_mapping(config)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    work = request.get_data()
    new_work = {'work_id' :work_id, 'time': time.time(), 'work': work, 'iterations' : iterations}
    work_queue.put(new_work)
    with thread_lock:
        work_id += 1 
    return 'the work is in queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = int(request.args.get('top'))
    completed_jobs = []
    for i in range(top):
        if completed_work.empty():
            break
        completed_jobs.append(completed_work.get())
    return jsonify(completed_jobs)


@app.route('/get_work')
def get_work():
    if work_queue.empty():
        return None
    else:
        return work_queue.get()

@app.route('/send_work', methods=['PUT'])
def send_work():
    work = request.get_data()
    completed_work.put(work.decode("utf-8"))
    return "work submitted"

@app.route('/', methods=['GET'])
def status():
    date = datetime.now()
    return date.strftime("%d/%m/%y")

if __name__ == "__main__":
    threading.Thread(target=load_balancing).start()
