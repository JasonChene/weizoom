#_author_:王丽
#editor:王丽  2015.10.19

Feature: 经营报告-经营概况——流量
"""
	说明：1）统计整个店铺的订单包含‘本店’和‘商城’的两部分
	2）有效订单：订单状态为 待发货、已发货、已完成的订单

	一、查询条件
		1、刷选日期
			1）开始日期和结束日期都为空；选择开始结束日期，精确到日期
			2）开始日期或者结束日期，只有一个为空，给出系统提示“请填写XX日期”
			3）默认为‘最近7天’，筛选日期：‘七天前’到‘今天’
			4）包含筛选日期的开始和结束的边界值
			5）手工设置筛选日期，点击查询后，‘快速查询’的所有项都处于‘未选中状态’，时间和选项匹配的，选项处于选中状态
		2、快速查看
		    1）今天：查询的当前日期，例如，今天是2015-6-16，筛选日期是：2015-6-16到2015-6-16
		    2）昨天：查询的前一天，例如，今天是2015-6-16，筛选日期是：2015-6-15到2015-6-15
			3）最近7天；包含今天，向前7天；例如，今天是2015-6-16，筛选日期是：2015-6-10到2015-6-16
			4）最近30天；包含今天，向前30天；例如，今天是2015-6-16，筛选日期是：2015-05-19到2015-6-16
			5）最近90天；包含今天，向前90天；例如，今天是2015-6-16，筛选日期：2015-3-19到2015-6-16
			6）全部：筛选日期更新到：2013.1.1到今天
			7）打印：

	二、经营概况——销量

		##同微商城的首页中的’购买趋势‘

		1、【订单量】：在查询区间的不同日期点的“店铺的订单量”的分布曲线

			例如：筛选日期：2015-05-1到2015-05-22
						2015-05-10的【订单量】=∑订单.个数[(2015-05-10 00:00 <= 订单.下单时间 < 2015-05-11 00:00) 
															and (订单.订单状态 in {待发货、已发货、已完成})]
						其他日期点的【订单量】依次类推

		2、【销售额】：在查询区间的不同日期点的“店铺的销售额”的分布曲线

			例如：筛选日期：2015-05-1到2015-05-22
						2015-05-10的【销售额】=∑订单.实付金额[(2015-05-10 00:00 <= 订单.下单时间 < 2015-05-11 00:00) 
															and (订单.订单状态 in {待发货、已发货、已完成})]
						其他日期点的【销售额】依次类推
"""

Background:
    Given jobs登录系统
	When jobs已添加商品
        """
        [{
            "name": "商品1",
            "promotion_title": "促销商品1",
            "detail": "商品1详情",
            "postage":"10",
            "swipe_images": [{
                "url": "/standard_static/test_resource_img/hangzhou1.jpg"
            }],
            "model": {
                "models": {
                    "standard": {
                        "price": 100.00,
                        "weight": 5.0,
                        "stock_type": "无限"
                    }
                }
            },
            "synchronized_mall":"是"
        }, {
            "name": "商品2",
            "promotion_title": "促销商品2",
            "detail": "商品2详情",
            "postage":"15",
            "swipe_images": [{
                "url": "/standard_static/test_resource_img/hangzhou1.jpg"
            }],
            "model": {
                "models": {
                    "standard": {
                        "price": 100.00,
                        "weight": 5.0,
                        "stock_type": "无限"
                    }
                }
            },
            "synchronized_mall":"是"
        }]
        """
	And jobs已添加支付方式
        """
        [{
            "type": "货到付款",
            "is_active": "启用"
        }, {
            "type": "微信支付",
            "is_active": "启用"
        }, {
            "type": "支付宝",
            "is_active": "启用"
        }]
        """

	When bill关注jobs的公众号于'2015-05-01'
	When tom关注jobs的公众号于'2015-05-02'
	When mary关注jobs的公众号于'2015-05-02'
	When zhangsan关注jobs的公众号于'2015-05-03'
	When zhangsan取消关注jobs的公众号

@mall2 @bi @salesAnalysis   @stats
Scenario:1  经营概况：销售额和成交订单
	
	When 微信用户批量消费jobs的商品
		| order_id |   date     | consumer | product | payment | pay_type | postage* | price* | paid_amount* | action       | order_status* |
		|   001    | 2015-04-04 | mary     | 商品1,1 | 支付    | 微信支付 | 10       |  100   | 110          | jobs,完成    |    已完成     |
		|   002    | 2015-05-02 | bill     | 商品1,1 |         | 支付宝   | 10       |  100   | 110          | jobs,取消    |    已取消     |
		|   003    | 2015-05-03 | tom      | 商品2,1 | 支付    | 微信支付 | 15       |  100   | 115          | jobs,完成    |    已完成     |
		|   004    | 2015-05-05 | bill     | 商品1,1 | 支付    | 货到付款 | 10       |  100   | 110          |              |    待发货     |
		|   005    | 2015-05-06 | tom      | 商品1,1 | 支付    | 货到付款 | 10       |  100   | 110          | jobs,发货    |    已发货     |
		|   006    | 2015-05-06 | bill     | 商品1,1 | 支付    | 支付宝   | 10       |  100   | 110          | jobs,退款    |    退款中     |
		|   007    | 2015-05-08 | bill     | 商品2,1 | 支付    | 微信支付 | 15       |  100   | 115          | jobs,完成退款|    退款成功   |
		|   008    | 2015-05-10 | mary     | 商品2,2 | 支付    | 支付宝   | 15       |  100   | 215          | jobs,发货    |    已发货     |
		|   009    | 2015-05-10 | tom      | 商品2,2 | 支付    | 支付宝   | 15       |  100   | 215          | jobs,发货    |    已发货     |
		|   010    | 今天       | mary     | 商品2,2 |         | 支付宝   | 15       |  100   | 215          |              |    待支付     |
		|   011    | 今天       | -duhao   | 商品2,5 |         | 支付宝   | 15       |  100   | 515          |              |    待支付     |
		|   012    | 今天       | zhangsan | 商品2,5 |         | 支付宝   | 15       |  100   | 515          |              |    待支付     |
 
	Given jobs登录系统
	When jobs设置筛选日期
		"""
		[{
			"begin_date":"2015-05-01",
			"end_date":"2015-05-10"
		}]
		"""

	Then jobs获得销售额趋势
		|   date     |  sales  |
		| 2015-05-01 |  0.00   |
		| 2015-05-02 |  0.00   |
		| 2015-05-03 | 115.00  |
		| 2015-05-04 |  0.00   |
		| 2015-05-05 | 110.00  |
		| 2015-05-06 | 110.00  |
		| 2015-05-07 |  0.00   |
		| 2015-05-08 |  0.00   |
		| 2015-05-09 |  0.00   |
		| 2015-05-10 | 430.00  |


	Then jobs获得成交订单趋势
		|    date    | order_quantity |
		| 2015-05-01 |       0        |
		| 2015-05-02 |       0        |
		| 2015-05-03 |       1        |
		| 2015-05-04 |       0        |
		| 2015-05-05 |       1        |
		| 2015-05-06 |       1        |
		| 2015-05-07 |       0        |
		| 2015-05-08 |       0        |
		| 2015-05-09 |       0        |
		| 2015-05-10 |       2        |