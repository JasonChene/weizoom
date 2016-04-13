#_author_:张雪 2016.4.11
Feature: 微信用户提交高级投票申请
	"""
		1.微信用户可以通过报名高级投票
		【名称】：必填项，高级投票活动的名称；
		【分组选择】：必填项，下拉框选择其中一个分组；
		【输入编号】：必填项，最多可输入16个字符；
		【输入详情】：必填项；
	"""

Background:
	Given jobs登录系统
	When jobs新建高级投票活动
	#新建高级微信投票活动,无分组
	"""
		[{
			"title":"微信高级投票",
			"rule":
			[{
				"content":"微信高级投票活动",
				"cycle":"daily",
				"vote_times":"1"
			}],
			"group":[],
			"player_num":"报名输入",
			"desc":"高级投票活动介绍",
			"start_date":"今天",
			"end_date":"2天后",
			"pic":"1.jpg"

		}]
	"""
	When jobs已添加单图文
		"""
		[{
			"title":"高级投票活动1单图文",
			"cover": [{
				"url": "/standard_static/test_resource_img/hangzhou1.jpg"
			}],
			"cover_in_the_text":"true",
			"summary":"微信高级投票",
			"content":"微信高级投票",
			"jump_url":"微信高级投票"
		}]
		"""
	When jobs已添加关键词自动回复规则
		"""
		[{
			"rules_name":"规则1",
			"keyword": 
				[{
					"keyword": "微信高级投票",
					"type": "equal"
				}],
			"keyword_reply": 
				[{
					"reply_content":"微信高级投票",
					"reply_type":"text_picture"
				}]
		
		}]
		"""
@mall2 @apps @shvote @shvote_apply
Scenario:1.微信用户可以进行高级投票报名
	When bill关注jobs的公众号
	When bill访问jobs的webapp
	When bill在微信中向jobs的公众号发送消息'微信高级投票'
	Then bill收到自动回复'高级投票活动1单图文'
	When bill点击图文"高级投票活动1单图文"进入高级投票活动页面
	When bill参加高级投票报名活动
	"""
		{
			"name":"bill",
			"group":["初中组"],
			"number":"001",
			"details":"bill的产品好"
		}
	"""
	Then jobs能获得报名详情列表
	"""
		[{
			"player":"bill",
			"votes":0,
			"number":"001",
			"status":"待审核"
		}]
	"""
	Then jobs获得微信高级投票活动列表
		"""
		[{
			"name":"微信高级投票",
			"participant_count":0,
			"sign_count":"1",
			"start_date":"今天",
			"end_date":"2天后",
			"status":"进行中",
			"actions": ["删除","链接","预览","报名详情","查看结果"]
		}]
		"""
