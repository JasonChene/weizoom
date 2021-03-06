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
from mall import export as mall_export
from modules.member.models import Member
from core.exceptionutil import unicode_full_stack
from apps.customerized_apps.shvote.m_shvote import update_shvote_status
from m_shvote import _get_rank

FIRST_NAV = mall_export.MALL_PROMOTION_AND_APPS_FIRST_NAV
COUNT_PER_PAGE = 20

class ShvoteParticipance(resource.Resource):
	app = 'apps/shvote'
	resource = 'shvote_participance'

	def get(request):
		"""
		响应GET
		"""
		record = None
		isMember = False
		is_already_participanted = False
		member = request.member
		mpUserPreviewName = None
		if 'id' in request.GET:
			participance_data_count = 0
			id = request.GET['id']
			try:
				record = app_models.Shvote.objects.get(id=id)
				activity_status, record = update_shvote_status(record)
				#获取公众号昵称
				mpUserPreviewName = request.webapp_owner_info.auth_appid_info.nick_name
				if member:
					isMember = member.is_subscribed
					participance_data = app_models.ShvoteParticipance.objects(belong_to=id, member_id=member.id)
					if participance_data.count() > 0:
						participance_data = participance_data.first()
						if participance_data.is_use == app_models.MEMBER_IS_USE['YES']:
							is_already_participanted = True

			except:
				c = RequestContext(request,{
					'is_deleted_data': True
				})
				return render_to_response('shvote/templates/webapp/m_shvote.html', c)
			c = RequestContext(request, {
				'record_id': id,
				'page_title': u"投票活动",
				'groups': json.dumps(record.groups),
				'activity_status': activity_status,
				'is_already_participanted': is_already_participanted,
				'isMember': isMember,
				'app_name': "shvote",
				'resource': "shvote",
				'is_hide_weixin_option_menu':True,
				'share_page_title': mpUserPreviewName if mpUserPreviewName else record.name,
				'share_img_url': record.share_image if record else '',
				"share_page_desc": record.name if record else '',
				'hide_non_member_cover': True, #非会员也可使用该页面
				'share_to_timeline_use_desc': True  #分享到朋友圈的时候信息变成分享给朋友的描述
			})
			return render_to_response('shvote/templates/webapp/m_shvote_participance.html', c)
		else:
			c = RequestContext(request, {
				'record': record
			})
			return render_to_response('shvote/templates/webapp/m_shvote.html', c)
	
	def api_put(request):
		"""
		响应PUT
		"""
		try:
			member_id = request.member.id
			record_id = request.POST['belong_to']
			post = request.POST
			all_participances = app_models.ShvoteParticipance.objects(belong_to=record_id,is_use=app_models.MEMBER_IS_USE['YES'])
			serial_number_valid = True
			for participance in all_participances:
				if post["serial_number"] == participance.serial_number:
					serial_number_valid = False
			if serial_number_valid:
				#如果曾经报名过，但是审核不通过，可以再次报名
				sh_participance_is_use = app_models.ShvoteParticipance.objects(belong_to=record_id,member_id=member_id,is_use=app_models.MEMBER_IS_USE['NO'])
				if sh_participance_is_use.count() > 0 :
					sh_participance_is_use.first().update(
						belong_to = record_id,
						member_id = member_id,
						icon = post["icon"],
						name = post["name"],
						group = post["group"],
						serial_number = post["serial_number"],
						details = post["details"],
						pics = json.loads(post["pics"]),
						is_use = app_models.MEMBER_IS_USE['YES'],
						created_at = datetime.now()
					)
					response = create_response(200)
				else:
					try:
						sh_participance = app_models.ShvoteParticipance(
							belong_to = record_id,
							member_id = member_id,
							icon = post["icon"],
							name = post["name"],
							group = post["group"],
							serial_number = post["serial_number"],
							details = post["details"],
							pics = json.loads(post["pics"]),
							created_at = datetime.now()
						)
						sh_participance.save()
						response = create_response(200)
					except:
						response = create_response(500)
						response.errMsg = u'您已报过名'
				return response.get_response()
			else:
				response = create_response(500)
				response.errMsg = u'该选手编号已经存在'
				return response.get_response()
		except:
			response = create_response(500)
			response.errMsg = u'报名失败'
			response.inner_errMsg = unicode_full_stack()
			return response.get_response()

	def api_post(request):
		"""
		投票
		"""
		vote_to = request.POST.get('vote_to', None)
		member = request.member
		response = create_response(500)
		if not member:
			response.errMsg = u'会员信息出错'
			return response.get_response()
		record_id = request.POST.get('recordId', None)
		member_id = member.id
		#非会员不能投票
		if not member.is_subscribed:
			response.errMsg = 'none_member'
			return response.get_response()
		#不能给取消关注的会员投票
		try:
			sh = app_models.ShvoteParticipance.objects.get(id=vote_to)
			if sh.member_id > 0:
				target_member = Member.objects.get(id=sh.member_id)
				if not target_member.is_subscribed:
					response.errMsg = u'该用户已退出投票活动'
					return response.get_response()
		except:
			response.errMsg = u'不存在该用户'
			return response.get_response()

		record = app_models.Shvote.objects(id=record_id)
		if record.count() > 0:
			if record.first().status == app_models.STATUS_STOPED:
				response.errMsg = u'该投票活动已经结束'
				return response.get_response()
			can_vote_count = record.first().votecount_per_one
		else:
			response.errMsg = u'该投票活动已被删除'
			return response.get_response()

		now_date_str = datetime.now().strftime('%Y-%m-%d')
		control = app_models.ShvoteControl.objects(
			created_at_str = now_date_str,
			member_id = member_id,
			belong_to = record_id
		)
		if control.count() > 0:
			control = control.first()
		else:
			control = app_models.ShvoteControl(
				created_at_str = now_date_str,
				member_id = member_id,
				belong_to = record_id
			)
			control.save()

		result = control.modify(query={"vote_count__lt": can_vote_count, "vote_to_list__ne": vote_to},
					   **{"inc__vote_count": 1, "push__vote_to_list": vote_to})
		if not result:
			response.errMsg = u'达到投票次数限制'
			return response.get_response()

		try:
			target = app_models.ShvoteParticipance.objects.get(belong_to=record_id, id=vote_to, status=app_models.MEMBER_STATUS['PASSED'])
			target.count += 1
			if target.vote_log.has_key(now_date_str):
				target.vote_log[now_date_str].append(member_id)
			else:
				target.vote_log[now_date_str] = [member_id]
			target.save()
			vote_detail = app_models.ShvoteDetail(
				member_id = member_id,
				belong_to = record_id,
				vote_to_member_id = vote_to,
				created_at = datetime.now()
			)
			vote_detail.save()
		except:
			response.errMsg = u'用户信息出错'
			return response.get_response()

		# result = target.modify(query={'vote_log__'+now_date_str+'__not__exists': member_id},
		# 					   **{
		# 						   'inc__count': 1,
		# 						   'push__vote_log__'+now_date_str: member_id
		# 					   })
		# if not result:
		# 	response.errMsg = u'只能投票一次'
		# 	return response.get_response()

		response = create_response(200)
		response.data = {"rank": _get_rank(target.id).rank}
		return response.get_response()


