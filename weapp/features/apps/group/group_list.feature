#_author_:许韦 2016.3.9

Feature:团购活动列表
	"""
	说明：
		1 团购活动列表的"查询":
			【商品名称】：支持模糊查询
			【状态】：默认为'全部'，下拉框显示：全部、未开启、进行中和已结束
			【起止时间】：开始时间和结束时间允许为空
			【团购名称】：支持模糊查询
		2 团购活动列表的"分页"，每10条记录一页
	"""
Background:
	Given jobs登录系统
	When jobs添加会员等级
		"""
		[{
			"name": "铜牌会员",
			"upgrade": "手动升级",
			"discount": "9"
		}, {
			"name": "银牌会员",
			"upgrade": "手动升级",
			"discount": "8"
		}, {
			"name": "金牌会员",
			"upgrade": "手动升级",
			"discount": "7"
		}]
		"""
	And jobs已添加商品规格
		"""
		[{
			"name": "颜色",
			"type": "图片",
			"values": [{
				"name": "黑色",
				"image": "/standard_static/test_resource_img/hangzhou1.jpg"
			}, {
				"name": "白色",
				"image": "/standard_static/test_resource_img/hangzhou2.jpg"
			}]
		}, {
			"name": "尺寸",
			"type": "文字",
			"values": [{
				"name": "M"
			}, {
				"name": "S"
			}]
		}]
		"""
	And jobs已添加支付方式
		"""
		[{
			"type": "货到付款",
			"description": "我的货到付款",
			"is_active": "启用"
		},{
			"type": "微信支付",
			"description": "我的微信支付",
			"is_active": "启用",
			"weixin_appid": "12345",
			"weixin_partner_id": "22345",
			"weixin_partner_key": "32345",
			"weixin_sign": "42345"
		},{
			"type": "支付宝",
			"is_active": "启用"
		}]
		"""
	And jobs已添加商品
	#添加商品：
			#促销商品，无分类，上架，无限库存；（促销商品）
			#待售商品，待售，无限库存；
			#会员折扣商品，上架，有限库存50；
			#启用规格商品，有限数量3；
			#酱牛肉，上架，无限库存；
			#花生酱，上架，有限数量200；
			#番茄酱，商家，有限数量100；
			#限时抢购商品，上架，无限库存
			#买赠商品，上架，有限数量20；
			#单品券商品，上架，无限库存；
			#积分抵扣商品；

		"""
		[{
			"name": "促销商品",
			"promotion_title": "促销商品",
			"categories": "",
			"detail": "促销商品的详情",
			"status": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou1.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 5.00,
						"weight": 1.0,
						"stock_type": "无限"
					}
				}
			}
		},{
			"name":"待售商品",
			"category":"",
			"detail":"待售商品的详情",
			"status":"待售",
			"swipe_images":[{
				"url":"/standard_static/test_resource_img/hangzhou2.jpg"
			}],
			"model":{"models": {
					"standard": {
						"price": 12.00,
						"weight": 2.5,
						"stock_type": "无限"
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "免运费",
			"distribution_time":"off"
		},{
			"name": "会员折扣商品",
			"is_member_product": "on",
			"category": "",
			"detail": "会员折扣商品的详情",
			"status": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou3.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 1.50,
						"weight": 0.5,
						"stock_type": "有限",
						"stocks": 50
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "免运费",
			"distribution_time":"off"
		},{
			"name": "启用规格商品",
			"category": "",
			"detail": "启用规格商品的详情",
			"status": "上架",
			"is_enable_model": "启用规格",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou4.jpg"
			}],
			"model": {
				"models": {
					"黑色 S": {
						"price": 10.00,
						"weight": 3.1,
						"stock_type": "有限",
						"stocks": 3
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "免运费",
			"distribution_time":"off"
		},{
			"name":"酱牛肉",
			"category": "",
			"detail": "酱牛肉的详情",
			"status": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou5.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 50.00,
						"weight": 5.0,
						"stock_type": "无限"
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "免运费",
			"distribution_time":"off"
		},{
			"name":"花生酱",
			"category": "",
			"detail": "花生酱的详情",
			"status": "上架",
			"invoice":true,
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou6.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 12.50,
						"weight": 1.5,
						"stock_type": "有限",
						"stocks": 200
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "10",
			"distribution_time":"on"
		},{
			"name":"番茄酱",
			"category": "",
			"detail": "番茄酱的详情",
			"status": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou6.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 20.00,
						"weight": 5,
						"stock_type": "有限",
						"stocks": 100
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			},{
				"type": "货到付款"
			}],
			"postage": "10"
		},{
			"name":"限时抢购商品",
			"price":100.00,
			"stock_type": "无限",
			"status":"上架"
		},{
			"name":"买赠商品",
			"price":100.00,
			"stock_type": "有限",
			"stocks": 20,
			"status":"上架"
		},{
			"name":"单品券商品",
			"price":100.00,
			"stock_type": "无限",
			"status":"上架"
		},{
			"name":"积分抵扣商品",
			"price":100.00,
			"stock_type": "无限",
			"status":"上架",
			"purchase_count":2
		},{
			"name": "起购数量商品",
			"price": 15.00,
			"stock_type": "有限",
			"stocks": 200,
			"status": "在售",
			"purchase_count": 3
		}
		]
		"""
	When jobs创建限时抢购活动
		"""
		[{
			"name": "限时抢购活动",
			"start_date": "今天",
			"end_date": "1天后",
			"product_name": "限时抢购商品",
			"member_grade": "全部会员",
			"count_per_purchase": 2,
			"promotion_price": 90.00
		}]
		"""
	And jobs创建买赠活动
		"""
		[{
			"name": "买赠活动",
			"start_date": "今天",
			"end_date": "1天后",
			"product_name": "买赠商品",
			"premium_products": [{
				"name": "买赠商品",
				"count": 1
			}],
			"count": 2,
			"is_enable_cycle_mode": false
		}]
		"""
	And jobs创建积分应用活动
		"""
		[{
			"name": "积分应用活动",
			"start_date": "今天",
			"end_date": "1天后",
			"product_name": "积分抵扣商品",
			"is_permanant_active": false,
			"rules": [{
				"member_grade": "全部会员",
				"discount": 50,
				"discount_money": 50.00
			}]
		}]
		"""
	And jobs添加优惠券规则
		"""
		[{
			"name": "单品券",
			"money": 1,
			"start_date": "2天前",
			"end_date": "2天后",
			"coupon_id_prefix": "coupon1_id_",
			"coupon_product": "单品券商品"
		}]
		"""


	When jobs新建团购活动
		"""
		[{
			"group_name":"团购活动1",
			"start_date":"今天",
			"end_date":"明天",
			"product_name":"酱牛肉",
			"group_dict":{
				"0":{
					"group_type":"5",
					"group_days":"1",
					"group_price":"45"},
				"1":{
						"group_type":"10",
						"group_days":"2",
						"group_price":"30.00"
				}},
			"ship_date":"10",
			"product_counts":"200",
			"material_image":"1.jpg",
			"share_description":"团购分享描述"
		},{
			"group_name":"团购活动2",
			"start_date":"明天",
			"end_date":"2天后",
			"product_name":"花生酱",
			"group_dict":{
				"0":{
					"group_type":"10",
					"group_days":"2",
					"group_price":"8.50"
				}},
			"ship_date":"20",
			"product_counts":"150",
			"material_image":"2.jpg",
			"share_description":"团购分享描述"
		},{
			"group_name":"团购活动3",
			"start_date":"3天前",
			"end_date":"昨天",
			"product_name":"番茄酱",
			"group_dict":{
				"0":{
					"group_type":"5",
					"group_days":"1",
					"group_price":"40.50"
			}},
			"ship_date":"5",
			"product_counts":"100",
			"material_image":"3.jpg",
			"share_description":"团购分享描述"
		}]
		"""
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动2",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"明天",
			"end_date":"2天后",
			"actions": ["参团详情","编辑","开启"]
		},{
			"name":"团购活动1",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"今天",
			"end_date":"明天",
			"actions": ["参团详情","编辑","开启"]
		},{
			"name":"团购活动3",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"已结束",
			"start_date":"3天前",
			"end_date":"昨天",
			"actions": ["参团详情","删除"]
		}]
		"""
	When jobs开启团购活动'团购活动1'
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动1",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"进行中",
			"start_date":"今天",
			"end_date":"明天",
			"actions": ["参团详情","结束"]
		},{
			"name":"团购活动2",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"明天",
			"end_date":"2天后",
			"actions": ["参团详情","编辑","开启"]
		},{
			"name":"团购活动3",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"已结束",
			"start_date":"3天前",
			"end_date":"昨天",
			"actions": ["参团详情","删除"]
		}]
		"""

