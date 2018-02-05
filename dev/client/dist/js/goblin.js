function dom_channel(channel){

	var html = `<div class="channel-box col-lg-4 col-md-6 col-sm-12 col-xs-12 clearfix" id="channel-${channel.id}">
					<div class="info-box">
						<button class="state btn btn-flat info-box-icon ${channel.state == 'on' ? 'bg-green' : 'bg-red'}"><i class="fa fa-lightbulb-o"></i></button>
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
								  <li class="${channel.binder == 'time' ? 'active' : ''}"><a href="#${'time_tab' + channel.id}" data-toggle="tab">TIME</a></li>
								  <li class="${channel.binder == 'temperature' ? 'active' : ''}"><a href="#${'temperature_tab' + channel.id}" data-toggle="tab">TEMPERATURE</a></li>
							</ul>
							<div class="tab-content">
								<div class="tab-pane ${channel.binder == 'time' ? 'active' : ''}" id="${'time_tab' + channel.id}">
									<div class="box-body form-group">
										<div class="bootstrap-timepicker ">
											<div class="input-group">
												<div class="input-group-addon">
												  <label>Turn on at</label>
												</div>
												<input type="text" class="form-control timepicker turnonat">
												<div class="input-group-addon">
												  <i class="fa fa-clock-o"></i>
												</div>
											</div>
										</div>
										<div class="bootstrap-timepicker ">
											<div class="input-group">
												<div class="input-group-addon">
												  <label>Turn off at</label>
												</div>
												<input type="text" class="form-control timepicker turnoffat">
												<div class="input-group-addon">
												  <i class="fa fa-clock-o"></i>
												</div>
											</div>
										</div>
									</div>
								</div>
								<div class="tab-pane ${channel.binder == 'temperature' ? 'active' : ''}" id="${'temperature_tab' + channel.id}">
									hi
								</div>
							</div>
							<button class="btn btn-flat btn-success save-btn">Save changes</button>
						</div>
					</div>
				</div>`

	var $channelbox = $(html)

	$channelbox.find('button.state').click(() => {
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

	var fetchAndUpdate = function(query, args){
		return fetch(query, args)
		.then(response => {
			if (response.ok){
				return response.json()
			}
			return Promise.reject(response.json())
		})
		.then(chinfo => $channelbox.replaceWith(dom_channel(chinfo.channel)))
		.catch(chinfo => alert(chinfo.error ? chinfo.error : 'An error has occured:\n' + chinfo))
	}

	$autocb.on('ifToggled', (event) => {
		var query = '';
		if(event.target.checked) {
			query = `api/channels/${channel.id}/set/auto`
		} else {
			query = `api/channels/${channel.id}/set/${channel.state == 'on' ? 'on' : 'off'}`
		}
		fetchAndUpdate(query, {method:'POST'})
	})
	
	//Timepicker
	$channelbox.find('.timepicker').timepicker({
		template: 'dropdown',
		showInputs: false,
		showMeridian: false,
		defaultTime: '00:00'
	})

	if (channel.timeBinder){
		$channelbox.find('.timepicker.turnonat').timepicker('setTime', channel.timeBinder.turnOnAt);
		$channelbox.find('.timepicker.turnoffat').timepicker('setTime', channel.timeBinder.turnOffAt);
	}

	$channelbox.find('.save-btn').click(e => {
		var query = `api/channels/${channel.id}/bind`
		var body = {}
		if ($('#time_tab' + channel.id).hasClass('active')){
			body['binder'] = 'time'
			body['timeBinder'] = {
				'turnOnAt' : $('#time_tab' + channel.id).find('.turnonat').val(),
				'turnOffAt' : $('#time_tab' + channel.id).find('.turnoffat').val()
			}
		}
		var args = {
			method:'POST',
			body: JSON.stringify(body),
			headers: new Headers({'Content-Type': 'application/json'})
		}
		fetchAndUpdate(query, args)
			.then(() => {
				var $btn = $(`#channel-${channel.id}`).find('.save-btn')
				var text = $btn.text()
				$btn.text("Saved!")
				$btn.prop("disabled",true)
				setTimeout(() => {
					$btn.text(text)
					$btn.prop("disabled",false)
				}, 2000)
			})
	});

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