class ShvoteParticipancesDialog(resource.Resource):
	app = 'apps/shvote'
	resource = 'shvote_participances_dialog'

	def api_get(request):
		"""
		响应GET
		"""
		items = []
		if 'id' in request.GET:
			try:
				# old_player_details是为了兼容旧数据的展示
				old_player_details = app_models.ShvoteParticipance.objects.get(id=request.GET['id'])
				player_details = app_models.ShvoteDetail.objects(vote_to_member_id=request.GET['id'])
			except:
				response = create_response(500)
				response.errMsg = u'选手信息出错，请稍后再试！'
				return response.get_response()

			if player_details:
				first_detail_time_str = player_details.first().created_at.strftime('%Y-%m-%d')
			else:
				first_detail_time_str = ''
			if old_player_details:
				vote_log = old_player_details.vote_log
				if vote_log:
					for created_at,member_ids in vote_log.items():
						if first_detail_time_str!= '':
							#有player_details记录，只取时间节点（first_detail_time_str）之前的部分
							if created_at < first_detail_time_str:
								old_player_member_info = Member.objects.filter(id__in=member_ids)
								for member_id in member_ids:
									try:
										member = old_player_member_info.get(id=member_id)
										member_name = member.username_for_html
									except:
										member_name = u'未知'
									items.append({
										'created_at': created_at,
										'name': member_name
									})
						else:#没有player_details记录，全部取出
							old_player_member_info = Member.objects.filter(id__in=member_ids)
							for member_id in member_ids:
								try:
									member = old_player_member_info.get(id=member_id)
									member_name = member.username_for_html
								except:
									member_name = u'未知'
								items.append({
									'created_at': created_at,
									'name': member_name
								})
			if player_details:
				member_ids = [p.member_id for p in player_details]
				member_info = Member.objects.filter(id__in=member_ids)
				for player_detail in player_details:
					try:
						member = member_info.get(id=player_detail.member_id)
						member_name = member.username_for_html
					except:
						member_name = u'未知'
					items.append({
						'created_at': player_detail.created_at.strftime('%Y-%m-%d %H:%M:%S'),
						'name': member_name
					})

		count_per_page = int(request.GET.get('count_per_page', 1))
		cur_page = int(request.GET.get('page', '1'))
		pageinfo, items = paginator.paginate(items, cur_page, count_per_page, query_string=request.META['QUERY_STRING'])

		response_data = {
			'items': items,
			'pageinfo': paginator.to_dict(pageinfo),
		}
		response = create_response(200)
		response.data = response_data
		return response.get_response()
