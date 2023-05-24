#!/bin/bash
# Apply kubernetes manifests

# ============= MYSQL ================ #
cd ./db_deployment
kubectl apply -f mysql-secret.yaml
kubectl apply -f mysql-storage.yaml
kubectl apply -f mysql-deployment.yaml

# ============ FLASK =============== #
cd ../api_deployment
kubectl apply -f booking_api-deployment.yaml
