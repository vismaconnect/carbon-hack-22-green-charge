import ast
import boto3
import io
import json
import os
import pandas as pd
import requests
import time

from datetime import datetime, timedelta, timezone
from requests.auth import HTTPBasicAuth

FILE_NAME_REGISTRATION_DATA = "device_data.csv"
FILE_NAME_PROGRESS_CHARGING_DATA = "charging_progress_data.json"
FILE_NAME_CHARGING_DATA = "charging_data.csv"
FILE_NAME_SEGMENTATION_DATA = "segmentation_data.csv"
SECRET_NAME_WATTIME = 'WATT_TIME'
SECRET_NAME_CARBON_AWARE = 'CarbonAwareAPI'
SECRET_REGION = 'eu-north-1'
BUCKET='BucketData'
S3_BUCKET = os.environ.get(BUCKET)
print("S3_BUCKET:", S3_BUCKET)
# conversion factor from lbsCO2/MWh to gCO2/kWh
CONVERSION_FACTOR_INTENSITY = 453.592 / 1000 


def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )

    return get_secret_value_response['SecretString']


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
        raise Exception(
            f"Unsuccessful S3 put_object response. Status - {status}")


def read_csv_from_s3(bucket, filename, separator=';'):

    s3_client = boto3.client("s3")

    response = s3_client.get_object(Bucket=bucket, Key=filename)
    df = pd.read_csv(response.get("Body"), sep=separator)

    return df


def write_json_to_s3(bucket, filename, dict_data):

    print(f"bucket: {bucket}, filename: {filename}")
    s3_client = boto3.client("s3")

    response = s3_client.put_object(
        Bucket=bucket, Key=filename, Body=(bytes(
            json.dumps(dict_data).encode('UTF-8')))
    )

    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")

    if status == 200:
        print(f"Successful S3 put_object response. Status - {status}")
    else:
        print(f"Unsuccessful S3 put_object response. Status - {status}")
        raise Exception(
            f"Unsuccessful S3 put_object response. Status - {status}")

 
def _get_power_data(device_name):
    
    print("device_name: ", device_name)
    
    df_devices = read_csv_from_s3(S3_BUCKET,
        FILE_NAME_REGISTRATION_DATA,
        separator=';')

    smart_plug_id = df_devices.loc[df_devices['device_name'] ==  device_name, 'smart_plug_id'].item()
    print("smart_plug_id: ", smart_plug_id)
    smart_plug_auth_key = df_devices.loc[df_devices['device_name'] == device_name, 'smart_plug_auth_key'].item()
    smart_plug_url = df_devices.loc[df_devices['device_name'] == device_name, 'smart_plug_url'].item()

    url = f"{smart_plug_url}/device/status"
    
    headers_string = {'ContentType': "application/x-www-form-urlencoded"}

    data_dictionary = {}
    data_dictionary['id'] = smart_plug_id
    data_dictionary['auth_key'] = smart_plug_auth_key
    response = requests.post(url, headers=headers_string, data=data_dictionary)
    json_response = response.json()
    print("json_response: ", json_response)

    power = float(json_response['data']['device_status']['meters'][0]['power'])
    timestamp = json_response['data']['device_status']['meters'][0]['timestamp']
    switch_status = json_response['data']['device_status']['relays'][0]['ison']

    print("timestamp: {}, power: {}".format(timestamp, power))
    return (power, timestamp, switch_status)

def get_smart_device_data(device_name):
    
    df_devices = read_csv_from_s3(S3_BUCKET,
        FILE_NAME_REGISTRATION_DATA,
        separator=';')

    smart_plug_id = df_devices.loc[df_devices['device_name'] ==
        device_name, 'smart_plug_id'].item()
    print("smart_plug_id: ", smart_plug_id)
    smart_plug_auth_key = df_devices.loc[df_devices['device_name'] == 
        device_name, 'smart_plug_auth_key'].item()
    smart_plug_url = df_devices.loc[df_devices['device_name'] == 
        device_name, 'smart_plug_url'].item()

    return (smart_plug_id, smart_plug_auth_key, smart_plug_url)

def get_device_region(device_name):
    
    df_devices = read_csv_from_s3(S3_BUCKET,
        FILE_NAME_REGISTRATION_DATA,
        separator=';')

    region_type = df_devices.loc[df_devices['device_name'] ==
        device_name, 'region_type_selection'].item()
    
    if region_type=='other_regions':
        region = df_devices.loc[df_devices['device_name'] ==
            device_name, 'region'].item()
    if region_type=='azure_regions':
        region = df_devices.loc[df_devices['device_name'] ==
            device_name, 'region_azure'].item()
    return region_type, region


