#!/bin/sh

TMP_DIR=tmp
Template_DIR=tmp
STAGE=Dev
STAGE_BUCKET=dev
NAME=charge-device-state-machine
BUCKET_FUNCTION=$NAME-function-$STAGE_BUCKET
YAML_FILE=calibrate.yaml

CLEAN_UP=false

# create dirs
mkdir -p $TMP_DIR
mkdir -p $Template_DIR

#set timestamp
year=$(date +%Y)
month=$(date +%m)
day=$(date +%d)
hour=$(date +%H)
minutes=$(date +%M)
datetime=$year$month$day$hour$minutes

cp $YAML_FILE $Template_DIR

sed -i "s/<<STAGE>>/$STAGE/g" $Template_DIR/$YAML_FILE

# deploy
sam validate --template-file $Template_DIR/$YAML_FILE
aws cloudformation package --template-file $Template_DIR/$YAML_FILE --output-template-file $TMP_DIR/$YAML_FILE --s3-bucket $BUCKET_FUNCTION
aws cloudformation deploy --template-file $TMP_DIR/$YAML_FILE --stack-name CalibrateStateMachine$STAGE --parameter-overrides Stage=$STAGE Bucket=$BUCKET_FUNCTION --capabilities CAPABILITY_NAMED_IAM

if $CLEAN_UP
then
    rm -rf $TMP_DIR
    rm -rf $Template_DIR
fi
