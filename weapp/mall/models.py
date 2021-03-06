# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
from datetime import datetime, timedelta

# from hashlib import md5
import json

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models import F, Sum, Q
# from django.db.models import signals
from django.conf import settings
from django.dispatch.dispatcher import receiver
from django.utils.functional import cached_property

from utils import area_util
from core.alipay.alipay_notify import AlipayNotify
# from core.alipay.alipay_submit import AlipaySubmit
from core.tenpay.tenpay_submit import TenpaySubmit
# from core import upyun_util
from core.wxpay.wxpay_notify import WxpayNotify
from account.models import UserAlipayOrderConfig,UserProfile
from account import models as account_models
from core.exceptionutil import unicode_full_stack
from watchdog.utils import *
from tools.express import util as express_util
from . import signals as mall_signals


MALL_CONFIG_PRODUCT_COUNT_NO_LIMIT = 999999999
MALL_CONFIG_PRODUCT_NORMAL = 7


class MallConfig(models.Model):
	owner = models.ForeignKey(User, related_name='mall_config')
	max_product_count = models.IntegerField(
		default=MALL_CONFIG_PRODUCT_NORMAL)  # 最大商品数量
	is_enable_bill = models.BooleanField(default=False)  # 是否启用发票功能
	show_product_sales = models.BooleanField(default=False) # 通用设置，商品销量
	show_product_sort = models.BooleanField(default=False) # 通用设置，销量排行
	show_product_search = models.BooleanField(default=False) # 通用设置， 商品搜索框
	show_shopping_cart =models.BooleanField(default=False) # 通用设置， 购物车
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# new add at 13  by bert
	order_expired_day = models.IntegerField(default=0)  # 未付款订单过期时间(单位是小时)

	class Meta(object):
		db_table = 'mall_config'
		verbose_name = '商城配置'
		verbose_name_plural = '商城配置'

	@staticmethod
	def set_max_product_count_for(user, max_product_count):
		if user is None or max_product_count < 0:
			return

		MallConfig.objects.filter(owner=user).update(
			max_product_count=max_product_count
			)

	@staticmethod
	def get_order_expired_day(user):
		if user is None:
			return -1

		if MallConfig.objects.filter(owner=user).count() > 0:
			return MallConfig.objects.filter(owner=user)[0].order_expired_day


class MallCounter(models.Model):

	"""
	商城计数器
	"""
	owner = models.ForeignKey(User, related_name="mall_counter")
	unread_order_count = models.IntegerField(default=0)  # 新订单个数

	class Meta(object):
		db_table = 'mall_counter'
		verbose_name = '商城计数器'
		verbose_name_plural = '商城计数器'

	@staticmethod
	def increase_unread_order(webapp_owner_id, count):
		MallCounter.objects.filter(
			owner_id=webapp_owner_id).update(
			unread_order_count=F('unread_order_count') +
			count)

	@staticmethod
	def clear_unread_order(webapp_owner_id):
		MallCounter.objects.filter(
			owner_id=webapp_owner_id).update(
			unread_order_count=0)

class MallShareOrderPageConfig(models.Model):
	"""
	订单完成分享挣积分信息配置
	"""
	owner = models.ForeignKey(User)
	is_share_page = models.BooleanField(default=False) # 是否提示分享挣积分
	background_image = models.CharField(max_length=1024, default='')
	share_image = models.CharField(max_length=1024, default='')
	share_describe = models.TextField(default='')
	material_id = models.IntegerField(default=0) #图文素材id
	news_id = models.IntegerField(default=0) #图文id
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_share_order_page_config'
		verbose_name = '订单完成分享挣积分信息配置'
		verbose_name_plural = '订单完成分享挣积分信息配置'


def increase_unread_order(webapp_owner_id, count):
	"""
	未读订单数加1
	"""
	records = MallCounter.objects.filter(owner_id=webapp_owner_id)
	if records.count()>0:
		records.update(unread_order_count=F('unread_order_count')+count)
	else:
		MallCounter.objects.create(owner_id=webapp_owner_id, unread_order_count=count).save()

NO_LIMIT = 0  # 不限制
FORBIDDEN_SALE_LIMIT = 1  # 禁售
ONLY_SALE_LIMIT = 2  # 仅售

PRE_PRODUCT_STATUS = {
	'NOT_YET': 0,  # 尚未提交审核
	'SUBMIT': 1,  # 提交审核
	'REFUSED': 2  # 驳回
}

class ProductUnverified(models.Model):
	"""
	未审核的商品信息

	表名：mall_product_unverified
	"""
	product_id = models.IntegerField(default=-1) #商品id
	product_data = models.TextField() #商品信息

	class Meta(object):
		db_table = 'mall_product_unverified'
		

# MODULE START: productcategory
class ProductCategory(models.Model):

	"""
	商品分类
	"""
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=256)  # 分类名称
	pic_url = models.CharField(max_length=1024, default='')  # 分类图片
	product_count = models.IntegerField(default=0)  # 包含商品数量
	display_index = models.IntegerField(default=1, db_index=True)  # 显示的排序
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_category'
		verbose_name = '商品分类'
		verbose_name_plural = '商品分类'

class ProductRefuseLogs(models.Model):
	"""
	审核商品驳回日志
	"""
	product_id = models.IntegerField(default=-1)  # 商品id
	refuse_reason = models.CharField(max_length=1024, default='')  # 驳回原因
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_product_refuse_logs'


class ProductCustomizedPrice(models.Model):
	corp_id = models.IntegerField(default=-1) #corp id
	product_id = models.IntegerField(default=-1)#product id
	product_model_id = models.IntegerField(default=-1) #ProductModel id
	price = models.FloatField(default=0.0)

	class Meta(object):
		db_table = 'mall_product_customized_price'

# MODULE START: product
#########################################################################
# Product：商品
#########################################################################
PRODUCT_STOCK_TYPE_LIMIT = 1
PRODUCT_STOCK_TYPE_UNLIMIT = 0
PRODUCT_SHELVE_TYPE_ON = 1
PRODUCT_SHELVE_TYPE_OFF = 0
PRODUCT_SHELVE_TYPE_RECYCLED = 2
PRODUCT_DEFAULT_TYPE = 'object'
PRODUCT_DELIVERY_PLAN_TYPE = 'delivery'
PRODUCT_TEST_TYPE = 'test'
PRODUCT_INTEGRAL_TYPE = 'integral'
PRODUCT_VIRTUAL_TYPE = 'virtual'  #第三方虚拟商品  weshop
PRODUCT_WZCARD_TYPE = 'wzcard'  #电子微众卡  weshop
PRODUCT_ENTITY_WZCARD_TYPE = 'wzcard_entity'  #实体微众卡  weshop
POSTAGE_TYPE_UNIFIED = 'unified_postage_type'
POSTAGE_TYPE_CUSTOM = 'custom_postage_type'

PRODUCT_TYPE2TEXT = {
	PRODUCT_DEFAULT_TYPE: u'普通商品',
	PRODUCT_DELIVERY_PLAN_TYPE: u'套餐商品',
	PRODUCT_INTEGRAL_TYPE: u'积分商品'
}
MAX_INDEX = 2**16 - 1

PRODUCT_STATUS = {
	'NOT_YET': 0, #尚未提交审核
	'SUBMIT': 1, #提交审核
	'REFUSED': 2 #驳回
}


