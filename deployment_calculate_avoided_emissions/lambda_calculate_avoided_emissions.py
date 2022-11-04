import boto3
import datetime
import io
import json
import os
import pandas as pd

FILE_NAME_CHARGING_DATA = "charging_data.csv"
FILE_NAME_AVOIDED_EMISSIONS = "avoided_emissions.csv"
SECRET_REGION = 'eu-north-1'
BUCKET='BucketSourceData'
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

    response = s3_client.get_object(Bucket=bucket, Key=filename)
    df = pd.read_csv(response.get("Body"), sep=separator)

    return df


def lambda_handler(event, context):

    print("event", event)

    try:
        body = json.loads(event['body'])
    except KeyError:
        body = event

    try:
        if type(body) == list:
            body = body[0]
        body['device_name']
        device_name = body['device_name']
    except KeyError:
        return {
            'statusCode': 400,
            'message': 'Invalid payload'
        }

    filename_charge_data = device_name + "_" + FILE_NAME_CHARGING_DATA
    df_charge_data = read_csv_from_s3(S3_BUCKET, filename_charge_data)
    df_charge_data = df_charge_data.reindex(index=df_charge_data.index[::-1])
    df_charge_data.reset_index(inplace=True)
    df_charge_data['datetime'] = pd.to_datetime(df_charge_data['timestamp'], unit='s')
    # calculate time spent per row
    # last row = finish -> time spent = 0
    df_charge_data['time_spent_seconds'] = (df_charge_data['datetime'].shift(-1) - df_charge_data['datetime'])
    df_charge_data['time_spent_seconds'] = df_charge_data['time_spent_seconds'].apply(lambda x: x.total_seconds())
    df_charge_data['time_spent_seconds'].iat[-1] = 0

    # unit of power = watt = J / s
    # unit of intensity = gCO2/kWh
    # 1 kWh = 1000 * 60 * 60 J
    # carbon equivalent = power * intensity * time
    # carbon equivalent (g) = power (kWh/s) * intensity (gCO2/kWh) * time (s)
    #                       = 1/(1000 ^ 2 * 60 * 60) * power (J/s) * intensity (lbs/MWh) * time (s)
    df_charge_data['carbon_equivalent'] = (df_charge_data['power'] *  df_charge_data['intensity'] *  df_charge_data['time_spent_seconds']) / (1000 * 60 * 60)
    
    df_charge_data['time_since_start_seconds'] = df_charge_data['time_spent_seconds'].cumsum()

    # calculate alternate charging data: if there were no pauses
    df_charge_data['switch_status'].iat[-1] = False
    df_charge_data_alt = df_charge_data[df_charge_data['switch_status']][['power', 'time_spent_seconds']]
    df_charge_data_alt['time_since_start_seconds'] = df_charge_data_alt['time_spent_seconds'].cumsum()
    df_charge_data_alt = df_charge_data_alt.drop(columns=['time_spent_seconds'])
    total_time_alt = df_charge_data_alt['time_since_start_seconds'].max()
    print(f"total time spent charging: {total_time_alt} seconds")
    df_charge_data_alt = df_charge_data_alt.merge(df_charge_data[['time_since_start_seconds', 'intensity']], left_on='time_since_start_seconds', right_on='time_since_start_seconds', how='outer')
    df_charge_data_alt = df_charge_data_alt.sort_values(by=['time_since_start_seconds'], ignore_index=True)
    df_charge_data_alt.fillna(method='ffill', inplace=True)
    df_charge_data_alt = df_charge_data_alt[df_charge_data_alt['time_since_start_seconds'] <= total_time_alt]
    df_charge_data_alt['time_spent_seconds'] = (df_charge_data_alt['time_since_start_seconds'].shift(-1) - df_charge_data_alt['time_since_start_seconds'])
    df_charge_data_alt['time_spent_seconds'].iat[-1] = 0
    df_charge_data_alt['carbon_equivalent'] = (df_charge_data_alt['power'] *  df_charge_data_alt['intensity'] *  df_charge_data_alt['time_spent_seconds']) / (1000 * 60 * 60)

    # calculate totals
    total_emissions_actual = df_charge_data['carbon_equivalent'].sum()
    total_emissions_alt = df_charge_data_alt['carbon_equivalent'].sum()
    percentage_saved = 100 * (total_emissions_alt - total_emissions_actual) / total_emissions_alt
    
    print("total_emissions_actual: ", total_emissions_actual)
    print("total_emissions_alt: ", total_emissions_alt)
    
    data = {
        'total_emissions_actual': total_emissions_actual,
        'total_emissions_alt': total_emissions_alt,
        'percentage_saved': percentage_saved
    }

    print("data: ", data)

    return data
