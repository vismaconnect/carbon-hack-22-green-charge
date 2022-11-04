#!/bin/sh

while getopts ":i:u:" opt; do
  case $opt in
    i) ACCOUNT_ID="$OPTARG"
    ;;
    u) ACCOUNT_USER="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac

  case $OPTARG in
    -*) echo "Option $opt needs a valid argument"
    exit 1
    ;;
  esac
done

printf "Argument ACCOUNT_ID is %s\n" "$ACCOUNT_ID"
printf "Argument ACCOUNT_USER is %s\n" "$ACCOUNT_USER"

TMP_DIR=tmp
Template_DIR=tmp
STAGE=Dev
STAGE_BUCKET=dev
NAME=charge-device-state-machine
BUCKET_FUNCTION=$NAME-function-$STAGE_BUCKET
YAML_FILE=charge_device.yaml

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

sed -i "s/<<TIMESTAMP>>/$datetime/g" $Template_DIR/$YAML_FILE
sed -i "s/<<STAGE>>/$STAGE/g" $Template_DIR/$YAML_FILE
# sed -i "s/<<STAGE_BUCKET>>/$STAGE_BUCKET/g" $Template_DIR/$YAML_FILE
sed -i "s/<<ACCOUNT_ID>>/$ACCOUNT_ID/g" $Template_DIR/$YAML_FILE
sed -i "s/<<ACCOUNT_USER>>/$ACCOUNT_USER/g" $Template_DIR/$YAML_FILE

# deploy
sam validate --template-file $Template_DIR/$YAML_FILE
aws cloudformation package --template-file $Template_DIR/$YAML_FILE --output-template-file $TMP_DIR/$YAML_FILE --s3-bucket $BUCKET_FUNCTION
aws cloudformation deploy --template-file $TMP_DIR/$YAML_FILE --stack-name ChargeDeviceStateMachine$STAGE --parameter-overrides Stage=$STAGE Bucket=$BUCKET_FUNCTION --capabilities CAPABILITY_NAMED_IAM

if $CLEAN_UP
then
    rm -rf $TMP_DIR
    rm -rf $Template_DIR
fi