class Product(models.Model):
	"""
	商品

	表名：mall_product
	"""
	owner = models.ForeignKey(User, related_name='user-product')
	name = models.CharField(max_length=256)  # 商品名称
	physical_unit = models.CharField(default='', max_length=256)  # 计量单位
	price = models.FloatField(default=0.0)  # 商品价格
	introduction = models.CharField(max_length=256)  # 商品简介
	weight = models.FloatField(default=0.0)  # 重量
	thumbnails_url = models.CharField(max_length=1024, default='')  # 商品缩略图
	pic_url = models.CharField(max_length=1024)  # 商品图
	detail = models.TextField(default='')  # 商品详情
	remark = models.TextField(default='')  # 备注
	display_index = models.IntegerField(default=0, blank=True)  # 显示的排序
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	shelve_type = models.IntegerField(
		default=PRODUCT_SHELVE_TYPE_OFF,
		db_index=True)  # 0:下架（待售） 1:上架（在售） 2:回收站
	shelve_start_time = models.CharField(max_length=50, null=True)  # 定时上架:上架时间
	shelve_end_time = models.CharField(max_length=50, null=True)  # 定时上架:下架时间
	stock_type = models.IntegerField(
		default=PRODUCT_STOCK_TYPE_UNLIMIT)  # 0:无限 1:有限
	stocks = models.IntegerField(default=-1)  # 起购数量
	is_deleted = models.BooleanField(default=False)  # 是否删除
	is_support_make_thanks_card = models.BooleanField(
		default=False)  # 是否支持制作感恩贺卡
	type = models.CharField(
		max_length=50,
		default=PRODUCT_DEFAULT_TYPE)  # 产品的类型
	update_time = models.DateTimeField(auto_now=True)  # 商品信息更新时间 2014-11-11
	postage_id = models.IntegerField(default=-1)  # 运费id ，-1为使用统一运费
	is_use_online_pay_interface = models.BooleanField(default=True)  # 在线支付方式
	is_use_cod_pay_interface = models.BooleanField(default=False)  # 货到付款支付方式
	# v2
	# product_mode = models.ForeignKey(ProductModel, blank=True, null=True)
	promotion_title = models.CharField(max_length=256, default='')  # 促销标题
	user_code = models.CharField(max_length=256, default='')  # 编码
	bar_code = models.CharField(max_length=256, default='')  # 条码
	unified_postage_money = models.FloatField(default=0.0)  # 统一运费金额
	postage_type = models.CharField(max_length=125, default=POSTAGE_TYPE_UNIFIED)  # 运费类型
	weshop_sync = models.IntegerField(default=0)  # 0不同步 1普通同步 2加价同步	#已废弃
	weshop_status = models.IntegerField(default=0)  # 0待售 1上架 2回收站			#已废弃
	is_member_product = models.BooleanField(default=False)  # 是否参加会员折扣
	supplier = models.IntegerField(default=0) # 供货商
	supplier_user_id = models.IntegerField(default=0) # 供货商(非8千)
	purchase_price = models.FloatField(default=0.0) # 进货价格
	is_enable_bill = models.BooleanField(default=False)  # 商品是否开具发票
	is_delivery = models.BooleanField(default=False) # 是否勾选配送时间
	buy_in_supplier = models.BooleanField(default=False) # 记录下单位置是商城还是供货商，0是商城1是供货商
	limit_zone_type = models.IntegerField(default=0) # 0不限制 1禁售 2仅售
	limit_zone = models.IntegerField(default=0) # 限制地区的模板id

	# 待审核商品
	is_pre_product = models.BooleanField(default=False)  # 是否待审核商品
	status = models.IntegerField(default=PRODUCT_STATUS['NOT_YET'])  # 审核状态
	is_updated = models.BooleanField(default=False)  # 是否已更新
	is_accepted = models.BooleanField(default=True)  # 审核是否已通过

	class Meta(object):
		db_table = 'mall_product'
		verbose_name = '商品'
		verbose_name_plural = '商品'
		# unique_together = ("name", "product_mode")

	def move_to_position(self, pos):
		"""将商品A移动到指定位置.如果所指定的位置存在商品B，商品B将失去位置信息， 安创建时间
		排序. 注意仅支持1-65534之间的排序

		Args:
		  pos(int): pos >=1

		Raises:
		  IndexError: 如果排序失败
		"""
		if pos < 0 or pos >= MAX_INDEX:
			raise IndexError('{} out of range [1, 65535)'.format(pos))
		# 查看指定的位置是否存在元素
		obj_bs = Product.objects.filter(owner_id=self.owner_id , display_index=pos)
		if obj_bs.exists():
			# obj_bs.update(display_index=0) 为了监听到display index的改变 zhaolei
			# ele = obj_bs.get()
			# ele.display_index=0
			# ele.save()

			# 2016-04-20 update by Eugene
			obj_bs.update(display_index=0)

		self.display_index = pos
		self.save()
		from cache.webapp_cache import update_product_cache
		update_product_cache(self.owner_id, self.id, False, False, True)

	# 填充标准商品规格信息
	def fill_standard_model(self):
		try:
			product_model = ProductModel.objects.get(
				product=self,
				is_standard=True)

			self.price = product_model.price
			self.weight = product_model.weight
			self.stock_type = product_model.stock_type
			self.min_limit = self.stocks
			self.stocks = product_model.stocks
			self.market_price = product_model.market_price
			return product_model
		except:
			if settings.DEBUG:
				raise
			else:
				fatal_msg = u"商品填充标准规格信息错误，商品id:{}, cause:\n{}".format(
					self.id,
					unicode_full_stack())
				watchdog_fatal(fatal_msg)

	@property
	def is_sellout(self):
		return self.total_stocks <= 0

	@property
	def total_stocks(self):
		if not hasattr(self, '_total_stocks'):
			self._total_stocks = 0
			if self.is_use_custom_model:
				models = self.models[1:]
			else:
				models = self.models
			if len(models) == 0:
				self._total_stocks = 0
				return self._total_stocks
			is_dict = (type(models[0]) == dict)

			for model in models:
				stock_type = model['stock_type'] if is_dict else model.stock_type
				stocks = model['stocks'] if is_dict else model.stocks
				if stock_type == PRODUCT_STOCK_TYPE_UNLIMIT:
					self._total_stocks = u'无限'
					return self._total_stocks
				else:
					self._total_stocks += stocks
		return self._total_stocks

	@property
	def is_use_custom_model(self):
		if not hasattr(self, '_is_use_custom_model'):
			self._is_use_custom_model = (
				ProductModel.objects.filter(
					product=self,
					is_standard=False,
					is_deleted=False).count() > 0)  # 是否使用定制规格
		return self._is_use_custom_model

	@staticmethod
	def fill_display_price(products):
		"""根据商品规格，获取商品价格
		"""
		# 获取所有models
		product2models = {}
		product_ids = [product.id for product in products]
		for model in ProductModel.objects.filter(product_id__in=product_ids):
			if model.is_deleted:
				# model被删除，跳过
				continue

			product_id = model.product_id
			if product_id in product2models:
				models = product2models[product_id]
			else:
				models = {
					'standard_model': None,
					'custom_models': [],
					'is_use_custom_model': False}
				product2models[product_id] = models

			if model.name == 'standard':
				models['standard_model'] = model
			else:
				models['is_use_custom_model'] = True
				models['custom_models'].append(model)

		# 为每个product确定显示价格
		for product in products:
			product_id = product.id
			if product_id in product2models:
				models = product2models[product.id]
				if models['is_use_custom_model']:
					custom_models = models['custom_models']
					if len(custom_models) == 1:
						product.display_price = custom_models[0].price
					else:
						prices = sorted(
							[model.price
							 for model in custom_models])
						# 列表页部分显示商品的最小价格
						# add by liupeiyu at 19.0
						# product.display_price = '%s-%s' % (prices[0], prices[-1])
						product.display_price = prices[0]
				else:
					product.display_price = models['standard_model'].price
			else:
				product.display_price = product.price

	@staticmethod
	def fill_model_detail(webapp_owner, products, product_ids, id2property={}, id2propertyvalue={}, is_enable_model_property_info=False, manager={}):
		_id2property = {}
		_id2propertyvalue = {}
		if is_enable_model_property_info:
			for id, property in id2property.items():
				_id2property[id] = {
					"id": property.id,
					"name": property.name,
					"values": []
				}

			for id, value in id2propertyvalue.items():
				_property_id, _value_id = id.split(':')
				_property = _id2property[_property_id]
				data = {
					'propertyId': _property['id'],
					'propertyName': _property['name'],
					"id": value.id,
					"name": value.name,
					"image": value.pic_url,
					"is_belong_product": False
				}
				_id2propertyvalue[id] = data
				_property['values'].append(data)
		user_id = manager.id if manager else webapp_owner.id
		divide_model = account_models.AccountDivideInfo.objects.filter(user_id=user_id).first()
		if divide_model:
			settlement_type = divide_model.settlement_type
			divide_rebate = divide_model.divide_rebate
			product_ids = [p.id for p in products]
			cps_product_id2promote = {p.product_id: p for p in PromoteDetail.objects.filter(promote_status=PROMOTING, product_id__in=product_ids)}
			product_model_id2price = {c.product_model_id: c.price for c in
									  ProductCustomizedPrice.objects.filter(product_id__in=product_ids)}

		# 获取所有models
		product2models = {}
		for model in ProductModel.objects.filter(product_id__in=product_ids):
			if model.is_deleted:
				# model被删除，跳过
				continue

			model_dict = {
				"id": model.id,
				"name": model.name,
				"price": '%.2f' % model.price,
				"weight": model.weight,
				"stock_type": model.stock_type,
				"stocks": model.stocks if model.stock_type == PRODUCT_STOCK_TYPE_LIMIT else u'无限',
				"user_code": model.user_code,
				"purchase_price": '%.2f' % model.purchase_price,
				"market_price": '%.2f' % model.market_price,
				"gross_profit": '%.2f' % (model.price - model.purchase_price),
				"gross_profit_rate": 0 if model.price == 0 else '%.2f' % ((model.price - model.purchase_price)/model.price)
			}
			if divide_model:
				"""
				社群的毛利、毛利率
				固定底价: 社群修改价 - 上浮结算价
				固定扣点: 商品售价 * 社群扣点
				毛利分成: {
					cps: 推广费 * 社群毛利点,
					non_cps: (商品售价 - 微众售价) * 社群毛利点  ==> 社群毛利,
							 (商品售价 - 微众售价)/商品售价 * 社群毛利点 ==>社群毛利率
				}
				对于多规格的商品，则填充毛利最大的
				"""
				if model.price == 0:
					gross_profit = 0
					gross_profit_rate = 0
				else:
					if settlement_type == account_models.ACCOUNT_DIVIDE_TYPE_FIXED:  # 固定底价
						customized_price = product_model_id2price.get(model.id, model.price)
						gross_profit = customized_price - model.price
						gross_profit_rate = gross_profit / customized_price * 100
					elif settlement_type == account_models.ACCOUNT_DIVIDE_TYPE_RETAIL:  # 固定扣点
						gross_profit = model.price * divide_rebate / 100
						gross_profit_rate = divide_rebate
					elif settlement_type == account_models.ACCOUNT_DIVIDE_TYPE_PROFIT:  # 毛利分成
						product_id = model.product.id
						if product_id in cps_product_id2promote.keys():
							model_dict['cps_gross_profit'] = '%.2f' % (cps_product_id2promote[product_id].promote_money * divide_rebate / 100)
							model_dict['cps_gross_profit_rate'] = '%.2f' % (float(model_dict['cps_gross_profit']) / model.price * 100)
							model_dict['cps_time_to'] = cps_product_id2promote[product_id].promote_time_to.strftime("%m-%d %H:%M:%S")

						gross_profit = (model.price - model.purchase_price) * divide_rebate / 100
						gross_profit_rate = gross_profit / model.price * 100

				model_dict['gross_profit'] = '%.2f' % gross_profit
				model_dict['gross_profit_rate'] = '%.2f' % gross_profit_rate

			'''
			获取model关联的property信息
				model.property_values = [{
					'propertyId': 1,
					'propertyName': '颜色',
					'id': 1,
					'value': '红'
				}, {
					'propertyId': 2,
					'propertyName': '尺寸',
					'id': 3,
					'value': 'S'
				}]

				model.property2value = {
					'颜色': '红',
					'尺寸': 'S'
				}
			'''
			if is_enable_model_property_info and model.name != 'standard':
				ids = model.name.split('_')
				property_values = []
				property2value = {}
				for id in ids:
					# id的格式为${property_id}:${value_id}
					_property_id, _value_id = id.split(':')
					_property = _id2property.get(_property_id, None)
					if _property == None:
						continue
					_value = _id2propertyvalue[id]
					property2value[_property['name']] = {
						'id': _value['id'],
						'name': _value['name']
					}
					property_values.append({
						'propertyId': _property['id'],
						'propertyName': _property['name'],
						'id': _value['id'],
						'name': _value['name']
					})
					_value['is_belong_product'] = True
				model_dict['property_values'] = property_values
				model_dict['property2value'] = property2value

			product_id = model.product_id
			if product_id in product2models:
				models = product2models[product_id]
			else:
				models = {
					'standard_model': None,
					'custom_models': [],
					'is_use_custom_model': False}
				product2models[product_id] = models

			if model.name == 'standard':
				models['standard_model'] = model_dict
			else:
				models['is_use_custom_model'] = True
				models['custom_models'].append(model_dict)

		# 为每个product确定显示信息
		for product in products:
			product.sales = -1  # 实现sales逻辑
			product.system_model_properties = _id2property.values()
			product_id = product.id
			if product_id in product2models:
				models = product2models[product.id]
				product.models = [models['standard_model']]
				if models['is_use_custom_model']:
					product._is_use_custom_model = True
					product.custom_models = models['custom_models']
					product.standard_model = models['standard_model']
					custom_models = models['custom_models']
					product.models.extend(custom_models)
					if len(custom_models) == 1:
						target_model = custom_models[0]
						max_profit_model = target_model
						# 格式: X.00
						display_price_range = target_model['price']
					else:
						# 列表页部分显示商品的最小价格那个model的信息
						custom_models.sort(lambda x, y: cmp(float(x['price']), float(y['price'])))
						target_model = custom_models[0]
						low_price = target_model['price']
						high_price = custom_models[-1]['price']
						custom_models.sort(lambda x, y: cmp(float(x['gross_profit']), float(y['gross_profit'])))
						max_profit_model = custom_models[-1]
						if low_price == high_price:
							# 格式: X.00
							display_price_range = low_price
						else:
							# 更改 格式: X.00 @延昊南
							low_price = low_price
							high_price = high_price
							display_price_range = '%s ~ %s' % (low_price, high_price)
				else:
					product._is_use_custom_model = False
					target_model = models['standard_model']
					max_profit_model = target_model
					product.standard_model = target_model
					display_price_range = target_model['price']

				product.gross_profit = max_profit_model.get('gross_profit', 0)
				product.gross_profit_rate = max_profit_model.get('gross_profit_rate', 0)
				product.cps_gross_profit = max_profit_model.get('cps_gross_profit', 0)
				product.cps_gross_profit_rate = max_profit_model.get('cps_gross_profit_rate', 0)
				product.cps_time_to = max_profit_model.get('cps_time_to', '')

				product.current_used_model = target_model
				product.display_price = target_model['price']
				product.display_price_range = display_price_range
				product.user_code = target_model['user_code']
				product.stock_type = target_model['stock_type']
				product.min_limit = product.stocks
				product.stocks = u'无限' if target_model[
					'stock_type'] == PRODUCT_STOCK_TYPE_UNLIMIT else target_model['stocks']
			else:
				# 所有规格都已经被删除
				product._is_use_custom_model = False
				product.current_used_model = {}
				product.display_price = product.price
				product.display_price_range = product.price
				product.user_code = product.user_code
				product.stock_type = PRODUCT_STOCK_TYPE_LIMIT
				product.stocks = 0
				product.min_limit = 0
				product.standard_model = {}
				product.models = []
				product.gross_profit = 0
				product.gross_profit_rate = 0
				product.cps_gross_profit = 0
				product.cps_gross_profit_rate = 0


	@staticmethod
	def fill_image_detail(webapp_owner, products, product_ids):
		for product in products:
			product.swipe_images = [
				{'id': img.id, 'url': img.url, 'linkUrl': img.link_url, 'width':
				 img.width, 'height': img.height, }
				for img in ProductSwipeImage.objects.filter(
					product_id=product.id)]

	@staticmethod
	def fill_property_detail(webapp_owner, products, product_ids):
		for product in products:
			product.properties = [
				{"id": property.id, "name": property.name,
				 "value": property.value}
				for property in ProductProperty.
				objects.filter(product_id=product.id)]

	@staticmethod
	def fill_category_detail(
			webapp_owner,
			products,
			product_ids,
			only_selected_category=False):
		categories = list(ProductCategory.objects.filter(owner=webapp_owner).order_by('id'))

		# 获取product关联的category集合
		id2product = dict([(product.id, product) for product in products])
		for product in products:
			product.categories = []
			product.id2category = {}
			id2product[product.id] = product
			if not only_selected_category:
				for category in categories:
					category_data = {
						'id': category.id,
						'name': category.name,
						'is_selected': False
					}
					product.categories.append(category_data)
					product.id2category[category.id] = category_data

		category_ids = [category.id for category in categories]
		id2category = dict([(category.id, category) for category in categories])
		for relation in CategoryHasProduct.objects.filter(product_id__in=product_ids).order_by('id'):
			category_id = relation.category_id
			product_id = relation.product_id
			if not category_id in id2category:
				# 微众商城分类，在商户中没有
				continue
			category = id2category[category_id]
			if not only_selected_category:
				id2product[product_id].id2category[
					category.id]['is_selected'] = True
			else:
				id2product[product_id].categories.append({
					'id': category.id,
					'name': category.name,
					'is_selected': True
				})

	@staticmethod
	def fill_flash_sale(products,webapp_owner):
		from mall.promotion import models as promotion_models
		for p in products:
			p.promotion = None

		product_ids = []
		id2product = {}
		for product in products:
			product_ids.append(product.id)
			id2product[product.id] = product

		#创建promotions业务对象集合
		product_promotion_relations = promotion_models.ProductHasPromotion.objects.filter(product_id__in=product_ids, promotion__owner=webapp_owner, promotion__status=promotion_models.PROMOTION_STATUS_STARTED)
		promotion_ids = list()
		promotion2product = dict()
		for relation in product_promotion_relations:
			promotion_ids.append(relation.promotion_id)
			promotion2product[relation.promotion_id] = id2product.get(relation.product_id)

		promotion_db_models = promotion_models.Promotion.objects.filter(id__in=promotion_ids)
		for promotion_db_model in promotion_db_models:
			if promotion_db_model.type != promotion_models.PROMOTION_TYPE_FLASH_SALE or ((promotion_db_model.status != promotion_models.PROMOTION_STATUS_STARTED) and (promotion_db_model.status != promotion_models.PROMOTION_STATUS_NOT_START)):
				#跳过已结束、已删除的促销活动
				continue

			flash_sale = promotion_models.FlashSale.objects.get(id=promotion_db_model.detail_id)

			product = promotion2product.get(promotion_db_model.id)
			if product:

				product.promotion = {
					'detail': {'promotion_price': flash_sale.promotion_price},
					'member_grade_id':promotion_db_model.member_grade_id
				}




	@staticmethod
	def fill_promotion_detail(webapp_owner, products, product_ids):
		from mall.promotion import models as promotion_models
		today = datetime.today()
		id2product = dict([(product.id, product) for product in products])

		type2promotions = {}
		id2promotion = {}
		product_promotion_relations = list(
			promotion_models.Promotion.objects.filter(
				product_id__in=product_ids))
		promotion_ids = [relation.promotion_id
						 for relation in product_promotion_relations]
		promotions = list(
			promotion_models.Promotion.objects.filter(
				product_id__in=product_ids))
		for promotion in promotions:
			type2promotions.setdefault(promotion.type, []).append(promotion)
			id2promotion[promotion.id] = promotion

		for relation in product_promotion_relations:
			product = id2product[relation.product_id]
			promotion = id2promotion[relation.promotion_id]
			product.promotion = {
				'id': promotion.id,
				'type': promotion.type_name,
				'name': promotion.name,
				'status_value': promotion.status,
				'status': promotion.status_name,
				'start_date': promotion.start_date.strftime("%Y-%m-%d %H:%M"),
				'end_date': promotion.end_date.strftime('%Y-%m-%d %H:%M')
			}

		for type, promotions in type2promotions.items():
			if type == promotion_models.PROMOTION_TYPE_FLASH_SALE:
				model2product = dict(
					[(product.current_used_model['id'], product) for product in products])
				product_model_ids = [product.current_used_model['id']
									 for product in products]
				model_promotion_details = promotion_models.ProductModelFlashSaleDetail.objects.filter(
					owner=webapp_owner,
					product_model_id__in=product_model_ids)
				for model_promotion_detail in model_promotion_details:
					model2product[promotion_detail.product_model_id].promotion[
						'price'] = model_promotion_detail.promotion_price
			else:
				pass

	@staticmethod
	def fill_sales_detail(webapp_owner, products, product_ids):
		id2product = dict([(product.id, product) for product in products])
		for product in products:
			product.sales = 0

		for sales in ProductSales.objects.filter(product_id__in=product_ids):
			product_id = sales.product_id
			if id2product.has_key(product_id):
				id2product[product_id].sales = sales.sales

	@staticmethod
	def fill_details(webapp_owner, products, options, manager={}):
		id2property = None
		id2propertyvalue = None
		is_enable_model_property_info = options.get(
			'with_model_property_info',
			False)
		if is_enable_model_property_info:
			# 获取model property，为后续使用做准备
			# properties = list(
			# 	ProductModelProperty.objects.filter(
			# 		owner=webapp_owner))

			pool_weapp_profile = UserProfile.objects.filter(webapp_type=2).first()
			if pool_weapp_profile:
				properties = ProductModelProperty.objects.filter(
					Q(owner=webapp_owner) | Q(owner=pool_weapp_profile.user))
			else:
				# TODO bert prodcut_pool 增加默认商品规格 owner
				properties = ProductModelProperty.objects.filter(
					owner=webapp_owner)
			property_ids = [property.id for property in properties]
			id2property = dict([(str(property.id), property)
							   for property in properties])
			id2propertyvalue = {}
			for value in ProductModelPropertyValue.objects.filter(property_id__in=property_ids):
				id = '%d:%d' % (value.property_id, value.id)
				id2propertyvalue[id] = value

		product_ids = [product.id for product in products]

		mall_type = options.get('mall_type', False)
		product_pool_id2product_pool = options.get('product_pool_id2product_pool', {})
		for product in products:
			if product.id!=None:
				product.detail_link = '/mall2/product/?id=%d&source=onshelf' % product.id

				if mall_type == 1 and product_pool_id2product_pool:
					pool = product_pool_id2product_pool.get(product.id, None)
					if pool:
						product.display_index = pool.display_index
						if pool.status == PP_STATUS_ON:
							product._status = u'在售'
						elif pool.status == PP_STATUS_OFF:
							product._status = u'待售'
						elif pool.status == PP_STATUS_DELETE:
							product._status = u'已删除'
						else:
							product._status = u'商品池中'



		if options.get('with_product_model', False):
			Product.fill_model_detail(
				webapp_owner,
				products,
				product_ids,
				id2property,
				id2propertyvalue,
				is_enable_model_property_info,
				manager)

		if options.get('with_product_promotion', False):
			Product.fill_promotion_detail(webapp_owner, products, product_ids)

		if options.get('with_image', False):
			Product.fill_image_detail(webapp_owner, products, product_ids)

		if options.get('with_property', False):
			Product.fill_property_detail(webapp_owner, products, product_ids)

		if options.get('with_selected_category', False):
			Product.fill_category_detail(
				webapp_owner,
				products,
				product_ids,
				True)

		if options.get('with_all_category', False):
			Product.fill_category_detail(
				webapp_owner,
				products,
				product_ids,
				False)

		if options.get('with_sales', False):
			Product.fill_sales_detail(webapp_owner, products, product_ids)

		# 商品列表页缓存专用
		if options.get('with_price', False):
			Product.fill_display_price(products)

		# 商品列表页缓存专用
		if options.get('flash_sale', False):
			Product.fill_flash_sale(products, webapp_owner)

		if options.get('with_settlement_info', False):
			Product.fill_settlement_info(webapp_owner, products)

	@staticmethod
	def get_from_model(product_id, product_model_name):
		product = Product.objects.get(id=product_id)
		model = ProductModel.objects.get(product_id=product_id, name=product_model_name)

		product.price = model.price
		product.weight = model.weight
		product.stock_type = model.stock_type
		product.min_limit = product.stocks
		product.stocks = model.stocks
		product.model_name = product_model_name
		product.market_price = model.market_price

		property_ids = []
		property_value_ids = []
		if product.model_name != 'standard':
			for model_property_info in product.model_name.split('_'):
				property_id, property_value_id = model_property_info.split(':')
				property_ids.append(property_id)
				property_value_ids.append(property_value_id)

				id2property = dict(
					[
						(property.id,
						 {"id": property.id, "name": property.name})
						for property in ProductModelProperty.objects.filter(
							id__in=property_ids)])
				for property_value in ProductModelPropertyValue.objects.filter(id__in=property_value_ids):
					id2property[property_value.property_id][
						'property_value'] = property_value.name
					id2property[property_value.property_id][
						'property_pic_url'] = property_value.pic_url
			product.custom_model_properties = id2property.values()
			product.custom_model_properties.sort(
				lambda x,
				y: cmp(
					x['id'],
					y['id']))
		else:
			product.custom_model_properties = None

		return product

	# @staticmethod
	# def get_model(product_id, product_model_name):
	# 	"""得到商品规格名称

	# 	Args:
	# 	  product_id(int):
	# 	  product_model_name(str): "X1:Y1[_X2:Y2]+"

	# 	Return: List
	# 	  example:
	# 	    [{id:1, name:xxx, property_value: '', property_pic_url: ''}, ...]
	# 	"""
	# 	product = Product.objects.get(id=product_id)
	# 	model = ProductModel.objects.get(product_id=product_id, name=product_model_name)

	# 	product.price = model.price
	# 	product.weight = model.weight
	# 	product.stock_type = model.stock_type
	# 	product.min_limit = product.stocks
	# 	product.stocks = model.stocks
	# 	product.model_name = product_model_name
	# 	product.market_price = model.market_price

	# 	property_ids = []
	# 	property_value_ids = []
	# 	if product.model_name != 'standard':
	# 		ptn_p = r'[a-zA-Z0-9]+(?=:)'
	# 		ptn_pv = r'(?<=:)[a-zA-Z0-9]+'
	# 		property_ids = re.findall(ptn_p, product_model_name)
	# 		property_value_ids = re.findall(ptn_pv, product_model_name)
	# 		p_id_pv_ids = [i.split(":") for i in product_model_name.split("_")]


	# 填充特定的规格信息
	def fill_specific_model(self, model_name, models=None):
		if models:
			candidate_models = filter(lambda m: m['name'] == model_name, models)
			if len(candidate_models) > 0:
				model = candidate_models[0]
				product = self
				product.price = model['price']
				product.weight = model['weight']
				product.stock_type = model['stock_type']
				if not hasattr(product, 'min_limit'):
					product.min_limit = product.stocks
				product.stocks = model['stocks']
				product.model_name = model_name
				product.model = model
				product.is_model_deleted = False
				product.market_price = model.get('market_price', 0.0)

				if model_name == 'standard':
					product.custom_model_properties = None
				else:
					product.custom_model_properties = [{'property_value': property_value['name']} for property_value in model['property_values']]
			else:
				temp_models = ProductModel.objects.filter(product_id=self.id, name=model_name)
				if len(temp_models) > 0:
					model = temp_models[0]

				product = self
				product.price = model.price
				product.weight = model.weight
				product.stock_type = model.stock_type
				if not hasattr(product, 'min_limit'):
					product.min_limit = product.stocks
				product.stocks = model.stocks
				product.model_name = model_name
				product.model = {"name": model.name}
				product.is_model_deleted = True
				product.market_price = model.market_price
				product.custom_model_properties = None
		else:
			try:
				model = ProductModel.objects.get(product_id=self.id, name=model_name)
			except:
				model = None
			product = self
			if model:

				product.price = model.price
				product.weight = model.weight
				product.stock_type = model.stock_type
				if not hasattr(product, 'min_limit'):
					product.min_limit = product.stocks
				product.stocks = model.stocks
				product.model_name = model_name
				product.model = model
				product.is_model_deleted = False
				product.market_price = 0.0
				product.user_code = model.user_code
				if model.is_deleted:
					product.is_model_deleted = True
				#raise ValueError("product model is deleted: %s" % model_name)

			else:
				product.price = product.price
				product.weight = product.weight
				product.stock_type = product.stock_type
				product.min_limit = product.stocks
				product.stocks = product.stocks
				product.model_name = model_name
				product.model = None
				product.is_model_deleted = True
				product.market_price = 0.0
				product.user_code = product.user_code
				product.is_model_deleted = True


			property_ids = []
			property_value_ids = []

			name = product.model_name
			if product.model_name != 'standard':
				for model_property_info in product.model_name.split('_'):
					property_id, property_value_id = model_property_info.split(':')
					property_ids.append(property_id)
					property_value_ids.append(property_value_id)

					id2property = dict(
						[
							(property.id,
							 {"id": property.id, "name": property.name})
							for property in ProductModelProperty.objects.filter(
								id__in=property_ids)])
					for property_value in ProductModelPropertyValue.objects.filter(id__in=property_value_ids):
						id2property[property_value.property_id][
							'property_value'] = property_value.name
						id2property[property_value.property_id][
							'property_pic_url'] = property_value.pic_url
				product.custom_model_properties = id2property.values()
				product.custom_model_properties.sort(
					lambda x,
					y: cmp(
						x['id'],
						y['id']))
			else:
				product.custom_model_properties = None

		if product.stock_type == PRODUCT_STOCK_TYPE_UNLIMIT:
			if not hasattr(product, 'min_limit'):
				product.min_limit = product.stocks
			product.stocks = -1

		return product.custom_model_properties

	# 填充所有商品规格信息
	def fill_model(self, show_delete=False):
		standard_model = self.fill_standard_model()

		if self.is_use_custom_model:
			self.custom_models = ProductModel.objects.filter(
				Q(product=self) &
				~Q(name='standard') &
				Q(is_deleted=show_delete)
			)
		else:
			self.custom_models = []

		self.models = []
		self.models.append({
			"id": standard_model.id,
			"name": "standard",
			"original_price": self.price,
			"price": self.price,
			"weight": self.weight,
			"stock_type": self.stock_type,
			"stocks": self.stocks,
			"market_price": self.market_price,
			"user_code": self.user_code
		})

		self.custom_properties = []
		self.product_model_properties = []
		recorded_model_property = set()  # 保存已记录的model property
		if len(self.custom_models) > 0:
			# 获取系统所有property
			id2property = dict(
				[
					(property.id, property)
					for property in ProductModelProperty.objects.filter(
						owner=self.owner, is_deleted=False)])
			properties = id2property.values()
			properties.sort(lambda x, y: cmp(x.id, y.id))
			for property in properties:
				self.custom_properties.append({
					"id": property.id,
					"name": property.name
				})
			self.custom_properties_json_str = json.dumps(self.custom_properties)

			property_ids = id2property.keys()
			id2value = dict([(value.id, value) for value in ProductModelPropertyValue.objects.filter(property_id__in=property_ids, is_deleted=False)])

			# 获取系统所有<property, [values]>
			id2property = {}
			for property in properties:
				id2property[
					property.id] = {
					"id": property.id,
					"name": property.name,
					"values": []}
			stock_custom_model_names = []  # 无限库存或库存不为>0的custom_model_name集合
			property_value_ids = []
			for custom_model in self.custom_models:
				if custom_model.stock_type == 0 or custom_model.stocks > 0:
					stock_custom_model_names.append(str(custom_model.name))
				for model_property_info in custom_model.name.split('_'):
					property_id, property_value_id = model_property_info.split(':')
					property_value_ids.append(int(property_value_id))
			self.stock_custom_model_names = stock_custom_model_names

			# 解决规格顺序错乱的BUG
			values = id2value.values()
			if values:
				values.sort(lambda x, y: cmp(x.id, y.id))

			for value in values:
				# 增加该规格值是否属于该产品
				is_belong_product = (value.id in property_value_ids)
				id2property[value.property_id]['values'].append({
					"id": value.id,
					"name": value.name,
					"image": value.pic_url,
					"is_belong_product": is_belong_product
				})
			self.model_properties = id2property.values()
			self.model_properties.sort(lambda x, y: cmp(x['id'], y['id']))

			# 获取商品关联的所有的model和property
			for custom_model in self.custom_models:
				if custom_model.name == 'standard':
					continue

				model_dict = {
					"id": custom_model.id,
					"name": custom_model.name,
					"original_price": custom_model.price,
					"price": custom_model.price,
					"weight": custom_model.weight,
					"stock_type": custom_model.stock_type,
					"stocks": custom_model.stocks,
					"user_code": custom_model.user_code,
					"market_price": custom_model.market_price
				}

				model_dict['property_values'] = []
				try:
					for model_property_info in custom_model.name.split('_'):
						property_id, property_value_id = model_property_info.split(
							':')
						if not id2value.has_key(int(property_value_id)):
							continue
						model_dict['property_values'].append({
							"propertyId": property_id,
							"propertyName": id2property[int(property_id)]['name'],
							"id": property_value_id,
							"name": id2value[int(property_value_id)].name
						})

						# 记录商品的model property
						if not property_id in recorded_model_property:
							model_property = id2property[int(property_id)]
							self.product_model_properties.append(model_property)
							recorded_model_property.add(property_id)

					self.models.append(model_dict)
				except:
					fatal_msg = u"商品填充所有商品规格信息错误，商品id:{}, 错误的mall_product_model.id:{}, cause:\n{}".format(
						self.id,
						custom_model.id,
						unicode_full_stack())
					watchdog_fatal(fatal_msg)

		self.models_json_str = json.dumps(self.models)
		self.product_model_properties_json_str = json.dumps(self.product_model_properties)

	# add by bert at 17.0
	@staticmethod
	def can_update_by(owner_id, product_id):
		# 当前owner下不还有商品，微众商城表里包含商品 这样的商品不能修改
		if Product.objects.filter(owner_id=owner_id, id=product_id).count() > 0:
			return True
		else:
			return False

	@staticmethod
	def can_update_weizoom_mall_button(user, product_id):
		# 商户访问商品时，
		# 微众商城表里包含商品, 并且已通过审核
		# 这样的商品 商户 不能改变页面 '是否加入微众商城' 值
		try:
			webapp_id = user.get_profile().webapp_id
			product = Product.objects.get(owner_id=user.id, id=product_id)
			wmall_has_other_products = WeizoomMallHasOtherMallProduct.objects.filter(
				product_id=product.id,
				webapp_id=webapp_id,
				is_checked=True)
			if wmall_has_other_products.count() > 0:
				return True
			else:
				return False
		except:
			return False

	@property
	def weizoom_mall(self):
		if hasattr(self, '_weizoom_mall'):
			return self._weizoom_mall
		else:
			try:
				if WeizoomMallHasOtherMallProduct.objects.filter(product_id=self.id).count() > 0:
					self._weizoom_mall = 1
				else:
					self._weizoom_mall = 0
				return self._weizoom_mall
			except:
				return 0

	@property
	def status(self):
		if hasattr(self, '_status'):
			return self._status
		else:
			if self.is_deleted:
				self._status = u'已删除'
			else:
				if self.shelve_type == PRODUCT_SHELVE_TYPE_ON:
					self._status = u'在售'
				elif self.shelve_type == PRODUCT_SHELVE_TYPE_OFF:
					self._status = u'待售'
				else:
					self._status = u'回收站'
			return self._status

	# 是否有购买次商品权限
	# add by liupeiyu at 17.1
	def is_can_buy_by_product(self, request):
		if hasattr(request, 'webapp_user') and request.webapp_user:
			order_ids = [o.id for o in Order.by_webapp_user_id(request.webapp_user.id).filter(webapp_id=request.user_profile.webapp_id)]
			count = OrderHasProduct.objects.filter(
				order_id__in=order_ids,
				product_id=self.id).count()
			if count > 0:
				self.is_can_buy_by_product = False
			else:
				self.is_can_buy_by_product = True
		else:
			self.is_can_buy_by_product = True

	def get_str_type(self):
		try:
			return PRODUCT_TYPE2TEXT[self.type]
		except:
			return ''

	# 如果规格有图片就显示，如果没有，使用缩略图
	def order_thumbnails_url(self):
		'''
		if hasattr(self, 'custom_model_properties') and self.custom_model_properties:
			for model in self.custom_model_properties:
				if model['property_pic_url']:
					return model['property_pic_url']
		'''
		return self.thumbnails_url

	# 是否免运费
	def is_free_postage(self):
		if self.postage_id > 0:
			return False

		return True

	def format_to_dict(self):
		return {
			'id': self.id,
			'name': self.name,
			'thumbnails_url': self.thumbnails_url,
			'detail_link': '/mall2/product/?id=%d&source=onshelf' % self.id,
			'categories': getattr(self, 'categories', []),
			'properties': getattr(self, 'properties', []),
			'display_price': self.display_price,
			'display_price_range': self.display_price_range,
			'user_code': self.user_code,
			'bar_code': self.bar_code,
			'min_limit': self.min_limit,
			'stocks': self.stocks if self.stock_type else '无限',
			'sales': getattr(self, 'sales', 0),
			'is_use_custom_model': self.is_use_custom_model,
			'models': self.models[1:],
			'total_stocks': self.total_stocks,
			'is_sellout': self.is_sellout,
			'standard_model': self.standard_model,
			'current_used_model': self.current_used_model,
			'created_at': datetime.strftime(self.created_at, '%Y-%m-%d %H:%M'),
			'display_index': self.display_index,
			'is_member_product': self.is_member_product,
			'purchase_price': self.purchase_price,
			'type': self.type,
		}


