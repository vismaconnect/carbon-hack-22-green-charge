import json
import os
import requests

from datetime import datetime
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session.__init__ import Session

SESSION_TYPE = 'memcache'

app = Flask(__name__)
sess = Session()

@app.route('/', methods=['GET'])
def base():
    return render_template ("index.html")

@app.route('/start_charge_input', methods=['GET', 'POST'])
def start_charge_input():
    error = ""

    if request.method == 'POST':
        device_name = request.form['device_name']
        time_window = request.form['time_window']

        if len(device_name) == 0:
            error = "Please supply device_name"
        else:
            return redirect(url_for('start_charge',
                device_name=device_name,
                time_window=time_window))

    return render_template('start_charge_input.html',
        form=request.form,
        time_window_list_tag=list(range(0, 25)),
        message=error)

@app.route('/start_calibration_input', methods=['GET', 'POST'])
def start_calibration_input():
    error = ""

    if request.method == 'POST':
        device_name = request.form['device_name']

        if len(device_name) == 0:
            error = "Please supply device_name"
        else:
            return redirect(url_for('start_calibration',
                device_name=device_name))

    return render_template('start_calibration_input.html',
        form=request.form, message=error)

@app.route('/start_register_device_input', methods=['GET', 'POST'])
def start_register_device_input():
    error = ""

    if request.method == 'POST':
        device_name = request.form['device_name']
        # Hide these values from getting into the URL
        session['region_type_selection'] = request.form['region_type_selection']
        session['region_azure'] = request.form['region_azure_select']
        session['region_ba'] = request.form['region_ba_select']
        session['smart_plug_id'] = request.form['smart_plug_id']
        session['smart_plug_auth_key'] = request.form['smart_plug_auth_key']
        session['charge_mode']  = request.form['charge_mode']
        session['smart_plug_url']  = request.form['smart_plug_url']

        if len(device_name) == 0 or \
            len(request.form['region_type_selection']) == 0 or \
            len(request.form['region_azure_select']) == 0 or \
            len(request.form['region_ba_select']) == 0 or \
            len(request.form['smart_plug_id']) == 0 or \
            len(request.form['smart_plug_auth_key']) == 0 or \
            len(request.form['charge_mode']) == 0 or \
            len(request.form['smart_plug_url']) == 0:
            error = "Please supply values for device_name, region_type_selection, azure_region, region, smart plug id, smart_plug_auth_key, smart_plug_url and charge_mode"
        else:
            return redirect(url_for('perform_registration',
                device_name=device_name))

    regions_file = open('./regions.json')
    regions_json = json.load(regions_file)
    regions_file.close()

    azure_regions_file = open('./azure-regions.json')
    azure_regions_json = json.load(azure_regions_file)
    azure_regions_file.close()

    return render_template('start_register_device_input.html',
        form=request.form,
        azure_regions_tag=azure_regions_json,
        regions_tag=regions_json,
        message=error)

@app.route('/avoided_emissions_input', methods=['GET', 'POST'])
def avoided_emissions_input():
    error = ""

    if request.method == 'POST':
        device_name = request.form['device_name']

        if len(device_name) == 0:
            error = "Please supply device_name."
        else:
            return redirect(url_for('avoided_emissions',
                device_name=device_name))

    return render_template('avoided_emissions_input.html',
        form=request.form, message=error)

@app.route('/charge/<string:device_name>/<string:time_window>/', methods=['GET'])
def start_charge(device_name, time_window):
    status, startDate, obs_1 = _start_charging(
        device_name, time_window)
    # Ignore obs_1

    return render_template ("start_charge.html",
        device_name_tag=device_name,
        status_tag=status,
        time_window_tag=time_window,
        startDate_tag=startDate
    )

@app.route('/calibrate/<string:device_name>', methods=['GET'])
def start_calibration(device_name):
    status, startDate, requestId, message = _start_calibration(device_name)

    title='Start calibration'
    
    return render_template ("start_calibration.html",
        message=message,
        title_tag=title,
        device_name_tag=device_name,
        status_tag=status,
        startDate_tag=startDate,
        requestId_tag=requestId
    )

