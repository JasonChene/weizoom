# -*- coding: utf-8 -*-

from datetime import datetime

from django.db import models
from django.contrib.auth.models import User

class TemplateCustomModule(models.Model):
	'''
	自定义模块
	'''
	owner = models.ForeignKey(User, related_name='owned_template_custom_modules')
	name = models.CharField(max_length=120, verbose_name="名称")
	reserve = models.IntegerField(default=0, verbose_name="预留字段")
	created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
	updated_at = models.DateTimeField(auto_now_add=True, verbose_name="修改时间")
	is_deleted = models.BooleanField(default=False, verbose_name="是否删除")

	class Meta(object):
		db_table = 'template_custom_module'
		verbose_name = '自定义模块'
		verbose_name_plural = '自定义模块'


class Image(models.Model):
	"""
	图片
	"""
	owner = models.ForeignKey(User, related_name="owned_termite_images")
	url = models.CharField(max_length=256, default='')  # 图片url
	width = models.IntegerField()  # width
	height = models.IntegerField()  # height
	created_at = models.DateTimeField(auto_now_add=True)  # 添加时间

	class Meta(object):
		db_table = 'webapp_image'
		verbose_name = '图片'
		verbose_name_plural = '图片'



class TemplateGlobalNavbar(models.Model):
	'''
	全局导航
	'''
	owner = models.ForeignKey(User, related_name='owned_template_global_navbar')
	is_enable = models.BooleanField(default=True, verbose_name='是否启用')
	content = models.TextField(default='', verbose_name='navbar的json字符串')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
	updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

	class Meta(object):
		db_table = 'template_global_navbar'
		verbose_name = '全局导航'
		verbose_name_plural = '全局导航'


	@staticmethod
	def get_object(user_id):
		if user_id > 0:
			global_navbar, _ = TemplateGlobalNavbar.objects.get_or_create(
				owner_id=user_id
			)
			return global_navbar
		else:
			return None

