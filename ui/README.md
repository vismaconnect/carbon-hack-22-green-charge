# Carbon hack 22

## Introduction

This is a simple Web UI for the GreenCharge solution


## Python Flask Dockerized Application

The Web UI application is a Python Flask applications. 

The application uses the lambda functions of the backend application.
The docker_build_local.sh and docker_build_aws.sh are template files.
You need to tailor them to your specific environment:

```bash
export AWS_ACCOUNT_ID=<>
export AWS_REGION=<>

export CALIBRATE_START_LAMBDA_FUNCTION_URL=<>
export CHARGE_START_LAMBDA_FUNCTION_URL=<>
export CHARGE_PROGRESS_LAMBDA_FUNCTION_URL=<>
export PERFORM_REGISTRATION_LAMBDA_FUNCTION_URL=<>
export CALCULATE_AVOIDED_EMISSIONS_LAMBDA_FUNCTION_URL=<>
``` 

Build and run the image locally using the following script:

```bash
./docker_build_local.sh
```

The application will be accessible at http:127.0.0.1:80.

In order to push the image to AWS ECR run this script:
```bash
./docker_build_aws.sh
```

To deploy the web application please refer to this tutorial:
https://acloudguru.com/blog/engineering/deploying-a-containerized-flask-application-with-aws-ecs-and-docker



