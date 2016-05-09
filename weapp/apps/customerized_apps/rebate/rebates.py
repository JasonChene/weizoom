# -*- coding: utf-8 -*-
import json
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
from datetime import datetime

FIRST_NAV = export.MALL_PROMOTION_AND_APPS_FIRST_NAV
COUNT_PER_PAGE = 20

class Rebates(resource.Resource):
	app = 'apps/rebate'
	resource = 'rebates'
	
	@login_required
	def get(request):
		"""
		响应GET
		"""
		has_data = app_models.Rebate.objects.count()

		c = RequestContext(request, {
			'first_nav_name': FIRST_NAV,
			'second_navs': export.get_promotion_and_apps_second_navs(request),
			'second_nav_name': export.MALL_APPS_SECOND_NAV,
            'third_nav_name': export.MALL_APPS_REBATE_NAV,
			'has_data': has_data
		})
		
		return render_to_response('rebate/templates/editor/rebates.html', c)
	
	@staticmethod
	def get_datas(request):
		name = request.GET.get('name', '')
		status = int(request.GET.get('status', -1))
		start_time = request.GET.get('start_time', '')
		end_time = request.GET.get('end_time', '')
		
		now_time = datetime.today().strftime('%Y-%m-%d %H:%M')
		params = {'owner_id':request.manager.id,'is_deleted': False}
		datas_datas = app_models.Rebate.objects(**params)
		for data_data in datas_datas:
			data_start_time = data_data.start_time.strftime('%Y-%m-%d %H:%M')
			data_end_time = data_data.end_time.strftime('%Y-%m-%d %H:%M')
			if data_start_time <= now_time and now_time < data_end_time:
				data_data.update(set__status=app_models.STATUS_RUNNING)
			elif now_time >= data_end_time:
				data_data.update(set__status=app_models.STATUS_STOPED)
		if name:
			params['name__icontains'] = name
		if status != -1:
			params['status'] = status
		if start_time:
			params['start_time__gte'] = start_time
		if end_time:
			params['end_time__lte'] = end_time
		datas = app_models.Rebate.objects(**params).order_by('-id')

		#进行分页
		count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
		cur_page = int(request.GET.get('page', '1'))
		pageinfo, datas = paginator.paginate(datas, cur_page, count_per_page, query_string=request.META['QUERY_STRING'])
		
		return pageinfo, datas

	@login_required
	def api_get(request):
		"""
		响应API GET
		"""
		pageinfo, datas = Rebates.get_datas(request)
		items = []
		#TODO 三个数值
		attention_number = 0
		order_money = 0.00
		first_buy_num = 0
		for data in datas:
			str_id = str(data.id)
			items.append({
				'id': str_id,
				'owner_id': data.owner_id,
				'name': data.name,
				'attention_number': attention_number,
				'order_money': order_money,
				'first_buy_num': first_buy_num,
				'start_time': data.start_time.strftime('%Y-%m-%d %H:%M'),
				'end_time': data.end_time.strftime('%Y-%m-%d %H:%M'),
				'status': data.status_text,
				'ticket': data.ticket,
				'created_at': data.created_at.strftime("%Y-%m-%d %H:%M:%S")
			})
		response_data = {
			'items': items,
			'pageinfo': paginator.to_dict(pageinfo),
			'sortAttr': 'id',
			'data': {}
		}
		response = create_response(200)
		response.data = response_data
		return response.get_response()