#########################################################################
# CategoryHasProduct：<category, product>关系
#########################################################################
class CategoryHasProduct(models.Model):
	product = models.ForeignKey(Product)
	category = models.ForeignKey(ProductCategory)
	display_index = models.IntegerField(default=0, null=True)  # 分组商品排序
	created_at = models.DateTimeField(auto_now_add=True)

	def move_to_position(self, pos):
		"""将分组内的特定商品移动到指定位置

		Args:
		  pos(int): 指定位置
		"""
		pos = int(pos)
		if pos < 0 or pos >= MAX_INDEX:
			raise IndexError('{} out of range [1, 65535)'.format(pos))
		category_has_products = CategoryHasProduct.objects.filter(
			category_id=self.category_id,
			display_index=pos
		)
		if category_has_products.exists():
			category_has_products.update(display_index=0)
		self.display_index = pos
		self.save()

	class Meta(object):
		unique_together = ('category', 'product')
		db_table = 'mall_category_has_product'
		verbose_name = '分类下的商品'
		verbose_name_plural = '分类下的商品'


#########################################################################
# ProductSwipeImage：商品轮播图片
#########################################################################
class ProductSwipeImage(models.Model):
	product = models.ForeignKey(Product)
	url = models.CharField(max_length=256, default='')
	link_url = models.CharField(max_length=256, default='')
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# v2
	width = models.IntegerField()  # 图片宽度
	height = models.IntegerField()  # 图片高度

	class Meta(object):
		db_table = 'mall_product_swipe_image'
		verbose_name = '商品轮播图'
		verbose_name_plural = '商品轮播图'


