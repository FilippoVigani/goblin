function fetchAndUpdate(query, args){
	args['credentials'] = 'include'
	return fetch(query, args)
	.then(response => {
		if (response.ok){
			return response.json()
		}
		return Promise.reject(response.json())
	})
	.then(chinfo => {
		var cbox = $('#channel-' + chinfo.channel.id)
		cbox.data('channel', chinfo.channel)
		cbox.find('button.state').removeClass('bg-green bg-red').addClass(chinfo.channel.state == 'on' ? 'bg-green' : 'bg-red')
		cbox.find('input[name="auto"]').prop('checked', chinfo.channel.setting == 'auto')
		cbox.find('.channel-binders').toggleClass('hidden', chinfo.channel.setting != 'auto')
		
		addBindersEditorDOM(chinfo.channel)
	})
	.catch(chinfo => alert(chinfo.error ? chinfo.error : 'An error has occured:\n' + JSON.stringify(chinfo)))
}

function channelDOM(channel){
	var html = 
		`<div class="channel-box col-lg-4 col-md-6 col-sm-12 col-xs-12 clearfix" id="channel-${channel.id}">
			<div class="info-box">
				<button class="state btn btn-flat info-box-icon ${channel.state == 'on' ? 'bg-green' : 'bg-red'}"><i class="fa fa-lightbulb-o"></i></button>
				<div class="info-box-content">
					<span class="info-box-text">${"Channel " + channel.id}</span>
					<span class="lead">${channel.name ? channel.name : ''}</span>
					<label class="tgl pull-right">  
						<input type="checkbox" ${channel.setting == 'auto' ? 'checked' : ''} name="auto" id="channel-${channel.id}-auto-checkbox" />
						<span data-on="Auto" data-off="Manual"></span>
					</label>
				</div>
			</div>
			<div class="channel-binders box box-warning ${channel.setting == 'auto' ? '' : 'hidden'}" id="channel-${channel.id}-binders">
			</div>
		</div>`

	var $channelbox = $(html)
	$channelbox.data('channel', channel)

	$channelbox.find('button.state').click(() => {
		channel = $channelbox.data('channel')
		fetchAndUpdate(`api/channels/${channel.id}/set/${channel.state == 'on' ? 'off' : 'on'}`, {method:'POST'})
	})

	$channelbox.find('input[name="auto"]').on('change', (e) => {
		channel = $channelbox.data('channel')
		var query = '';
		if($(e.target).is(":checked")) {
			query = `api/channels/${channel.id}/set/auto`
		}else {
			query = `api/channels/${channel.id}/set/${channel.state == 'on' ? 'on' : 'off'}`
		}
		$(e.target).prop('disabled', true)
		fetchAndUpdate(query, {method:'POST'})
		setTimeout(() => {
			$(e.target).prop('disabled', false)
		}, 300)
		
	})

	return $channelbox
}

