# __author__ : "冯雪静"
Feature: 手动调整会员等级
	Jobs能管理会员管理中的会员等级


Background:
	Given jobs登录系统
	When jobs开启自动升级
		"""
		{
			"upgrade": "自动升级",
			"condition": ["满足一个条件即可"]
		}
		"""
	When jobs添加会员等级
		"""
		[{
			"name": "铜牌会员",
			"upgrade": "自动升级",
			"pay_money": 1000.00,
			"pay_times": 20,
			"upgrade_lower_bound": 10000,
			"discount": "9"
		}, {
			"name": "银牌会员",
			"upgrade": "自动升级",
			"pay_money": 3000.00,
			"pay_times": 30,
			"upgrade_lower_bound": 30000,
			"discount": "8"
		}, {
			"name": "金牌会员",
			"upgrade": "手动升级",
			"discount": "7"
		}]
		"""
	Then jobs能获取会员等级列表
		"""
		[{
			"name": "普通会员",
			"upgrade": "自动升级",
			"discount": "10"
		}, {
			"name": "铜牌会员",
			"upgrade": "自动升级",
			"pay_money": 1000.00,
			"pay_times": 20,
			"upgrade_lower_bound": 10000,
			"discount": "9"
		}, {
			"name": "银牌会员",
			"upgrade": "自动升级",
			"pay_money": 3000.00,
			"pay_times": 30,
			"upgrade_lower_bound": 30000,
			"discount": "8"
		}, {
			"name": "金牌会员",
			"upgrade": "手动升级",
			"discount": "7"
		}]
		"""
	When bill关注jobs的公众号
	When tom关注jobs的公众号

	Given jobs登录系统
  	Given jobs给bill增加1000积分
  	Given jobs给tom增加10000积分
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10000
		}, {
			"name": "bill",
			"member_rank": "普通会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1000
		}]
		"""

@mall2
Scenario: 1 手动把会员调到自动升级的会员等级里面
	jobs手动调整已有会员的会员等级
	1. jobs能获取会员列表
	2. jobs删除会员等级后，里面的会员，回到相应的等级里面


	When jobs更新"bill"的会员等级
		"""
		{
			"name": "bill",
			"member_rank": "银牌会员"
		}
		"""
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10000
		}, {
			"name": "bill",
			"member_rank": "银牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1000
		}]
		"""
	When jobs删除会员等级'银牌会员'
	Then jobs能获取会员等级列表
		"""
		[{
			"name": "普通会员",
			"upgrade": "自动升级",
			"discount": "10"
		}, {
			"name": "铜牌会员",
			"upgrade": "自动升级",
			"pay_money": 1000.00,
			"pay_times": 20,
			"upgrade_lower_bound": 10000,
			"discount": "9"
		}, {
			"name": "金牌会员",
			"upgrade": "手动升级",
			"discount": "7"
		}]
		"""
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10000
		}, {
			"name": "bill",
			"member_rank": "普通会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1000
		}]
		"""
	When jobs更新"tom"的会员等级
		"""
		{
			"name": "tom",
			"member_rank": "金牌会员"
		}
		"""
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "金牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10000
		}, {
			"name": "bill",
			"member_rank": "普通会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1000
		}]
		"""
	When jobs删除会员等级'金牌会员'
	Then jobs能获取会员等级列表
		"""
		[{
			"name": "普通会员",
			"upgrade": "自动升级",
			"discount": "10"
		}, {
			"name": "铜牌会员",
			"upgrade": "自动升级",
			"pay_money": 1000.00,
			"pay_times": 20,
			"upgrade_lower_bound": 10000,
			"discount": "9"
		}]
		"""
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10000
		}, {
			"name": "bill",
			"member_rank": "普通会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1000
		}]
		"""


@mall2
Scenario: 2 手动添加积分使会员升级
	手动添加积分使会员升级
  	1. 添加少量积分会员不升级
  	2. 添加足够积分后会员升级

  	Given jobs给bill增加100积分
  	Given jobs给tom增加100积分
	Then jobs可以获得会员列表
	"""
		[{
			"name": "tom",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 10100,
			"integral":10100
		}, {
			"name": "bill",
			"member_rank": "普通会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 1100,
			"integral":1100
		}]
	"""

  	Given jobs给bill增加10000积分
  	Given jobs给tom增加80000积分
	Then jobs可以获得会员列表
		"""
		[{
			"name": "tom",
			"member_rank": "银牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 90100,
			"integral":90100
		}, {
			"name": "bill",
			"member_rank": "铜牌会员",
			"pay_money": 0.00,
			"pay_times": 0,
			"experience": 11100,
			"integral":11100
		}]
		"""
