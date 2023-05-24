#!/bin/bash
# Delete kubernetes manifests

# ============ FLASK =============== #
cd ./api_deployment
kubectl delete -f booking_api-deployment.yaml

# ============= MYSQL ================ #
cd ../db_deployment
kubectl delete -f mysql-secret.yaml
kubectl delete -f mysql-storage.yaml
kubectl delete -f mysql-deployment.yaml

