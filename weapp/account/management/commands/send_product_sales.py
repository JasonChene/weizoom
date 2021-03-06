# -*- coding: utf-8 -*-
#__auth__='justiing'
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Sum, F
#邮件部分
from core.sendmail import sendmail


import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os
from django.contrib.auth.models import User
from tools.regional.models import *
from modules.member.models import Member,MemberHasSocialAccount,MemberIntegralLog,MemberHasTag,MemberGrade
from mall.models import *
from mall.promotion.models import *
from member.member_list import get_member_orders,get_member_info,get_member_ship_info
from weixin.user.models import ComponentAuthedAppid,ComponentAuthedAppidInfo
from account.models import UserProfile
from mall.product import utils
import xlsxwriter

from datetime import datetime,timedelta,date
DATE_FORMAT="%Y-%m-%d"
sales_order_status = [ORDER_STATUS_PAYED_NOT_SHIP, ORDER_STATUS_PAYED_SHIPED, ORDER_STATUS_SUCCESSED, ORDER_STATUS_REFUNDING, ORDER_STATUS_GROUP_REFUNDING]


class Command(BaseCommand):
	help = "send product sales email"
	args = ''
	
	def handle(self,*args, **options):
			print args

			week_day = datetime.now().weekday()
			current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

			first_day = "{}-01".format(current_time.rsplit('-',1)[0])

			file_path = 'product_pool_sales.xlsx'
			workbook   = xlsxwriter.Workbook(file_path)
			table = workbook.add_worksheet()
			alist = [u'商品', u'供货商', u'分类', u'当月销量数量', u'当月销量金额', u'累计销售数量', u'累计销售金额']
			table.write_row('A1',alist)
			pool_weapp_profile = UserProfile.objects.filter(webapp_type=2).first()
			owner_pool = User.objects.get(id=pool_weapp_profile.user_id)

			product_ids = Product.objects.filter(owner=owner_pool, shelve_type__in=(PRODUCT_SHELVE_TYPE_ON,PRODUCT_SHELVE_TYPE_OFF)).values_list('id', flat=True)
			manager_supplier_ids2name = dict([(s.id, s.name) for s in Supplier.objects.filter(owner_id=pool_weapp_profile.user_id)])

			supplier_ids2name = {}
			product_id2store_name, product_id2sync_time = utils.get_sync_product_store_name(product_ids)
			#添加分类
			product_id2classification = {}
			relations = ClassificationHasProduct.objects.filter(product_id__in=product_ids)
			for r in relations:
				product_id2classification[r.product_id] = r.classification.name
			tmp_line = 1
			for product_id in product_ids:
				tmp_line += 1
				product = Product.objects.get(id=product_id)
				product_name = product.name

				store_name = manager_supplier_ids2name.get(product.supplier, "")
				if store_name:
					is_sync = True
				if not store_name:
					store_name = supplier_ids2name[product.supplier] if product.supplier and supplier_ids2name.has_key(product.supplier) else product_id2store_name.get(product.id, "")
					is_sync = product_id2store_name.has_key(product.id)
				if store_name:
					if is_sync:
						supplier_name_export = u'同[{}]'.format(store_name)
					else:
						supplier_name_export = u'自[{}]'.format(store_name)
				else:
					supplier_name_export = ''

				product_sales= 0 
				weizoom_card = 0.0
				coupon_money = 0.0
				integral_money = 0.0
				cash = 0.0
				total = 0.0

				order_has_products = OrderHasProduct.objects.filter(product_id=product_id, order__origin_order_id__lte=0, order__status__in=sales_order_status, order__payment_time__gte=first_day)
				product_sales = order_has_products.aggregate(Sum('number'))['number__sum']
				product_sales = product_sales if product_sales else 0
				product_price_sum = order_has_products.aggregate(Sum('total_price'))['total_price__sum']
				product_price_sum = product_price_sum if product_price_sum else 0.0

				all_order_has_products = OrderHasProduct.objects.filter(product_id=product_id, order__origin_order_id__lte=0, order__status__in=sales_order_status)
				all_product_sales = all_order_has_products.aggregate(Sum('number'))['number__sum']
				all_product_sales = all_product_sales if all_product_sales else 0
				all_product_sum = all_order_has_products.aggregate(Sum('total_price'))['total_price__sum']
				all_product_sum = all_product_sum if all_product_sum else 0.0
				tmp_list = [product_name, supplier_name_export, product_id2classification.get(product_id,''), product_sales, round(product_price_sum,2), all_product_sales, round(all_product_sum,2)]
				table.write_row('A{}'.format(tmp_line),tmp_list)

			workbook.close()

			receivers = ['houtingfei@weizoom.com', 'zhangzhiyong@weizoom.com', 'guoyucheng@weizoom.com', 'mengqi@weizoom.com']
			mode = ''
			if len(args) == 1:
				if args[0] == 'test':
					mode = 'test'
			title = u'微众自运营平台商品销量{}'.format(current_time)
			content = u'您好，这是本月统计的微众自运营平台商品销量'

			sendmail(receivers, title, content, mode, file_path)