#########################################################################
# ProductSales：商品销量
#########################################################################
class ProductSales(models.Model):
	product = models.ForeignKey(Product)
	sales = models.IntegerField(default=0) #销量

	class Meta(object):
		db_table = 'mall_product_sales'
		verbose_name = '商品销量'
		verbose_name_plural = '商品销量'


#########################################################################
# ImageGroup：商城图片分组
#########################################################################
class ImageGroup(models.Model):
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=125, default='')  # 图片分组名
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_image_group'
		verbose_name = '商城图片分组'
		verbose_name_plural = '商城图片分组'


#########################################################################
# Image：商城图片
#########################################################################
class Image(models.Model):
	owner = models.ForeignKey(User)
	group = models.ForeignKey(ImageGroup)
	title = models.CharField(max_length=125, default='')  # 图片标题
	url = models.CharField(max_length=256, default='')  # 图片url
	width = models.IntegerField()  # width
	height = models.IntegerField()  # height
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_image'
		verbose_name = '商城图片'
		verbose_name_plural = '商城图片'


#########################################################################
# ProductModelProperty：商品规格属性
#########################################################################
PRODUCT_MODEL_PROPERTY_TYPE_TEXT = 0
PRODUCT_MODEL_PROPERTY_TYPE_IMAGE = 1


class ProductModelProperty(models.Model):
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=256)  # 商品规格属性名
	type = models.IntegerField(default=PRODUCT_MODEL_PROPERTY_TYPE_TEXT)  # 属性类型
	is_deleted = models.BooleanField(default=False)  # 是否删除
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_model_property'
		verbose_name = '商品规格属性'
		verbose_name_plural = '商品规格属性'

	@property
	def values(self):
		return list(
			ProductModelPropertyValue.objects.filter(
				property=self,
				is_deleted=False))

	@property
	def is_image_property(self):
		return self.type == PRODUCT_MODEL_PROPERTY_TYPE_IMAGE


#########################################################################
# ProductModelPropertyValue：商品规格属性值
#########################################################################
class ProductModelPropertyValue(models.Model):
	property = models.ForeignKey(
		ProductModelProperty,
		related_name='model_property_values')
	name = models.CharField(max_length=256)  # 商品名称
	pic_url = models.CharField(max_length=1024)  # 商品图
	is_deleted = models.BooleanField(default=False)  # 是否已删除
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_model_property_value'
		verbose_name = '商品规格属性值'
		verbose_name_plural = '商品规格属性值'


#########################################################################
# ProductModel：商品规格
#########################################################################
class ProductModel(models.Model):
	owner = models.ForeignKey(User)
	product = models.ForeignKey(Product)
	name = models.CharField(max_length=255, db_index=True)  # 商品规格名
	is_standard = models.BooleanField(default=True)  # 是否是标准规格
	price = models.FloatField(default=0.0)  # 商品价格
	market_price = models.FloatField(default=0.0)  # 商品市场价格
	purchase_price = models.FloatField(default=0.0)  # 商品结算价格
	weight = models.FloatField(default=0.0)  # 重量
	stock_type = models.IntegerField(
		default=PRODUCT_STOCK_TYPE_UNLIMIT)  # 0:无限 1:有限
	stocks = models.IntegerField(default=0)  # 有限：数量
	is_deleted = models.BooleanField(default=False)  # 是否已删除
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# v2
	user_code = models.CharField(max_length=256, default='')  # 编码

	class Meta(object):
		db_table = 'mall_product_model'
		verbose_name = '商品规格属性'
		verbose_name_plural = '商品规格属性'

	def __getitem__(self, name):
		return getattr(self, name, None)


#########################################################################
# ProductModelHasProperty: <商品规格，商品规格属性值>关系
#########################################################################
class ProductModelHasPropertyValue(models.Model):
	model = models.ForeignKey(ProductModel)
	property_id = models.IntegerField(default=0)
	property_value_id = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_model_has_property'


#########################################################################
# ProductProperty: 商品属性
#########################################################################
class ProductProperty(models.Model):
	owner = models.ForeignKey(User)
	product = models.ForeignKey(Product)
	name = models.CharField(max_length=256)  # 商品属性名
	value = models.CharField(max_length=256)  # 商品属性值
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_property'
		verbose_name = '商品属性'
		verbose_name_plural = '商品属性'


#########################################################################
# ProductPropertyTemplate: 商品属性模板
#########################################################################
class ProductPropertyTemplate(models.Model):
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=256)  # 商品属性名
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_property_template'
		verbose_name = '商品属性模板'
		verbose_name_plural = '商品属性模板'


#########################################################################
# TemplateProperty: 模板中的属性
#########################################################################
class TemplateProperty(models.Model):
	owner = models.ForeignKey(User)
	template = models.ForeignKey(ProductPropertyTemplate)
	name = models.CharField(max_length=256)  # 商品属性名
	value = models.CharField(max_length=256)  # 商品属性值
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_product_template_property'
		verbose_name = '商品模板属性'
		verbose_name_plural = '商品模板属性'


# MODULE END: product
# Termite GENERATED END: model


ORDER_STATUS_NOT = 0  # 待支付：已下单，未付款
ORDER_STATUS_CANCEL = 1  # 已取消：取消订单(回退销量)
ORDER_STATUS_PAYED_SUCCESSED = 2  # 已支付：已下单，已付款，已不存此状态
ORDER_STATUS_PAYED_NOT_SHIP = 3  # 待发货：已付款，未发货
ORDER_STATUS_PAYED_SHIPED = 4  # 已发货：已付款，已发货
ORDER_STATUS_SUCCESSED = 5  # 已完成：自下单10日后自动置为已完成状态
ORDER_STATUS_REFUNDING = 6  # 退款中
ORDER_STATUS_REFUNDED = 7  # 退款完成(回退销量)
ORDER_STATUS_GROUP_REFUNDING = 8 #团购退款（没有退款完成按钮）
ORDER_STATUS_GROUP_REFUNDED = 9 #团购退款完成

# 权重小的优先
ORDER_STATUS2DELIVERY_ITEM_WEIGHT = {
	ORDER_STATUS_NOT: 1,
	ORDER_STATUS_PAYED_NOT_SHIP: 2,
	ORDER_STATUS_PAYED_SHIPED: 3,
	ORDER_STATUS_REFUNDING: 4,
	ORDER_STATUS_SUCCESSED: 5,
	ORDER_STATUS_REFUNDED:6,
	ORDER_STATUS_CANCEL: 7
}

DELIVERY_ITEM_WEIGHT2ORDER_STATUS = {
	1: ORDER_STATUS_NOT,
	2: ORDER_STATUS_PAYED_NOT_SHIP,
	3: ORDER_STATUS_PAYED_SHIPED,
	4: ORDER_STATUS_REFUNDING,
	5: ORDER_STATUS_SUCCESSED,
	6: ORDER_STATUS_REFUNDED,
	7: ORDER_STATUS_CANCEL
}



ORDER_BILL_TYPE_NONE = 0  # 无发票
ORDER_BILL_TYPE_PERSONAL = 1  # 个人发票
ORDER_BILL_TYPE_COMPANY = 2  # 公司发票
STATUS2TEXT = {
	ORDER_STATUS_NOT: u'待支付',
	ORDER_STATUS_CANCEL: u'已取消',
	ORDER_STATUS_PAYED_SUCCESSED: u'已支付',
	ORDER_STATUS_PAYED_NOT_SHIP: u'待发货',
	ORDER_STATUS_PAYED_SHIPED: u'已发货',
	ORDER_STATUS_SUCCESSED: u'已完成',
	ORDER_STATUS_REFUNDING: u'退款中',
	ORDER_STATUS_REFUNDED: u'退款成功',
	ORDER_STATUS_GROUP_REFUNDING: u'退款中',
	ORDER_STATUS_GROUP_REFUNDED: u'退款成功',
}

AUDIT_STATUS2TEXT = {
	ORDER_STATUS_REFUNDING: u'退款中',
	ORDER_STATUS_REFUNDED: u'退款成功',
	ORDER_STATUS_GROUP_REFUNDING: u'团购退款',
}

REFUND_STATUS2TEXT = {
	ORDER_STATUS_REFUNDING: u'退款中',
	ORDER_STATUS_REFUNDED: u'退款成功'
}

ORDERSTATUS2TEXT = STATUS2TEXT

ORDERSTATUS2MOBILETEXT = copy.copy(ORDERSTATUS2TEXT)
ORDERSTATUS2MOBILETEXT[ORDER_STATUS_PAYED_SHIPED] = u'待收货'

PAYMENT_INFO = u'下单'
DEFAULT_DATETIME = datetime.strptime('2000-01-01', '%Y-%m-%d')

THANKS_CARD_ORDER = 'thanks_card'  # 感恩贺卡类型的订单

ORDER_TYPE2TEXT = {
	PRODUCT_DEFAULT_TYPE: u'普通订单',
	PRODUCT_DELIVERY_PLAN_TYPE: u'套餐订单',
	PRODUCT_TEST_TYPE: u'测试订单',
	THANKS_CARD_ORDER: u'贺卡订单',
	PRODUCT_INTEGRAL_TYPE: u'积分商品',
	PRODUCT_VIRTUAL_TYPE: u'虚拟卡券订单',
	PRODUCT_WZCARD_TYPE: u'微众电子卡订单'
}

ORDER_SOURCE_OWN = 0
ORDER_SOURCE_WEISHOP = 1
ORDER_SOURCE2TEXT = {
	ORDER_SOURCE_OWN: u'本店',
	ORDER_SOURCE_WEISHOP: u'商城',
}

QUALIFIED_ORDER_STATUS = [ORDER_STATUS_PAYED_NOT_SHIP, ORDER_STATUS_PAYED_SHIPED, ORDER_STATUS_SUCCESSED]

