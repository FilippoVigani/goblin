#!/usr/bin/env python3
"""Flask server that that interfaces a web client with the physical layer"""
import json
import time
import atexit
import datetime
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import RPi.GPIO as GPIO

CHANNELS_PATH = './channels.json'
app = Flask(__name__, static_folder='client', static_url_path='')

@app.route('/')
def homepage():
	"""Returns website homepage"""
	return app.send_static_file('index.html')

@app.route('/api/channels', methods=['GET'])
def get_channels():
	"""Returns list of channels"""
	return jsonify(CHANNELS)

@app.route('/api/channels/<channel_id>/set/<setting>', methods=['POST'])
def set_channel_setting(channel_id, setting):
	"""Changes a channel setting {on,off,auto}"""
	try:
		channel = next(c for c in CHANNELS if c['id'] == int(channel_id))
	except:
		return jsonify({'error': "Channel {} not found".format(channel_id)}), 404
	channel['setting'] = setting.lower()
	update_state(channel)
	save_channels()
	response = {'channel': channel,
				'message' : "Channel {} {}".format(channel['id'], 'set to auto.' if channel['setting'] == 'auto' else "turned {}".format(channel['setting']))}
	return jsonify(response)

def update_all_states():
	"""Updates all the channels states to match their setting"""
	print(" * Updating channels states.")
	for channel in CHANNELS:
		update_state(channel)

def update_state(channel):
	"""Updates the physical state of a channel to match its setting"""
	if not 'setting' in channel or not channel['setting'] in ['on','off','auto']:
		#turn(channel, off=True)
		return 
	if channel['setting'] == 'auto':
		if 'temperatureBinder' in channel: #Only needed for temperature binders, as time binders are controlled by cron scheduler
			temp = readTemperature(channel['temperatureBinder']['thermometer'])
			#find matching time slot
			slot = None
			for ts in channel['temperatureBinder']['slots']:
				from_datetime = time_to_datetime(ts['from'])
				to_datetime = time_to_datetime(ts['to'])
				now_datetime = datetime.datetime.now()
				if from_datetime <= to_datetime:
					if from_datetime <= now_datetime < to_datetime:
						slot = ts
						break
				else:
					if now_datetime >= from_datetime or now_datetime < to_datetime:
						slot = ts
						break
			if not slot:
				now = datetime.datetime.now()
				print("Time slot not found for time {}.{} for channel {}".format(now.hour, now.minute, channel['id']))
				return
			
			if temp > slot['max'] and (not 'state' in channel or channel['state'] == 'on'): #Too hot!
				print("Temperature too high on thermometer {}".format(channel['temperatureBinder']['thermometer']))
				turn(channel, off=True)
			elif temp < slot['min'] and (not 'state' in channel or channel['state'] == 'off'): #Too cold!
				print("Temperature too cold on thermometer {}".format(channel['temperatureBinder']['thermometer']))
				turn(channel, on=True)
		elif not 'timeBinder':
			print("Channel {} is set to auto but no binder was found.".format(channel['id']))
			turn(channel, off=True)
		return
	if channel['setting'] == 'on' and ('state' not in channel or channel['state'] != 'on'):
		return turn(channel, on=True)
	if channel['setting'] == 'off' and ('state' not in channel or channel['state'] != 'off'):
		return turn(channel, off=True)

def readTemperature(thermometer):
	return 23

def turn(channel, on=False, off=False):
	if on:
		channel['state'] = 'on'
		GPIO.output(channel['GPIO'], GPIO.LOW)
	elif off:
		channel['state'] = 'off'
		GPIO.output(channel['GPIO'], GPIO.HIGH)
	else:
		return
	print("Channel {} turned {}".format(channel['id'], channel['state']))

def remove_key(element, key):
	if key in element:
		del element[key]
	return element

def save_channels():
	"""Saves channels settings on disk"""
	channelsStrippedOfState = list(map(lambda c: remove_key(dict(c), 'state'), CHANNELS))
	with open(CHANNELS_PATH, 'w') as cf:
		json.dump(channelsStrippedOfState, cf, indent='\t')

def time_to_datetime(time):
	hm = time.replace(':','.').split('.')
	return datetime.datetime.now().replace(hour=int(hm[0]), minute=int(hm[-1]), second=0, microsecond=0)

def schedule_temperature_binders():
	"""Updates all the channels every 5 minutes to match their temperature settings"""
	SCHEDULER.add_job(
    	update_all_states,
    	trigger=IntervalTrigger(minutes=5),
    	id='update_channels_state_job',
    	name='Update channel state every {} minutes.'.format(min),
    	replace_existing=True
    	)

def schedule_time_binder(channel):
	"""Set up a scheduler bound to a channel that turns on and off the channel at the spicified time"""
	if 'timeBinder' in channel:
			onAt = time_to_datetime(channel['timeBinder']['turnOnAt'])
			SCHEDULER.add_job(
				lambda: turn(channel, on=channel['setting']=='auto'),
				trigger=CronTrigger(hour=onAt.hour, minute=onAt.minute),
				id="channel_{}_time_binder_turn_on".format(channel['id']),
				name="Turn on channel {} every day at {}".format(channel['id'], channel['timeBinder']['turnOnAt']),
				replace_existing=True)
			offAt = time_to_datetime(channel['timeBinder']['turnOffAt'])
			SCHEDULER.add_job(
				lambda: turn(channel, off=channel['setting']=='auto'),
				trigger=CronTrigger(hour=offAt.hour, minute=offAt.minute),
				id="channel_{}_time_binder_turn_off".format(channel['id']),
				name="Turn off channel {} every day at {}".format(channel['id'], channel['timeBinder']['turnOffAt']),
				replace_existing=True)

def remove_time_binder(channel):
	""""Remove the scheduled jobs bound to a specific channel"""
	SCHEDULER.remove_job("channel_{}_time_binder_turn_on".format(channel['id']))
	SCHEDULER.remove_job("channel_{}_time_binder_turn_off".format(channel['id']))

def cleanup():
	"""Stuff to clean before exiting"""
	print('Shutting down...')
	SCHEDULER.shutdown()
	GPIO.cleanup()

if __name__ == "__main__":
	global CHANNELS
	global SCHEDULER
	""" Read channels data from file system """
	with open(CHANNELS_PATH) as cf:
		CHANNELS = json.load(cf)
	GPIO.setmode(GPIO.BCM)
	for channel in CHANNELS:
		GPIO.setup(channel['GPIO'], GPIO.OUT, initial=GPIO.HIGH)
	update_all_states()
	SCHEDULER = BackgroundScheduler()
	SCHEDULER.start()
	schedule_temperature_binders()
	for channel in CHANNELS:
		schedule_time_binder(channel)

	atexit.register(cleanup)

	app.run(host='0.0.0.0')