function binderEditorDOM(channel, binderIndex){
	var html = 
		`<div class="binder-editor">
			<div class="box-body form-group">
				<button class="btn btn-flat btn-primary split-btn">Split <i class="fa fa-pie-chart"></i></button>
				<div class="bootstrap-timepicker ">
					<div class="input-group">
						<div class="input-group-addon">
						  <label>From</label>
						</div>
						<input type="text" class="form-control timepicker from" name="from">
						<div class="input-group-addon">
						  <i class="fa fa-clock-o"></i>
						</div>
					</div>
				</div>
				<div class="bootstrap-timepicker ">
					<div class="input-group">
						<div class="input-group-addon">
						  <label>To</label>
						</div>
						<input type="text" class="form-control timepicker to" name="to">
						<div class="input-group-addon">
						  <i class="fa fa-clock-o"></i>
						</div>
					</div>
				</div>
				<div class="switch-field">
					<input type="radio" id="switch_left" name="state" value="on" ${channel.binders[binderIndex].state == 'on' ? 'checked' : ''}/>
					<label class="on" for="switch_left">On</label>
					<input type="radio" id="switch_center" name="state" value="temperature" ${channel.binders[binderIndex].state == 'temperature' ? 'checked' : ''} />
					<label class="temperature" for="switch_center">Temperature</label>
					<input type="radio" id="switch_right" name="state" value="off" ${channel.binders[binderIndex].state == 'off' ? 'checked' : ''}/>
					<label class="off" for="switch_right">Off</label>
				</div>
				<div class="temperature-control ${channel.binders[binderIndex].state == 'temperature' ? '' : 'hidden'}">
					<div class="input-group">
						<span class="input-group-addon"><label>Min</label></span>
						<input class="form-control temperaturepicker" type="number" placeholder="°C" step="0.5" min="0" max="100" name="min" value="${channel.binders[binderIndex].min}">
						<span class="input-group-addon"><i class="fa fa-thermometer-3"></i></span>
					</div>
					<div class="input-group">
						<span class="input-group-addon"><label>Max</label></span>
						<input class="form-control temperaturepicker" type="number" placeholder="°C" step="0.5" min="0" max="100" name="max" value="${channel.binders[binderIndex].max}">
						<span class="input-group-addon"><i class="fa fa-thermometer-3"></i></span>
					</div>
				</div>
				<div class="spacer"></div>
				<div class="buttons">
					<button class="btn btn-flat btn-danger discard-btn">Discard</button>
					<button class="btn btn-flat btn-success save-btn">Save</button>
				</div>
			</div>
		</div>`
	var $editor = $(html)

	//Timepicker
	$editor.find('.timepicker').timepicker({
		template: 'dropdown',
		showInputs: false,
		showMeridian: false,
		defaultTime: '00:00'
	})

	$editor.find('input[name=state]').on('change', (e) =>{
		if (e.target.value == 'temperature'){
			$editor.find('.temperature-control').removeClass('hidden')
		} else{
			$editor.find('.temperature-control').addClass('hidden')
		}
	})

	if (channel.binders){
		$editor.find('.timepicker[name=from]').timepicker('setTime', channel.binders[binderIndex].from.replace('.', ':'))
		$editor.find('.timepicker[name=to]').timepicker('setTime', channel.binders[binderIndex].to.replace('.', ':'))
	}

	setTimeout(() => {
		$editor.addClass('open')
	}, 0)

	$editor.find('.discard-btn').on('click', () => {
		$editor.removeClass('open')
		setTimeout(() => {
			$editor.remove();
		}, 300)
	})

	var save = function(){
		var body = {
			from: $('input.timepicker[name=from]').val(),
			to: $('input.timepicker[name=to]').val(),
			state: $('input[name=state][type=radio]:checked').val(),
			min: parseFloat($('input.temperaturepicker[name=min]').val()),
			max: parseFloat($('input.temperaturepicker[name=max]').val()),
		}

		var query = `api/channels/${channel.id}/binders/${binderIndex}`
		var args = {
			method:'POST',
			body: JSON.stringify(body),
			headers: new Headers({'Content-Type': 'application/json'})
		}
		fetchAndUpdate(query, args)

	}

	$editor.find('.split-btn').on('click', () => {
		save()
		var query = `api/channels/${channel.id}/binders/${binderIndex}/split`
		var args = {
			method:'POST',
		}
		fetchAndUpdate(query, args)

		$editor.removeClass('open')
		setTimeout(() => {
			$editor.remove()
		}, 300)
	})

	

	$editor.find('.save-btn').on('click', () => {
		save()
		$editor.removeClass('open')
		setTimeout(() => {
			$editor.remove()
		}, 300)
		addBindersEditorDOM(channel)
	})

	return $editor
}

function timeStringToSeconds(timeString){
	var minutes = timeString.replace('.',':').split(':')[1]
	var hours = timeString.replace('.',':').split(':')[0]
	return minutes*60 + hours*3600
}