class Order(models.Model):
	"""
	订单

	表名: mall_order
	"""
	order_id = models.CharField(max_length=100)  # 订单号
	webapp_user_id = models.IntegerField()  # WebApp用户的id
	webapp_id = models.CharField(max_length=20, verbose_name='店铺ID')  # webapp,订单成交的店铺id
	webapp_source_id = models.IntegerField(default=0, verbose_name='商品来源店铺ID')  # 订单内商品实际来源店铺的id，已废弃
	buyer_name = models.CharField(max_length=100)  # 购买人姓名
	buyer_tel = models.CharField(max_length=100)  # 购买人电话
	ship_name = models.CharField(max_length=100)  # 收货人姓名
	ship_tel = models.CharField(max_length=100)  # 收货人电话
	ship_address = models.CharField(max_length=200)  # 收货人地址
	area = models.CharField(max_length=100)
	status = models.IntegerField(default=ORDER_STATUS_NOT)  # 订单状态
	order_source = models.IntegerField(default=ORDER_SOURCE_OWN)  # 订单来源 0本店 1商城
	bill_type = models.IntegerField(default=ORDER_BILL_TYPE_NONE)  # 发票类型
	bill = models.CharField(max_length=100, default='')  # 发票信息
	remark = models.TextField()  # 备注
	supplier_remark = models.TextField()  # 供应商备注
	product_price = models.FloatField(default=0.0)  # 商品金额
	coupon_id = models.IntegerField(default=0)  # 优惠券id，用于支持返还优惠券
	coupon_money = models.FloatField(default=0.0)  # 优惠券金额
	postage = models.FloatField(default=0.0)  # 运费
	integral = models.IntegerField(default=0)  # 积分
	integral_money = models.FloatField(default=0.0)  # 积分对应金额
	member_grade = models.CharField(max_length=50, default='')  # 会员等级
	member_grade_discount = models.IntegerField(default=100)  # 折扣
	member_grade_discounted_money = models.FloatField(default=0.0)  # 折扣金额
	# 最终总金额: (product_price + postage) - (coupon_money + integral_money + weizoom_card_money + promotion_saved_money + edit_money)
	final_price = models.FloatField(default=0.0)
	pay_interface_type = models.IntegerField(default=-1)  # 支付方式
	express_company_name = models.CharField(max_length=50, default='')  # 物流公司名称
	express_number = models.CharField(max_length=100)  # 快递单号
	leader_name = models.CharField(max_length=256)  # 订单负责人
	customer_message = models.CharField(max_length=1024)  # 商家留言
	payment_time = models.DateTimeField(blank=True, default=DEFAULT_DATETIME)  # 订单支付时间
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	type = models.CharField(max_length=50, default=PRODUCT_DEFAULT_TYPE)  # 产品的类型
	integral_each_yuan = models.IntegerField(verbose_name='一元是多少积分', default=-1)
	reason = models.CharField(max_length=256, default='')  # 取消订单原因
	update_at = models.DateTimeField(auto_now=True)  # 订单信息更新时间 2014-11-11
	weizoom_card_money = models.FloatField(default=0.0)  # 微众卡抵扣金额
	promotion_saved_money = models.FloatField(default=0.0)  # 促销优惠金额
	edit_money = models.FloatField(default=0.0)  # 商家修改差价
	origin_order_id = models.IntegerField(default=0) # 原始订单id，用于微众精选拆单
	# origin_order_id=-1表示有子订单，>0表示有父母订单，=0为默认数据
	supplier = models.IntegerField(default=0) # 订单供货商，用于微众精选拆单
	is_100 = models.BooleanField(default=True) # 是否"coupon_id":"是快递100能够查询的快递(是否使用快递查询服务,在订单点击发货时来更新is_100的状态)
	delivery_time = models.CharField(max_length=50, default='')  # 配送时间字符串
	is_first_order = models.BooleanField(default=False) # 是否是用户的首单
	supplier_user_id = models.IntegerField(default=0) # 订单供货商user的id，用于系列拆单
	total_purchase_price = models.FloatField(default=0)  # 总订单采购价格
	# refund_money = models.FloatField(default=-1)     # 订单的退款金额
	member_card_money = models.FloatField(default=0.0)  # 会员卡抵扣金额  alter table mall_order add column member_card_money float default 0;
	third_party_money = models.FloatField(default=0.0)  # 第三方抵扣金额，如锦歌饭卡 duhao 20170320  alter table mall_order add column third_party_money float default 0;

	class Meta(object):
		db_table = 'mall_order'
		verbose_name = '订单'
		verbose_name_plural = '订单'

	@property
	def has_sub_order(self):
		"""
		判断该订单是否有子订单
		"""
		return self.origin_order_id == -1 and self.status > 0 #未支付的订单按未拆单显示

	@property
	def is_sub_order(self):
		return self.origin_order_id > 0

	@staticmethod
	def get_sub_order_ids(origin_order_id):
		orders = Order.objects.filter(origin_order_id=origin_order_id)
		sub_order_ids = [order.order_id for order in orders]
		return sub_order_ids


	@staticmethod
	def by_webapp_user_id(webapp_user_id, order_id=None):
		if order_id:
			return Order.objects.filter(Q(webapp_user_id__in=webapp_user_id) | Q(id__in=order_id)).filter(origin_order_id__lte=0)
		if isinstance(webapp_user_id, int) or isinstance(webapp_user_id, long):
			return Order.objects.filter(webapp_user_id=webapp_user_id, origin_order_id__lte=0)
		else:
			return Order.objects.filter(webapp_user_id__in=webapp_user_id, origin_order_id__lte=0)

	@staticmethod
	def by_webapp_id(webapp_id):
		# 微众商城代码
		# if str(webapp_id) == '3394':
		# 	return Order.objects.filter(webapp_id=webapp_id)
		if isinstance(webapp_id, list):
			return Order.objects.filter(webapp_id__in=webapp_id, origin_order_id__lte=0)
		else:
			return Order.objects.filter(webapp_id=webapp_id, origin_order_id__lte=0)
	##########################################################################
	# get_coupon: 获取定单使用的优惠券信息
	##########################################################################
	def get_coupon(self):
		if self.coupon_id == 0:
			return None
		else:
			from mall.promotion import models as coupon_model
			coupon = coupon_model.Coupon.objects.filter(id=self.coupon_id)
			if len(coupon) == 1:
				return coupon[0]
			return None

	##########################################################################
	# get_weizoom_card_id: 获取定单使用的微众卡的id
	##########################################################################
	# def get_used_weizoom_card_id(self):
	# 	if self.pay_interface_type == PAY_INTERFACE_WEIZOOM_COIN:
	# 		from market_tools.tools.weizoom_card import models as weizoom_card_model
	# 		weizoom_card_id = weizoom_card_model.WeizoomCardHasOrder.objects.get(
	# 			order_id=self.order_id).card_id
	# 		weizoom_card_number = weizoom_card_model.WeizoomCard.objects.get(
	# 			id=weizoom_card_id).weizoom_card_id
	# 		return weizoom_card_id, weizoom_card_number
	# 	else:
	# 		return None, None

	@staticmethod
	def fill_payment_time(orders):
		order_ids = [order.order_id for order in orders]
		order2paylog = dict(
			[
				(pay_log.order_id, pay_log)
				for pay_log in OrderOperationLog.objects.filter(
					order_id__in=order_ids, action='支付')])
		for order in orders:
			if order.order_id in order2paylog:
				order.payment_time = order2paylog[order.order_id].created_at
			else:
				order.payment_time = ''

	##########################################################################
	# get_orders_by_coupon_ids: 通过优惠券id获取订单列表
	##########################################################################
	@staticmethod
	def get_orders_by_coupon_ids(coupon_ids):
		if len(coupon_ids) == 0:
			return None
		else:
			# return list(Order.objects.filter(coupon_id__in=coupon_ids))
			orders = list(Order.objects.filter(coupon_id__in=coupon_ids))
			for i, order in enumerate(orders):
				if order.origin_order_id > 0:
					# 显示母订单数据
					orders[i] = Order.objects.filter(id=order.origin_order_id).first()
			return orders

	@property
	def get_pay_interface_name(self):
		return PAYTYPE2NAME.get(self.pay_interface_type, u'')

	@property
	def get_str_area(self):
		from tools.regional import views as regional_util
		if self.area:
			return regional_util.get_str_value_by_string_ids(self.area)
		else:
			return ''

	# 订单金额
	def get_total_price(self):
		return self.member_grade_discounted_money + self.postage

	# 支付金额
	# 1、如果是本店的订单，就显示 支付金额
	# 2、如果是商城下的单，显示  订单金额
	def get_final_price(self, webapp_id):
		if self.webapp_id == webapp_id:
			return self.final_price
		else:
			return self.get_total_price()

	# 订单使用积分
	# 1、如果是本店的订单，返回使用积分
	# 2、如果是商城下的单，返回空
	def get_use_integral(self, webapp_id):
		if self.webapp_id == webapp_id:
			return self.integral
		else:
			return ''

	@cached_property
	def get_products(self):
		return OrderHasProduct.objects.filter(order=self)

	@staticmethod
	def get_order_has_price_number(order):
		numbers = OrderHasProduct.objects.filter(
			order=order).aggregate(
			Sum("total_price"))
		number = 0
		if numbers["total_price__sum"] is not None:
			number = numbers["total_price__sum"]

		return number

	@staticmethod
	def get_order_has_product(order):
		relations = list(OrderHasProduct.objects.filter(order=order))
		product_ids = [r.product_id for r in relations]
		return Product.objects.filter(id__in=product_ids)

	@staticmethod
	def get_order_has_product_number(order):
		numbers = OrderHasProduct.objects.filter(
			order=order).aggregate(
			Sum("number"))
		number = 0
		if numbers["number__sum"] is not None:
			number = numbers["number__sum"]
		return number

	def get_status_text(self):
		return STATUS2TEXT[self.status]

	# add by bert at member_4.0
	@staticmethod
	def get_orders_final_price_sum(webapp_user_ids):
		numbers = Order.by_webapp_user_id(webapp_user_ids).filter(
			status__gte=ORDER_STATUS_PAYED_SUCCESSED).aggregate(
			Sum("final_price"))
		number = 0.0
		if numbers["final_price__sum"] is not None:
			number = numbers["final_price__sum"]
		return number

	@staticmethod
	def get_pay_numbers(webapp_user_ids):
		return Order.objects.filter(
			webapp_user_id__in=webapp_user_ids,
			status__gte=ORDER_STATUS_PAYED_SUCCESSED, origin_order_id__lte=0).count()

	@staticmethod
	def get_webapp_user_ids_pay_times_greater_than(webapp_id, pay_times):
		list_info = Order.by_webapp_user_id(webapp_id).filter(
			status__gte=ORDER_STATUS_PAYED_SUCCESSED).values('webapp_user_id').annotate(
			dcount=Count('webapp_user_id'))
		webapp_user_ids = []
		if list_info:
			for vlaue in list_info:
				if vlaue['dcount'] >= int(pay_times):
					webapp_user_ids.append(vlaue['webapp_user_id'])
		return webapp_user_ids

	@staticmethod
	def get_webapp_user_ids_pay_days_in(webapp_id, days):
		date_day = datetime.today()-timedelta(days=int(days))
		return [
			order.webapp_user_id for order in Order.objects.filter(
				webapp_id=webapp_id,
				status__gte=ORDER_STATUS_PAYED_SUCCESSED,
				payment_time__gte=date_day, origin_order_id__lte=0)]

	@property
	def get_express_details(self):
		if hasattr(self, '_express_details'):
			return self._express_details

		self._express_details = express_util.get_express_details_by_order(self)
		return self._express_details

	@property
	def get_express_detail_last(self):
		if len(self.get_express_details) > 0:
			return self.get_express_details[-1]

		return None

	@staticmethod
	def get_orders_from_webapp_user_ids(webapp_user_ids):
		return Order.objects.filter(webapp_user_id__in=webapp_user_ids)


def belong_to(webapp_id):
	"""
	webapp_id为request中的商铺id
	返回输入该id的所有Order的QuerySet
	"""
	# if user_id and not mall_type:
	# 	return Order.objects.filter(Q(webapp_id=webapp_id)|Q(supplier_user_id=user_id))
	# else:
	# 	return Order.objects.filter(webapp_id=webapp_id, origin_order_id__lte=0)
	sync_able_status_list = [ORDER_STATUS_PAYED_SUCCESSED,
							 ORDER_STATUS_PAYED_NOT_SHIP,
							 ORDER_STATUS_PAYED_SHIPED,
							 ORDER_STATUS_SUCCESSED]

	profile = UserProfile.objects.get(webapp_id=webapp_id)
	user_id = profile.user_id
	webapp_type = profile.webapp_type
	if webapp_type:
		orders = Order.objects.filter(webapp_id=webapp_id, origin_order_id__lte=0,webapp_user_id__gt=0)
	else:
		orders = Order.objects.filter(Q(webapp_id=webapp_id, origin_order_id__in=[-1,0],webapp_user_id__gt=0)|Q(supplier_user_id=user_id, origin_order_id__gt=0,status__in=sync_able_status_list,webapp_user_id__gt=0))

	group_order_relations = OrderHasGroup.objects.filter(webapp_id=webapp_id)
	if group_order_relations.count() > 0:
		group_order_ids = [r.order_id for r in group_order_relations]
		not_pay_group_order_ids = [order.order_id for order in Order.objects.filter(
			order_id__in=group_order_ids,
			status=ORDER_STATUS_NOT
			)
		]
		not_ship_group_on_order_ids = [order.order_id for order in Order.objects.filter(
			order_id__in=[
				r.order_id for r in group_order_relations.filter(
				group_status__in=[GROUP_STATUS_ON, GROUP_STATUS_failure])
				],
				status=ORDER_STATUS_PAYED_NOT_SHIP
			)]
		cancel_group_order_ids = [order.order_id for order in Order.objects.filter(
			order_id__in=[
				r.order_id for r in group_order_relations.filter(
				group_status__in=[GROUP_STATUS_OK, GROUP_STATUS_failure])
				],
				status=ORDER_STATUS_CANCEL,
				pay_interface_type=PAY_INTERFACE_WEIXIN_PAY
			)]
		orders = orders.exclude(order_id__in=not_pay_group_order_ids+not_ship_group_on_order_ids+cancel_group_order_ids)
	if not webapp_type:
		sync_order_order_ids = [order.order_id for order in orders.filter(supplier_user_id=user_id)]
		group_order_not_success_order_ids = [relation.order_id for relation in OrderHasGroup.objects.filter(
								order_id__in=sync_order_order_ids,
								group_status__in=[GROUP_STATUS_ON, GROUP_STATUS_failure])
							]
		orders = orders.exclude(order_id__in=group_order_not_success_order_ids)
	return orders


	# 微众商城代码
	# if webapp_id == '3394':
	# 	return Order.objects.filter(webapp_id=webapp_id)
	# else:
	# 	return Order.objects.filter(webapp_source_id=webapp_id, origin_order_id__lte=0)


Order.objects.belong_to = belong_to
#from django.db.models import signals
# def after_save_order(instance, created, **kwargs):
#	print kwargs


#signals.post_save.connect(after_save_order, sender=Order, dispatch_uid = "mall.after_save_order")

# added by chuter
########################################################################
# OrderPaymentInfo: 订单支付信息
########################################################################
class OrderPaymentInfo(models.Model):
	order = models.ForeignKey(Order)
	transaction_id = models.CharField(max_length=32)  # 交易号
	appid = models.CharField(max_length=64)  # 公众平台账户的AppId
	openid = models.CharField(max_length=100)  # 购买用户的OpenId
	out_trade_no = models.CharField(max_length=100)  # 该平台中订单号

	class Meta(object):
		db_table = 'mall_order_payment_info'
		verbose_name = '订单支付信息'
		verbose_name_plural = '订单支付信息'


class OrderHasRefund(models.Model):
	origin_order_id = models.IntegerField(default=0)  # 原始订单id，用于微众精选拆单
	delivery_item_id = models.IntegerField(default=0)  # 对应子订单主键id
	cash = models.FloatField(default=0.0)
	weizoom_card_money = models.FloatField(default=0.0)  # 微众卡抵扣金额
	integral = models.IntegerField(default=0)  # 积分
	integral_money = models.FloatField(default=0) # 积分对应金额,退款当时的
	coupon_money = models.FloatField(default=0)  # 优惠券金额
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	total = models.FloatField(default=0)  # 积分
	finished = models.BooleanField(default=False)  # 是否退款完成
	member_card_money = models.FloatField(default=0.0)  # 会员卡抵扣金额


	class Meta(object):
		db_table = 'mall_order_has_refund'
		verbose_name = '子订单退款信息'
		verbose_name_plural = '子订单退款信息'


