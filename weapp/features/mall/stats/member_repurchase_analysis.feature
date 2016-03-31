#_author_:张三香 2016.03.31

Feature:会员分析-复购分析
	"""
		1、会员状态：全部、已关注、取消关注,默认显示'全部'
		2、购买次数:只计算'已完成'状态的订单
		3、会员购买占比:默认会员分为1、2、3-5、5以上这四个阶段, 显示人数、占比(xx.xx% 保留2为小数)
			会员状态选择'全部'时
				购买x次的会员
					人数:x
					占比:x/当前系统中全部的总购买人数
			会员状态选择'已关注'时
				购买x次的会员
					人数:x
					占比:x/已关注状态下的总购买人数
			会员状态选择'已取消'时
				购买x次的会员
					人数:x
					占比:x/已取消状态下的总购买人数

		3、复购会员分析：
			3.1、复购会员为购买次数在2次以上的会员
			3.2、默认是未设置消费总额的,复购会员分析显示规则如下：
					消费金额:0-最大金额
					人数:当前系统中所有的复购会员数
					占比:100%
			3.3、设置消费总额:
				a.固定显示3个消费区间:
					消费区间1：x-x
					消费区间2：x-x
					消费区间3：x-x
				b.消费区间之间可以不连续,不连续的部分统一显示为'其他'
				c.消费额区间需逐渐递增，不能交叉
				d.消费额区间只能是大于等于0的整数
	"""

