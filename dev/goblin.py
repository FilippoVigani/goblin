#!/usr/bin/env python3
"""Flask server that that interfaces a web client with the physical layer"""
import json
import time
import atexit
import datetime
import copy
import os
import hashlib
import base64
try:
	import Adafruit_DHT
except ModuleNotFoundError:
	print(" ! Adafruit_DHT wasn't found. Continuing.")
from flask import Flask, jsonify, request, redirect, session, escape
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import RPi.GPIO as GPIO

CHANNELS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'channels.json')
USERS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'users.json')
THERMOMETERS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'thermometers.json')
app = Flask(__name__, static_folder='client', static_url_path='')

app.secret_key = base64.b64encode(os.urandom(64)).decode('utf-8') #used for session

@app.route('/')
def homepage():
	"""Returns website homepage"""
	if ('username' in session):
		response = app.send_static_file('index.html')
		response.headers['Cache-Control'] = 'no-cache'
		return response
	else:
		return redirect('/login.html')

def authenticate(username, password):
	try:
		user = next(u for u in USERS if u.get('username') == username)
	except:
		return False
	return hashlib.sha256(((password if password else '') + user.get('salt')).encode('utf-8')).hexdigest() == user.get('password_hash')

@app.route('/api/login', methods=['POST'])
def login():
	"""User authentication"""
	if authenticate(request.form.get('username'), request.form.get('password')):
		session['username'] = request.form.get('username')
		return redirect('/')
	else:
		return redirect('/login.html')

@app.route('/api/channels', methods=['GET'])
def get_channels():
	"""Returns list of channels"""
	if not 'username' in session:
		return jsonify({'error': "User not logged in"}), 403
	return jsonify(CHANNELS)

@app.route('/api/thermometers', methods=['GET'])
def get_thermometers():
	"""Returns list of channels"""
	if not 'username' in session:
		return jsonify({'error': "User not logged in"}), 403
	return jsonify(THERMOMETERS)

@app.route('/api/channels/<channel_id>/set/<setting>', methods=['POST'])
def set_channel_setting(channel_id, setting):
	"""Changes a channel setting {on,off,auto}"""
	if not 'username' in session:
		return jsonify({'error': "User not logged in"}), 403
	try:
		channel = next(c for c in CHANNELS if c['id'] == int(channel_id))
	except:
		return jsonify({'error': "Channel {} not found".format(channel_id)}), 404
	channel['setting'] = setting.lower()

	remove_scheduled_binders(channel)

	update_state(channel)
	schedule_binders(channel)
	save_channels()

	response = {'channel': channel,
				'message' : "Channel {} {}".format(channel['id'], 'set to auto.' if channel['setting'] == 'auto' else "turned {}".format(channel['setting']))}
	return jsonify(response)

def time_of_day_to_seconds(timeOfDay, laterThan = -1):
	x = time.strptime(timeOfDay,'%H:%M')
	seconds = datetime.timedelta(hours=x.tm_hour,minutes=x.tm_min,seconds=x.tm_sec).total_seconds()
	if (laterThan >= 0 and seconds <= laterThan):
		seconds += 24*60*60
	return seconds

def seconds_to_time_of_day(seconds):
	return time.strftime("%H:%M", time.gmtime(seconds))

@app.route('/api/channels/<channel_id>/binders/<binder_index>/split', methods=['POST'])
def split_binder(channel_id, binder_index):
	"""Splits the selected binder in half"""
	if not 'username' in session:
		return jsonify({'error': "User not logged in"}), 403
	binder_index = int(binder_index)
	try:
		channel = next(c for c in CHANNELS if c.get('id') == int(channel_id))
	except:
		return jsonify({'error': "Channel {} not found".format(channel_id)}), 404

	try:
		newBinder = copy.copy(channel.get('binders')[binder_index])
	except:
		response = {'channel': channel,
				'error': "Binder {} not found in channel {}".format(binder_index, channel_id)}
		return jsonify(response)

	remove_scheduled_binders(channel)

	fromSeconds = time_of_day_to_seconds(newBinder.get('from'))
	toSeconds = time_of_day_to_seconds(newBinder.get('to'), laterThan=fromSeconds)
	splitPointTimeOfDay = seconds_to_time_of_day((fromSeconds + toSeconds) / 2)
	newBinder['to'] = splitPointTimeOfDay
	channel['binders'][binder_index]['from'] = splitPointTimeOfDay
	channel['binders'].insert(binder_index, newBinder)

	update_state(channel)
	schedule_binders(channel)
	save_channels()
	response = {'channel': channel,
				'message' : "Channel {} {}".format(channel.get('id'), 'set to auto.' if channel.get('setting') == 'auto' else "turned {}".format(channel.get('setting')))}
	return jsonify(response)

