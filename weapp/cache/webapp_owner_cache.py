# -*- coding: utf-8 -*-

import time
from datetime import timedelta, datetime, date
import urllib, urllib2
import os
import json
import shutil

from django.conf import settings
from django.contrib.auth.models import User

from utils import cache_util
import cache
from mall import models as mall_models
from modules.member import models as member_models
from weixin.user import models as weixin_user_models
from webapp import models as webapp_models
from account import models as account_models

from core.exceptionutil import unicode_full_stack
from watchdog.utils import watchdog_error
from market_tools.tools.weizoom_card.models import AccountHasWeizoomCardPermissions


local_cache = {}


def get_webapp_owner_info_from_db(webapp_owner_id):
	def inner_func():
		#user profile
		user_profile = account_models.UserProfile.objects.get(user_id=webapp_owner_id)
		webapp_id = user_profile.webapp_id

		#mpuser preview info
		try:
			mpuser = weixin_user_models.WeixinMpUser.objects.get(owner_id=webapp_owner_id)
			mpuser_preview_info = weixin_user_models.MpuserPreviewInfo.objects.get(mpuser=mpuser)
			try:
				weixin_mp_user_access_token = weixin_user_models.WeixinMpUserAccessToken.objects.get(mpuser=mpuser)
			except:
				weixin_mp_user_access_token = weixin_user_models.WeixinMpUserAccessToken()
		except:
			error_msg = u"获得user('{}')对应的mpuser_preview_info构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			mpuser_preview_info = weixin_user_models.MpuserPreviewInfo()
			weixin_mp_user_access_token = weixin_user_models.WeixinMpUserAccessToken()
			mpuser = weixin_user_models.WeixinMpUser()

		#webapp
		try:
			webapp = webapp_models.WebApp.objects.get(owner_id=webapp_owner_id)
		except:
			error_msg = u"获得user('{}')对应的webapp构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			webapp = webapp_models.WebApp()

		#integral strategy
		try:
			integral_strategy_settings = member_models.IntegralStrategySttings.objects.get(webapp_id=webapp_id)
		except:
			error_msg = u"获得user('{}')对应的IntegralStrategySttings构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			integral_strategy_settings = member_models.IntegralStrategySttings()

		#member grade
		try:
			member_grades = [member_grade.to_dict() for member_grade in member_models.MemberGrade.objects.filter(webapp_id=webapp_id)]
		except:
			error_msg = u"获得user('{}')对应的MemberGrade构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			member_grades = []

		#pay interface
		try:
			pay_interfaces = [pay_interface.to_dict() for pay_interface in mall_models.PayInterface.objects.filter(owner_id=webapp_owner_id)]
		except:
			error_msg = u"获得user('{}')对应的PayInterface构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			pay_interfaces = []

		# 微众卡权限
		has_permission = AccountHasWeizoomCardPermissions.is_can_use_weizoom_card_by_owner_id(webapp_owner_id)

		try:
			operation_settings = account_models.OperationSettings.get_settings_for_user(webapp_owner_id)
		except:
			error_msg = u"获得user('{}')对应的OperationSettings构建cache失败, cause:\n{}"\
					.format(webapp_owner_id, unicode_full_stack())
			watchdog_error(error_msg, user_id=webapp_owner_id, noraise=True)
			operation_settings = {}
		return {
			'value': {
				'weixin_mp_user_access_token': weixin_mp_user_access_token.to_dict(),
				"mpuser_preview_info": mpuser_preview_info.to_dict(),
				'webapp': webapp.to_dict(),
				'user_profile': user_profile.to_dict(),
				'mpuser': mpuser.to_dict(),
				'integral_strategy_settings': integral_strategy_settings.to_dict(),
				'member_grades': member_grades,
				'pay_interfaces': pay_interfaces,
				'has_permission': has_permission,
				'operation_settings': operation_settings.to_dict(),
			}
		}
	return inner_func

class Object(object):
	def __init__(self):
		pass

