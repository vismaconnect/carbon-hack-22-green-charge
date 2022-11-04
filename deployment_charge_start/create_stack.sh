#!/bin/sh

while getopts ":i:u:r:" opt; do
  case $opt in
    i) ACCOUNT_ID="$OPTARG"
    ;;
	r) ACCOUNT_REGION="$OPTARG" 
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
printf "Argument ACCOUNT_REGION is %s\n" "$ACCOUNT_REGION"
printf "Argument ACCOUNT_USER is %s\n" "$ACCOUNT_USER"

TMP_DIR=tmp
Template_DIR=templates
STAGE=Dev
STAGE_BUCKET=dev
NAME=charge-device-lambda
BUCKET_FUNCTION=$NAME-function-$STAGE_BUCKET
YAML_FILE=charge_start.yaml

S3_CONFIG="BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

REBUILD_LAYER=false
CREATE_BUCKET=true
DEPLOY_LAMBDA=true
CLEAN_UP=false

if $REBUILD_LAYER
then
    ./zip_layer_libs.sh
fi

if $CREATE_BUCKET
then
    # ensure s3 $BUCKET_FUNCTION
    aws s3 mb s3://$BUCKET_FUNCTION
	aws s3api put-public-access-block --bucket $BUCKET_FUNCTION --public-access-block-configuration $S3_CONFIG
	aws s3api put-bucket-encryption --bucket $BUCKET_FUNCTION --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

fi

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


if $DEPLOY_LAMBDA
then
cp lambda_charge_start.py $TMP_DIR/lambda_function.py

sed -i "s/<<ACCOUNT_ID>>/$ACCOUNT_ID/g" $TMP_DIR/lambda_function.py
sed -i "s/<<ACCOUNT_REGION>>/$ACCOUNT_REGION/g" $TMP_DIR/lambda_function.py

# zip files
cd $TMP_DIR
zip -ur ../$Template_DIR/function.zip lambda_function.py
cd ..

cp $YAML_FILE $Template_DIR

sed -i "s/<<TIMESTAMP>>/$datetime/g" $Template_DIR/$YAML_FILE
sed -i "s/<<STAGE>>/$STAGE/g" $Template_DIR/$YAML_FILE
sed -i "s/<<STAGE_BUCKET>>/$STAGE_BUCKET/g" $Template_DIR/$YAML_FILE
sed -i "s/<<ACCOUNT_ID>>/$ACCOUNT_ID/g" $Template_DIR/$YAML_FILE
sed -i "s/<<ACCOUNT_USER>>/$ACCOUNT_USER/g" $Template_DIR/$YAML_FILE

# deploy
sam validate --template-file $Template_DIR/$YAML_FILE
aws cloudformation package --template-file $Template_DIR/$YAML_FILE --output-template-file $TMP_DIR/$YAML_FILE --s3-bucket $BUCKET_FUNCTION
aws cloudformation deploy --template-file $TMP_DIR/$YAML_FILE --stack-name ChargeStartFunction$STAGE --parameter-overrides Stage=$STAGE Bucket=$BUCKET_FUNCTION
fi

if $CLEAN_UP
then
    rm -rf $TMP_DIR
    rm -rf $Template_DIR
fi
