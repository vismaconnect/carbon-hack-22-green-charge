import boto3
import json
import os

FILE_NAME_CHARGING_DATA = "_charging_progress_data.json"
BUCKET='BucketData'
S3_BUCKET = os.environ.get(BUCKET)
print("S3_BUCKET:", S3_BUCKET)

def lambda_handler(event, context):

    finished = False

    print("event", event)

    try:
        body = json.loads(event['body'])
    except KeyError:
        body = event

    try:
        if type(body) == list:
            body = body[0]
        body['device_name']
    except KeyError:
        print("Mandatory payload elenent device_name not found. Please provide the payload element.")
        raise

    device_name = body['device_name']

    s3 = boto3.resource('s3')

    filename = device_name + FILE_NAME_CHARGING_DATA
    content_object = s3.Object(S3_BUCKET, filename)
    file_content = content_object.get()['Body'].read().decode('utf-8')
    json_content = json.loads(file_content)
    print(json_content)    

    return {
        'device_name' : device_name,
        'duration' : json_content['duration'],
        'intensity_current' : json_content['intensity_current'],
        'intensity_overall' : json_content['intensity_overall'],
        'intensity_charging' : json_content['intensity_charging'],
        'percentage_saved' : json_content['percentage_saved'],
        'current_power' : json_content['current_power']
    }
