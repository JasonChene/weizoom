# -*- coding: utf-8 -*-
# __author__='justing'
import json
import time

from behave import *

from test import bdd_util
from features.testenv.model_factory import *

from django.test.client import Client

@when(u"{user}已删除图文'{news_title}'")
def step_impl(context, user, news_title):
    materials_url = '/new_weixin/api/materials/'
    response = context.client.get(bdd_util.nginx(materials_url))
    newses_info = json.loads(response.content)['data']['items']
    for news_info in newses_info:
        if news_info['newses'][0]['title'] == news_title:
            material_id = news_info['id']
            material_type = news_info['type']
    url = '/new_weixin/api/%s_news/?_method=delete' % material_type
    response = context.client.post(url, {'id': material_id})

@when(u"{user}设置图文列表的查询条件")
def step_impl(context, user):
    query = json.loads(context.text)['title']
    context.url = '/new_weixin/api/materials/?sort_attr=-created_at&query=%s' %query