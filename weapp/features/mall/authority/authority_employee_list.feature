#_author_:zhangsx

Feature:员工管理-员工信息列表页面，分页
Background:
     Given jobs登录系统
     And jobs已添加角色信息
         """
         [{
             "role_name":"角色0",
             #"button":"添加权限",
             "permissions":
             [{
                  "type":""，
                   "value":
                   [{
                      "name":"暂未给此角色添加权限"
                   }]
             }]
          
         },{
             "role_name":"角色1",
             #"button":"修改权限",
             "permissions":
             [{
                 "type":"商品管理"，
                 "value":
                     [
                         {"name":"添加新商品"},
                         {"name":"在售商品管理"},
                         {"name":"待售商品管理"}
                     ]
             }]
         },{
             "role_name":"角色2",
             #"button":"修改权限",
             "permissions":
                 [{
                     "type":"商品管理"，
                     "value":
                     [{
                         "name":"添加新商品"
                     }]
                 },{
                     "type":"促销管理"，
                     "value":
                     [
                         {"name":"促销查询"},
                         {"name":"限时抢购"}
                     ]
                 },{
                     "type":"配置管理"，
                     "value":
                     [
                         {"name":"运费模板"},
                         {"name":"物流名称管理"},
                         {"name":"支付方式"}
                     ]  
                 }]
         }]
         """
     And jobs已新建部门
         """
         [
          {"department_name":"部门a"},
          {"department_name":"部门b"},   
          {"department_name":"部门c"}
         ]
         """
     #jobs已新建15个员工，具体数据由开发同学后台添加一下
     And jobs已新建员工
       """
         [{
             "employees":
              [{
                 "account_name":"ceshi15",
                 "password":"123456a",
                 "confirm_password":"123456a",
                 "employee_name":"张15",
                 "department_name":"部门a"
             }]
             "roles":
             [{
                 "role_name":"角色0",
                 "is_selected":"Y"
             },{
                 "role_name":"角色1",
                 "is_selected":"Y"
             },{
                 "role_name":"角色2",
                 "is_selected":"N"
             }]
             "permissions":
              [{
                 "presentation":"",
                 "type":"商品管理"，
                 "value":
                     [
                         {"name":"添加新商品"},
                         {"name":"在售商品管理"},
                         {"name":"待售商品管理"}
                     ]
               }]
         },{
            "employees":
               [{
                 "account_name":"ceshi01",
                 "password":"123456a",
                 "confirm_password":"123456a",
                 "employee_name":"张01",
                 "department_name":"部门c"
               }]
             "roles":
               [{
                 "role_name":"角色0",
                 "is_selected":"N"
               },{
                 "role_name":"角色1",
                 "is_selected":"N"
               },{
                 "role_name":"角色2",
                 "is_selected":"N"
               }]
             "permissions":
               [{
                 "presentation":"此员工未设置权限",
                 "type":"",
                 "value":""
               }]
         }]
       """   
Scenario:1员工信息列表页面、分页
     When jobs已设置分页条件
    """
    {
        "page_count":10
    }
    """
     #默认显示所有部门的员工信息列表
         When jobs登录系统
         Then jobs获取员工信息列表
         """
         [{ 
             "reminder":"",
             "employees":
              [{
                 "account_name":"ceshi15",
                 "employee_name":"张15",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                "account_name":"ceshi14",
                 "employee_name":"张14",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi13",
                 "employee_name":"张13",
                 "department_name":"部门a",
                 "roles":"角色1",
                 "is_active":"启用"
             },{
                "account_name":"ceshi12",
                 "employee_name":"张12",
                 "department_name":"部门a",
                 "roles":"角色0",
                 "is_active":"停用"
             },{
                "account_name":"ceshi11",
                 "employee_name":"张11",
                 "department_name":"部门a",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi10",
                 "employee_name":"张45",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi09",
                 "employee_name":"张09",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi08",
                 "employee_name":"张08",
                 "department_name":"部门b",
                 "roles":"角色1",
                 "is_active":"启用" 
             },{
                "account_name":"ceshi07",
                 "employee_name":"张07",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi06",
                 "employee_name":"张06",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             }]
         }]
         """ 
         And jobs获取显示共2页        
         When jobs浏览'下一页'
         Then jobs获取员工信息列表
         """
         [{
            "reminder":"",
             "employees":
              [{
                 "account_name":"ceshi05",
                 "employee_name":"张04",
                 "department_name":"部门c",
                 "roles":"",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi04",
                 "employee_name":"张04",
                 "department_name":"部门c",
                 "roles":"角色0",
                 "is_active":"启用"
             },{
                "account_name":"ceshi03",
                 "employee_name":"张03",
                 "department_name":"部门c",
                 "roles":"",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi02",
                 "employee_name":"张02",
                 "department_name":"部门c",
                 "roles":"",
                 "is_active":"启用"  
             },{
                "account_name":"ceshi01",
                 "employee_name":"张01",
                 "department_name":"部门c",
                 "roles":"",
                 "is_active":"启用"
             }]
         }]
         """
         When jobs浏览'上一页'
         Then jobs获取员工信息列表
         """
         [{ 
             "reminder":"",
             "employees":
              [{
                 "account_name":"ceshi15",
                 "employee_name":"张15",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                "account_name":"ceshi14",
                 "employee_name":"张14",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi13",
                 "employee_name":"张13",
                 "department_name":"部门a",
                 "roles":"角色1",
                 "is_active":"启用"
             },{
                "account_name":"ceshi12",
                 "employee_name":"张12",
                 "department_name":"部门a",
                 "roles":"角色0",
                 "is_active":"停用"
             },{
                "account_name":"ceshi11",
                 "employee_name":"张11",
                 "department_name":"部门a",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi10",
                 "employee_name":"张45",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi09",
                 "employee_name":"张09",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi08",
                 "employee_name":"张08",
                 "department_name":"部门b",
                 "roles":"角色1",
                 "is_active":"启用" 
             },{
                "account_name":"ceshi07",
                 "employee_name":"张07",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             },{
                "account_name":"ceshi06",
                 "employee_name":"张06",
                 "department_name":"部门b",
                 "roles":"",
                 "is_active":"启用"
             }]
             -·
         }]
         """ 
         
     #选中部门查看员工信息列表
         When jobs查看'部门a'的员工信息
         #Then jobs展示区左侧'部门a'被选中
         Then jobs获取'部门a'员工信息列表
         """
         [{ 
             "reminder":"",
             "employees":
              [{
                 "account_name":"ceshi15",
                 "employee_name":"张15",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                "account_name":"ceshi14",
                 "employee_name":"张14",
                 "department_name":"部门a",
                 "roles":"角色0及其他",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi13",
                 "employee_name":"张13",
                 "department_name":"部门a",
                 "roles":"角色1",
                 "is_active":"启用"
             },{
                 "account_name":"ceshi12",
                 "employee_name":"张12",
                 "department_name":"部门a",
                 "roles":"角色0",
                 "is_active":"停用"
             },{
                 "account_name":"ceshi11",
                 "employee_name":"张11",
                 "department_name":"部门a",
                 "roles":"",
                 "is_active":"启用"
             }]
         }]   
         """



   