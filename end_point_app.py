from flask import Flask, request
import os

config = {
    "DEBUG": True  # run app in debug mode
}

public_ip = os.getenv('PUBLICID')
app = Flask(__name__)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = request.args.get('iterations')
    work = request.get_json()
    requests.put(f"http://{public_ip}/send_work", json={"work": str(work), "iterations": iterations})
    return 'work pushed to queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = request.args.get('top')
    response = requests.post(f"http://{public_ip}/send_work", json={"top": top})
    return response.content