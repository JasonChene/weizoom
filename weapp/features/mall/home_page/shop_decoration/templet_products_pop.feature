#_author_:师帅 15/10/13
#editor 新新 2015.10.14

Feature:自定义模块——【基础模块】商品-页面
	"""
        设置一个列表样式的商品展示区，只能选择到上架的商品设置商品列表展示区
        1、选择商品窗体规则
        	（1）可以选择'在售'的所有商品
        	（2）'在售'的所有商品按照'创建时间'倒序排列
        	（3）商品名称过长显示不全的"..."方式显示
        	（4）可以多选商品
        	（5）一个商品可以重复选择
        	（6）搜索模糊匹配'商品名称'
        	 (7) 在售商品列表分页显示，每页8个
        	（8）'新增商品'功能，打开新页面,进入'添加新商品'页，添加新商品，刷新之后在当前选择窗体中出现
        2、小图、一大两小的模式，当商品数量不够整组的时候，空缺的商品位置，空缺显示
        3、删除中间的商品后，后面的自动补齐
          （例如：一大两小，删除大图后，左下小图补到上方大图，右下小图补到左下小图）
        4、商品下架、删除之后,使用此商品的商品模板和使用商品模板的地方同步删除此商品，后面的商品依次补齐
        5、修改商品信息后，对应使用此商品的商品模板和使用商品模板的地方对应修改
        6、商品如果参加了促销活动显示促销价格
    """

Background:
	Given jobs登录系统
	And jobs已添加商品
		"""
		[{
			"name": "商品1可单行显示",
			"shelve_type":"上架",
			"price": 1.00
		},{
			"name": "商品2可两行显示",
			"shelve_type":"上架",
			"price": 2.00
		},{
			"name": "商品3不可两行显示",
			"shelve_type":"上架",
			"price": 3.00
		},{
			"name": "商品4",
			"shelve_type":"下架",
			"price": 4.00
		}]
		"""

@mall2  @termite2
Scenario:1 选择在售商品窗体：在售商品列表、搜索、添加新商品
	
	#搜索功能,按商品名称搜索
	#模糊匹配搜索
	When jobs按商品名称搜索
		"""
		{
			"search":"两行"
		}
		"""
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name":"商品3不可两行显示"
		},{
			"name":"商品2可两行显示"
		}]
		"""
	#完全匹配搜索
	When jobs按商品名称搜索
		"""
		{
			"search":"商品2可两行显示"
		}
		"""
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name":"商品2可两行显示"
		}]
		"""
	#空搜索
	When jobs按商品名称搜索
		"""
		{
			"search":""
		}
		"""
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name":"商品3不可两行显示"
		},{
			"name":"商品2可两行显示"
		},{
			"name":"商品1可单行显示"
		}]
		"""
	#添加新商品
	Given jobs已添加商品
		"""
		[{
			"name": "商品5",
			"shelve_type":"上架",
			"price": 5.00
		}]
		"""
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name":"商品5"
		},{
			"name":"商品3不可两行显示"
		},{
			"name":"商品2可两行显示"
		},{
			"name":"商品1可单行显示"
		}]
		"""

@mall2  @termite2
Scenario:2 商品选择列表分页,每页显示8个商品
	Given jobs已添加商品
		"""
		[{
			"name": "商品5",
			"shelve_type":"上架",
			"price": 5.00
		},{
			"name": "商品6",
			"shelve_type":"上架",
			"price": 6.00
		},{
			"name": "商品7",
			"shelve_type":"上架",
			"price": 7.00
		},{
			"name": "商品8",
			"shelve_type":"上架",
			"price": 8.00
		},{
			"name": "商品9",
			"shelve_type":"上架",
			"price": 9.00
		},{
			"name": "商品10",
			"shelve_type":"上架",
			"price": 10.00
		}]
		"""
	Then jobs商品模块商品选择列表显示'2'页
	When jobs访问商品选择列表第'1'页
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name": "商品10"
		},{
			"name": "商品9"
		},{
			"name": "商品8"
		},{
			"name": "商品7"
		},{
			"name": "商品6"
		},{
			"name": "商品5"
		},{
			"name": "商品3不可两行显示"
		},{
			"name": "商品2可两行显示"
		}]
		"""
	When jobs在微页面浏览'下一页'商品
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name":"商品1可单行显示"
		}]
		"""
	When jobs在微页面浏览'上一页'商品
	Then jobs在微页面获取'在售'商品选择列表
		"""
		[{
			"name": "商品10"
		},{
			"name": "商品9"
		},{
			"name": "商品8"
		},{
			"name": "商品7"
		},{
			"name": "商品6"
		},{
			"name": "商品5"
		},{
			"name":"商品3不可两行显示"
		},{
			"name":"商品2可两行显示"
		}]
		"""

@mall2  @termite2
Scenario:3 一个商品可以被重复选择
	When jobs创建微页面
		"""
		[{	
			"title": {
				"name": "微页面标题1"
			},
			"products":{
				"index": 1,
				"items": [{
					"name":"商品3不可两行显示",
					"price": 3.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				}],
				"list_style1":"大图",
				"list_style2":"默认样式",
				"show_product_name":"true",
				"show_price":"true"
			}
		}]
		"""
	Then jobs能获取'微页面标题1'
		"""
		{	
			"title": {
				"name": "微页面标题1"
			},
			"products":{
				"index": 1,
				"items": [{
					"name":"商品3不可两行显示",
					"price": 3.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				}],
				"list_style1":"大图",
				"list_style2":"默认样式",
				"show_product_name":"true",
				"show_price":"true"
			}
		}
		"""
	When jobs编辑微页面'微页面标题1'
		"""
		{
			"title": {
				"name": "微页面标题1"
			}, 
			"products": {
				"index": 1,
				"items": [{
					"name":"商品3不可两行显示",
					"price": 3.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				}],
				"list_style1":"小图",
				"list_style2":"简洁样式",
				"show_product_name":"true",
				"show_price":"true"
			}
		}
		"""

	Then jobs能获取'微页面标题1'
		"""
		{
			"title": {
				"name": "微页面标题1"
			}, 
			"products": {
				"index": 1,
				"items": [{
					"name":"商品3不可两行显示",
					"price": 3.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				},{
					"name":"商品1可单行显示",
					"price": 1.00
				},{
					"name":"商品2可两行显示",
					"price": 2.00
				}],
				"list_style1":"小图",
				"list_style2":"简洁样式",
				"show_price":"true"
			}
		}
		"""