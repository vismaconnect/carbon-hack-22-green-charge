import boto3
import datetime
import io
import json
import os
import pandas as pd
import ruptures as rpt

FILE_NAME = "segmentation_data.csv"
FILE_NAME_REGISTRATION_DATA = "device_data.csv"
SECRET_REGION = 'eu-north-1'
BUCKET='BucketData'
S3_BUCKET = os.environ.get(BUCKET)
NR_BREAKPOINTS = 1
LAG_DERIVATIVE = 8
MARGIN = 0.02
MODEL = "rbf"
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


def find_derivative_signal(signal):
    
    diff = round(LAG_DERIVATIVE /100 * len(signal))
    diff = max(3, diff)

    signal_derivative = signal.diff(periods=diff)
    signal_derivative = signal_derivative[diff:]
    
    return signal_derivative, diff


def find_power_thresholds(signal_derivative, signal, diff):
    
    algo = rpt.Binseg(model=MODEL).fit(signal_derivative)
    result = algo.predict(n_bkps=NR_BREAKPOINTS)

    result_adjusted = result[0] + diff
    
    region1_values = signal.iloc[:result_adjusted]
    region2_values = signal.iloc[result_adjusted:]
    
    if region1_values['power'].mean() < region2_values['power'].mean():
        raise ValueError

    if region1_values['power'].min() <= region2_values['power'].max():
        power_threshold = region1_values['power'].min()
        print('min < max')
    else:
        power_threshold = region2_values['power'].max()
        print('min >= max')

    print(power_threshold)
    power_threshold = power_threshold * (1 - MARGIN)

    return power_threshold, result_adjusted


def lambda_handler(event, context):

    # print("event", event)

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
        print("Mandatory  element 'device_name' not found.")
        raise
    
    try:
        if type(body) == list:
            body = body[0]
        calibration_data_list = body['charging_data_list']
    except KeyError:
        print("No calibration_data_list given")
        raise
    # print("calibration_data_list: ", calibration_data_list)    

    calibration_data_list = calibration_data_list[::-1]
    # print("calibration_data_list: ", calibration_data_list)

    df_segment_data = pd.DataFrame(calibration_data_list)
    # remove any zero entries from the start when charging has not yet started
    index_start = df_segment_data.ne(0).idxmax()['power']
    print(index_start)
    df_segment_data = df_segment_data.iloc[index_start:]
    print(df_segment_data.head(5))

    df_segment_data_sorted = df_segment_data.sort_values(by=['power'])
    df_segment_data_sorted_non_zero = df_segment_data_sorted[df_segment_data_sorted['power'] > 0]
    power_lowest = df_segment_data_sorted_non_zero.power.min()
    print("power_lowest: ", power_lowest)

    df_segment_data['minutes_charging'] = df_segment_data.index
    df_segment_data['datetime'] = pd.to_datetime(df_segment_data['timestamp'], unit='s')
    # calculate time spent per row
    # last row = finish -> time spent = 0
    df_segment_data['time_spent_seconds'] = (df_segment_data['datetime'].shift(-1) - df_segment_data['datetime'])
    df_segment_data['time_spent_seconds'] = df_segment_data['time_spent_seconds'].apply(lambda x: x.total_seconds())
    df_segment_data['time_spent_seconds'].iat[-1] = 0
    # calculate energy charged per time interval
    df_segment_data['energy'] = df_segment_data['time_spent_seconds'] * df_segment_data['power']
    # calculate percentage charged at begin of interval
    total_energy = df_segment_data['energy'].sum()
    df_segment_data['estimated_percentage_charged'] =  (df_segment_data['energy'].shift(1) / total_energy) * 100
    df_segment_data['estimated_percentage_charged'].iat[0] = 0
    df_segment_data['estimated_percentage_charged'] = df_segment_data['estimated_percentage_charged'].cumsum()

    datetime = df_segment_data['datetime']
    power_values = df_segment_data[['power']]
    
    signal = power_values
    signal_derivative, diff = find_derivative_signal(signal)

    power_thresholds, index_breakpoint = find_power_thresholds(signal_derivative, signal, diff)
    time_segment1 = (datetime.iloc[index_breakpoint - 1] - datetime.iloc[0]).total_seconds() / 60.0
    time_segment2 = (datetime.iloc[-1] - datetime.iloc[index_breakpoint]).total_seconds() / 60.0
    percentage_charged_at_breakpoint = df_segment_data['estimated_percentage_charged'].iloc[index_breakpoint - 1]

    data = {
        'duration_minutes': [time_segment1, time_segment2],
        'power_lower_bound': [power_thresholds, power_lowest],
        'estimed_percentage_charged': [percentage_charged_at_breakpoint, 100],
    }
    df_segments = pd.DataFrame(data=data)

    file_name = device_name + "_" + FILE_NAME
    write_csv_to_s3(S3_BUCKET, file_name,  df_segments)

    return {
        'statusCode': 200,
        'message' : data
    }
