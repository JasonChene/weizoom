# -*- coding: utf-8 -*-

from datetime import datetime

import mongoengine as models

class lotteryParticipance(models.Document):
	webapp_user_id= models.LongField(default=0) #参与者id
	member_id= models.LongField(default=0) #参与者id
	belong_to = models.StringField(default="", max_length=100) #对应的活动id
	has_prize = models.BooleanField(default=False) #是否中奖
	total_count = models.IntField(default=0) #已参与次数
	count = models.IntField(default=0) #可参与次数
	# tel = models.StringField(default="", max_length=100)
	# termite_data = models.DynamicField(default="") #termite数据
	# prize = models.DynamicField(default="") #活动奖励
	lottery_date = models.DateTimeField() #最近一次抽奖时间
	# created_at = models.DateTimeField() #创建时间

	meta = {
		'collection': 'lottery_lottery_participance'
	}

class lottoryRecord(models.Document):
	"""
	抽奖记录表
	"""
	webapp_user_id= models.LongField(default=0) #参与者id
	member_id= models.LongField(default=0) #参与者id
	belong_to = models.StringField(default="", max_length=100) #对应的抽奖活动id
	prize = models.StringField(default="", max_length=100) #奖项内容
	tel = models.StringField(default="", max_length=20)
	created_at = models.DateTimeField() #创建时间

	meta = {
		'collection': 'lottery_lottery_record'
	}

STATUS_NOT_START = 0
STATUS_RUNNING = 1
STATUS_STOPED = 2
class lottery(models.Document):
	owner_id = models.LongField() #创建人id
	name = models.StringField(default="", max_length=100) #名称
	start_time = models.DateTimeField() #开始时间
	end_time = models.DateTimeField() #结束时间
	status = models.IntField(default=0) #状态
	participant_count = models.IntField(default=0) #参与者数量
	winner_count = models.IntField(default=0) #中奖人数
	related_page_id = models.StringField(default="", max_length=100) #termite page的id
	created_at = models.DateTimeField() #创建时间
	expend = models.IntField(default=0) #消耗积分
	delivery = models.IntField(default=0) #参与送积分
	delivery_setting = models.StringField(default="true", max_length=20) #送积分规则
	limitation = models.StringField(default="once_per_user", max_length=32) #抽奖限制
	chance = models.IntField(default=0) #中奖几率
	type = models.StringField(default="true", max_length=10) #是否允许重复中奖
	
	meta = {
		'collection': 'lottery_lottery'
	}
	
	@property
	def status_text(self):
		if self.status == STATUS_NOT_START:
			return u'未开始'
		elif self.status == STATUS_RUNNING:
			now = datetime.today()
			if now >= self.end_time:
				return u'已结束'
			else:
				return u'进行中'
		elif self.status == STATUS_STOPED:
			return u'已结束'
		else:
			return u'未知'
	
	@property
	def is_finished(self):
		status_text = self.status_text
		if status_text == u'已结束':
			return True
		else:
			return False


	
