import boto3
import requests
import json
from flask import Flask, request, jsonify
import time 
import threading
import queue

AUTO_SCALE_TIME = 3
thread_lock = threading.Lock()
work_id = 1


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
            buffer = response.json()
            completed_work = work(buffer['1'].encode('utf-8'), 3)
            response = requests.put("http://{public_ip}:5000/send_work", json=\u007b"completed_work": str(completed_work)\u007d)
            start_time = time.time()
    os.system('sudo shutdown -h now')
    EOF

    sudo apt update
    cd /home/ubuntu/
    python3 app.py

    '''

    instance = ec2.run_instances(ImageId='ami-042e8287309f5df03', 
    KeyName='worker_keys', MinCount=1, MaxCount=1, UserData=user_data, 
    InstanceType='t2.micro', SecurityGroupIds=['sg-00baa6b599e1f8596',], InstanceInitiatedShutdownBehavior = 'terminate')
    instance.wait_until_running()

def load_balancing():
    while True:
        middle_work = int(work_queue.qsize() / 2)
        if int(time.time() - middle_work['time']) > AUTO_SCALE_TIME:
                spawn_worker()

app = Flask(__name__)
work_queue = queue.Queue() 
work_queue.put({'work_id' : 1, 'time': time.time(), 'work': "hello world", 'iterations' : 200})
completed_work = queue.Queue() 
app.config.from_mapping(config)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = request.args.get('iterations')
    work = request.get_json()
    new_work = {'work_id' :work_id, 'time': time.time(), 'work': work, 'iterations' : iterations}
    work_queue.put(new_work)
    with thread_lock:
        work_id += 1 
    return 'the work is in queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = request.args.get('top')
    completed_jobs = []
    for i in range(top):
        if completed_work.empty():
            break
        completed_jobs.append(completed_work.get())
    return json.dumps(completed_jobs, indent=2)


@app.route('/get_work')
def get_work():
    if work_queue.empty():
        return None
    else:
        return work_queue.get()

@app.route('/send_work', methods=['PUT'])
def send_work():
    work = request.get_json()
    completed_work.put(work)
    return "work submitted"
    
if __name__ == "__main__":
    threading.Thread(target=load_balancing).start()
    app.run(host='0.0.0.0', port=5000)

# 
# threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=True)).start()