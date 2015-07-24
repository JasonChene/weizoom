# __author__ : "冯雪静"

Feature:用户通过分享链接购买商品，给分享者增加积分
	tom通过bill分享jobs商品的链接购买商品，给bill增加积分

Background:
	Given jobs登录系统
	And jobs已添加商品
		"""
		[{
			"name":"商品1",
			"price":100.00
		},{
			"name":"商品2",
			"price":100.00
		}]	
		"""
	And jobs设置积分策略
		"""
		[{
			"be_member_increase_count":20,
			"click_shared_url_increase_count_before_buy":11,  
			"click_shared_url_increase_count_after_buy":21, 
			"buy_via_shared_url_increase_count_for_author":31, 
			"buy_increase_count_for_father":10,
			"buy_via_offline_increase_count_for_author":30,
			"click_shared_url_increase_count":11,
			"buy_award_count_for_buyer":21,
			"member_integral_strategy_settings_detail":[{
				"increase_count_after_buy":"0.3*成交金额",
				"buy_via_shared_url_increase_count_for_author":"基础奖励+0.2*成交金额",
				"buy_increase_count_for_father":"基础奖励+0.1*成交金额",
				"is_used": "是"
			}]
		}]
		"""
	And jobs已添加了支付方式
		"""
		[{
			"type": "微信支付",
			"description": "我的微信支付",
			"is_active": "启用"
		}, {
			"type": "货到付款",
			"description": "我的货到付款",
			"is_active": "启用"
		}, {
			"type": "支付宝",
			"description": "我的支付宝",
			"is_active": "启用"
		}]
		"""
	And bill关注jobs的公众号
	And 开启手动清除cookie模式

@member @member.shared_integral 
Scenario:点击给未购买的分享者增加积分
	bill没有购买jobs的商品1，把商品1的链接分享到朋友圈
	1.nokia点击bill分享的链接后，给bill增加积分
	2.nokia再次点击bill分享的链接后，不给bill增加积分
	3.tom点击bill分享的链接后，给bill增加积分
	4.tom再次点击bill分享的链接后，不给bill增加积分

	When 清空浏览器
	When bill访问jobs的webapp
	When bill获得jobs的20会员积分
	Then bill在jobs的webapp中拥有20会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"首次关注",
			"integral":20
		}]
		"""
	#When bill把jobs的微站链接分享到朋友圈
	When bill把jobs的商品"商品1"的链接分享到朋友圈
	When 清空浏览器
	When nokia点击bill分享链接
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有31会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When 清空浏览器
	When nokia点击bill分享链接
	When 清空浏览器
	When bill访问jobs的webapp	
	Then bill在jobs的webapp中拥有42会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When 清空浏览器
	When tom点击bill分享链接
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有53会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""
	
@member @member.shared_integral 
Scenario:点击给已购买的分享者增加积分
	bill购买jobs的商品1后，把商品1的链接分享到朋友圈
	1.nokia点击bill分享的链接后，给bill增加积分
	2.nokia再次点击bill分享的链接后，不给bill增加积分
	3.tom点击bill分享的链接后，给bill增加积分
	4.tom再次点击bill分享的链接后，不给bill增加积分

	When 清空浏览器
	When bill访问jobs的webapp
	When bill获得jobs的20会员积分
	Then bill在jobs的webapp中拥有20会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When bill购买jobs的商品
	"""
		{
			"ship_name": "bill",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品1",
				"count": 1
			}],
			"customer_message": "bill的订单备注1"
		}
		"""
	When bill使用支付方式'货到付款'进行支付
	Then bill支付订单成功
		"""
		{
			"status": "待发货",
			"final_price": 100.00,
			"products": [{
				"name": "商品1",
				"price":100.00,
				"count": 1
			}]
		}
		"""
	When bill把jobs的商品"商品1"的链接分享到朋友圈
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有41会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"购物返利",
			"integral":21
		},
		{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When 清空浏览器
	When nokia点击bill分享链接
	When nokia点击bill分享链接
	When bill访问jobs的webapp	
	Then bill在jobs的webapp中拥有52会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"购物返利",
			"integral":21
		},
		{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When 清空浏览器
	When tom点击bill分享链接
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有63会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"购物返利",
			"integral":21
		},
		{
			"content":"首次关注",
			"integral":20
		}]
		"""

@member @member.shared_integral 
Scenario:通过分享链接购买后给分享者增加积分
	bill把jobs的商品2的链接分享到朋友圈
	1.nokia点击bill分享的链接并购买，给bill增加积分
	2.nokia再次点击bill分享的链接并购买，不给bill增加积分
	3.tom点击bill分享的链接并购买，给bill增加积分

	When 清空浏览器
	When bill访问jobs的webapp
	When bill获得jobs的20会员积分
	Then bill在jobs的webapp中拥有20会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When bill把jobs的商品"商品2"的链接分享到朋友圈

	When 清空浏览器
	When nokia点击bill分享链接
	When nokia通过bill分享的链接购买jobs的商品
		"""
		{
			"ship_name": "nokia",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "nokia的订单备注1"
		}
		"""
	When nokia使用支付方式'货到付款'进行支付
	Then nokia支付订单成功
		"""
		{
			"status": "待发货",
			"final_price": 100.00,
			"products": [{
				"name": "商品2",
				"price":100.00,
				"count": 1
			}]
		}
		"""
	#When nokia点击bill分享链接
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有62会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""

	When 清空浏览器
	When tom点击bill分享链接
	When tom通过bill分享的链接购买jobs的商品
		"""
		{
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "tom的订单备注1"
		}
		"""
	When tom使用支付方式'货到付款'进行支付
	Then tom支付订单成功
		"""
		{
			"status": "待发货",
			"final_price": 100.00,
			"products": [{
				"name": "商品2",
				"price":100.00,
				"count": 1
			}]
		}
		"""

	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有104会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""

