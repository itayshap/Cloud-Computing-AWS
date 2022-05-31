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
    response = requests.get("http://54.87.0.73:5000/get_work")
    if response is None (time.time() - start_time) > SECONDS_TO_TERMINATE:
        break
    else:
        buffer = response.json()
        completed_work = work(buffer['1'].encode('utf-8'), 3)
        response = requests.put("http://54.87.0.73:5000/send_work", json={"completed_work": str(completed_work)})
        start_time = time.time()
os.system('sudo shutdown -h now')