# -*- coding: utf-8 -*-
import json

from datetime import date, datetime

from BeautifulSoup import BeautifulSoup
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models import F
from django.contrib.auth.decorators import login_required
from account.models import UserWeixinPayOrderConfig
from core import resource
from core import paginator
from core.exceptionutil import unicode_full_stack
from core.jsonresponse import create_response
from mall.models import PayInterface
from market_tools.tools.template_message.module_api import send_apps_template_message
import models as app_models
from modules.member.models import Member, MemberHasSocialAccount

PAY_INTERFACE_WEIXIN_PAY = 2 #支付方式为微信支付

class GroupGranter(resource.Resource):
	app = 'apps/group'
	resource = 'group_granter'

	@login_required
	def api_get(request):
		record_id = request.GET.get('record_id', None)
		group_relation_id = request.GET.get('group_relation_id', None)
		member_id = request.GET.get('member_id', None)
		response = create_response(500)
		if not record_id or not member_id or not group_relation_id:
			response.errMsg = u'活动信息出错,请重试~'
			return response.get_response()
		record = app_models.Group.objects(id=record_id)
		if record.count() <=0:
			response.errMsg = u'不存在该团购活动'
			return response.get_response()
		else:
			record = record.first()
		owner_id = record.owner_id
		member_info = app_models.GroupDetail.objects(relation_belong_to=group_relation_id, member_id=member_id, msg_api_status=False)
		if member_info.count() <= 0:
			response.errMsg = u'没有必要给该会员发送模板消息'
			return response.get_response()
		else:
			member_info = member_info.first()
		member_senders_info = member_info.msg_api_failed_members_info
		if not send_apps_template_message(owner_id, member_senders_info):
			response.errMsg = u'发送模板消息失败'
			return response.get_response()
		else:
			response = create_response(200)
			return response.get_response()

	@login_required
	def api_put(request):
		"""
		发送团购模板消息
		"""
		record_id = request.GET.get('record_id', None)
		group_relation_id = request.GET.get('group_relation_id', None)
		member_ids = request.POST.get('member_ids', None)
		response = create_response(500)
		if not record_id or not member_ids or not group_relation_id:
			response.errMsg = u'活动信息出错,请重试~'
			return response.get_response()
		member_ids = member_ids.split(',')
		record = app_models.Group.objects(id=record_id)
		if record.count() <=0:
			response.errMsg = u'不存在该活动'
			return response.get_response()
		else:
			record = record.first()
		owner_id = record.owner_id
		record_name = record.name
		member_info_list = app_models.GroupDetail.objects(
			relation_belong_to=group_relation_id,
			grouped_member_id__in=member_ids,
			is_already_paid=True
		)
		member_id2status = {m.id: m.is_subscribed for m in Member.objects.filter(id__in=member_ids)}
		member_id2openid = {m.member.id: m.account.openid for m in MemberHasSocialAccount.objects.filter(member_id__in=member_ids)}

		if len(member_info_list) <= 0:
			response.errMsg = u'没有符合条件的会员'
			return response.get_response()
		result_data = {}
		member_sets = app_models.GroupDetail.objects(relation_belong_to=group_relation_id)
		for member_info in member_info_list:
			member_id = member_info.member_id
			#非会员不发放
			if not member_id2status[member_id]:
				result_data[member_id] = u'非会员无法发送消息'
				continue
			#获取该member_id的固定openid
			openid = member_id2openid[member_id]
			curr_member_set = member_sets.filter(member_id=member_id)

			#生产环境
			# red = RedPackMessage(weixin_pay_config.partner_id, weixin_pay_config.app_id, nick_name,
			# 	nick_name,openid,price,price,price,1, wishing, ip,
			# 	u"点赞拼大奖红包",
			# 	remark,
			# 	weixin_pay_config.partner_key)