@member @member.shared_integral  
Scenario:每次购买给邀请者增加积分
	1.bill是tom的邀请者
	2.tom每次购买jobs的商品，给bill增加积分

	When 清空浏览器
	When bill关注jobs的公众号
	When bill访问jobs的webapp
	When bill把jobs的微站链接分享到朋友圈
	
	When 清空浏览器
	When tom点击bill分享链接
	When tom关注jobs的公众号
	When tom访问jobs的webapp
	When 清空浏览器
	Given jobs登录系统
	Then jobs能获取到bill的好友
		"""
		[{
		"name": "tom",
		"source": "会员分享",
		"is_fans": "是"
		}]
		"""
	When 清空浏览器
	When tom访问jobs的webapp
	When tom购买jobs的商品
		"""
		{
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "tom的订单备注1"
		}
		"""
	
	When 清空浏览器
	Given jobs登录系统
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "待支付",
			"actions": ["取消", "支付"],
			"total_price": 100.0,
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区 泰兴大厦",
			"customer_message": "tom的订单备注1",
			"products": [{
				"name": "商品2",
				"count": 1,
				"total_price": 100.0
			}]
		}
		"""
	When jobs支付最新订单
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "待发货",
			"actions": ["发货","取消"]
		}
		"""
	When jobs对最新订单进行发货
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "已发货",
			"actions": ["完成", "修改物流","取消"]
		}
		"""
	When jobs完成最新订单
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有61会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"推荐关注的好友购买奖励",
			"integral":30
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""

@member @member.shared_integral
Scenario: 关闭消费返积分，通过分享链接购买后给分享者增加积分
	bill把jobs的商品2的链接分享到朋友圈
	1.nokia点击bill分享的链接并购买，给bill增加积分
	2.nokia再次点击bill分享的链接并购买，不给bill增加积分
	3.tom点击bill分享的链接并购买，给bill增加积分

	When 清空浏览器
	When bill访问jobs的webapp
	When bill获得jobs的20会员积分
	Then bill在jobs的webapp中拥有20会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When bill把jobs的商品"商品2"的链接分享到朋友圈

	When 清空浏览器
	When nokia点击bill分享链接
	When nokia通过bill分享的链接购买jobs的商品
		"""
		{
			"ship_name": "nokia",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "nokia的订单备注1"
		}
		"""
	When nokia使用支付方式'货到付款'进行支付
	Then nokia支付订单成功
		"""
		{
			"status": "待发货",
			"final_price": 100.00,
			"products": [{
				"name": "商品2",
				"price":100.00,
				"count": 1
			}]
		}
		"""
	When nokia点击bill分享链接
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有62会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""
	When 清空浏览器
	When tom点击bill分享链接
	When tom通过bill分享的链接购买jobs的商品
		"""
		{
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "tom的订单备注1"
		}
		"""
	When tom使用支付方式'货到付款'进行支付
	Then tom支付订单成功
		"""
		{
			"status": "待发货",
			"final_price": 100.00,
			"products": [{
				"name": "商品2",
				"price":100.00,
				"count": 1
			}]
		}
		"""

	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有104会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"好友通过分享链接购买奖励",
			"integral":31
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",

			"integral":20
		}]
		"""

@member @member.shared_integral 
Scenario:每次购买给邀请者增加积分
	1.bill是tom的邀请者
	2.tom每次购买jobs的商品，给bill增加积分

	When 清空浏览器
	When bill关注jobs的公众号
	When bill访问jobs的webapp
	When bill把jobs的微站链接分享到朋友圈
	
	When 清空浏览器
	When tom点击bill分享链接
	When tom关注jobs的公众号
	When tom访问jobs的webapp
	When 清空浏览器
	Given jobs登录系统
	Then jobs能获取到bill的好友
		"""
		[{
		"name": "tom",
		"source": "会员分享",
		"is_fans": "是"
		}]
		"""
	When 清空浏览器
	When tom访问jobs的webapp
	When tom购买jobs的商品
		"""
		{
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区",
			"ship_address": "泰兴大厦",
			"products": [{
				"name": "商品2",
				"count": 1
			}],
			"customer_message": "tom的订单备注1"
		}
		"""
	
	When 清空浏览器
	Given jobs登录系统
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "待支付",
			"actions": ["取消", "支付"],
			"total_price": 100.0,
			"ship_name": "tom",
			"ship_tel": "13811223344",
			"ship_area": "北京市 北京市 海淀区 泰兴大厦",
			"customer_message": "tom的订单备注1",
			"products": [{
				"name": "商品2",
				"count": 1,
				"total_price": 100.0
			}]
		}
		"""
	When jobs支付最新订单
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "待发货",
			"actions": ["发货","取消"]
		}
		"""
	When jobs对最新订单进行发货
	Then jobs可以获得最新订单详情
		"""
		{
			"order_type": "普通订单",
			"status": "已发货",
			"actions": ["完成", "修改物流","取消"]
		}
		"""
	When jobs完成最新订单
	When 清空浏览器
	When bill访问jobs的webapp
	Then bill在jobs的webapp中拥有61会员积分
	Then bill在jobs的webapp中获得积分日志
		"""
		[{
			"content":"推荐关注的好友购买奖励",
			"integral":30
		},{
			"content":"好友点击分享链接奖励",
			"integral":11
		},{
			"content":"首次关注",
			"integral":20
		}]
		"""

