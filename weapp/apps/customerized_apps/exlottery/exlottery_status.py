# -*- coding: utf-8 -*-

import json
from datetime import datetime

from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models import F
from django.contrib.auth.decorators import login_required

from core import resource
from core import paginator
from core.jsonresponse import create_response

import models as app_models
from mall import export
from apps import request_util
from termite import pagestore as pagestore_manager
from modules.member.models import Member
from utils.string_util import byte_to_hex

FIRST_NAV = export.MALL_PROMOTION_AND_APPS_FIRST_NAV
COUNT_PER_PAGE = 20

class ExlotteryStatus(resource.Resource):
	app = 'apps/exlottery'
	resource = 'exlottery_status'

	@login_required
	def api_post(request):
		"""
        响应POST
        """
		target_status = request.POST['target']
		if target_status == 'stoped':
			target_status = app_models.STATUS_STOPED
			now_time = datetime.today().strftime('%Y-%m-%d %H:%M')
			app_models.Exlottery.objects(id=request.POST['id']).update(set__end_time=now_time)
			pagestore = pagestore_manager.get_pagestore('mongo')
			datas = app_models.Exlottery.objects(id=request.POST['id'])
			for data in datas:
				related_page_id = data.related_page_id
			page = pagestore.get_page(related_page_id, 1)
			page['component']['components'][0]['model']['end_time'] = now_time
			pagestore.save_page(related_page_id, 1, page['component'])

		elif target_status == 'running':
			target_status = app_models.STATUS_RUNNING
		elif target_status == 'not_start':
			target_status = app_models.STATUS_NOT_START
		app_models.Exlottery.objects(id=request.POST['id']).update(set__status=target_status)

		response = create_response(200)
		return response.get_response()





