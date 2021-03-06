# -*- coding: utf-8 -*-

import json
from datetime import datetime

from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

from core import resource
from core.jsonresponse import create_response
from utils.cache_util import delete_cache

import models as app_models
import export
from mall import export as mall_export
from apps import request_util
from modules.member import integral as integral_api
from mall.promotion import utils as mall_api


FIRST_NAV = mall_export.MALL_PROMOTION_AND_APPS_FIRST_NAV
COUNT_PER_PAGE = 20

class Sign(resource.Resource):
	app = 'apps/sign'
	resource = 'sign'

	@login_required
	def get(request):
		"""
		响应GET
		"""
		owner_id = request.manager.id
		sign = app_models.Sign.objects(owner_id=owner_id)
		if sign.count()>0:
			sign = sign[0]
			is_create_new_data = False
			project_id = 'new_app:sign:%s' % sign.related_page_id
			keywords = sign.reply['keyword']
			# keywords = {}
		else:
			sign = None
			is_create_new_data = True
			project_id = 'new_app:sign:0'
			keywords = {}

		c = RequestContext(request, {
			'first_nav_name': FIRST_NAV,
			'second_navs': mall_export.get_promotion_and_apps_second_navs(request),
			'second_nav_name': mall_export.MALL_APPS_SECOND_NAV,
			'third_nav_name': mall_export.MALL_APPS_SIGN_NAV,
			'sign': sign,
			'is_create_new_data': is_create_new_data,
			'project_id': project_id,
			'webapp_owner_id': owner_id,
			'keywords': json.dumps(keywords)
		})

		return render_to_response('sign/templates/editor/workbench.html', c)

	@login_required
	def api_get(request):
		"""
		响应Api_GET
		"""
		owner_id = request.manager.id
		sign = app_models.Sign.objects(owner_id=owner_id)
		if sign.count()>0:
			sign = sign[0]
			keywords = sign.reply['keyword']
			# keywords = {}
		else:
			keywords = {}

		response = create_response(200)
		response.data = keywords #{'keyword1':'blur','keyword2':'accurate'}
		return response.get_response()


	@login_required
	def api_put(request):
		"""
		响应PUT
		"""
		data = export.get_sing_fields_to_save(request)
		status = request.POST['status']
		if status:
			data['status'] = 0 if status == 'off' else 1
		data['related_page_id'] = request.POST['related_page_id']
		sign = app_models.Sign(**data)
		sign.save()

		error_msg = None

		data = json.loads(sign.to_json())
		data['id'] = data['_id']['$oid']
		if error_msg:
			data['error_msg'] = error_msg
		response = create_response(200)
		response.data = data
		return response.get_response()

	@login_required
	def api_post(request):
		"""
		响应POST
		"""
		if request.POST.get('status', None):
			status = 1 if request.POST['status'] == 'on' else 0
			signs = app_models.Sign.objects(id=request.POST['signId'])
			signs.update(set__status=status)
			if status == 1 and signs.count() >0:
				#将所有已签到用户的签到状态重置，作为一个新的签到
				sign = signs[0]
				app_models.SignParticipance.objects(belong_to=str(sign.id)).update(set__serial_count=0, set__latest_date=None)
				# app_models.SignControl.objects.all().delete()
			cache_key = 'apps_sign_%s_html' % str(signs[0].owner_id)
		else:
			data = export.get_sing_fields_to_save(request)
			update_data = {}
			update_fields = set(['name', 'share', 'reply', 'prize_settings'])
			for key, value in data.items():
				if key in update_fields:
					update_data['set__'+key] = value
			sign = app_models.Sign.objects(id=request.POST['signId']).first()
			sign.update(**update_data)
			cache_key = 'apps_sign_%s_html' % sign.owner_id
		#更新后清除redis缓存
		delete_cache(cache_key)

		response = create_response(200)
		return response.get_response()