class OrderHasProduct(models.Model):
	"""
	<order, product>关联
	"""
	order = models.ForeignKey(Order)
	product = models.ForeignKey(Product, related_name='product')
	product_name = models.CharField(max_length=256)  # 商品名
	product_model_name = models.CharField(max_length=256, default='')  # 商品规格名
	price = models.FloatField()  # 商品单价
	total_price = models.FloatField()  # 订单价格
	is_shiped = models.IntegerField(default=0)  # 是否出货
	number = models.IntegerField(default=1)  # 商品数量
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	promotion_id = models.IntegerField(default=0)  # 促销信息id
	promotion_money = models.FloatField(default=0.0)  # 促销抵扣金额
	grade_discounted_money = models.FloatField(default=0.0)  # 折扣金额
	integral_sale_id = models.IntegerField(default=0) #使用的积分应用的id
	origin_order_id = models.IntegerField(default=0) # 原始(母)订单id，用于微众精选拆单
	purchase_price = models.FloatField(default=0)  # 采购单价
	original_price = models.FloatField(default=0)  # 商品原价 add by bert 请勿随意赋值
	thumbnail_url = models.CharField(max_length=1024, default='')  # 商品图片
	weight = models.FloatField(default=0)
	product_model_name_texts = models.CharField(max_length=1024, default='[]')  # 规格名称的值
	product_model_id = models.IntegerField(default=0) # 规格ID
	# # 商品毛利润
	# product_profit = models.FloatField(default=0)
	# # 商品毛利率
	# product_profit_ratio = models.FloatField(default=0)
	#
	# # 社群计算价(即和社群结算的时候应该结算多少钱)
	# webapp_purchase_price = models.FloatField(default=0)

	class Meta(object):
		db_table = 'mall_order_has_product'

	# 填充特定的规格信息
	@property
	def get_specific_model(self):
		if hasattr(self, '_product_specific_model'):
			return self._product_specific_model
		else:
			try:
				self._product_specific_model = self.product.fill_specific_model(
					self.product_model_name)
				return self._product_specific_model
			except:
				return None

	# 如果规格有图片就显示，如果没有，使用缩略图
	@property
	def order_thumbnails_url(self):
		if hasattr(self, '_order_thumbnails_url'):
			return self._order_thumbnails_url
		else:
			if self.get_specific_model:
				for model in self.get_specific_model:
					if model['property_pic_url']:
						self._order_thumbnails_url = model['property_pic_url']
						return self._order_thumbnails_url
			# 没有图片使用商品的图片
			self._order_thumbnails_url = self.product.thumbnails_url
			return self._order_thumbnails_url


class OrderHasPromotion(models.Model):
	"""
	<order, promotion>关联
	"""
	order = models.ForeignKey(Order)
	webapp_user_id = models.IntegerField()  # WebApp用户的id
	promotion_id = models.IntegerField(default=0)  #促销id
	promotion_type = models.CharField(max_length=125, default='') #促销类型
	promotion_result_json = models.TextField(default='{}') #促销结果
	created_at = models.DateTimeField(auto_now_add=True) #创建时间
	integral_money = models.FloatField(default=0.0) # 积分抵扣钱数
	integral_count = models.IntegerField(default=0) # 使用的积分

	class Meta(object):
		db_table = 'mall_order_has_promotion'

	@property
	def promotion_result(self):
		data = json.loads(self.promotion_result_json)
		data['type'] = self.promotion_type
		return data


ORDER_CARD_DELETED = 0
ORDER_CARD_USED = 1
ORDER_CARD_REFUND = 2


ORDER_CARD_TYPE = {
}

class OrderCardInfo(models.Model):
	"""
	订单的微众卡信息
	"""
	order_id = models.CharField(max_length=100)  # 订单号
	trade_id = models.CharField(max_length=100)  # 交易号
	used_card = models.CharField(max_length=1024)   # 订单使用的微众卡
	created_at = models.DateTimeField(auto_now_add=True)  # 创建时间

	class Meta(object):
		db_table = 'mall_order_card_info'
		verbose_name = '订单微众卡相关信息'
		verbose_name_plural = '订单微众卡相关信息'



########################################################################
# OrderOperationLog:订单操作日志
########################################################################
class OrderOperationLog(models.Model):
	order_id = models.CharField(max_length=50)
	remark = models.CharField(max_length=128, default='')
	action = models.CharField(max_length=50)
	operator = models.CharField(max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_order_operation_log'
		verbose_name = '订单后台操作日志'
		verbose_name_plural = '订单后台操作日志'


########################################################################
# OrderStatusLog:订单状态日志
########################################################################
class OrderStatusLog(models.Model):
	order_id = models.CharField(max_length=50)
	from_status = models.IntegerField()
	to_status = models.IntegerField()
	remark = models.CharField(max_length=128, default='')
	operator = models.CharField(max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_order_status_log'
		verbose_name = '订单状态日志'
		verbose_name_plural = '订单状态日志'


# Termite GENERATED START: model
# MODULE START: PostageConfig
#########################################################################
# PostageConfig：运费配置
#########################################################################
class PostageConfig(models.Model):
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=256)  # 名称
	first_weight = models.FloatField(default=0.0)  # 首重
	first_weight_price = models.FloatField(default=0.0)  # 首重价格
	is_enable_added_weight = models.BooleanField(default=True)  # 是否启用续重机制
	added_weight = models.CharField(max_length=256, default='0')  # 续重
	added_weight_price = models.CharField(max_length=256, default='0')  # 续重价格
	display_index = models.IntegerField(default=1, db_index=True)  # 显示的排序
	is_used = models.BooleanField(default=True)  # 是否启用
	is_system_level_config = models.BooleanField(default=False)  # 是否是系统创建的不可修改的配置
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# v2
	update_time = models.DateTimeField(auto_now=True)  # 更新时间
	is_enable_special_config = models.BooleanField(default=True)  # 是否启用续重机制
	is_enable_free_config = models.BooleanField(default=True)  # 是否启用包邮机制
	is_deleted = models.BooleanField(default=False) #是否删除
	supplier_id = models.IntegerField(default=0) # 供货商的id

	class Meta(object):
		db_table = 'mall_postage_config'
		verbose_name = '运费配置'
		verbose_name_plural = '运费配置'

	def get_special_configs(self):
		return SpecialPostageConfig.objects.filter(postage_config=self)

	def get_free_configs(self):
		return FreePostageConfig.objects.filter(postage_config=self)

#########################################################################
# SpecialPostageConfig：特殊地区运费配置
#########################################################################


class SpecialPostageConfig(models.Model):
	owner = models.ForeignKey(User)
	postage_config = models.ForeignKey(PostageConfig)
	first_weight_price = models.FloatField(default=0.0)  # 首重价格
	added_weight_price = models.CharField(max_length=256)  # 续重价格
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# v2
	destination = models.CharField(max_length=512)  # 目的省份的id集合
	first_weight = models.FloatField(default=0.0)  # 首重
	added_weight = models.FloatField(default=0.0)  # 续重

	class Meta(object):
		db_table = 'mall_postage_config_special'
		verbose_name = '运费特殊配置'
		verbose_name_plural = '运费特殊配置'

	def get_special_has_provinces(self):
		return PostageConfigSpecialHasProvince.objects.filter(
			postage_config_special=self)

	def get_provinces_array(self):
		provinces = []
		for special_has_provinces in self.get_special_has_provinces():
			provinces.append(
				{'id': special_has_provinces.province.id, 'name':
				 special_has_provinces.province.name})
		return provinces

	@property
	def destination_str(self):
		province_ids = self.destination.split(',')
		provinces = area_util.get_provinces_by_ids(province_ids)
		self._dest_str = u', '.join(provinces)
		return self._dest_str


#########################################################################
# FreePostageConfig：特殊地区包邮配置
#########################################################################
class FreePostageConfig(models.Model):
	owner = models.ForeignKey(User)
	postage_config = models.ForeignKey(PostageConfig)
	destination = models.CharField(max_length=512)  # 目的省份的id集合
	condition = models.CharField(
		max_length=25,
		default='count')  # 免邮条件类型, 共有'count', 'money'两种
	condition_value = models.CharField(max_length=25)  # 免邮条件值
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_free_postage_config'
		verbose_name = '特殊地区包邮配置'
		verbose_name_plural = '特殊地区包邮配置'

	@property
	def destination_str(self):
		province_ids = self.destination.split(',')
		provinces = area_util.get_provinces_by_ids(province_ids)
		self._dest_str = u', '.join(provinces)
		return self._dest_str

#########################################################################
# 电子面单账号相关Model
#########################################################################

class ExpressBillAccount(models.Model):
	"""	
	电子面单账号
	"""
	owner = models.ForeignKey(User)
	express_name = models.CharField(max_length=50) #快递公司
	customer_name = models.CharField(max_length=256) #商户代码/编号/id
	customer_pwd = models.CharField(max_length=256)  #商户密码/密钥
	logistics_number = models.CharField(max_length=256) #密码串/月结号
	sendsite = models.CharField(max_length=256) #网点名称
	remark = models.TextField(null=True) #备注
	is_deleted = models.BooleanField(default=False) #是否删除
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_express_bill_account'

#########################################################################
# 发货人相关Model
#########################################################################

class Shipper(models.Model):
	"""	
	发货人信息
	"""
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=50) #发货人
	tel_number = models.CharField(max_length=15) #手机号
	province = models.CharField(max_length=50) #发货地区省
	city = models.CharField(max_length=50) #市
	district = models.CharField(max_length=512) #区/县
	address = models.CharField(max_length=256) #详细地址
	postcode = models.CharField(max_length=50) #邮政编码
	company_name = models.CharField(max_length=50) #单位名称
	remark = models.TextField(null=True) #备注
	is_active = models.BooleanField(default=False) #是否默认
	is_deleted = models.BooleanField(default=False) #是否删除
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_shipper'

#########################################################################
# PostageConfigSpecialHasProvince：运费特殊配置对应省份
# TODO: 该model在mall中已不再使用，后续删除之
#########################################################################
from tools.regional.models import Province


class PostageConfigSpecialHasProvince(models.Model):
	owner = models.ForeignKey(User)
	postage_config = models.ForeignKey(PostageConfig)
	postage_config_special = models.ForeignKey(SpecialPostageConfig)
	province = models.ForeignKey(Province)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_postage_config_special_has_province'
		verbose_name = '运费特殊配置对应省份'
		verbose_name_plural = '运费特殊配置对应省份'
# MODULE END: postagesettings
# Termite GENERATED END: model


#########################################################################
# ShoppingCart：购物车
#########################################################################
class ShoppingCart(models.Model):
	webapp_user_id = models.IntegerField(default=0)  # WebApp用户
	product = models.ForeignKey(Product)  # 商品
	product_model_name = models.CharField(max_length=125)  # 商品规格名
	count = models.IntegerField(default=1)  # 商品数量
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_shopping_cart'
		verbose_name = '购物车'
		verbose_name_plural = '购物车'


#########################################################################
# PurchaseDailyStatistics：每日购买统计
#########################################################################
class PurchaseDailyStatistics(models.Model):
	webapp_id = models.CharField(max_length=20, verbose_name='店铺ID')  # webapp
	webapp_user_id = models.IntegerField()  # WebApp用户的id
	order_id = models.CharField(max_length=100)  # 订单号
	order_price = models.FloatField(default=0.0)  # 订单金额
	date = models.CharField(max_length=50)  # 购买日期
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_purchase_daily_statistics'
		verbose_name = '购买统计'
		verbose_name_plural = '购买统计'


#########################################################################
# PayInterface：支付方式
#########################################################################
PAY_INTERFACE_ALIPAY = 0
PAY_INTERFACE_TENPAY = 1
PAY_INTERFACE_WEIXIN_PAY = 2
PAY_INTERFACE_COD = 9
PAY_INTERFACE_PREFERENCE = 10
PAY_INTERFACE_BEST_PAY = 11
PAY_INTERFACE_KANGOU = 12
###########################
# ADD BY BERT  AT 16
###########################
PAY_INTERFACE_WEIZOOM_COIN = 3

PAYTYPE2LOGO = {
	PAY_INTERFACE_ALIPAY: '/standard_static/img/mockapi/alipay.png',
	PAY_INTERFACE_TENPAY: '/standard_static/img/mockapi/tenpay.png',
	PAY_INTERFACE_WEIXIN_PAY: '/standard_static/img/mockapi/weixin_pay.png',
	PAY_INTERFACE_COD: '/standard_static/img/mockapi/cod.png',
	PAY_INTERFACE_WEIZOOM_COIN: '/standard_static/img/mockapi/wzcoin.png',
	PAY_INTERFACE_BEST_PAY: '/standard_static/img/mockapi/best_pay.png',
	PAY_INTERFACE_BEST_PAY: '/standard_static/img/mockapi/kangou.png',
}
PAYTYPE2NAME = {
	-1: u'',
	PAY_INTERFACE_PREFERENCE: u'优惠抵扣',
	PAY_INTERFACE_ALIPAY: u'支付宝',
	PAY_INTERFACE_TENPAY: u'财付通',
	PAY_INTERFACE_WEIXIN_PAY: u'微信支付',
	PAY_INTERFACE_COD: u'货到付款',
	PAY_INTERFACE_WEIZOOM_COIN: u"微众卡支付",
	PAY_INTERFACE_BEST_PAY:u"翼支付",
	PAY_INTERFACE_KANGOU:u"看购支付"
}
PAYNAME2TYPE = {
	u'优惠抵扣':PAY_INTERFACE_PREFERENCE,
	u'支付宝': PAY_INTERFACE_ALIPAY,
	u'财付通': PAY_INTERFACE_TENPAY,
	u'微信支付': PAY_INTERFACE_WEIXIN_PAY,
	u'货到付款': PAY_INTERFACE_COD,
	u"微众卡支付": PAY_INTERFACE_WEIZOOM_COIN,
	u"翼支付": PAY_INTERFACE_BEST_PAY,
	u"看购支付": PAY_INTERFACE_KANGOU
}

VALID_PAY_INTERFACES = [
	PAY_INTERFACE_WEIXIN_PAY,
	PAY_INTERFACE_COD,
	PAY_INTERFACE_WEIZOOM_COIN,
	PAY_INTERFACE_ALIPAY,
	PAY_INTERFACE_KANGOU,
	PAY_INTERFACE_BEST_PAY]
ONLINE_PAY_INTERFACE = [
	PAY_INTERFACE_WEIXIN_PAY,
	PAY_INTERFACE_ALIPAY,
	PAY_INTERFACE_WEIZOOM_COIN,
	PAY_INTERFACE_TENPAY,
	PAY_INTERFACE_KANGOU,
PAY_INTERFACE_BEST_PAY]


