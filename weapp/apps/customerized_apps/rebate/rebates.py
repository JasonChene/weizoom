# -*- coding: utf-8 -*-
import json
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.db.models import F
from django.contrib.auth.decorators import login_required
from core import resource
from core import paginator
from core.exceptionutil import unicode_full_stack
from core.jsonresponse import create_response
import models as app_models
from mall import export
from datetime import date,datetime
import export as rebate_export
import os
from modules.member.models import Member
from watchdog.utils import watchdog_error
from weapp import settings
from mall import models as mall_models

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
		is_export = request.GET.get('is_export', '')
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
			elif now_time <= data_start_time:
				data_data.update(set__status=app_models.STATUS_NOT_START)
		if name:
			params['name__icontains'] = name
		datas = app_models.Rebate.objects(**params).order_by('-id')

		#进行分页
		count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
		cur_page = int(request.GET.get('page', '1'))
		if is_export !='is_export':
			pageinfo, datas = paginator.paginate(datas, cur_page, count_per_page, query_string=request.META['QUERY_STRING'])

		#统计每个活动的扫码关注人数
		items = []
		record_id2partis = {}
		record_ids = [str(d.id) for d in datas]
		all_member_ids = set()
		all_partis = app_models.RebateParticipance.objects(belong_to__in=record_ids)
		for p in all_partis:
			member_id = p.member_id
			all_member_ids.add(member_id)
		member_id2subscribe = {m.id: m.is_subscribed for m in Member.objects.filter(id__in=all_member_ids)}
		record_own_member_ids = {}
		member_id2partis = {}
		for p in all_partis:
			belong_to = p.belong_to
			member_id = p.member_id
			if not record_id2partis.has_key(belong_to):
				if member_id2subscribe[member_id]:
					record_id2partis[belong_to] = {member_id}
			else:
				if member_id2subscribe[member_id]:
					record_id2partis[belong_to].add(member_id)

			if not record_own_member_ids.has_key(belong_to):
				record_own_member_ids[belong_to] = {member_id}
			else:
				record_own_member_ids[belong_to].add(member_id)

			if not member_id2partis.has_key(member_id):
				member_id2partis[member_id] = {
					belong_to: p.created_at
				}
			else:
				member_id2partis[member_id][belong_to] = p.created_at

		#统计扫码后成交金额和首次下单数
		webapp_user_id_belong_to_member_id, id2record, member_id2records, member_id2order_ids, all_orders, member_id2participations = rebate_export.get_target_orders(datas)
		#除去完成退款的订单
		all_orders = all_orders.exclude(status=mall_models.ORDER_STATUS_REFUNDED)
		id2order = {o.order_id: o for o in all_orders}
		record_id2orders = {}
		for rid in record_ids:
			member_ids = record_own_member_ids.get(rid, None)
			if not member_ids:
				continue
			for mid in member_ids:
				if member_id2order_ids.has_key(mid):
					#注意！！！！
					#由于一个会员可以同时参与多个返利活动，
					#并且会员在此期间下的订单会同时显示在多个活动中
					#所以以下的动作会使得record_id2orders[rid]中出现多个相同的order_id
					if not record_id2orders.has_key(rid):
						record_id2orders[rid] = member_id2order_ids[mid]
					else:
						record_id2orders[rid] += member_id2order_ids[mid]
		record_id2cash = {}
		record_id2first_buy_num = {}
		for rid, order_ids in record_id2orders.items():
			temp_order_ids = set(order_ids) #这里的id会重复
			record = id2record[rid]
			for oid in temp_order_ids:
				oid = str(oid)
				temp_order = id2order.get(oid, None)
				if not temp_order:
					continue

				temp_member_id = webapp_user_id_belong_to_member_id.get(temp_order.webapp_user_id, None)
				if not temp_member_id or temp_member_id not in record_own_member_ids[rid]:
					continue
				if temp_order.created_at>record.start_time and temp_order.created_at<record.end_time: #扫码后的
					#判断首单
					if temp_order.is_first_order and temp_order.created_at > member_id2partis[temp_member_id][rid]:
						if not record_id2first_buy_num.has_key(rid):
							record_id2first_buy_num[rid] = 1
						else:
							record_id2first_buy_num[rid] += 1

					#判断扫码后的金额
					if not record_id2cash.has_key(rid):
						record_id2cash[rid] = id2order[oid].final_price
					else:
						record_id2cash[rid] += id2order[oid].final_price

		for data in datas:
			str_id = str(data.id)
			items.append({
				'id': str_id,
				'owner_id': data.owner_id,
				'name': data.name,
				'attention_number': len(record_id2partis[str_id]) if record_id2partis.get(str_id, None) else 0,
				'order_money': ('%.2f' % record_id2cash[str_id]) if record_id2cash.get(str_id, None) else 0,
				'first_buy_num': record_id2first_buy_num[str_id] if record_id2first_buy_num.get(str_id, None) else 0,
				'start_time': data.start_time.strftime('%Y-%m-%d %H:%M'),
				'end_time': data.end_time.strftime('%Y-%m-%d %H:%M'),
				'status': data.status_text,
				'ticket': data.ticket,
				'created_at': data.created_at.strftime("%Y-%m-%d %H:%M:%S")
			})

		if is_export !='is_export':
			return pageinfo, items
		else:
			return items

	@login_required
	def api_get(request):
		"""
		响应API GET
		"""
		pageinfo, items = Rebates.get_datas(request)
		response_data = {
			'items': items,
			'pageinfo': paginator.to_dict(pageinfo),
			'sortAttr': 'id',
			'data': {}
		}
		response = create_response(200)
		response.data = response_data
		return response.get_response()

