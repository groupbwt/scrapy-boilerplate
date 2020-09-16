#!/bin/bash
set -eu
echo $RABBITMQ_USERNAME
echo $RABBITMQ_VIRTUAL_HOST
(
count=0;
# sleep to allow rabbitmq to start init flow and create necessary files in mounted dir
sleep 10;
# Execute list_users until service is up and running
until timeout 5 rabbitmqctl list_users >/dev/null 2>/dev/null || (( count++ >= 60 )); do sleep 1; done;
if rabbitmqctl list_users | grep guest > /dev/null
then
    sleep 1;
    # Delete default user and create new users
    rabbitmqctl add_user $RABBITMQ_USERNAME $RABBITMQ_PASSWORD
    rabbitmqctl set_user_tags $RABBITMQ_USERNAME administrator
    rabbitmqctl add_vhost $RABBITMQ_VIRTUAL_HOST
    rabbitmqctl set_permissions -p / $RABBITMQ_USERNAME ".*" ".*" ".*"
    rabbitmqctl set_permissions -p $RABBITMQ_VIRTUAL_HOST $RABBITMQ_USERNAME ".*" ".*" ".*"
    echo "user setup completed"
else
    echo "user already setup"
fi
) &

# Call original entrypoint
exec docker-entrypoint.sh rabbitmq-server $@