class PayInterface(models.Model):
	owner = models.ForeignKey(User)
	type = models.IntegerField()  # 支付接口类型
	description = models.CharField(max_length=50)  # 描述
	is_active = models.BooleanField(default=True)  # 是否启用
	related_config_id = models.IntegerField(default=0)  # 各种支付方式关联配置信息的id
	created_at = models.DateTimeField(auto_now_add=True)  # 创建日期

	class Meta(object):
		db_table = 'mall_pay_interface'
		verbose_name = '支付方式'
		verbose_name_plural = '支付方式'

	def pay(self, order, webapp_owner_id):
		if PAY_INTERFACE_ALIPAY == self.type:
			return '/webapp/alipay/?woid={}&order_id={}&related_config_id={}'.format(webapp_owner_id, order.order_id, self.related_config_id)
		elif PAY_INTERFACE_TENPAY == self.type:
			from account.models import UserProfile
			user_profile = UserProfile.objects.get(user_id=webapp_owner_id)
			call_back_url = "http://{}/tenpay/mall/pay_result/get/{}/{}/".format(
				user_profile.host,
				webapp_owner_id,
				self.related_config_id)
			notify_url = "http://{}/tenpay/mall/pay_notify_result/get/{}/{}/".format(
				user_profile.host,
				webapp_owner_id,
				self.related_config_id)
			pay_submit = TenpaySubmit(
				self.related_config_id,
				order,
				call_back_url,
				notify_url)
			tenpay_url = pay_submit.submit()

			return tenpay_url
		elif PAY_INTERFACE_COD == self.type:
			return './?woid={}&module=mall&model=pay_result&action=get&pay_interface_type={}&order_id={}'.format(
				webapp_owner_id,
				PAY_INTERFACE_COD,
				order.order_id)
		elif PAY_INTERFACE_WEIXIN_PAY == self.type:
			return '/webapp/wxpay/?woid={}&order_id={}&pay_id={}&showwxpaytitle=1'.format(
				webapp_owner_id,
				order.order_id,
				self.id)
		elif PAY_INTERFACE_BEST_PAY == self.type:
			return '/webapp/bestpay/?woid={}&order_id={}&pay_id={}&showwxpaytitle=1'.format(
				webapp_owner_id,
				order.order_id,
				self.id)
		# jz 2015-10-09
		# elif PAY_INTERFACE_WEIZOOM_COIN == self.type:
		# 	return './?woid={}&module=mall&model=weizoompay_order&action=pay&pay_interface_type={}&pay_interface_id={}&order_id={}'.format(
		# 		webapp_owner_id,
		# 		PAY_INTERFACE_WEIZOOM_COIN,
		# 		self.id,
		# 		order.order_id)
		else:
			return ''

	def parse_pay_result(self, request):
		error_msg = ''
		if PAY_INTERFACE_ALIPAY == self.type:
			order_id = request.GET.get('out_trade_no', None)
			trade_status = request.GET.get('result', '')
			is_trade_success = ('success' == trade_status.lower())
		elif PAY_INTERFACE_TENPAY == self.type:
			trade_status = int(request.GET.get('trade_status', -1))
			is_trade_success = (0 == trade_status)
			error_msg = request.GET.get('pay_info', '')
			order_id = request.GET.get('out_trade_no', None)
		elif PAY_INTERFACE_COD == self.type:
			is_trade_success = True
			order_id = request.GET.get('order_id')
		elif PAY_INTERFACE_WEIXIN_PAY == self.type:
			is_trade_success = True
			order_id = request.GET.get('order_id')
		else:
			pass

		#兼容改价
		try:
			order_id = order_id.split('-')[0]
		except:
			pass

		return {
			'is_success': is_trade_success,
			'order_id': order_id,
			'error_msg': error_msg
		}

	def parse_notify_result(self, request):
		error_msg = ''
		if PAY_INTERFACE_ALIPAY == self.type:
			config = UserAlipayOrderConfig.objects.get(
				id=self.related_config_id)
			notify = AlipayNotify(request, config)
		elif PAY_INTERFACE_TENPAY == self.type:
			notify = TenpayNotify(request)
		elif PAY_INTERFACE_WEIXIN_PAY == self.type:
			notify = WxpayNotify(request)
		else:
			notify = None

		if notify:
			order_id = notify.get_payed_order_id()
			is_trade_success = notify.is_pay_succeed()
			error_msg = notify.get_pay_info()
			reply_response = notify.get_reply_response()
			order_payment_info = notify.get_order_payment_info()
		else:
			order_id = ''
			is_trade_success = False
			error_msg = ''
			reply_response = ''
			order_payment_info = None

		#兼容改价
		try:
			order_id = order_id.split('-')[0]
		except:
			pass

		return {
			'order_id': order_id,
			'is_success': is_trade_success,
			'error_msg': error_msg,
			'reply_response': reply_response,
			'order_payment_info': order_payment_info
		}

	def get_str_name(self):
		return PAYTYPE2NAME[self.type]


import time
from account.models import UserWeixinPayOrderConfig
from core.wxapi import get_weixin_api
from core.wxapi.weixin_api import WeixinApiError
from core.wxapi.api_pay_delivernotify import PayDeliverMessage
from weixin.user.models import get_mpuser_access_token_by_appid


@receiver(mall_signals.post_ship_order, sender=Order)
def notify_weixin_pay_after_ship_order(order, **kwargs):
	if order.pay_interface_type != PAY_INTERFACE_WEIXIN_PAY:
		# 对非微信支付的其它支付方式不进行任何处理
		return

	try:
		order_payment_info = OrderPaymentInfo.objects.get(order=order)
	except:
		fatal_msg = u"对微信支付的订单({})获取对应的支付信息失败, cause:\n{}".format(
			order.id,
			unicode_full_stack())
		watchdog_fatal(fatal_msg)
		return
	#微信支付已经 去掉发货接口
	# mpuser_access_token = get_mpuser_access_token_by_appid(
	# 	order_payment_info.appid)
	# if mpuser_access_token is None:
	# 	fatal_msg = u"对微信支付的订单({})获取对应公众号授权信息失败, cause:\n{}".format(
	# 		order_payment_info.id,
	# 		unicode_full_stack())
	# 	watchdog_fatal(fatal_msg)
	# 	return

	# try:
	# 	weixin_pay_config = UserWeixinPayOrderConfig.objects.get(
	# 		app_id=mpuser_access_token.app_id)
	# except:
	# 	fatal_msg = u"对微信支付的订单({})获取对应支付配置信息失败, cause:\n{}".format(
	# 		order_payment_info.id,
	# 		unicode_full_stack())
	# 	watchdog_fatal(fatal_msg)
	# 	return

	# weixin_api = get_weixin_api(mpuser_access_token)
	# post_message = PayDeliverMessage(
	# 	mpuser_access_token.app_id,
	# 	weixin_pay_config.paysign_key,
	# 	order_payment_info.openid,
	# 	order_payment_info.transaction_id,
	# 	order_payment_info.out_trade_no,
	# 	int(time.time()),
	# 	1,  # 发货状态，1 表明成功，0 表明失败，失败时需要在 deliver_msg 填上失败原因
	# 	'',
	# 	)

	# try:
	# 	result = weixin_api.create_deliverynotify(post_message, True)
	# except WeixinApiError as api_error:
	# 	fatal_msg = u"调用微信发货通知接口失败，失败信息:\n{}".format(api_error.__unicode__())
	# 	watchdog_fatal(fatal_msg)
	# except:
	# 	fatal_msg = u"调用微信发货通知接口失败, cause:\n{}".format(unicode_full_stack())
	# 	watchdog_fatal(fatal_msg)


#########################################################################
# WeizoomMall: 微众商城用户
#########################################################################
class WeizoomMall(models.Model):
	webapp_id = models.CharField(
		max_length=20,
		verbose_name='webapp id',
		db_index=True,
		unique=True)
	is_active = models.BooleanField(default=True, verbose_name='是否微众商城')
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'weizoom_mall'
		verbose_name = '微众商城用户'
		verbose_name_plural = '微众商城用户'

	# todo 微众商城代码
	@staticmethod
	def is_weizoom_mall(webapp_id):
		# if WeizoomMall.objects.filter(webapp_id=webapp_id).count() > 0:
		# 	return WeizoomMall.objects.filter(webapp_id=webapp_id)[0].is_active
		# else:
		return False

#########################################################################
# WeizoomMallHasOtherMallProduct: 微众商城用户共享其它商家的商品
#########################################################################


class WeizoomMallHasOtherMallProduct(models.Model):
	weizoom_mall = models.ForeignKey(WeizoomMall)
	webapp_id = models.CharField(max_length=20, verbose_name='店铺ID')  # webapp
	is_checked = models.BooleanField(
		default=False,
		verbose_name='是否审核通过')  # 是否审核通过
	product_id = models.IntegerField(default=-1, verbose_name='商品ID')  # 商品id
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'weizoom_mall_has_other_mall_product'
		verbose_name = '微众商城用户共享其它商家的商品'
		verbose_name_plural = '微众商城用户共享其它商家的商品'

#########################################################################
# WeizoomMallHasOtherMallProduct: 微众商城产生的其它商户商品的订单信息
#########################################################################


class WeizoomMallHasOtherMallProductOrder(models.Model):
	weizoom_mall = models.ForeignKey(WeizoomMall)
	webapp_id = models.CharField(max_length=20, verbose_name='店铺ID')  # 商品对应店铺ID
	order_id = models.CharField(max_length=256)  # 订单号
	product_id = models.IntegerField(default=-1, verbose_name='商品ID')  # 商品id
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'weizoom_mall_has_other_mall_product_order'
		verbose_name = '微众商城产生的其它商户商品的订单信息'
		verbose_name_plural = '微众商城产生的其它商户商品的订单信息'

	@staticmethod
	def create(webapp_id, product, order):
		# if WeizoomMall.objects.filter(webapp_id=webapp_id).count() > 0:
		weizoom_mall = WeizoomMall.objects.filter(webapp_id=webapp_id)[0]
		# 	if WeizoomMallHasOtherMallProduct.objects.filter(weizoom_mall=weizoom_mall, product_id=product_id).count() > 0:
		# partner_webapp_id = WeizoomMallHasOtherMallProduct.objects.filter(
		# 	weizoom_mall=weizoom_mall,
		# 	product_id=product_id)[0].webapp_id

		from account.models import UserProfile
		user_profile = UserProfile.objects.get(user_id=product.owner_id)
		if webapp_id != user_profile.webapp_id:
			WeizoomMallHasOtherMallProductOrder.objects.get_or_create(
				weizoom_mall=weizoom_mall,
				webapp_id=user_profile.webapp_id,
				order_id=order.order_id,
				product_id=product.id
				)

	@staticmethod
	def get_order_ids_for(webapp_id):
		return [
			weizoom_mall_order.order_id for weizoom_mall_order in WeizoomMallHasOtherMallProductOrder.objects.filter(
				webapp_id=webapp_id)]

	@staticmethod
	def get_orders_weizoom_mall_for_other_mall(webapp_id):
		return [
			weizoom_mall_order.order_id for weizoom_mall_order in WeizoomMallHasOtherMallProductOrder.objects.filter(
				weizoom_mall__webapp_id=webapp_id)]


#########################################################################
# UserHasOrderFilter: 用户对应的订单筛选条件
#########################################################################
class UserHasOrderFilter(models.Model):
	owner = models.ForeignKey(User)
	filter_name = models.CharField(max_length=1024, verbose_name='名称')
	filter_value = models.CharField(max_length=1024, verbose_name='筛选条件')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

	class Meta(object):
		db_table = 'user_has_order_filter'
		verbose_name = '用户对应的订单筛选条件'
		verbose_name_plural = '用户对应的订单筛选条件'

	@staticmethod
	def create(user, filter_name, filter_value):
		return UserHasOrderFilter.objects.create(
			owner=user,
			filter_name=filter_name,
			filter_value=filter_value
		)

	# value ： status:5^4^3|pay_interface_type:2|type:object|source:0
	#
	# 订单状态：status ()
	# 支付方式：pay_interface_type (支付宝0，财付通1，微信支付2，微众卡支付3，货到付款9，优惠抵扣10)
	# 来源： source (商户1，本店0)
	# 订单类型：type (普通object，套餐delivery，测试test)
	# return 查询参数的dict，和source的值
	@staticmethod
	def get_filter_params_by_value(value):
		str_param = value.strip()
		params = None
		source = None
		if len(value) > 0:
			params = dict()
			items = str_param.split('|')
			for item in items:
				try:
					attr = item.split(':')
					if attr[0] == 'source':
						source = int(attr[1])
					else:
						values = attr[1].split('^')
						if len(values) > 1:
							params[attr[0]+'__in'] = values
						else:
							params[attr[0]] = attr[1]
				except:
					pass

		return params, source


#########################################################################
# ExpressDelivery: 物流名称管理
#########################################################################
class ExpressDelivery(models.Model):
	owner = models.ForeignKey(User)
	display_index = models.IntegerField(default=1, db_index=True)  # 显示的排序
	name = models.CharField(max_length=1024, verbose_name='名称')
	express_number = models.CharField(max_length=1024, verbose_name='编号')
	express_value = models.CharField(max_length=1024, verbose_name='快递value')
	remark = models.TextField(default='', verbose_name='备注')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

	class Meta(object):
		db_table = 'mall_express_delivery'
		verbose_name = '物流名称'
		verbose_name_plural = '物流名称'


class MemberProductWishlist(models.Model):
	owner = models.ForeignKey(User)
	member_id = models.IntegerField(default=0) #会员ID
	product_id = models.IntegerField(default=0) #商品ID
	is_collect = models.BooleanField(default=False) #商品是否被收藏
	add_time = models.DateTimeField(auto_now_add=True) #商品收藏的时间
	delete_time = models.DateTimeField(blank=True, default=DEFAULT_DATETIME) #商品取消收藏的时间
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_member_product_wishlist'
		verbose_name = '会员商品收藏列表'
		verbose_name_plural = '会员商品收藏列表'


# #######        订单评价实现        ####
SCORE = (
	('1', '1分'),
	('2', '2分'),
	('3', '3分'),
	('4', '4分'),
	('5', '5分'),
)


#####################
# 订单评价
#####################
class OrderReview(models.Model):
	owner_id = models.IntegerField()  # 订单的主人
	order_id = models.IntegerField()  # 订单号
	member_id = models.IntegerField()  # 会员ID
	serve_score = models.CharField(  # 服务态度评分
		max_length=1,
		choices=SCORE,
		default='5'
	)
	deliver_score = models.CharField(  # 发货速度评分
		choices=SCORE,
		max_length=1,
		default='5'
	)
	process_score = models.CharField(  # 物流服务评分
		max_length=1,
		choices=SCORE,
		default='5'
	)

	class Meta(object):
		db_table = 'mall_order_review'
		verbose_name = '用户对应的订单评价'
		verbose_name_plural = '用户对应的订单评价'