@app.route('/api/channels/<channel_id>/binders/<binder_index>', methods=['POST'])
def set_binder(channel_id, binder_index):
	"""Splits the selected binder in half"""
	if not 'username' in session:
		return jsonify({'error': "User not logged in"}), 403
	binder_index = int(binder_index)
	try:
		channel = next(c for c in CHANNELS if c.get('id') == int(channel_id))
	except:
		return jsonify({'error': "Channel {} not found".format(channel_id)}), 404

	remove_scheduled_binders(channel)

	binder = channel['binders'][binder_index]
	newBinder = request.get_json(silent=True)
	fromSeconds = time_of_day_to_seconds(newBinder.get('from', binder.get('from')))
	toSeconds = time_of_day_to_seconds(newBinder.get('to', binder.get('to')), laterThan=fromSeconds)
	
	binder.update({
		'state': newBinder.get('state', binder.get('state')),
		'min': newBinder.get('min', binder.get('min')),
		'max': newBinder.get('max', binder.get('max')),
		'from': seconds_to_time_of_day(fromSeconds),
		'to': seconds_to_time_of_day(toSeconds)
	})

	if binder.get('from') == binder.get('to'):
		channel['binders'] = [binder]
	else:
		for b in channel.get('binders'):
			if b is binder: continue
			b_fromSeconds = time_of_day_to_seconds(b.get('from'), laterThan=toSeconds)
			b_toSeconds = time_of_day_to_seconds(b.get('to'), laterThan=b_fromSeconds)
			if (fromSeconds <= b_fromSeconds and b_toSeconds <= toSeconds):
				print('delete')
				channel['binders'].remove(b)
		binder_index = channel['binders'].index(binder)
		channel['binders'][binder_index-1]['to'] = binder.get('from')
		channel['binders'][(binder_index+1) % len(channel['binders'])]['from'] = binder.get('to')

	update_state(channel)
	schedule_binders(channel)
	save_channels()
	response = {'channel': channel,
				'message' : "Binder {} of channel {} updated".format(binder_index, channel.get('id'))}
	return jsonify(response)

def update_all_states():
	"""Updates all the channels states to match their setting"""
	print(" * Updating channels states.")
	for channel in CHANNELS:
		update_state(channel)

def update_state(channel):
	"""Updates the physical state of a channel to match its setting"""
	if channel.get('setting') == 'auto':
		if 'binders' in channel: #Only needed for temperature binders, as time binders are controlled by cron scheduler
			#find matching time slot
			slot = None
			for binder in channel.get('binders'):
				from_datetime = time_of_day_to_datetime(binder.get('from'))
				to_datetime = time_of_day_to_datetime(binder.get('to'))
				if from_datetime == to_datetime:
					slot = binder
					break
				now_datetime = datetime.datetime.now()
				if from_datetime <= to_datetime:
					if from_datetime <= now_datetime < to_datetime:
						slot = binder
						break
				else:
					if now_datetime >= from_datetime or now_datetime < to_datetime:
						slot = binder
						break
			if not slot:
				now = datetime.datetime.now()
				print(" ! Time slot not found for time {}.{} for channel {}".format(now.hour, now.minute, channel.get('id')))
				return
			if slot.get('state') == 'on' and not channel.get('state') == 'on':
				return turn(channel, on=True)
			if slot.get('state') == 'off'and not channel.get('state') == 'off':
				return turn(channel, off=True)
			if slot.get('state') == 'temperature':
				temp = binder.get('thermometer').get('temperature')
				if temp > slot.get('max') if slot.get('max') else 0.0 and channel.get('state','on') == 'on': #Too hot!
					print(" + Temperature too high on thermometer {}".format(binder.get('thermometer')))
					turn(channel, off=True)
				elif temp < slot.get('min') if slot.get('min') else 0.0 and channel.get('state','off') == 'off': #Too cold!
					print(" + Temperature too cold on thermometer {}".format(binder.get('thermometer')))
					turn(channel, on=True)
		return
	if channel.get('setting') == 'on' and channel.get('state') != 'on':
		return turn(channel, on=True)
	if channel.get('setting') == 'off' and channel.get('state') != 'off':
		return turn(channel, off=True)