@mall2 @apps_group @apps_group_backend @apps_group_list
Scenario:1 团购活动列表查询
	Given jobs登录系统
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动1",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"进行中",
			"start_date":"今天",
			"end_date":"明天",
			"actions": ["参团详情","结束"]
		},{
			"name":"团购活动2",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"明天",
			"end_date":"2天后",
			"actions": ["参团详情","编辑","开启"]
		},{
			"name":"团购活动3",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"已结束",
			"start_date":"3天前",
			"end_date":"昨天",
			"actions": ["参团详情","删除"]
		}]
		"""
	#空查询（默认查询）
		When jobs设置团购活动列表查询条件
			"""
			{}
			"""
		Then jobs获得团购活动列表
			"""
			[{
				"name":"团购活动1"
			},{
				"name":"团购活动2"
			},{
				"name":"团购活动3"
			}]
			"""
	#活动名称
		#模糊匹配
			When jobs设置团购活动列表查询条件
				"""
				{
					"name":"团购"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[{
					"name":"团购活动1"
				},{
					"name":"团购活动2"
				},{
					"name":"团购活动3"
				}]
				"""
		#精确匹配
			When jobs设置团购活动列表查询条件
				"""
				{
					"name":"团购活动3"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[{
					"name":"团购活动3"
				}]
				"""
		#查询结果为空
			When jobs设置团购活动列表查询条件
				"""
				{
					"name":"测试"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[]
				"""
	#状态（全部、未开始、进行中、已结束）
		When jobs设置团购活动列表查询条件
			"""
			{
				"status":"全部"
			}
			"""
		Then jobs获得团购活动列表
			"""
			[{
				"name":"团购活动1",
				"status":"进行中"
			},{
				"name":"团购活动2",
				"status":"未开启"
			},{
				"name":"团购活动3",
				"status":"已结束"
			}]
			"""
		When jobs设置团购活动列表查询条件
			"""
			{
				"status":"进行中"
			}
			"""
		Then jobs获得团购活动列表
			"""
			[{
				"name":"团购活动1",
				"status":"进行中"
			}]
			"""
	#活动时间
		#开始时间非空，结束时间为空
			When jobs设置团购活动列表查询条件
				"""
				{
					"start_date":"今天",
					"end_date":""
				}
				"""
			Then jobs获得团购活动列表
				"""
				[{
					"name":"团购活动1",
					"start_date":"今天",
					"end_date":"明天"
				},{
					"name":"团购活动2",
					"start_date":"明天",
					"end_date":"2天后"
				}]
				"""

		#开始时间为空，结束时间非空
			When jobs设置团购活动列表查询条件
				"""
				{
					"start_date":"",
					"end_date":"今天"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[{
					"name":"团购活动3",
					"start_date":"3天前",
					"end_date":"昨天"
				}]
				"""

		#开始时间与结束时间相等
			When jobs设置团购活动列表查询条件
				"""
				{
					"start_date":"今天",
					"end_date":"今天"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[]
				"""

		#开始时间和结束时间不相等
			When jobs设置团购活动列表查询条件
				"""
				{
					"start_date":"3天前",
					"end_date":"明天"
				}
				"""
			Then jobs获得团购活动列表
				"""
				[{
					"name":"团购活动1",
					"start_date":"今天",
					"end_date":"明天"
				},{
					"name":"团购活动3",
					"start_date":"3天前",
					"end_date":"昨天"
				}]
				"""
		#组合条件查询
		When jobs设置团购活动列表查询条件
			"""
			{
				"name":"团购活动2",
				"status":"未开启",
				"start_date":"明天",
				"end_date":"3天后"
			}
			"""
		Then jobs获得团购活动列表
			"""
			[{
				"name":"团购活动2",
				"start_date":"明天",
				"end_date":"2天后"
			}]
			"""

@mall2 @apps_group @apps_group_backend @apps_group_list
Scenario:2 团购活动列表分页
	Given jobs登录系统
	And jobs设置分页查询参数
		"""
		{
			"count_per_page":1
		}
		"""
		#Then jobs获得团购活动列表共'3'页

	When jobs访问团购活动列表第'1'页
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动1",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"进行中",
			"start_date":"今天",
			"end_date":"明天",
			"actions": ["参团详情","结束"]
		}]
		"""
	When jobs访问团购活动列表下一页
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动2",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"明天",
			"end_date":"2天后",
			"actions": ["参团详情","编辑","开启"]
		}]
		"""
	When jobs访问团购活动列表第'3'页
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动3",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"已结束",
			"start_date":"3天前",
			"end_date":"昨天",
			"actions": ["参团详情","删除"]
		}]
		"""
	When jobs访问团购活动列表上一页
	Then jobs获得团购活动列表
		"""
		[{
			"name":"团购活动2",
			"opengroup_num":"0",
			"consumer_num":"0",
			"visitor_num":"0",
			"status":"未开启",
			"start_date":"明天",
			"end_date":"2天后",
			"actions": ["参团详情","编辑","开启"]
		}]
		"""
