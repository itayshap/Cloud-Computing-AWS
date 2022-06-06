from flask import Flask, request
import os
from datetime import datetime

config = {
    "DEBUG": True  # run app in debug mode
}

public_ip = os.getenv('PUBLICID')
app = Flask(__name__)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = int(request.args.get('iterations'))
    work = request.get_json()
    requests.put(f"http://{public_ip}/send_work", json={"work": str(work), "iterations": iterations})
    return 'work pushed to queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = int(request.args.get('top'))
    response = requests.post(f"http://{public_ip}/get_work", json={"top": top})
    return response.content

@app.route('/', methods=['GET'])
def status():
    date = datetime.now()
    return date.strftime("%d/%m/%y")