def fetch_thermometers_data():
	print(" * Reading thermometers data.")
	for thermometer in THERMOMETERS:
		fetch_thermometer_data(thermometer)

def fetch_thermometer_data(thermometer):
	if thermometer.get('model') == 'DHT22':
		try:
			h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, thermometer.get('GPIO'))
			thermometer.temperature = t
			thermometer.humidity = h
		except NameError:
			pass

def turn(channel, on=False, off=False):
	if on:
		channel['state'] = 'on'
		GPIO.output(channel['GPIO'], GPIO.LOW)
	elif off:
		channel['state'] = 'off'
		GPIO.output(channel['GPIO'], GPIO.HIGH)
	else:
		return
	print(" + Channel {} turned {}".format(channel.get('id'), channel.get('state')))

def remove_key(element, key):
	if key in element:
		del element[key]
	return element

def save_channels():
	"""Saves channels settings on disk"""
	channelsStrippedOfState = list(map(lambda c: remove_key(dict(c), 'state'), CHANNELS))
	try:
		with open(CHANNELS_PATH, 'w') as cf:
			json.dump(channelsStrippedOfState, cf, indent='\t')
	except:
		print('Error while saving to file!')

def time_of_day_to_datetime(timeOfDay):
	if not timeOfDay:
		return datetime.datetime.now()
	hm = datetime.datetime.strptime(timeOfDay,'%H:%M')
	return datetime.datetime.now().replace(hour=hm.hour, minute=hm.minute, second=0, microsecond=0)

def schedule_temperature_binders():
	"""Updates all the channels every 5 minutes to match their temperature settings"""
	SCHEDULER.add_job(
    	update_all_states,
    	trigger=IntervalTrigger(minutes=5, start_date=datetime.datetime.now()),
    	id='update_channels_state_job',
    	name='Update channel state every 5 minutes.',
    	replace_existing=True
    	)

	"""Read temperature and humidity data from all sensors"""
	SCHEDULER.add_job(
    	fetch_thermometers_data,
    	trigger=IntervalTrigger(seconds=30, start_date=datetime.datetime.now()),
    	id='fetch_thermometers_data_job',
    	name='Update thermometers infos every 30 seconds.'.format(min),
    	replace_existing=True
    	)

def schedule_binders(channel):
	"""Set up a scheduler bound to a channel that updates the channel state on the time lapses points"""
	if (channel.get('setting') != 'auto'):
		return
	for i, binder in enumerate(channel.get('binders', [])):
		updateAt = time_of_day_to_datetime(binder.get('from'))
		name = "Scheduled update for channel {} every day at {} ({})".format(channel.get('id'), binder.get('from'), binder.get('state'))
		SCHEDULER.add_job(
				lambda: update_state(channel),
				trigger=CronTrigger(hour=updateAt.hour, minute=updateAt.minute),
				id="channel_{}_update_{}".format(channel.get('id'), i),
				name=name,
				replace_existing=True)
		print(' ~ ' + name)

def remove_scheduled_binders(channel):
	""""Remove the scheduled jobs bound to a specific channel"""
	for i, binder in enumerate(channel.get('binders', [])):
		try:
			SCHEDULER.remove_job("channel_{}_update_{}".format(channel.get('id'), i))
		except:
			pass
	print(' - Removed scheduled timers for channel {}'.format(channel.get('id')))

def cleanup():
	"""Stuff to clean before exiting"""
	print('Shutting down...')
	SCHEDULER.shutdown()
	GPIO.cleanup()

if __name__ == "__main__":
	global CHANNELS
	global SCHEDULER
	global USERS
	""" Read channels data from file system """
	with open(CHANNELS_PATH) as cf:
		CHANNELS = json.load(cf)
	with open(USERS_PATH) as uf:
		USERS = json.load(uf)
	with open(THERMOMETERS_PATH) as tf:
		THERMOMETERS = json.load(tf)
	GPIO.setmode(GPIO.BCM)
	for channel in CHANNELS:
		GPIO.setup(channel.get('GPIO'), GPIO.OUT, initial=GPIO.HIGH)
	SCHEDULER = BackgroundScheduler()
	SCHEDULER.start()
	schedule_temperature_binders()
	for channel in CHANNELS:
		schedule_binders(channel)

	atexit.register(cleanup)

	app.run(host='0.0.0.0', use_reloader=False, threaded=True)