Background:
	Given jobs登录系统
	Given jobs设定会员积分策略
		"""
		{
			"be_member_increase_count":200,
			"integral_each_yuan":10
		}
		"""
	When jobs添加支付方式
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
			"description": "我的支付宝支付",
			"is_active": "启用"
		}]
		"""
	And jobs开通使用微众卡权限
	And jobs添加支付方式
		"""
		[{
			"type": "微众卡支付",
			"description": "我的微众卡支付",
			"is_active": "启用"
		}]
		"""
	Given jobs已创建微众卡
		"""
		{
			"cards":[{
				"id":"0000001",
				"password":"1234567",
				"status":"未使用",
				"price":110.00
			}]
		}
		"""
	And jobs已添加商品
		"""
		[{
			"name": "商品1",
			"price":100.0,
			"postage": 10
		},{
			"name": "商品2",
			"price":200.0,
			"postage": 15
		},{
			"name": "商品3",
			"price":10.0
		}]
		"""
	When jobs创建积分应用活动
		"""
		[{
			"name": "商品1积分应用",
			"start_date": "今天",
			"end_date": "10天后",
			"product_name": "商品1",
			"is_permanant_active": "true",
			"rules": [{
				"member_grade": "全部",
					"discount": 20,
					"discount_money": 20.0
				}]
		},{
			"name": "商品2积分应用",
			"start_date": "今天",
			"end_date": "10天后",
			"product_name": "商品2",
			"is_permanant_active": "true",
			"rules": [{
				"member_grade": "全部",
				"discount": 20,
				"discount_money": 20.0
			}]
		}]
		"""
	And jobs添加优惠券规则
		"""
		[{
			"name": "全体券1",
			"money": 10,
			"start_date": "今天",
			"end_date": "10天后",
			"coupon_id_prefix": "coupon1_id_"
		}]
		"""

	#会员数据
		Given bill关注jobs的公众号
		And bill2关注jobs的公众号
		And bill3关注jobs的公众号
		And bill4关注jobs的公众号
		And bill5关注jobs的公众号
		And bill6关注jobs的公众号
		And tom关注jobs的公众号
		And tom2关注jobs的公众号

	Given jobs登录系统
	When jobs为会员发放优惠券
		"""
		{
			"name": "全体1",
			"count": 1,
			"members": ["bill2"],
			"coupon_ids": ["coupon1_id_1"]
		}
		"""
	When jobs为会员发放优惠券
		"""
		{
			"name": "全体1",
			"count": 1,
			"members": ["bill3"],
			"coupon_ids": ["coupon1_id_2","coupon1_id_3"]
		}
		"""

	When 微信用户批量消费jobs的商品
		| order_id |   date   | consumer | product  | payment | pay_type | postage*| price* | product_integral |       coupon         | paid_amount*|  weizoom_card   | alipay*| wechat*| cash*|   action    | order_status*|
		|   1001   | 2014-8-5 | bill     | 商品1,1  | 支付    | 支付宝   | 10      | 100    |                  |                      | 110         | 0000001,1234567 | 0      | 0      | 0    |  jobs,完成  | 已完成       |

		|   2000   | 2014-8-6 | bill2    | 商品1,1  |         |          | 10      | 100    |                  |                      | 115         |                 | 0      | 0      | 0    |  jobs,取消  | 已取消       |    
		|   2001   | 2014-8-6 | bill2    | 商品1,1  | 支付    | 微信支付 | 10      | 100    | 200              |                      | 90          |                 | 0      | 90     | 0    |  jobs,完成  | 已完成       |
		|   2002   | 2014-8-6 | bill2    | 商品1,1  | 支付    | 支付宝   | 10      | 100    |                  | 全体券1,coupon1_id_1 | 100         |                 | 100    | 0      | 0    |  jobs,完成  | 已完成       |

		|   3000   | 2014-8-7 | bill3    | 商品2,1  | 支付    | 货到付款 | 15      | 200    |                  |                      | 215         |                 | 0      | 0      | 215  |             | 待发货       |
		|   3001   | 2014-8-7 | bill3    | 商品2,1  | 支付    | 微信支付 | 15      | 200    | 200              | 全体券1,coupon1_id_2 | 185         |                 | 0      | 185    | 0    |  jobs,完成  | 已完成       |
		|   3002   | 2014-8-7 | bill3    | 商品2,1  | 支付    | 微信支付 | 15      | 200    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   3003   | 2014-8-7 | bill3    | 商品3,1  | 支付    | 微信支付 | 0       | 10     |                  | 全体券1,coupon1_id_3 |  0          |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |


		|   4001   | 2014-8-8 | bill4    | 商品1,2  | 支付    | 微信支付 | 10      | 100    |                  |                      | 210         |                 | 0      | 210    | 0    |  jobs,完成  | 已完成       |
		|   4002   | 2014-8-8 | bill4    | 商品1,2  | 支付    | 微信支付 | 10      | 100    |                  |                      | 210         |                 | 0      | 210    | 0    |  jobs,完成  | 已完成       |
		|   4003   | 2014-8-8 | bill4    | 商品1,3  | 支付    | 微信支付 | 10      | 100    |                  |                      | 310         |                 | 0      | 310    | 0    |  jobs,完成  | 已完成       |
		|   4004   | 2014-8-8 | bill4    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |

		|   5000   | 2014-8-9 | bill5    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,发货  | 已发货       |
		|   5001   | 2014-8-9 | bill5    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   5002   | 2014-8-9 | bill5    | 商品1,2  | 支付    | 微信支付 | 10      | 100    |                  |                      | 210         |                 | 0      | 210    | 0    |  jobs,完成  | 已完成       |
		|   5003   | 2014-8-9 | bill5    | 商品1,3  | 支付    | 微信支付 | 10      | 100    |                  |                      | 310         |                 | 0      | 310    | 0    |  jobs,完成  | 已完成       |
		|   5004   | 2014-8-9 | bill5    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   5005   | 2014-8-9 | bill5    | 商品1,2  | 支付    | 微信支付 | 10      | 100    |                  |                      | 210         |                 | 0      | 210    | 0    |  jobs,完成  | 已完成       |

		|   6000   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,退款  | 退款中       |
		|   6001   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   6002   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   6003   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   6004   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   6005   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   6006   | 2014-9-5 | bill6    | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |

		|   1100   | 2014-9-6 | tom      | 商品2,1  | 支付    | 微信支付 | 15      | 200    |                  |                      | 215         |                 | 0      | 215    | 0    |jobs,完成退款| 退款成功     |
		|   1101   | 2014-9-6 | tom      | 商品1,1  | 支付    | 微信支付 | 10      | 100    |                  |                      | 110         |                 | 0      | 110    | 0    |  jobs,完成  | 已完成       |
		|   2101   | 2014-9-6 | tom2     | 商品2,1  | 支付    | 微信支付 | 15      | 200    |                  |                      | 215         |                 | 0      | 215    | 0    |  jobs,完成  | 已完成       |
		|   2102   | 2014-9-6 | tom2     | 商品2,2  | 支付    | 微信支付 | 15      | 200    |                  |                      | 415         |                 | 0      | 415    | 0    |  jobs,完成  | 已完成       |
	When tom取消关注jobs的公众号
	When tom2取消关注jobs的公众号

	Given jobs登录系统
	Then jobs可以获得会员列表
		|  member  |  integral  | pay_money | pay_times | status |
		|  tom2    |     200    |    630    |    2      | 已取消 |
		|  tom     |     200    |    110    |    1      | 已取消 |
		|  bill6   |     200    |    660    |    6      | 已关注 |
		|  bill5   |     200    |    950    |    5      | 已关注 |
		|  bill4   |     200    |    840    |    4      | 已关注 |
		|  bill3   |     0      |    295    |    3      | 已关注 |
		|  bill2   |     0      |    190    |    2      | 已关注 |
		|  bill    |     200    |    110    |    1      | 已关注 |

Scenario:1 复购分析,查看会员购买占比数据
	Given jobs登录系统
	#会员状态-全部
	Then jobs获得默认筛选条件
		"""
		{
			"member_status":"全部"
		}
		"""
	Then jobs获得会员购买占比统计数据
		"""
		{
			"购买1次的会员":2,
			"购买2次的会员":2,
			"购买3-5次的会员":3,
			"购买5次以上的会员":1
		}
		"""

	#会员状态-已关注
	When jobs设置筛选条件
		"""
		{
			"member_status":"已关注"
		}
		"""
	Then jobs获得会员购买占比统计数据
		"""
		{
			"购买1次的会员":1,
			"购买2次的会员":1,
			"购买3-5次的会员":3,
			"购买5次以上的会员":1
		}
		"""

	#会员状态-取消关注
	When jobs设置筛选条件
		"""
		{
			"member_status":"取消关注"
		}
		"""
	Then jobs获得会员购买占比统计数据
		"""
		{
			"购买1次的会员":1,
			"购买2次的会员":1,
			"购买3-5次的会员":0,
			"购买5次以上的会员":0
		}
		"""

Scenario:2 复购分析,查看复购会员分析数据
	Given jobs登录系统
	Then jobs获得默认筛选条件
		"""
		{
			"member_status":"全部"
		}
		"""
	Then jobs获得复购会员分析统计数据
		"""
		[{
			"pay_money":"190-950",
			"buyer_counts":6
		}]
		"""

	When jobs设置消费总额
		"""
		{
			"one_interval_mini":0,
			"one_interval_max":180,
			"two_interval_mini":190,
			"two_interval_max":700,
			"three_interval_mini":701,
			"three_interval_max":2000
		}
		"""
	When jobs设置筛选条件
		"""
		{
			"member_status":"全部"
		}
		"""
	Then jobs获得复购会员分析统计数据
		"""
		[{
			"pay_money":"0-180",
			"buyer_counts":0
		},{
			"pay_money":"190-700",
			"buyer_counts":4
		},{
			"pay_money":"701-900",
			"buyer_counts":1
		},{
			"pay_money":"其他"
			"buyer_counts":1
		}]
		"""

	When jobs设置筛选条件
		"""
		{
			"member_status":"已关注"
		}
		"""
	Then jobs获得复购会员分析统计数据
		"""
		[{
			"pay_money":"0-180",
			"buyer_counts":0
		},{
			"pay_money":"190-700",
			"buyer_counts":3
		},{
			"pay_money":"701-900",
			"buyer_counts":1
		},{
			"pay_money":"其他"
			"buyer_counts":1
		}]
		"""

	When bill4取消关注jobs的公众号
	When bill5取消关注jobs的公众号
	When jobs设置筛选条件
		"""
		{
			"member_status":"取消关注"
		}
		"""
	Then jobs获得复购会员分析统计数据
		"""
		[{
			"pay_money":"0-180",
			"buyer_counts":0
		},{
			"pay_money":"190-700",
			"buyer_counts":1
		},{
			"pay_money":"701-900",
			"buyer_counts":1
		},{
			"pay_money":"其他"
			"buyer_counts":1
		}]
		"""