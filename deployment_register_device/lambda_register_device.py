import boto3
import datetime
import io
import json
import os
import pandas as pd
import requests

from requests.auth import HTTPBasicAuth

FILE_NAME_REGISTRATION_DATA = "device_data.csv"
BUCKET='BucketData'
S3_BUCKET = os.environ.get(BUCKET)
print("S3_BUCKET:", S3_BUCKET)


def write_csv_to_s3(bucket, filename, df, separator=';', mode='w'):

    print(f"bucket: {bucket}, filename: {filename}")
    s3_client = boto3.client("s3")

    with io.StringIO() as csv_buffer:
        df.to_csv(csv_buffer, index=False, sep=separator, mode=mode)

        response = s3_client.put_object(
            Bucket=bucket, Key=filename, Body=csv_buffer.getvalue()
        )

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 put_object response. Status - {status}")
    else:
        print(f"Unsuccessful S3 put_object response. Status - {status}")
        raise Exception(f"Unsuccessful S3 put_object response. Status - {status}")


def read_csv_from_s3(bucket, filename, separator=';'):

    s3_client = boto3.client("s3")

    try:
        response = s3_client.get_object(Bucket=bucket, Key=filename)
        df = pd.read_csv(response.get("Body"), sep=separator)
    except Exception:
        df = pd.DataFrame()
        
    return df

    
def lambda_handler(event, context):
  
    print("event", event)

    try:
        body = json.loads(event['body'])
    except KeyError:
        body = event

    df_devices = read_csv_from_s3(S3_BUCKET,
        FILE_NAME_REGISTRATION_DATA,
        separator=';')

    calibration_data_list = []
    try:
        if type(body) == list:
            body = body[0]
        body['device_name'] and \
        body['region_type_selection'] and \
        body['region_azure'] and \
        body['region_ba'] and \
        body['smart_plug_id'] and \
        body['smart_plug_auth_key'] and \
        body['smart_plug_url'] and \
        body['charge_mode']
        device_name = body['device_name']
        region_type_selection = body['region_type_selection']
        region_azure = body['region_azure']
        region_ba = body['region_ba']
        smart_plug_id = body['smart_plug_id']
        smart_plug_auth_key = body['smart_plug_auth_key']
        smart_plug_url = body['smart_plug_url']
        charge_mode = body['charge_mode']
        print("device_name: ", device_name)
        print("region_type_selection: ", region_type_selection)
        print("region_azure: ", region_azure)
        print("region_ba: ", region_ba)
        print("smart_plug_id: ", smart_plug_id)
        print("smart_plug_auth_key: ", smart_plug_url)
        print("charge_mode: ", charge_mode)
        
        df_devices_row = pd.DataFrame(
            [[
               device_name,
               region_type_selection,
               region_azure,
               region_ba,
               smart_plug_id,
               smart_plug_auth_key,
               smart_plug_url,
               charge_mode
            ]],
            columns=[
               "device_name",
               "region_type_selection",
               "region_azure",
               "region",
               "smart_plug_id",
               "smart_plug_auth_key",
               "smart_plug_url",
               "charge_mode"
            ]
        )
        
        frames = [df_devices, df_devices_row]
        df_devices = pd.concat(frames)

        write_csv_to_s3(S3_BUCKET,
            FILE_NAME_REGISTRATION_DATA,
            df_devices)

    except KeyError:
        message = "parameters: device_name, region_ba, smart_plug_id, smart_plug_auth_key, smart_plug_url and charge_mode should be passed."
        print(message)
        return {
          'status' : 400,
          'message' : message
        }
        
    return {
      'status' : 200
    }