def _toggle_charging(device_name, switch_value):
    
    smart_plug_id, smart_plug_auth_key, smart_plug_url = get_smart_device_data(device_name)

    url = f"{smart_plug_url}/device/relay/control"
    
    headers_string = {'ContentType': "application/x-www-form-urlencoded"}

    data_dictionary = {}
    data_dictionary['turn'] = switch_value
    data_dictionary['channel'] = 0
    data_dictionary['id'] = smart_plug_id
    data_dictionary['auth_key'] = smart_plug_auth_key
    response = requests.post(url, headers=headers_string, data=data_dictionary)
    json_response = response.json()
    print("json_response", json_response)

    isok = json_response['isok']

    if not isok:
        print("ERROR: Problems toggling switch state of device")


def _get_intensity_data(device_name):
    
    region_type, region = get_device_region(device_name)
    print("region_type: {}".format(region_type))
    print("region: {}".format(region))

    if region_type=='other_regions':
        secret_output = get_secret(SECRET_NAME_WATTIME, SECRET_REGION)
        if type(secret_output) == str:
            secret_output = ast.literal_eval(secret_output)
        USER_NAME = secret_output['WATT_TIME_USER_NAME']
        PASSWORD = secret_output['WATT_TIME_PASSWORD']
        BASE_URL = secret_output['WATT_TIME_BASE_URL']
        login_url = f"{BASE_URL}/login"

        token = requests.get(login_url,
            auth=HTTPBasicAuth(USER_NAME, PASSWORD)).json()['token']

        data_url = f"{BASE_URL}/index"
        headers = {'Authorization': 'Bearer {}'.format(token)}
        params = {'ba': region}
        response = requests.get(data_url, headers=headers, params=params)
        print("json_response: ", response.text)

        json_response = response.json()

        timestamp = json_response['point_time']
        intensity = int(json_response['moer'])
        # convert intensity from lbsCO2/MWh to gCO2/kWh
        intensity = CONVERSION_FACTOR_INTENSITY * intensity


    if region_type=='azure_regions':
        secret_output = get_secret(SECRET_NAME_CARBON_AWARE, SECRET_REGION)
        if type(secret_output) == str:
            secret_output = ast.literal_eval(secret_output)
        BASE_URL = secret_output['BASE_URL']
        data_url = f"{BASE_URL}/emissions/forecasts/current"
        params = {'location': region}
        response = requests.get(data_url, params=params)
        print("json_response: ", response.text)
        json_response = response.json()
        forecastData = json_response[0]['forecastData']
        df_forecastData = pd.DataFrame(forecastData)
        intensity = int(df_forecastData['value'].iloc[0])
        timestamp = df_forecastData['timestamp'].iloc[0]

    print("timestamp: {}, intensity: {}".format(
            timestamp, intensity))
    
    return intensity
    

