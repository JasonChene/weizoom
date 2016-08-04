# -*- coding: utf-8 -*-

__author__ = 'aix'

import os

from django.template import Context, RequestContext
from django.shortcuts import render_to_response

from mall.promotion.card_exchange import CardExchange
from modules.member.models import MemberInfo
from mall.promotion import models as promotion_models
from market_tools.tools.weizoom_card import models as card_models

template_path_items = os.path.dirname(__file__).split(os.sep)
TEMPLATE_DIR = '%s/templates' % template_path_items[-1]

COUNT_PER_PAGE = 15
def get_page(request):
	"""
	手机端推广分销页面
	"""
	webapp_id = request.user_profile.webapp_id
	member_id = request.member.id
	c = RequestContext(request, {

	})

	return render_to_response('%s/distribution/webapp/xxx.html' % TEMPLATE_DIR, c)