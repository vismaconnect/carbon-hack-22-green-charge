import boto3
import datetime
import json

def lambda_handler(event, context):
  
    print("event", event)

    try:
        body = json.loads(event['body'])
    except KeyError:
        body = event

    calibration_data_list = []
    try:
        if type(body) == list:
            body = body[0]
        body['device_name'] and \
        body['time_window']
        device_name = body['device_name']
        time_window = body['time_window']
        print("device_name: ", device_name)
        print("time_window: ", time_window)
    except KeyError:
        print("parameters: device_name and time_window should be passed.")
        # Intepret this as the start of the run, switch charging on
  
    now = datetime.datetime.now()
    
    json_string = json.dumps(body)
    print("json_string: ", json_string)
    client = boto3.client('stepfunctions')
    response = client.start_execution(
        stateMachineArn='arn:aws:states:<<ACCOUNT_REGION>>:<<ACCOUNT_ID>>:stateMachine:ChargeDevice',
        name='calibrate-start-' + now.strftime("%d%m%Y%H%M%S"),
        input=json_string
    )
    response_message = json.loads(json.dumps(response, default=str))
    print(response_message)

    return {
      'status' : 200,
      'message' : response_message
    }