def get_webapp_owner_info(webapp_owner_id):
	key = 'webapp_owner_info_{wo:%s}' % webapp_owner_id
	data = cache_util.get_from_cache(key, get_webapp_owner_info_from_db(webapp_owner_id))
	obj = Object()
	obj.mpuser_preview_info = weixin_user_models.MpuserPreviewInfo.from_dict(data['mpuser_preview_info'])
	obj.app = webapp_models.WebApp.from_dict(data['webapp'])

	obj.user_profile = account_models.UserProfile.from_dict(data['user_profile'])
	obj.mpuser = weixin_user_models.WeixinMpUser.from_dict(data['mpuser'])
	obj.weixin_mp_user_access_token = weixin_user_models.WeixinMpUserAccessToken.from_dict(data['weixin_mp_user_access_token'])
	obj.integral_strategy_settings = member_models.IntegralStrategySttings.from_dict(data['integral_strategy_settings'])
	obj.member_grades = member_models.MemberGrade.from_list(data['member_grades'])
	obj.member2grade = dict([(grade.id, grade) for grade in obj.member_grades])
	obj.pay_interfaces = mall_models.PayInterface.from_list(data['pay_interfaces'])
	obj.is_weizoom_card_permission = data['has_permission']
	obj.operation_settings = account_models.OperationSettings.from_dict(data['operation_settings'])
	return obj



from django.dispatch.dispatcher import receiver
from django.db.models import signals
from weapp.hack_django import post_update_signal
#######################################################################
# update_webapp_owner_info_cache: 更新webapp_owner_info cache
#     该函数会在后台编辑时被调用
#######################################################################
def update_webapp_owner_info_cache_with_login(instance, **kwargs):
	if isinstance(instance, account_models.UserProfile):
		webapp_owner_id = instance.user_id
	elif isinstance(instance, AccountHasWeizoomCardPermissions):
		webapp_owner_id = instance.owner_id
	else:
		if cache.request.user_profile:
			webapp_owner_id = cache.request.user_profile.user_id
		else:
			return
	key = 'webapp_owner_info_{wo:%s}' % webapp_owner_id
	cache_util.delete_cache(key)
	get_webapp_owner_info(webapp_owner_id)


post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=weixin_user_models.MpuserPreviewInfo, dispatch_uid = "mpuser_preview_info.update")
signals.post_save.connect(update_webapp_owner_info_cache_with_login, sender=weixin_user_models.MpuserPreviewInfo, dispatch_uid = "mpuser_preview_info.save")
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=member_models.IntegralStrategySttings, dispatch_uid = "integral_strategy_settings.update")
signals.post_save.connect(update_webapp_owner_info_cache_with_login, sender=member_models.IntegralStrategySttings, dispatch_uid = "integral_strategy_settings.save")
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=member_models.MemberGrade, dispatch_uid = "member_grade.update")
signals.post_save.connect(update_webapp_owner_info_cache_with_login, sender=member_models.MemberGrade, dispatch_uid = "member_grade.save")
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=webapp_models.WebApp, dispatch_uid = "webapp.update")
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=account_models.UserProfile, dispatch_uid = "user_profile.update")
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=weixin_user_models.WeixinMpUser, dispatch_uid = "weixin_mp_user.update")
#pay interface
post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=mall_models.PayInterface, dispatch_uid = "PayInterface.update")
signals.post_save.connect(update_webapp_owner_info_cache_with_login, sender=mall_models.PayInterface, dispatch_uid = "PayInterface.save")

post_update_signal.connect(update_webapp_owner_info_cache_with_login, sender=account_models.OperationSettings, dispatch_uid = "OperationSettings.update")
signals.post_save.connect(update_webapp_owner_info_cache_with_login, sender=account_models.OperationSettings, dispatch_uid = "OperationSettings.save")
signals.post_save.connect(
                          update_webapp_owner_info_cache_with_login,
                          sender=AccountHasWeizoomCardPermissions,
                          dispatch_uid="accounthwzcp.save")
post_update_signal.connect(update_webapp_owner_info_cache_with_login,
                           sender=AccountHasWeizoomCardPermissions,
                           dispatch_uid="accountwzcp.update")
