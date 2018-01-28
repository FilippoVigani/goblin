#!/usr/bin/env python
"""Flask server that serves file and interfaces with physical level"""

import json
import time
import atexit
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

CHANNELS_PATH = './channels.json'
APP = Flask(__name__, static_folder='client', static_url_path='')

@APP.route('/')
def homepage():
	"""Returns website homepage"""
	return APP.send_static_file('index.html')

@APP.route('/api/channels')
def get_channels():
	"""Returns list of channels"""
	return CHANNELS

@APP.route('/api/channels/<channel_id>/<setting>')
def set_channel_setting(channel_id, setting):
	"""Changes a channel setting {on,off,auto}"""
	try:
		channel = next(c for c in CHANNELS if c['id'] == int(channel_id))
	except:
		return jsonify({'error': "Channel {} not found".format(channel_id)})
	channel['setting'] = setting.lower()
	update_state(channel)
	save_channels()
	return jsonify("Channel {} {}".format(channel['id'], 'set to auto.' if channel['setting'] == 'auto' else "turned {}".format(channel['setting'])))

def update_all_states():
	print(" * Updating channels states.")
	for channel in CHANNELS:
		update_state(channel)

def update_state(channel):
	"""Updates the physical state of a channel to match its setting"""
	if not 'setting' in channel or not channel['setting'] in ['on','off','auto']:
		return 
	if channel['setting'] == 'auto':
		return
	#GPIO.output(channel['GPIO'], GPIO.LOW if channel['setting'] == 'on' else GPIO.LOW)
	channel['state'] = channel['setting']

def save_channels():
	"""Saves channels settings on disk"""
	with open(CHANNELS_PATH, 'w') as cf:
		json.dump(CHANNELS, cf, indent='\t')

def run_scheduler(min=5):
	"""Updates all the channels states to match their setting"""
	scheduler = BackgroundScheduler()
	scheduler.start()
	scheduler.add_job(
    	update_all_states,
    	trigger=IntervalTrigger(minutes=min),
    	id='update_channels_state_job',
    	name='Update channel state every {} minutes.'.format(min),
    	replace_existing=True
    	)
	# Shut down the scheduler when exiting the app
	atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
	with open(CHANNELS_PATH) as cf:
		CHANNELS = json.load(cf)
	update_all_states()
	run_scheduler()
	APP.run()

	

