# Cloud Computing Home assignment 2

 ## Running the application:
1. Run init.sh
2. Run setup.sh - At the end of the script, the url for the 2 endpoints will be printed 


## Failure Guide:
Here are some potential problems with our design and suggested solutions: <br/>
1.	Input validations – we haven’t validated the query parameters or the body of the requests, obviously we should handle input validations in production.

2.	Our queue manager was created with access from any protocol and IP, not limited exclusively to end points – in production the access to the queue manager should be solely to the end points. <br>

3.	 In our implementation there is only one queue manager, in case of machine failure our system is completely disabled. Further, if one worker retrieves work and crushes while processing the work, the work will be lost as it was pulled out from the queue. One option is to redundantly stores the messages across several queue servers. Once a worker retrieves a work from the queue the work is not deleted from the queues for a pre-determined period of time. In this period of time other workers cannot retrieve this message, once the work is completed by the worker, the worker returns it to the completed queue and delete it from the unprocessed work queues, thus preventing this work to be processed multiple times by other workers. If the pre-determined period of time elapsed without the work being removed from the queue, the system will presume that the worker is down, and other workers will be allowed to retrieve the work to reprocessing. <br/>

4.	Following article 3, in case of a brain split, upon recovery of the communication, there should be a conflict mechanism invoked to resolve any data discrepancies. One option is comparing timestamp of the states of the works in the queues to determine which works to delete.  <br/>

5.	Also, we should consider adding a Dead Letter Queue that allows you to handle message failures, it will set aside massages that can’t be processed to determine why their processing didn’t succeed.

