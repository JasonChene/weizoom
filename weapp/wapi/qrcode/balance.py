# -*- coding: utf-8 -*-
import time

from core import api_resource, paginator
from market_tools.tools.channel_qrcode.models import ChannelQrcodeSettings, ChannelQrcodeHasMember
from wapi.decorators import param_required
from modules.member.models import *
from mall.models import Order, ORDER_STATUS_SUCCESSED, ORDER_STATUS_REFUNDED, STATUS2TEXT, OrderHasProduct, Product, ProductModel,OrderOperationLog

class QrcodeBalance(api_resource.ApiResource):
	"""
	二维码
	"""
	app = 'qrcode'
	resource = 'balance'

	@param_required(['channel_qrcode_id'])
	def get(args):
		"""
		获取结算的数据
		现金总收入：订单提成+首单提成
		订单提成：（店铺总销售额-店铺退款金额）*？%
		首单提成：已完成的首次下单个数*？
		店铺总销售额：已完成订单的总额
		店铺退款金额：该订单上次已结算过，但本期次订单发生了退款，这类的退款订单金额
		"""
		start = time.time()
		channel_qrcode_id = int(args.get('channel_qrcode_id'))
		balance_time_from = args.get('balance_time_from','2016-06-24 00:00:00')
		channel_qrcode = ChannelQrcodeSettings.objects.get(id=channel_qrcode_id)
		created_at = channel_qrcode.created_at.strftime("%Y-%m-%d %H:%M:%S")

		member_ids = [member_log.member_id for member_log in ChannelQrcodeHasMember.objects.filter(channel_qrcode_id=channel_qrcode_id)]
		webapp_user_ids = [webappuser.id for webappuser in WebAppUser.objects.filter(member_id__in=member_ids)]

		filter_data_args = {
			"webapp_user_id__in": webapp_user_ids,
			"origin_order_id__lte": 0,
			"created_at__gte": created_at
		}

		cur_start_date = args.get('start_date', None)
		cur_end_date = args.get('end_date', None)
		filter_data_args["status__in"] = [ORDER_STATUS_SUCCESSED, ORDER_STATUS_REFUNDED]
		channel_orders = Order.objects.filter(**filter_data_args).order_by('-created_at')
		order_numbers = [co.order_id for co in channel_orders]
		order_log_numbers = []
		order_number2finished_at = {}
		#处理筛选
		if cur_start_date and cur_end_date:
			if cur_start_date < created_at:
				cur_start_date = created_at
			orderoperationlogs = OrderOperationLog.objects.filter(
				order_id__in=order_numbers,
				action__in=[u'完成', u'退款完成'],
				created_at__gte=cur_start_date,
				created_at__lte=cur_end_date
			)

			for op in orderoperationlogs:
				if op.created_at.strftime("%Y-%m-%d %H:%M:%S") >= cur_start_date and op.created_at.strftime("%Y-%m-%d %H:%M:%S") <= cur_end_date:
					order_log_numbers.append(op.order_id)
				order_number2finished_at[op.order_id] = op.created_at

		orders = []
		for channel_order in channel_orders:
			if channel_order.order_id in order_log_numbers:
				sale_price = channel_order.final_price + channel_order.coupon_money + channel_order.integral_money + channel_order.weizoom_card_money + channel_order.promotion_saved_money + channel_order.edit_money
				final_price = channel_order.final_price
				orders.append({
					"order_id": channel_order.id,
					"order_number": channel_order.order_id,
					"is_first_order": channel_order.is_first_order,
					"status_text": STATUS2TEXT[channel_order.status],
					"sale_price": sale_price,  #销售额
					"finished_at": order_number2finished_at.get(channel_order.order_id, channel_order.update_at).strftime('%Y-%m-%d %H:%M:%S'),
					"final_price": final_price,
					"created_at": channel_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
				})
		end = time.time()
		print end - start, "pppppppppp"

		return {
			'items': orders
		}
