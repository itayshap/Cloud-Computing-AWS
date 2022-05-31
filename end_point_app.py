from flask import Flask, request, jsonify
import math

config = {
    "DEBUG": True  # run app in debug mode
}

app = Flask(__name__)

@app.route('/enqueue', methods=['PUT'])
def enqueue():
    iterations = request.args.get('iterations')
    work = request.get_json()
    requests.put("http://54.87.0.73:5000/send_work", json={"work": str(completed_work), "iterations": iterations})
    return 'work pushed to queue'

@app.route('/pullCompleted', methods=['POST'])
def pullCompleted():
    top = request.args.get('top')
    response = requests.post("http://54.87.0.73:5000/send_work", json={"top": top})
    return response.content