#####################
# 订单商品评价
#####################
# 审核状态
PRODUCT_REVIEW_STATUS = (
	('-1', '已屏蔽'),
	('0', '待审核'),
	('1', '已通过'),
	('2', '通过并置顶'),
)


class ProductReview(models.Model):
	member_id = models.IntegerField()
	owner_id = models.IntegerField()
	order_review = models.ForeignKey(OrderReview)
	order_id = models.IntegerField()  # 订单ID
	product_id = models.IntegerField()
	order_has_product = models.ForeignKey(OrderHasProduct)
	product_score = models.CharField(  # 商品评分
		max_length=1,
		choices=SCORE,
		default='5')
	review_detail = models.TextField()  # 评价详情
	created_at = models.DateTimeField(auto_now=True)  # 评价时间
	top_time = models.DateTimeField(blank=True, default=DEFAULT_DATETIME) # 置顶时间
	status = models.CharField(  # 审核状态
		max_length=2,
		choices=PRODUCT_REVIEW_STATUS,
		default='0')

	class Meta(object):
		db_table = 'mall_product_review'
		verbose_name = '用户对应的商品评价'
		verbose_name_plural = '用户对应的商品评价'

# #######        /订单评价实现        ####


class ProductReviewPicture(models.Model):
	product_review = models.ForeignKey(ProductReview)
	order_has_product = models.ForeignKey(OrderHasProduct)
	att_url = models.CharField(max_length=1024)  # 附件地址

	class Meta:
		verbose_name = "商品评价图片"
		verbose_name_plural = "商品评价图片"
		db_table = "mall_product_review_picture"

class MallOrderFromSharedRecord(models.Model):
	"""
	add by bert 记录通过分享链接下单 订单号和分享者信息
	"""
	order_id = models.IntegerField()
	fmt = models.CharField(default='', max_length=255)
	url = models.CharField(default='', max_length=255)
	is_updated = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta:
		verbose_name = "通过分享链接订单"
		verbose_name_plural = "通过分享链接订单"
		db_table = "mall_order_from_shared_record"
# #######        供货商实现        ####
# 五五分成
SUPPLIER_TYPE_DIVIDE = 0
# 零售返点
SUPPLIER_TYPE_RETAIL = 1
# 固定低价
SUPPLIER_TYPE_FIXED = 2
# 普通供货商
SUPPLIER_TYPE_NORMAL = -1

# 结算账期  1【自然月】   2【15天】   3【自然周】
SUPPLIER_SETTLEMENT_PERIOD_MONTH = 1
SUPPLIER_SETTLEMENT_PERIOD_15TH_DAY = 2
SUPPLIER_SETTLEMENT_PERIOD_WEEK = 3


class Supplier(models.Model):
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=200)  # 供货商名称
	responsible_person = models.CharField(max_length=100)  # 供货商负责人
	supplier_tel = models.CharField(max_length=100)  # 供货商电话
	supplier_address = models.CharField(max_length=256)  # 供货商地址
	remark = models.CharField(max_length=256)  # 备注
	type = models.IntegerField(default=SUPPLIER_TYPE_NORMAL)
	is_delete = models.BooleanField(default=False)  # 是否已经删除
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	settlement_period = models.IntegerField(default=SUPPLIER_SETTLEMENT_PERIOD_MONTH)

	class Meta(object):
		verbose_name = "供货商"
		verbose_name_plural = "供货商操作"
		db_table = "mall_supplier"



class SupplierPostageConfig(models.Model):
	supplier_id = models.IntegerField(default=0)
	product_id = models.IntegerField(default=0)
	condition_type = models.CharField(
		max_length=25,
		default='money')  # 免邮条件类型, 共有'count', 'money'两种
	condition_money = models.DecimalField(max_digits=65, decimal_places=2, null=True) #免邮的消费金额
	condition_count = models.IntegerField(default=0)  # 免邮商品数量
	postage = models.DecimalField(max_digits=65, decimal_places=2, null=True) #邮费
	status = models.BooleanField(default=True) # 是否启用邮费配置
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'mall_supplier_postage_config'
		verbose_name = '供货商邮费配置'
		verbose_name_plural = '供货商邮费配置'



# 订单与团购活动的关联
GROUP_STATUS_ON = 0  # 团购进行中
GROUP_STATUS_OK = 1  # 团购成功
GROUP_STATUS_failure = 2  # 团购失败


class OrderHasGroup(models.Model):
	"""
	<order, group>关联
	"""
	order_id = models.CharField(max_length=100)  # 订单号(order中的order_id
	group_id = models.CharField(max_length=100)
	activity_id = models.CharField(max_length=100)
	group_status = models.IntegerField(default=GROUP_STATUS_ON)
	webapp_user_id = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True) #创建时间
	webapp_id = models.CharField(max_length=20, verbose_name='店铺ID')  # webapp,订单成交的店铺id

	class Meta(object):
		db_table = 'mall_order_has_group'

class WeizoomHasMallProductRelation(models.Model):
	owner = models.ForeignKey(User) # 微众系列的商户
	mall_id = models.IntegerField() # 供货商的owner_id
	mall_product_id = models.IntegerField() # 供货商商品
	weizoom_product_id = models.IntegerField() # 微众系列上架供货商的商品
	is_updated = models.BooleanField(default=False) # 是否需要更新
	is_deleted = models.BooleanField(default=False) # 供货商是否下架了商品
	sync_time = models.DateTimeField(auto_now_add=True) # 微众系列同步商品的时间
	delete_time = models.DateTimeField(auto_now=True) # 商品的失效时间
	delete_type = models.BooleanField(default=False) # 删除类型，True为自营平台自己删除，False为供货商操作商品连带删除
	created_at = models.DateTimeField(auto_now_add=True) # 添加时间

	class Meta(object):
		verbose_name = "微众系列同步其他商户商品的关系记录表"
		verbose_name_plural = "微众系列同步其他商户商品的关系"
		db_table = "mall_weizoom_has_mall_product_relation"


class WxCertSettings(models.Model):
	"""
		存储微信每个帐号的证书文件地址
	"""
	owner = models.ForeignKey(User) #活动所有者
	cert_path = models.CharField(default="", max_length=1024) #证书
	up_cert_path = models.CharField(default="", max_length=2048) #证书

	key_path = models.CharField(default="", max_length=1024) #证书key
	up_key_path = models.CharField(default="", max_length=2048) #证书key

	class Meta(object):
		verbose_name = "微信证书文件地址"
		verbose_name_plural = "微信证书文件地址"
		db_table = "mall_weixin_cert"


class ProductSearchRecord(models.Model):
	woid = models.IntegerField()
	webapp_user_id = models.IntegerField()
	content = models.TextField()
	is_deleted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		verbose_name = "商品搜索记录"
		verbose_name_plural = "商品搜索记录"
		db_table = "mall_product_search_record"

PP_STATUS_OFF = 0 #商品下架(待售)
PP_STATUS_ON = 1 #商品上架
PP_STATUS_DELETE = -1 #商品删除 不在当前供应商显示
PP_STATUS_ON_POOL = 2 #商品在商品池中显示

PP_TYPE_SYNC = 1 #从其他商品池同步而来的商品
PP_TYPE_CREATE = 2 #商户自身创建的商品

class ProductPool(models.Model):
	woid = models.IntegerField() #自营平台woid
	product_id = models.IntegerField() #商品管理上传的商品id
	status = models.IntegerField(default=PP_STATUS_ON_POOL) #商品状态
	type = models.IntegerField(default=PP_TYPE_SYNC) #商品类型
	display_index = models.IntegerField(default=0, blank=True)  # 显示的排序
	sync_at = models.DateTimeField(blank=True,null=True)  # 上架时间
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# 是否处理过cps推广
	is_cps_promotion_processed = models.BooleanField(default=False)

	class Meta(object):
		verbose_name = "商品池商品"
		verbose_name_plural = "商品池商品"
		db_table = "product_pool"

def product_belong_to(mall_type, owner, type):
	if mall_type and type in [PRODUCT_SHELVE_TYPE_OFF, PRODUCT_SHELVE_TYPE_ON]:
		if type == PRODUCT_SHELVE_TYPE_OFF:
			status = PP_STATUS_OFF
		else:
			status = PP_STATUS_ON
		product_pool_ids = ProductPool.objects.filter(woid=owner.id, status=status).values_list('product_id', flat=True)

		products = Product.objects.filter(
				Q(owner=owner,
				shelve_type=type,
				is_deleted=False)|Q(id__in=product_pool_ids))
	else:
		products = Product.objects.filter(
				owner=owner,
				shelve_type=type,
				is_deleted=False)

	return products

Product.objects.belong_to = product_belong_to


class PandaHasProductRelation(models.Model):
	"""
	panda同步过来的商品中间关系
	"""
	panda_product_id = models.IntegerField()
	weapp_product_id = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
			verbose_name = "panda同步过来的商品中间关系"
			verbose_name_plural = "panda同步过来的商品中间关系"
			db_table = "panda_has_product_relation"


class ProductLimitPurchasePrice(models.Model):
	"""
	8000商品限时结算价格
	"""
	product_id = models.IntegerField(),
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()

	class Meta:
		verbose_name = "商品池商品"
		verbose_name_plural = "商品池商品"
		db_table = "product_limit_purchase_price"

# 一级分类
FIRST_CLASSIFICATION = 1
# 二级分类
SECONDARY_CLASSIFICATION = 2
# 分类上线（类似于未删除）
CLASSIFICATION_ONLINE = 1
# 分类下线（类似于删除）
CLASSIFICATION_OFFLINE = 0

class Classification(models.Model):
	"""
	商品分类
	"""
	owner_id = models.IntegerField(default=0)
	name = models.CharField(max_length=1024) #分类名
	level = models.IntegerField(default=-1) #分类等级
	status = models.IntegerField(default=1) # 1表示上线0表示下线
	father_id = models.IntegerField(default=-1) #父级分类id
	product_count = models.IntegerField(default=0) #分类下的商品数量
	note = models.CharField(max_length=1024, default='') #分类备注
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		verbose_name = "商品分类"
		verbose_name_plural = "商品分类"
		db_table = "mall_classification"

class ClassificationHasProduct(models.Model):
	"""
	商品分类拥有商品的关系表
	"""
	classification = models.ForeignKey(Classification)
	product_id = models.IntegerField(default=-1)
	woid = models.IntegerField(default=-1)
	display_index = models.IntegerField(default=-1)
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		verbose_name = "商品分类与商品的关系"
		verbose_name_plural = "商品分类与商品的关系"
		db_table = "mall_classification_has_product"


class ClassificationQualification(models.Model):
	"""
	商品分类配置的特殊资质
	"""
	classification = models.ForeignKey(Classification)
	name = models.CharField(max_length=48, default='') #资质名称
	created_at = models.DateTimeField(auto_now_add=True) #创建时间

	class Meta(object):
		db_table = 'mall_classification_qualification'


class SupplierDivideRebateInfo(models.Model):
	"""
	供货商五五分成信息(不一定是五成)--目前只有首月五五分成,以后可能扩展成,不同额度不同返点.
	"""
	# 供货商id
	supplier_id = models.IntegerField()
	# 钱额度
	divide_money = models.IntegerField()
	# 基础返点
	basic_rebate = models.IntegerField()
	# 在此额度内返点
	rebate = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)
	is_deleted = models.BooleanField(default=False)

	class Meta(object):
		db_table = 'supplier_divide_rebate_info'


class SupplierRetailRebateInfo(models.Model):
	"""
	零售返点的供货商的返点信息(包括团购)
	"""
	# 供货商id
	supplier_id = models.IntegerField()
	# 平台id(如果支持团购) 0的表示改供货商的基础扣点; 0的默认值表示改供货商的基础扣点
	# 如果有owner_id说明该扣点是属于团购扣点
	owner_id = models.IntegerField(default=0)
	# 扣点
	rebate = models.IntegerField()
	created_at = models.DateTimeField(auto_now_add=True)
	is_deleted = models.BooleanField(default=False)

	class Meta(object):
		db_table = 'supplier_retail_rebate_info'

class ProductLimitZoneTemplate(models.Model):
	"""
	商品仅售和禁售的模板
	"""
	owner = models.ForeignKey(User)
	name = models.CharField(max_length=64)  # 模板名称
	provinces = models.CharField(max_length=1024) # 所有省id
	cities = models.CharField(max_length=4096) # 所有城市id
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间
	# is_deleted = models.BooleanField(default=False)

	class Meta(object):
		verbose_name = "商品仅售和禁售的模板"
		verbose_name_plural = "商品仅售和禁售的模板"
		db_table = "mall_product_limit_zone_template"


class ProductLabelGroup(models.Model):
	"""
	商品标签的分类（分组）
	"""
	owner_id = models.IntegerField(default=0)
	name = models.CharField(max_length=256, null=True)
	is_deleted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_product_label_group'
		verbose_name = '标签分类'


class ProductLabel(models.Model):
	"""
	商品标签
	"""
	label_group_id = models.IntegerField(default=0)
	owner_id = models.IntegerField(default=0)
	name = models.CharField(max_length=256)
	created_at = models.DateTimeField(auto_now_add=True)
	is_deleted = models.BooleanField(default=False)

	class Meta(object):
		db_table = 'mall_product_label'
		verbose_name = '标签'


class ProductHasLabel(models.Model):
	"""
	商品有哪些标签
	"""
	product_id = models.IntegerField(null=False)
	label_id = models.IntegerField(null=False)
	# -1表示改标签是商品自己的标签不是类目的标签
	classification_id = models.IntegerField(default=-1)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_product_has_label'


class ClassificationHasLabel(models.Model):
	"""
	商品类目（分类)有什么标签
	"""
	classification_id = models.IntegerField(default=-1)
	label_id = models.CharField(max_length=1024, default='')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta(object):
		db_table = 'mall_classification_has_label'

#########################cps models###########################

PROMOTING = 1 # 推广中
PROMOTE_OVER = 2 # 推广结束

class PromoteDetail(models.Model): #推广明细
	product_id = models.IntegerField() #weapp product id
	promote_status = models.IntegerField(default=PROMOTING)#推广状态 （未推广，推广中，已结束）   推广设置中展示：未推广，已结束。推广明细中：推广中，已结束
	promote_money = models.FloatField(default=0) #推广费用/件
	promote_stock =  models.IntegerField(default=1) #推广库存
	promote_time_from = models.DateTimeField(default=datetime.now()) #开始时间
	promote_time_to = models.DateTimeField(default=datetime.now()) #结束时间
	promote_sale_count = models.IntegerField(default=0) #推广销量
	promote_total_money = models.FloatField(default=0) #推广费用总费用
	is_new = models.BooleanField(default=True) #是否已读
	created_at = models.DateTimeField(auto_now_add=True) #创建时间
	
	class Meta(object):
		db_table = 'mall_promote_detail'

##############################################################