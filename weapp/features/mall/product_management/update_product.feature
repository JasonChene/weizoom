#editor:王丽 2015.10.15

@func:webapp.modules.mall.views.update_product
Feature: Update Product
	Jobs能通过管理系统更新商品

Background:
	Given jobs登录系统
	And jobs已添加商品分类
		"""
		[{
			"name": "分类1"
		}, {
			"name": "分类2"
		}, {
			"name": "分类3"
		}]
		"""
	When jobs已添加支付方式
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
		}]
		"""
	When jobs开通使用微众卡权限
	When jobs添加支付方式
		"""
		[{
			"type": "微众卡支付",
			"description": "我的微众卡支付",
			"is_active": "启用"
		}]
		"""
	When jobs添加邮费配置
		"""
		[{
			"name":"顺丰",
			"first_weight":1,
			"first_weight_price":15.00,
			"added_weight":1,
			"added_weight_price":5.00
		}, {
			"name" : "圆通",
			"first_weight":1,
			"first_weight_price":10.00
		}]
		"""
	When jobs选择'顺丰'运费配置
	And jobs已添加商品
		"""
		[{
			"name": "商品1",
			"categories": "分类1,分类2,分类3",
			"detail": "商品1的详情",
			"shelve_type": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou1.jpg"
			}, {
				"url": "/standard_static/test_resource_img/hangzhou2.jpg"
			}, {
				"url": "/standard_static/test_resource_img/hangzhou3.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 11.00,
						"weight": 5,
						"stock_type": "无限"
					}
				}
			},
			"postage": "顺丰"
		}, {
			"name": "商品2",
			"categories": "",
			"thumbnails_url": "/standard_static/test_resource_img/hangzhou2.jpg",
			"pic_url": "/standard_static/test_resource_img/hangzhou2.jpg",
			"introduction": "商品2的简介",
			"detail": "商品2的详情",
			"shelve_type": "下架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou1.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 12.00,
						"weight": 5,
						"stock_type": "有限",
						"stocks": 3
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			}],
			"postage": 10.00
		}]
		"""
	Then jobs能获取商品列表
		"""
		[{
			"name": "商品1"
		}]
		"""

@mall2 @product @saleingProduct @toSaleProduct   @mall.product
Scenario:1 更新商品
	Jobs添加一组商品后，能更改单个商品的所有字段的属性

	When jobs更新商品'商品1'
		"""
		{
			"name": "商品11",
			"categories": "分类2,分类3",
			"detail": "商品1的详情",
			"shelve_type": "下架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou3.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 111.00,
						"weight": 15.0,
						"stock_type": "有限",
						"stocks": 5
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			}],
			"postage": "免运费"
		}
		"""
	Then jobs能获取商品列表
		"""
		[{
			"name": "商品11"
		}]
		"""
	And jobs能获取商品'商品11'
		"""
		{
			"name": "商品11",
			"category": "分类2,分类3",
			"remark": "",
			"shelve_type": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou3.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 111.00,
						"weight": 15.0,
						"stock_type": "有限",
						"stocks": 5
					}
				}
			},
			"pay_interfaces":[{
				"type": "在线支付"
			}],
			"postage": "顺丰"
		}
		"""

	When jobs更新商品'商品2'
		"""
		{
			"name": "商品2",
			"categories": "",
			"detail": "商品2的详情",
			"shelve_type": "上架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou2.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 12.00,
						"weight": 5,
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
			"postage": "顺丰"
		}
		"""
	Then jobs能获取商品列表
		"""
		[{
			"name": "商品11"
		}]
		"""
	And jobs能获取商品'商品2'
		"""
		{
			"name": "商品2",
			"category": "",
			"detail": "商品2的详情",
			"shelve_type": "下架",
			"swipe_images": [{
				"url": "/standard_static/test_resource_img/hangzhou2.jpg"
			}],
			"model": {
				"models": {
					"standard": {
						"price": 12.00,
						"weight": 5,
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
			"postage": "顺丰"
		}
		"""

	When jobs更新商品'商品11'
		"""
		{
			"name": "商品11",
			"categories": ""
		}
		"""
	Then jobs能获取商品'商品11'
		"""
		{
			"name": "商品11",
			"category": ""
		}
		"""

@mall2 @product @saleingProduct @toSaleProduct   @mall.product
Scenario:2 切换邮费配置
	jobs把运费配置更改为'圆通'
	jobs查看商品详情

	When jobs选择'圆通'运费配置
	Then jobs能获取商品'商品1'
		"""
		{
			"name": "商品1",
			"postage": "圆通"
		}
		"""
	And jobs能获取商品'商品2'
		# postage为数值，表示“统一运费”
		"""
		{
			"name": "商品2",
			"postage": 10.00
		}
		"""
