# -*- coding: utf-8 -*-
#__auth__='justiing'
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Sum

#邮件部分
from core.sendmail import sendmail


import sys
import os

reload(sys)
sys.setdefaultencoding('utf-8')

from datetime import datetime,timedelta,date
from mall.models import *
from tools.regional.models import *
from utils import dateutil

import xlsxwriter

DATE_FORMAT="%Y-%m-%d"


class Command(BaseCommand):
	help = "send zypt order by area"
	args = ''
	
	def handle(self,*args, **options):
			print args

			week_day = datetime.now().weekday()
			current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

			first_day = "{}-01 00:00:00".format(current_time.rsplit('-',1)[0])
			first_datetime = dateutil.parse_datetime(first_day)
			file_path = 'order_by_area.xlsx'
			
			workbook   = xlsxwriter.Workbook(file_path)
			table = workbook.add_worksheet()
			alist = [u"省级", u"市级", u"销售额"]


			table.write_row('A1',alist)

			id2provice_names = dict([(p.id, p.name) for p in Province.objects.all()])

			tmp_line = 1
			print (first_datetime, '--', datetime.now())
			for c in City.objects.all():
				product_price_sum = Order.objects.filter(status__in=[2,3,5], payment_time__gte= first_datetime, payment_time__lte=datetime.now(), area__startswith="%s_%s" % (c.province_id, c.id)).aggregate(Sum('product_price'))['product_price__sum'] 
				if product_price_sum:
					tmp_line += 1
					tmp_list = [id2provice_names[c.province_id], c.name, round(product_price_sum, 2)]
					table.write_row('A{}'.format(tmp_line),tmp_list)

			workbook.close()

			receivers = ['zhangzhiyong@weizoom.com', 'guoyucheng@weizoom.com']
			mode = ''
			if len(args) == 1:
				if args[0] == 'test':
					mode = 'test'
					receivers = ['guoyucheng@weizoom.com']
			title = u'微众自运营平台当月按区域统计订单金额{}'.format(current_time)
			content = u'您好，微众自运营平台当月按区域统计订单金额'

			sendmail(receivers, title, content, mode, file_path)