def _determine_intensity_threshold(device_name, intensity,
        time_window, device_load_time):
    region_type, region = get_device_region(device_name)
    
    time_window_int=int(time_window)
    print("device_load_time: ", device_load_time)
    
    if region_type=='other_regions':

        if time_window==0:
            return (intensity, 0)

        #print("percentile_threshold: ", percentile_threshold)
        print("current intensity: ", intensity)
        
        secret_output = get_secret(SECRET_NAME_WATTIME, SECRET_REGION)
        if type(secret_output) == str:
            secret_output = ast.literal_eval(secret_output)
        USER_NAME = secret_output['WATT_TIME_USER_NAME']
        PASSWORD = secret_output['WATT_TIME_PASSWORD']
        BASE_URL = secret_output['WATT_TIME_BASE_URL']
        login_url = f"{BASE_URL}/login"

        token = requests.get(login_url,
            auth=HTTPBasicAuth(USER_NAME, PASSWORD)).json()['token']

        data_url = f"{BASE_URL}/forecast"
        headers = {'Authorization': 'Bearer {}'.format(token)}
        params = {'ba': region}
        response = requests.get(data_url, headers=headers, params=params)
        print("json_response: ", response.text)

        # example "2022-10-26T06:10:00+00:00"
        format = "%Y-%m-%dT%H:%M:%S+00:00"
        forecast_start = datetime.strptime(response.json()['generated_at'], format)
        forecast_list = response.json()['forecast']
        df_forecast_data = pd.DataFrame(forecast_list)
        df_forecast_data['datetime'] = pd.to_datetime(
            df_forecast_data['point_time'], format=format)
        granularity = round((df_forecast_data['datetime'].iloc[1] -
            df_forecast_data['datetime'].iloc[0]).total_seconds()/60) #forecast is updated every x minutes
        print("granularity: ", granularity)
        charging_periods = int(round(device_load_time/granularity,0))
        print("charging_periods: ", charging_periods)
        # convert intensity from lbsCO2/MWh to gCO2/kWh
        df_forecast_data['value'] = CONVERSION_FACTOR_INTENSITY * df_forecast_data['value']

    if region_type=='azure_regions':
        if time_window==0:
            return (intensity, 0)
        
        #print("percentile_threshold: ", percentile_threshold)
        print("current intensity: ", intensity)
        
        secret_output = get_secret(SECRET_NAME_CARBON_AWARE, SECRET_REGION)
        if type(secret_output) == str:
            secret_output = ast.literal_eval(secret_output)
        BASE_URL = secret_output['BASE_URL']
        data_url = f"{BASE_URL}/emissions/forecasts/current"
        params = {'location': region}
        response = requests.get(data_url, params=params)
        print("json_response: ", response.text)
        json_response = response.json()
        
        granularity = json_response[0]['windowSize'] #forecast is updated every x minutes
        print("granularity: ", granularity)
        charging_periods = int(round(device_load_time/granularity,0))
        print("charging_periods: ", charging_periods)
        
        forecastData = json_response[0]['forecastData']
        df_forecast_data = pd.DataFrame(forecastData)
        forecast_start = df_forecast_data['timestamp'].iloc[0]
        
        # example "2022-10-26T06:10:00+00:00"
        format = "%Y-%m-%dT%H:%M:%S+00:00"
        df_forecast_data['datetime'] = pd.to_datetime(
            df_forecast_data['timestamp'], format=format)
        forecast_start = df_forecast_data['datetime'].iloc[0]

    finish_by_date = forecast_start + timedelta(hours=time_window_int)
    print("finish_by_date: ", finish_by_date)

    #percentile_ratio_threshold = percentile_threshold/100
    #print("percentile_ratio_threshold: ", percentile_ratio_threshold)

    print("df_forecast_data.shape: ", df_forecast_data.shape)
    df_charging_window = df_forecast_data[
            (df_forecast_data['datetime'] < finish_by_date)
    ]
    print("df_charging_window.shape: ", df_charging_window.shape)

    df_charging_periods_sorted = df_charging_window.sort_values(
                by=['value'], ascending=True)
    df_charging_periods_sorted = df_charging_periods_sorted.head(charging_periods)

    max_value = df_charging_periods_sorted.value.max()
    print("df_charging_periods_sorted.shape: ", df_charging_window.shape)
    print("df_charging_periods_sorted.value.min(): ", df_charging_window.value.min())
    print("df_charging_periods_sorted.value.max(): ", max_value)
    
    intensity_threshold = max_value
    print("intensity_threshold: ", intensity_threshold)
    
    return intensity_threshold


def _persist_charging_statistics(device_name, charging_data_list):

    df_charging_data = pd.DataFrame(charging_data_list)
    duration = str(round((df_charging_data.timestamp.max() - 
        df_charging_data.timestamp.min())/60,0))
    intensity_current = df_charging_data.intensity.head(1).sum()
    intensity_overall = df_charging_data.intensity.mean()
    df_charging_data_on = \
        df_charging_data[df_charging_data['switch_status'] == True]
    intensity_charging = df_charging_data_on.intensity.mean()
    if intensity_overall > 0:
        percentage_saved =  str(round((1-(
            intensity_charging/intensity_overall))*100,0))
    else:
        percentage_saved = 0
    current_power = str(round(charging_data_list[0]['power'],1))

    print("duration: ", duration, " minutes")
    print("percentage_saved: ", percentage_saved, " %")
    print("current_power: ", current_power, " Watt")
    
    progress_data_dict = {}
    progress_data_dict['duration'] = str(duration)
    progress_data_dict['intensity_current'] = str(intensity_current)
    progress_data_dict['intensity_overall'] = str(intensity_overall)
    progress_data_dict['intensity_charging'] = str(intensity_charging)
    progress_data_dict['percentage_saved'] = str(percentage_saved)
    progress_data_dict['current_power'] = str(current_power)
    
    filename = device_name + "_" + FILE_NAME_PROGRESS_CHARGING_DATA
    write_json_to_s3(S3_BUCKET, filename, progress_data_dict)
    

