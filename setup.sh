# debug
# set -o xtrace

KEY_NAME="cloud-course-`date +'%N'`"
KEY_PEM="$KEY_NAME.pem"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-`date +'%N'`"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


# echo "setup rule allowing SSH access to $MY_IP only"
# aws ec2 authorize-security-group-ingress        \
#     --group-name $SEC_GRP --port 22 --protocol tcp \
#     --cidr $MY_IP/32

# echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
# aws ec2 authorize-security-group-ingress        \
#     --group-name $SEC_GRP --port 5000 --protocol tcp \
#     --cidr $MY_IP/32


SEC_GRP_QM="myQM-sg-`date +'%N'`"
echo "setup firewall $SEC_GRP_QM"
aws ec2 create-security-group   \
    --group-name $SEC_GRP_QM       \
    --description "Access my instances" 

echo "setup rule allowing SSH access to QM"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP_QM --port 22 --protocol tcp \
    --cidr 0.0.0.0/0

echo "setup rule allowing HTTP (port 5000) access to QM"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP_QM --port 5000 --protocol tcp \
    --cidr 0.0.0.0/0

UBUNTU_20_04_AMI="ami-042e8287309f5df03"

echo "Creating IAM role for Queue Manager ec2..."
aws iam create-role --role-name QueueManagerRole --assume-role-policy-document file://trust_policy.json
aws iam attach-role-policy --role-name QueueManagerRole --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
aws iam create-instance-profile --instance-profile-name QueueManagerRole
aws iam add-role-to-instance-profile --role-name QueueManagerRole --instance-profile-name QueueManagerRole


echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP_QM)


INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

echo "attache IAM role to the  Queue Manager ec2 instance"
aws ec2 associate-iam-instance-profile --instance-id $INSTANCE_ID --iam-instance-profile Name=QueueManagerRole

PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" QM_app.py ubuntu@$PUBLIC_IP:/home/ubuntu/

echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
    sudo apt update
    sudo apt-get install python3.7
    sudo apt install python3-flask -y
    sudo apt install -y python3-boto3
    # run app
    export PUBLICID=$PUBLIC_IP
    export FLASK_APP=QM_app
    nohup flask run --host 0.0.0.0  &>/dev/null &
    exit
EOF

echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$PUBLIC_IP:5000


echo "Creating first Endpoint instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP_QM)


INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

EP1_PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $EP1_PUBLIC_IP"

echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" end_point_app.py ubuntu@$EP1_PUBLIC_IP:/home/ubuntu/

echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$EP1_PUBLIC_IP <<EOF
    sudo apt update
    sudo apt-get install python3.7
    sudo apt install python3-flask -y
    # run app
    export PUBLICID=$PUBLIC_IP
    export FLASK_APP=end_point_app
    nohup flask run --host 0.0.0.0  &>/dev/null &
    exit
EOF

echo "Creating Second Endpoint instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t2.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP_QM)


INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

EP2_PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $EP2_PUBLIC_IP"

echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" end_point_app.py ubuntu@$EP2_PUBLIC_IP:/home/ubuntu/

echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$EP2_PUBLIC_IP <<EOF
    sudo apt update
    sudo apt install python3-flask -y
    # run app
    export PUBLICID=$PUBLIC_IP
    export FLASK_APP=end_point_app
    nohup flask run --host 0.0.0.0  &>/dev/null &
    exit
EOF


echo "Endpoint one at http://$EP1_PUBLIC_IP"
echo "New Endpoint two at http://$EP2_PUBLIC_IP"