class Rebates_Export(resource.Resource):
	'''
	批量导出
	'''
	app = 'apps/rebate'
	resource = 'rebates_export'

	@login_required
	def api_get(request):
		"""
		分析导出
		"""
		download_excel_file_name = u'返利活动批量导出.xls'
		excel_file_name = 'rebate_participances_'+datetime.now().strftime('%H_%M_%S')+'.xls'
		dir_path_suffix = '%d_%s' % (request.user.id, date.today())
		dir_path = os.path.join(settings.UPLOAD_DIR, dir_path_suffix)

		if not os.path.exists(dir_path):
			os.makedirs(dir_path)
		export_file_path = os.path.join(dir_path,excel_file_name)
		#Excel Process Part
		try:
			import xlwt
			datas =Rebates.get_datas(request)
			fields_pure = []
			export_data = []

			#from sample to get fields4excel_file
			fields_pure.append(u'活动名称')
			fields_pure.append(u'关注人数')
			fields_pure.append(u'扫码后成交金额')
			fields_pure.append(u'首次下单数')
			fields_pure.append(u'有效期')
			fields_pure.append(u'活动状态')

			#processing data
			num = 0
			for data in datas:
				export_record = []
				name = data["name"]
				attention_number = data["attention_number"]
				order_money = data["order_money"]
				first_buy_num = data["first_buy_num"]
				time = data["start_time"]+u'至'+data["end_time"]
				status = data["status"]

				export_record.append(name)
				export_record.append(attention_number)
				export_record.append(order_money)
				export_record.append(first_buy_num)
				export_record.append(time)
				export_record.append(status)
				export_data.append(export_record)
			#workbook/sheet
			wb = xlwt.Workbook(encoding='utf-8')
			ws = wb.add_sheet(u'返利活动')
			header_style = xlwt.XFStyle()

			##write fields
			row = col = 0
			for h in fields_pure:
				ws.write(row,col,h)
				col += 1

			##write data
			if export_data:
				row = 1
				lens = len(export_data[0])
				for record in export_data:
					row_l = []
					for col in range(lens):
						record_col= record[col]
						if type(record_col)==list:
							row_l.append(len(record_col))
							for n in range(len(record_col)):
								data = record_col[n]
								try:
									ws.write(row+n,col,data)
								except:
									#'编码问题，不予导出'
									print record
									pass
						else:
							try:
								ws.write(row,col,record[col])
							except:
								#'编码问题，不予导出'
								print record
								pass
					if row_l:
						row = row + max(row_l)
					else:
						row += 1
				try:
					wb.save(export_file_path)
				except Exception, e:
					print 'EXPORT EXCEL FILE SAVE ERROR'
					print e
					print '/static/upload/%s/%s'%(dir_path_suffix,excel_file_name)
			else:
				ws.write(1,0,'')
				wb.save(export_file_path)
			response = create_response(200)
			response.data = {'download_path':'/static/upload/%s/%s'%(dir_path_suffix,excel_file_name),'filename':download_excel_file_name,'code':200}
		except Exception, e:
			error_msg = u"导出文件失败, cause:\n{}".format(unicode_full_stack())
			watchdog_error(error_msg)
			response = create_response(500)
			response.innerErrMsg = unicode_full_stack()

		return response.get_response()