def lambda_handler(event, context):

    finished = False

    print("event", event)

    try:
        body = json.loads(event['body'])
    except KeyError:
        body = event

    payload= ''
    try:
        if type(body) == list:
            body = body[0]
        body['Payload']
        payload = body['Payload']
        payload['device_name']
    except KeyError:
        print("Mandatory payload elenent 'device_name' not found. Please provide Payload element.")
        raise

    device_name = payload['device_name']

    try:
        time_window = payload['time_window']
        print("time_window: ", time_window)
    except KeyError:
        print("time_window not passed, use default")
        time_window = 0

    try:
        calibrate = payload['calibrate']
        print("callibrate: ", time_window)
    except KeyError:
        print("callibrate not passed, use default False")
        calibrate = False

    try:
        intensity_threshold = payload['intensity_threshold']
    except KeyError:
        print("intensity_threshold not passed, use default")
        intensity_threshold = 9998

    charging_data_list=[]
    try:
        if type(body) == list:
            body = body[0]
        charging_data_list = payload['charging_data_list']
    except KeyError:
        print("No charging_data_list given, use default")
    print("charging_data_list: ", charging_data_list)

    file_name_segmentation_data = device_name + "_" + FILE_NAME_SEGMENTATION_DATA
    
    if time_window!=0:
        df_segmentation = read_csv_from_s3(S3_BUCKET, file_name_segmentation_data)
        charge_time_partial_minutes = int(df_segmentation.duration_minutes.iloc[0])
        power_threshold = df_segmentation.power_lower_bound.iloc[0]
        POWER_FULL_LEVEL = df_segmentation.power_lower_bound.iloc[-1]
    else:
        charge_time_partial_minutes=-1
        power_threshold=0
        POWER_FULL_LEVEL=1.0

    power, timestamp, switch_status = _get_power_data(device_name)
    dt = datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    utc_timestamp = utc_time.timestamp()
    print(f"timestamp_device: {timestamp}")
    print(f"timestamp_python: {utc_timestamp}")

    current_intensity = _get_intensity_data(device_name)

    charging_data={}
    charging_data['power'] = power
    charging_data['timestamp'] = utc_timestamp
    charging_data['intensity'] = current_intensity
    charging_data['switch_status'] = switch_status

    # Only do this the first time:
    if len(charging_data_list) == 0 and not calibrate:
        print("First time and not calibrate")
        intensity_threshold = _determine_intensity_threshold(
            device_name, current_intensity, time_window, charge_time_partial_minutes)
    elif len(charging_data_list) == 0 and calibrate:
        print("First time and calibrate")
        intensity_threshold = 9999

    print("Values:")
    print("- intensity_threshold", intensity_threshold)
    print("- POWER_FULL_LEVEL: ", POWER_FULL_LEVEL)
    print("- power: ", power, ", switch_status: ", switch_status,
            ", current_intensity: ", current_intensity)

    df_charging_data = pd.DataFrame(charging_data_list)
    try:
        duration_minutes = str(round((df_charging_data['timestamp'].max() - 
            df_charging_data.timestamp.min())/60,0))
    except:
        duration_minutes = 0
    print(f"duration_minutes: {duration_minutes}")

    if (int(float(duration_minutes)) - charge_time_partial_minutes >= int(float(time_window))) and\
        (power > power_threshold):
        # do not stop charging, time left is too small to get sufficient charge otherwise
        # or this is a calibration run
        if not switch_status:
            # switch on
            print("switch on because of insufficient time remaining")
            _toggle_charging(device_name, "on")
            switch_status = True
    elif switch_status and float(current_intensity) > float(intensity_threshold):
        # switch off
        print("switch off because of high intensity")
        _toggle_charging(device_name, "off")
        switch_status = False
    elif switch_status and power <= POWER_FULL_LEVEL:
        # switch off
        print("switch off because battery is full")
        _toggle_charging(device_name, "off")
        switch_status = False
        finished = True
    elif not switch_status and float(current_intensity) <= float(intensity_threshold):
        # switch on
        print("switch on because of low enough intensity")
        _toggle_charging(device_name, "on")
        switch_status = True
    else:
        print("ELSE: power: ", power, ", switch_status: ",
            switch_status, ", current_intensity: ", current_intensity)

    charging_data['finished'] = finished

    #Prepend for easier access from step function
    charging_data_list.insert(0, charging_data)
    print("charging_data_list: ", charging_data_list)

    _persist_charging_statistics(device_name, charging_data_list)

    if finished:
        df_charging_data = pd.DataFrame(charging_data_list)
        print("END RESULT:", df_charging_data.shape)
        file_name = device_name + "_" + FILE_NAME_CHARGING_DATA
        write_csv_to_s3(S3_BUCKET, file_name, df_charging_data)

    #time_window = time_window.strftime("%Y-%m-%d %H:%M:%S")

    return {
        'device_name' : payload['device_name'],
        'time_window' : time_window,
        'calibrate' : calibrate,
        'intensity_threshold' : intensity_threshold,
        'charging_data_list': charging_data_list
    }
