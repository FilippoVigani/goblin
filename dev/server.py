from flask import Flask
import json
app = Flask(__name__, static_folder='client', static_url_path='')

@app.route("/api/channels")
def channels():
    return "Hello World!"

@app.route('/api/channels')
def getChannels():
	return channels

@app.route('/api/channel/<channel_id>/<setting>')
def setChannelSetting(channel_id, setting):
	channel = next(c for c in channels if c.channel == channel_id)
	print(channel)
	channel['setting'] = setting.lower()
	updateState(channel)
	return "Channel {} {}".format(channel['channel'], 'set to auto.' if channel['setting'] == 'auto' else "turned {}".format(channel['setting']))

def updateState(channel):
	pass

if __name__ == "__main__":
	channels = json.load(open('./channels.json'))
	print(channels)
	for channel in channels:
		updateState(channel)
	app.run()