function secondsToTimeString(seconds){
	seconds = (seconds + 24*60*60) % (24*60*60)
	var hours = Math.floor(seconds / 3600);
	var minutes = Math.floor((seconds - (hours * 3600)) / 60);
	return hours + ':' + ('0' + minutes).slice(-2)
}

function addBindersEditorDOM(channel){
	$('#channel-' + channel.id + '-binders svg').remove()
	if (channel.binders instanceof Array){
		var margin = 16
		var size = 200
		var svg = SVG('channel-' + channel.id + '-binders').viewbox(0,0,size,size);

		channel.binders.forEach( (binder, i) => {
			var slice;
			var mask = svg.mask()
			mask.add(svg.rect(size,size).fill('#fff'))
			if (binder.to == binder.from){
				slice = svg.circle(size - margin*2).move(margin,margin)
			} else {
				var path = `M ${size/2} ${size/2}`;
				var from = timeStringToSeconds(binder.from)/(24.*3600)
				var to = timeStringToSeconds(binder.to)/(24.*3600)
				console.log(from + ' -> ' + to)
				var startAngle = -(from)*2*Math.PI+Math.PI
				var endAngle = -(to)*2*Math.PI+Math.PI
				var x1 = size/2 + Math.sin(startAngle) * (size/2 - margin)
				var y1 = size/2 + Math.cos(startAngle) * (size/2 - margin)
				var x2 = size/2 + Math.sin(endAngle)*(size/2 - margin)
				var y2 = size/2 + Math.cos(endAngle)*(size/2 - margin)
				path += ` L ${x1} ${y1}`
				var arc = ` A ${size/2 - margin} ${size/2 - margin} 0 ${to >= from && to - from > 0.5 || from >= to && to + (1 - from) > 0.5 ? 1 : 0} 1 ${x2} ${y2}`
				path += arc
				
				var sep1 = svg.line(size/2, size/2, x1, y1).stroke({color: '#000', width: 3, linecap: 'round' })
				mask.add(sep1)
				var sep2 = svg.line(size/2, size/2, x2, y2).stroke({color: '#000', width: 3, linecap: 'round' })
				mask.add(sep2)

				slice = svg.path(path)
			}
			
			slice.attr(
			{
				'id' : 'channel-' + channel.id + '-binder-' + i,
				'class' : binder.state
			}).maskWith(mask)
			$('#channel-' + channel.id + '-binder-' + i).on('click', () => {
				$editor = binderEditorDOM(channel, i)
				$('#channel-' + channel.id + '-binders').append($editor)
				$editor.focus()
			})
		})
		//Draw text
		channel.binders.map(binder => binder.from).forEach(time => {
			var angle = -timeStringToSeconds(time)/(24.*3600)*2*Math.PI
			var startAngle = angle - Math.PI/2
			var endAngle = angle + Math.PI/2
			var x1 = size/2 + Math.sin(startAngle) * (size/2)
			var y1 = size/2 + Math.cos(startAngle) * (size/2)
			var x2 = size/2 + Math.sin(endAngle)*(size/2)
			var y2 = size/2 + Math.cos(endAngle)*(size/2)
			var arc = ` A ${size/2} ${size/2} 0 0 1 ${x2} ${y2}`

			var text = svg.text(time).font({
				family: 'Helvetica',
				size: 9,
				anchor: 'middle',
				baseline: 'middle'
			})
			text.path(`M ${x1} ${y1} ${arc}`).textPath().attr('startOffset', '50%')
		})
	}
}

$(document).ready(() => {
	fetch('api/channels', {method:'GET', credentials: 'include'}).then(response => response.json())
	.then(channels => {
		channels.forEach(channel => {
			$('#container').append(channelDOM(channel))
			addBindersEditorDOM(channel)
		})
	})
	}
)