@app.route('/perform_registration/<string:device_name>', methods=['GET'])
def perform_registration(device_name):
    status = _perform_registration(
        device_name,
        session['region_type_selection'],
        session['region_azure'],
        session['region_ba'],
        session['smart_plug_id'],
        session['smart_plug_auth_key'],
        session['smart_plug_url'],
        session['charge_mode']
    )

    if status == 200:
        message='Device registration successful'
        session.pop('region_type_selection', None)
        session.pop('region_azure', None)
        session.pop('region_ba', None)
        session.pop('smart_plug_id', None)
        session.pop('smart_plug_auth_key', None)
        session.pop('smart_plug_url', None)
        session.pop('charge_mode', None)
    else:
        message='Returned status: ' + str(status)
    
    return render_template ("index.html",
        message=message,
    )

@app.route('/progress/<string:device_name>', methods=['GET'])
def progress(device_name):
    duration, intensity_current, intensity_overall, \
         intensity_charging ,percentage_saved, current_power, message = \
         _get_current_data(device_name)

    return render_template ("progress.html",
        message=message,
        device_name_tag=device_name,
        duration_tag=duration,
        intensity_current_tag=intensity_current,
        intensity_overall_tag=intensity_overall,
        intensity_charging_tag=intensity_charging,
        percentage_saved_tag=percentage_saved,
        current_power_tag=current_power,
        last_updated_tag=datetime.now())

@app.route('/progress_calibration/<string:device_name>', methods=['GET'])
def progress_calibration(device_name):
    duration, obs_1, obs_2, obs_3, obs_4, current_power, message = \
        _get_current_data(device_name)
    #Ignore obs_1 to obs_4

    return render_template ("progress_calibration.html",
        message=message,
        device_name_tag=device_name,
        duration_tag=duration,
        current_power_tag=current_power,
        last_updated_tag=datetime.now())

@app.route('/avoided_emissions/<string:device_name>/',
    methods=['GET', 'POST'])
def avoided_emissions(device_name):

    total_emissions_actual, total_emissions_alt, percentage_saved, message = \
        _get_avoided_emissions_data(device_name)

    # For some reasons total_emissions_actual and total_emissions_alt come
    # out as tuple rather than floats, so take the first element for now.
    return render_template ("avoided_emissions.html",
        message=message,
        device_name_tag=device_name,
        total_emissions_actual_tag= \
            "Unknown" if message else total_emissions_actual[0],
        total_emissions_alt_tag= \
            "Unknown" if message else total_emissions_alt[0],
        percentage_saved_tag=percentage_saved)

def _get_current_data(device_name):

    url = "https://<<CHARGE_PROGRESS_LAMBDA_FUNCTION_URL>>/"
    headers_string = {
        'Content-Type':'application/json',
        'Cache-Control':'no-cache'
    }
    json_data =  {
        'device_name': device_name
    }

    duration=None
    intensity_current=None
    intensity_overall=None
    intensity_charging=None
    percentage_saved=None
    current_power=None
    message=None

    response = requests.post(url,
        headers=headers_string,
        data=json.dumps(json_data))
    print("response: ", response)

    try:
        if len(response.json()) > 0 :
            json_response = response.json()

            duration = json_response['duration']
            intensity_current = json_response['intensity_current']
            intensity_overall = json_response['intensity_overall']
            intensity_charging = json_response['intensity_charging']
            percentage_saved = json_response['percentage_saved']
            current_power = json_response['current_power']
    except Exception:
        message="Progress data cannot be found. The device needs to be registered first and a calibration run needs to be finished."
        duration="Unknown"
        intensity_current="Unknown"
        intensity_overall="Unknown"
        intensity_charging="Unknown"
        percentage_saved="Unknown"
        current_power="Unknown" 

    return (duration, intensity_current, intensity_overall, intensity_charging,
        percentage_saved, current_power, message)

