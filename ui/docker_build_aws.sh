#! /bin/bash

# Details about your AWS account and region
export AWS_ACCOUNT_ID=<>
export AWS_REGION=<>

# Fill in the URL of the lambda function the webapp uses. Be sure to leave out the https:// part
# example:
# export CALIBRATE_START_LAMBDA_FUNCTION_URL=g5swxdn56l3v6g3k1g66lj0ahq0jbhhi.lambda-url.eu-north-1.on.aws
export CALIBRATE_START_LAMBDA_FUNCTION_URL=<>
export CHARGE_START_LAMBDA_FUNCTION_URL=<>
export CHARGE_PROGRESS_LAMBDA_FUNCTION_URL=<>
export PERFORM_REGISTRATION_LAMBDA_FUNCTION_URL=<>
export CALCULATE_AVOIDED_EMISSIONS_LAMBDA_FUNCTION_URL=<>

# Create an ECR repository for the application and put the name here.
export ECR_REPOSITORY=<>

export DOCKER_PATH=.
export ECR_PREFIX=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
export BUILD_VERSION=1

function create_image()	{
  aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_PREFIX
  docker build --tag $APP_NAME --file Dockerfile $DOCKER_PATH --build-arg CALIBRATE_START_LAMBDA_FUNCTION_URL=$CALIBRATE_START_LAMBDA_FUNCTION_URL --build-arg CHARGE_START_LAMBDA_FUNCTION_URL=$CHARGE_START_LAMBDA_FUNCTION_URL --build-arg CHARGE_PROGRESS_LAMBDA_FUNCTION_URL=$CHARGE_PROGRESS_LAMBDA_FUNCTION_URL --build-arg PERFORM_REGISTRATION_LAMBDA_FUNCTION_URL=$PERFORM_REGISTRATION_LAMBDA_FUNCTION_URL --build-arg CALCULATE_AVOIDED_EMISSIONS_LAMBDA_FUNCTION_URL=$CALCULATE_AVOIDED_EMISSIONS_LAMBDA_FUNCTION_URL  
  docker tag $ECR_APP_NAME $ECR_PREFIX/$ECR_APP_NAME
  docker push $ECR_PREFIX/$ECR_APP_NAME
}

export APP_NAME=$ECR_REPOSITORY
export ECR_APP_NAME=$APP_NAME:latest

create_image
