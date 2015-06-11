# -*- coding: utf-8 -*-
import json
import time

from behave import *

from test import bdd_util
from features.testenv.model_factory import *

from django.test.client import Client
from mall.models import *
from tools.regional.models import Province


def _get_province_ids(province_names):
	ids = []
	province_names = province_names.split(',')
	for province_name in province_names:
		province = Province.objects.get(name=province_name)
		ids.append(str(province.id))
	return ids


def _get_post_data_postage(postage):
	postage['firstWeight'] = postage['first_weight']
	postage['firstWeightPrice'] = postage['first_weight_price']
	postage['addedWeight'] = postage.get('added_weight', '0')
	postage['addedWeightPrice'] = postage.get('added_weight_price', '0')
	
	if 'special_area' in postage:
		postage['isEnableSpecialConfig'] = 'true'
		special_configs = []
		for data in postage.get('special_area'):
			special_config = {
				"id": -1,
				"firstWeight": data.get('first_weight', "1.0"),
				"firstWeightPrice": data.get('first_weight_price', "1.0"),
				"addedWeight": data.get('added_weight', "1.0"),
				"addedWeightPrice": data.get('added_weight_price', "1.0")
			}
			special_config['destination'] = _get_province_ids(data.get('to_the', ''))
			special_configs.append(special_config)
		postage['specialConfigs'] = json.dumps(special_configs)
	else:
		postage['isEnableSpecialConfig'] = 'false'
		postage['specialConfigs'] = "[]"

	if 'free_postages' in postage:
		postage['isEnableFreeConfig'] = 'true'
		free_postages = []
		for data in postage.get('free_postages'):
			free_postage = {
				"id": -1,
				"condition": data['condition'],
				"value": data['value']
			}
			free_postage['destination'] = _get_province_ids(data.get('to_the', ''))
			free_postages.append(free_postage)
		postage['freeConfigs'] = json.dumps(free_postages)
	else:
		postage['isEnableFreeConfig'] = 'false'
		postage['freeConfigs'] = "[]"

	return postage


def _get_special_area_for_config(postage_config):
	special_areas = json.loads(postage_config.values_json_str)
	if special_areas:
		postage_config.special_area = []
		for special_area in special_areas:
			province = ','.join([p['name'] for p in special_area['province']])
			postage_config.special_area.append({
				'to_the': province,
				'first_weight_price': special_area['first_weight_price'],
				'added_weight_price': special_area['added_weight_price']
			})
	else:
		postage_config.special_area = []


@when(u"{user}添加邮费配置")
def step_impl(context, user):
	client = context.client
	context.postages = json.loads(context.text)
	spcial_area_index = -1
	for postage in context.postages:
		data = _get_post_data_postage(postage)
		response = client.post('/mall/api/postage_template/create/', data)
		bdd_util.assert_api_call_success(response)
		time.sleep(0.2)


@when(u"{user}已添加了邮费配置")
def step_impl(context, user):
	client = context.client
	context.postages = json.loads(context.text)
	spcial_area_index = -1
	for postage in context.postages:
		data = _get_post_data_postage(postage)
		response = client.post('/mall/editor/postage_config/create/', data)


@then(u"{user}能获取添加的邮费配置")
def step_impl(context, user):
	if hasattr(context, 'client'):
		context.client.logout()
	context.client = bdd_util.login(user)
	client = context.client
	
	response = context.client.get('/mall/postage_templates/get/')

	actual =response.context['postage_configs']
	#for config in actual:
		# if config.added_weight:
		# 	config.added_weight = float(config.added_weight)
		# if config.added_weight_price:
		# 	config.added_weight_price = float(config.added_weight_price)

		# #获取special area
		# update_response = context.client.get('/mall/editor/postage_config/update/%d/' % config.id)
		# postage_config = update_response.context['postage_config']
		# _get_special_area_for_config(postage_config)
		# config.special_area = postage_config.special_area

	expected = json.loads(context.text)
	bdd_util.assert_list(expected, actual)


@when(u"{user}修改'{postage_name}'运费配置")
def step_impl(context, user, postage_name):
	context.postages = json.loads(context.text)
	for postage in context.postages:
		data = _get_post_data_postage(postage)
		config = PostageConfig.objects.get(name=data['name'])
		data['id'] = config.id

		response = context.client.post('/mall/api/postage_template/update/', data)


@then(u"{user}能获取'{postage_name}'运费配置")
def step_impl(context, user, postage_name):
	config = PostageConfig.objects.get(name=postage_name)
	response = context.client.get('/mall/postage_template/edit/?id=%d' % config.id)
	actual = response.context['postage_config']

	expecteds = json.loads(context.text)
	for postage in expecteds:
		bdd_util.assert_dict(postage, actual)


@given(u"{user}已添加运费配置")
def step_impl(context, user):
	client = context.client
	context.postages = json.loads(context.text)
	spcial_area_index = -1
	for postage in context.postages:
		data = _get_post_data_postage(postage)
		response = client.post('/mall/api/postage_template/create/', data)


@when(u"{user}选择'{postage_name}'运费配置")
def step_impl(context, user, postage_name):
	print '*' * 60
	print context.client.user.id, postage_name
	print '*' * 60
	config = PostageConfig.objects.get(name=postage_name, owner_id=context.client.user.id)
	data = {'id': config.id }
	response = context.client.post('/mall/api/used_postage_template/create/', data)