def _get_avoided_emissions_data(device_name):

    url = "https://<<CALCULATE_AVOIDED_EMISSIONS_LAMBDA_FUNCTION_URL>>/"
    headers_string = {
        'Content-Type':'application/json',
        'Cache-Control':'no-cache'
    }

    json_data = {
        'device_name': device_name
    }

    total_emissions_actual=None
    total_emissions_alt=None
    percentage_saved=None
    message=None

    response = requests.post(url,
        headers=headers_string,
        data=json.dumps(json_data, indent=4, default=str))

    json_response = None

    try:
        json_response = response.json()
        print("json_response: ", json_response)
    except Exception:
        message = "Avoided emission data not available for this device. Possibly no complete charging run has been done."
        total_emissions_actual="Unknown"
        total_emissions_alt="Unknown"
        percentage_saved="Unknown"
        return (total_emissions_actual, total_emissions_alt, percentage_saved, message)

    try:
        total_emissions_actual = \
             json_response['total_emissions_actual'],
        total_emissions_alt = json_response['total_emissions_alt'],
        percentage_saved = json_response['percentage_saved']
    except KeyError:
        # Happens when API rate limit has been exceeded
        total_emissions_actual="Unknown"
        total_emissions_alt="Unknown"
        percentage_saved="Unknown"
        message="The data can't be retrieved."

    return (total_emissions_actual, total_emissions_alt, percentage_saved, message)


def _start_calibration(device_name):

    url = "https://<<CALIBRATE_START_LAMBDA_FUNCTION_URL>>/"
    headers_string = {
        'Content-Type':'application/json',
        'Cache-Control':'no-cache'
    }

    json_data = {
        'device_name': device_name
    }

    message=None
    status=None
    startDate=None
    requestId=None

    try:
        response = requests.post(url,
            headers=headers_string,
            data=json.dumps(json_data, indent=4, default=str))

        print("response: ", response)
        json_response = response.json()
        status = json_response['status']
        startDate = json_response['message']['startDate']
        requestId = json_response['message']['ResponseMetadata']['RequestId']
    except Exception:
        # Happens when API rate limit has been exceeded
        message="The device cannot be calibrated. A probable cause is that the device with this name has not been registered yet."
        status="Unknown"
        startDate="Unknown"
        requestId="Unknown"

    return (status, startDate, requestId, message)


def _start_charging(device_name, time_window="0"):

    url = "https://<<CHARGE_START_LAMBDA_FUNCTION_URL>>/"
    headers_string = {
        'Content-Type':'application/json',
        'Cache-Control':'no-cache'
    }

    json_data = {
        'device_name': device_name,
        'time_window': time_window
    }

    status=None
    startDate=None
    requestId=None

    response = requests.post(url,
        headers=headers_string,
        data=json.dumps(json_data, indent=4, default=str))
    print("response: ", response)
    json_response = response.json()

    try:
        status = json_response['status']
        startDate = json_response['message']['startDate']
        requestId = json_response['message']['ResponseMetadata']['RequestId']
    except KeyError:
        # Happens when API rate limit has been exceeded
        status="Unknown"
        startDate="Unknown"
        requestId="Unknown"

    return (status, startDate, requestId)

def _perform_registration(device_name,
                        region_type_selection,
                        region_azure,
                        region_ba,
                        smart_plug_id,
                        smart_plug_auth_key,
                        smart_plug_url,
                        charge_mode):

    url = "https://<<PERFORM_REGISTRATION_LAMBDA_FUNCTION_URL>>/"
    headers_string = {
        'Content-Type':'application/json',
        'Cache-Control':'no-cache'
    }

    json_data = {
        'device_name': device_name,
        'region_type_selection': region_type_selection,
        'region_azure': region_azure,
        'region_ba': region_ba,
        'smart_plug_id': smart_plug_id,
        'smart_plug_auth_key': smart_plug_auth_key,
        'smart_plug_url': smart_plug_url,
        'charge_mode': charge_mode
    }

    status=None

    response = requests.post(url,
        headers=headers_string,
        data=json.dumps(json_data))
    print("response: ", response)
    json_response = response.json()

    try:
        status = json_response['status']
    except KeyError:
        status="Unknown"

    return status

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))

    app.secret_key = 'HDJHD&RGDHS&@JKSHGS%#$#'
    app.config['SESSION_TYPE'] = 'filesystem'

    sess.init_app(app)

    app.debug = True
    app.run(debug=True,host='0.0.0.0',port=port)

