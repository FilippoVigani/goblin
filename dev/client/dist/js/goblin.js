function dom_channel(channel){

	var html = `<div class="channel-box col-lg-4 col-md-6 col-sm-12 col-xs-12 clearfix">
					<div class="info-box" id="channel-${channel.id}">
						<button class="btn btn-flat info-box-icon ${channel.state == 'on' ? 'bg-green' : 'bg-red'}"><i class="fa fa-lightbulb-o"></i></button>
						<div class="info-box-content">
							<span class="info-box-text">${"Channel " + channel.id}</span>
							<span class="lead">${channel.name ? channel.name : ''}</span>
							<div class="auto-select pull-right">
								<label for="channel-${channel.id}-auto-checkbox">Auto</label>
								<input type="checkbox" ${channel.setting == 'auto' ? 'checked' : ''} id="channel-${channel.id}-auto-checkbox"/>
							</div>
						</div>
					</div>
					<div class="channel-binders box box-warning ${channel.setting == 'auto' ? '' : 'hidden'}">
						<div class="nav-tabs-custom">
			            <ul class="nav nav-tabs">
			              <li class=""><a href="#${'time_tab' + channel.id}" data-toggle="tab">TIME</a></li>
			              <li class=""><a href="#${'temperature_tab' + channel.id}" data-toggle="tab">TEMPERATURE</a></li>
			            </ul>
			            <div class="tab-content">
			              <div class="tab-pane" id="${'time_tab' + channel.id}">
			                <div class="box-body form-group">
			                	<div class="bootstrap-timepicker timepicker">
									<div class="input-group">
										<div class="input-group-addon">
										  <label>Turn on at</label>
										</div>
										<input type="text" class="form-control timepicker">
										<div class="input-group-addon">
										  <i class="fa fa-clock-o"></i>
										</div>
									</div>
								</div>
								<div class="bootstrap-timepicker timepicker">
									<div class="input-group">
										<div class="input-group-addon">
										  <label>Turn off at</label>
										</div>
										<input type="text" class="form-control timepicker">
										<div class="input-group-addon">
										  <i class="fa fa-clock-o"></i>
										</div>
									</div>
								</div>
							</div>
			              </div>
			              <div class="tab-pane" id="${'temperature_tab' + channel.id}">
			                hi
			              </div>
			            </div>
			          </div>
					</div>
				</div>`

	var $channelbox = $(html)

	$channelbox.find('button').click(() => {
		fetch(`api/channels/${channel.id}/set/${channel.state == 'on' ? 'off' : 'on'}`, {method:'POST'})
			.then(response => {
				if (response.ok){
					return response.json()
				}
			}).then(chinfo => $channelbox.replaceWith(dom_channel(chinfo.channel)))
	})

	var $autocb = $channelbox.find('input[type="checkbox"]').iCheck({
			checkboxClass: 'icheckbox_square-orange',
			radioClass: 'iradio_square-orange',
			increaseArea: '40%' // optional
	  })

	$autocb.on('ifToggled', (event) => {
		var query = '';
		if(event.target.checked) {
			query = `api/channels/${channel.id}/set/auto`
		} else {
			query = `api/channels/${channel.id}/set/${channel.state == 'on' ? 'on' : 'off'}`
		}
		fetch(query, {method:'POST'})
			.then(response => {
				if (response.ok){
					return response.json()
				}
			}).then(chinfo => $channelbox.replaceWith(dom_channel(chinfo.channel)))
	})

	
	//Timepicker
	$channelbox.find('.timepicker').timepicker({
		template: 'dropdown',
		showInputs: false,
		showMeridian: false
	})

	return $channelbox
}

$(document).ready(() => {
	fetch('api/channels', {method:'GET'}).then(response => response.json())
	.then(channels => {
		channels.forEach(channel => {
			$('#container').append(dom_channel(channel))
		})
		
	})
	}
)
