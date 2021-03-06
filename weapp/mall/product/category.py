# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
import copy
from operator import attrgetter
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q

from mall.promotion.utils import verification_multi_product_promotion, verification_multi_product_promotion_weizoom_mall
from .. import models as mall_models
from .. import export
from . import utils as category_ROA_utils
from core import resource, paginator
from core.jsonresponse import create_response
from core.exceptionutil import unicode_full_stack
from watchdog.utils import watchdog_warning

from account.models import UserProfile


class Categories(resource.Resource):
    """
    分组列表通用类，只返回分组本身信息
    """
    app = 'mall2'
    resource = 'categories'

    @login_required
    def api_get(request):
        filter_name = request.GET.get('filter_name', '')
        categories = mall_models.ProductCategory.objects.filter(
            owner=request.manager)
        if filter_name:
            categories = categories.filter(name__contains=filter_name)
        count_per_page = int(request.GET.get('count_per_page', 10))
        cur_page = int(request.GET.get('page', '1'))
        pageinfo, categories = paginator.paginate(
            categories, cur_page, count_per_page,
            query_string=request.META['QUERY_STRING'])

        items = []
        for category in categories:
            data = {
                'id': category.id,
                'name': category.name,
                'created_at': category.created_at.strftime("%Y-%m-%d %H:%M")
            }
            items.append(data)

        response = create_response(200)
        response.data = {
            'items': items,
            'pageinfo': paginator.to_dict(pageinfo),
            'sortAttr': '',
            'data': {}
        }
        return response.get_response()


class CategoryProducts(resource.Resource):
    """
    促销选择分组时返回该分组的可用商品
    """
    app = 'mall2'
    resource = 'category_products'

    @login_required
    def api_get(request):
        """
        @param category_ids:分组id列表
        @param promotion_type:支持coupon,integral_sale
        @return promotion_type: 促销类型
        """
        mall_type = UserProfile.objects.get(user_id=request.manager.id).webapp_type
        category_ids = request.GET.get('category_ids', '').split(',')
        promotion_type = request.GET.get('promotion_type', 'coupon')
        relations = mall_models.CategoryHasProduct.objects.filter(
            category_id__in=category_ids)

        product_ids = set([relation.product_id for relation in relations])
        if mall_type == 1:
            _, error_product_ids = verification_multi_product_promotion_weizoom_mall(request.manager, product_ids, promotion_type)
        else:
            _, error_product_ids = verification_multi_product_promotion(request.manager, product_ids, promotion_type)

        product_ids = list(set(product_ids) - set(error_product_ids))

        if mall_type == 1:
            products = list(mall_models.Product.objects.filter(id__in=product_ids))
        else:
            products = list(mall_models.Product.objects.filter(
                owner=request.manager, is_deleted=False, shelve_type=mall_models.PRODUCT_SHELVE_TYPE_ON,id__in=product_ids))

        mall_models.Product.fill_details(request.manager,
                                         products,
                                         {"with_product_model": True,
                                          "with_model_property_info": True,
                                          'with_sales': True})

        mall_models.Product.fill_details(request.manager,
                             products,
                                    {"with_product_model": True,
                                     "with_model_property_info": True,
                                     'with_sales': True})

        id2product = {}
        for product in products:
            data = product.format_to_dict()
            id2product[product.id] = data
        items = id2product.values()
        items.sort(lambda x, y: cmp(x['id'], y['id']))
        response = create_response(200)
        response.data = {
            'products': items
        }
        return response.get_response()

class CategoryProductList(resource.Resource):
    app = 'mall2'
    resource = 'category_product_list'

    
    @login_required
    def api_get(request):
        """
        功能1: 获得商品分类的可选商品列表

        Args:
          id:
          action:

        可选商品指的是还不属于当前分类的商品.
          可选商品集合 ＝ manager的所有商品集合 － 已经在分类中的商品集合

        功能2: 获取指定排序的分类

        Args:
          action: 'sorted'
          category_id:
          reverse: 'true' or 'false'

        """
        mall_type = request.user_profile.webapp_type
        action = request.GET.get('action')
        category_id = int(request.GET.get('id'))
        if not action:
            COUNT_PER_PAGE = 20
            name_query = request.GET.get('name')

            #获取商品集合
            product_pool2status = {}
            if mall_type:
                product_pool = mall_models.ProductPool.objects.filter(woid=request.manager.id, status__in=[mall_models.PP_STATUS_OFF, mall_models.PP_STATUS_ON])
                
                product_pool2status = dict([(pool.product_id, pool.status) for pool in product_pool])
                product_ids = product_pool2status.keys()

                products = mall_models.Product.objects.filter(Q(owner=request.manager,
                    is_deleted=False)|Q(id__in=product_ids)).exclude(
                    shelve_type=mall_models.PRODUCT_SHELVE_TYPE_RECYCLED)
            else:
                products = mall_models.Product.objects.filter(
                    owner=request.manager, is_deleted=False).exclude(
                    shelve_type=mall_models.PRODUCT_SHELVE_TYPE_RECYCLED)
            # 微众商城代码
            #duhao 20151120
            #当在 商品-分组管理 页面管理分组时，弹出的商品列表应该只包含商城自己商品列表里的在售商品
            # if request.manager.id == 216:
            #     _products = []
            #     for product in products:
            #         if product.owner_id == 216 or (product.weshop_sync > 0 and product.shelve_type == mall_models.PRODUCT_SHELVE_TYPE_ON and \
            #             product.weshop_status in (mall_models.PRODUCT_SHELVE_TYPE_ON, mall_models.PRODUCT_SHELVE_TYPE_OFF)):
            #             product.shelve_type = product.weshop_status
            #             _products.append(product)
            #     products = _products
                    
            if name_query:
                # products = [
                #     product for product in products if name_query in product.name
                # ]
                products = products.filter(name__contains=name_query)

            products = list(products)
            if category_id != -1:
                #获取已在分类中的商品
                relations = mall_models.CategoryHasProduct.objects.filter(
                    category_id=category_id)
                existed_product_ids = set(
                    [relation.product_id for relation in relations]
                )

                #获取没在分类中的商品集合(分类的可选商品集合)
                products = filter(
                    lambda product: (product.id not in existed_product_ids),
                    products
                )
            products.sort(lambda x,y: cmp(y.id, x.id))
            products.sort(lambda x,y: cmp(y.update_time, x.update_time))

            #进行分页
            count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
            cur_page = int(request.GET.get('page', '1'))
            pageinfo, products = paginator.paginate(
                products,
                cur_page,
                count_per_page,
                query_string=request.META['QUERY_STRING'])

            mall_models.Product.fill_display_price(products)
            mall_models.Product.fill_details(request.manager,
                                             products,
                                             {'with_sales': True})
            result_products = []
            for product in products:
                relation = '%s_%s' % (category_id, product.id)

                if mall_type and product_pool2status:
                    if product.id in product_pool2status.keys():
                        status_pool = product_pool2status[product.id]
                        if status_pool == mall_models.PP_STATUS_ON:
                            status = u'在售'
                        elif status_pool == mall_models.PP_STATUS_OFF:
                            status = u'待售'
                        elif status_pool == mall_models.PP_STATUS_DELETE:
                            status = u'已删除'
                        else:
                            status = u'商品池中'
                    else:
                        status = product.status
                else:
                    status = product.status

                result_products.append({
                    "id": product.id,
                    "name": product.name,
                    "display_price": product.display_price,
                    "status": status,
                    "sales": product.sales if product.sales else -1,
                    "update_time": product.update_time.strftime("%Y-%m-%d")
                })
            # result_products.sort(lambda x,y: cmp(y['update_time'], x['update_time']))

            response = create_response(200)
            response.data = {
                'items': result_products,
                'pageinfo': paginator.to_dict(pageinfo),
                'sortAttr': '',
                'data': {}
            }
            return response.get_response()
        elif action == 'sorted':
            reverse = json.loads(request.GET.get('reverse', 'true'))
            #获取category集合
            product_categories = mall_models.ProductCategory.objects.filter(
                id=category_id)
            mall_type = request.user_profile.webapp_type
            category_ROA_utils.sorted_products(mall_type, request.manager.id, product_categories, reverse)

            response = create_response(200)
            response.data = {
                'product_categories': product_categories
            }
            return response.get_response()

class CategoryList(resource.Resource):
    app = 'mall2'
    resource = 'category_list'

    @login_required
    def get(request):
        """
        商品分类列表页面
        """
        c = RequestContext(request, {
                    'first_nav_name': export.PRODUCT_FIRST_NAV,
                    'second_navs': export.get_mall_product_second_navs(request),
                    'second_nav_name': export.PRODUCT_MANAGE_CATEGORY_NAV,
                    'has_categories':True}
        )
        return render_to_response('mall/editor/product_categories.html', c)

    @login_required
    def api_get(request):
        """
        功能: 获得商品分组列表
        """
        COUNT_PER_PAGE = 15
        #获取category集合
        product_categories = mall_models.ProductCategory.objects.filter(
            owner=request.manager)
        #查询
        category_name = request.GET.get('category_name','')
        product_name = request.GET.get('product_name','')
        if category_name:
            product_categories = product_categories.filter(name__icontains=category_name)
        if product_name:
            products = mall_models.Product.objects.filter(name__icontains=product_name, is_deleted=False)
            category_ids = mall_models.CategoryHasProduct.objects.filter(product__in=products).values_list('category_id', flat=True)
            product_categories = product_categories.filter(id__in=category_ids)

        mall_type = request.user_profile.webapp_type

        #进行分页
        count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
        cur_page = int(request.GET.get('page', '1'))
        pageinfo, product_categories = paginator.paginate(
            product_categories,
            cur_page,
            count_per_page,
            query_string=request.META['QUERY_STRING'])

        #构造返回数据
        category_ROA_utils.sorted_products(mall_type,request.manager.id, product_categories, True)
        items = []
        for category in product_categories:
            items1 = []
            for product in category.products:
                product_data = {
                    'id':product.id,
                    'name':product.name,
                    'display_price':product.display_price,
                    'status':str(product.status),
                    'display_index':product.display_index,
                    'sales':product.sales,
                    'join_category_time':product.join_category_time.strftime('%Y-%m-%d %H:%M')
                }
                items1.append(product_data)
            data = {
                'id': category.id,
                'name': category.name,
                'products':items1
            }
            items.append(data)
        response = create_response(200)
        response.data = {
            'items': items,
            'pageinfo': paginator.to_dict(pageinfo),
            'sortAttr': '',
            'data': {}
        }
        return response.get_response()

    @login_required
    def put(request):
        """创建商品分类
        """

    @login_required
    def api_post(request):
        """更新商品排序

        Args:
          category_id:
          product_id:
          position:
        """
        try:
            category_id = request.POST.get('category_id')
            product_id = request.POST.get('product_id')
            position = request.POST.get('position')
            category_has_product = mall_models.CategoryHasProduct.objects.get(
                category_id=category_id,
                product_id=product_id
            )
            category_has_product.move_to_position(position)
            response = create_response(200)
            return response.get_response()
        except:
            watchdog_warning(
                u"更新商品分组商品排序失败, cause:\n{}".format(unicode_full_stack())
            )
            response = create_response(500)
            return response.get_response()


class Category(resource.Resource):
    app = 'mall2'
    resource = 'category'

    @login_required
    def get(request):
        """
        编辑商品分类页面
        """
        product_categories = mall_models.ProductCategory.objects.filter(
            owner=request.manager,
            id=request.GET.get('id')
        )
        c = RequestContext(request, {
                    'category_id': request.GET.get('id'),
                    'first_nav_name': export.PRODUCT_FIRST_NAV,
                    'second_navs': export.get_mall_product_second_navs(request),
                    'second_nav_name': export.PRODUCT_MANAGE_CATEGORY_NAV,
                    'has_categories':True,
                    'category_name':product_categories[0].name}
        )
        return render_to_response('mall/editor/category.html', c)

    @login_required
    def api_get(request):
        category_id = request.GET.get('category_id')
        mall_type = request.user_profile.webapp_type
        product_categories = mall_models.ProductCategory.objects.filter(
            owner=request.manager,
            id=category_id
        )
        if product_categories:
            category_ROA_utils.sorted_products(mall_type,request.manager.id, product_categories, True)
            items = []
            for product in product_categories[0].products:
                category_has_products = mall_models.CategoryHasProduct.objects.filter(product_id=product.id).order_by('category__id')
                category_list = []
                for category_has_product in category_has_products:
                    category_list.append({
                        'id':category_has_product.category.id,'name':category_has_product.category.name
                        })
                product_data = {
                    'id':product.id,
                    'name':product.name,
                    'display_price':product.display_price,
                    'status':str(product.status),
                    'display_index':product.display_index,
                    'sales':product.sales,
                    'join_category_time':product.join_category_time.strftime('%Y-%m-%d %H:%M'),
                    'categories':category_list
                }
                items.append(product_data)
            response = create_response(200)
            response.data = {
                'name':product_categories[0].name,
                'items': items,
                'category_name':product_categories[0].name
            }
            return response.get_response()
        else:
            response = create_response(500)
            response.data = {'msg':"该商品分类已不存在"}
            return response.get_response()
    @login_required
    def api_put(request):
        """创建商品分类

        method: put
        args: {'name': 'str',
               'product_ids': ''}

        """
        # pdb.set_trace()
        if request.POST:
            product_category = mall_models.ProductCategory.objects.create(
                owner=request.manager,
                name=request.POST.get('name', '').strip()
            )
            product_ids = request.POST.getlist('product_ids[]')
            product_category.product_count = len(product_ids)
            product_category.save()

            for product_id in product_ids:
                mall_models.CategoryHasProduct.objects.create(
                    product_id=product_id,
                    category=product_category
                )
            return create_response(200).get_response()

    @login_required
    def api_post(request):
        """更新商品分类

        Args:
          id: 分类id
          name: 新的分类名
          product_ids: 新的属于该分类的商品id集合

        """
        category_id = request.POST['id']
        product_ids = request.POST.getlist('product_ids[]')
        product_categorys = mall_models.ProductCategory.objects.filter(owner=request.manager, id=category_id)
        if 0 != product_categorys.count():
            product_categorys.update(
            name=request.POST.get('name', '').strip(),
            product_count=len(product_ids)
            )
        else:
            response = create_response(500)
            response.data = {'msg':"该商品分类已不存在"}
            return response.get_response()
        #重建<category, product>关系
        for product_id in product_ids:
            mall_models.CategoryHasProduct.objects.create(
                product_id=product_id,
                category_id=category_id)

        return create_response(200).get_response()

    @login_required
    def api_delete(request):
        """删除商品分类or商品分类删除一个商品

        Args:
          category_id: 分类id
          product_id: 商品id  # 对删除商品分类可选
        """

        product_id = request.POST.get('product_id')
        category_id = request.POST.get('category_id')
        # import pdb
        # pdb.set_trace()
        if product_id:
            mall_models.CategoryHasProduct.objects.filter(
                product_id=product_id,
                category_id=category_id
            ).delete()
        elif category_id:
            mall_models.ProductCategory.objects.filter(
                owner=request.manager,
                id=category_id
            ).delete()
        from cache.webapp_cache import update_product_list_cache
        # 手动调用,django的信号似乎在delete之前执行了,生产了错误的缓存
        update_product_list_cache(request.manager.id)
        return create_response(200).get_response()


class UpdateProductCategory(resource.Resource):
    """
    商品列表：编辑商品分组
    """
    app = 'mall2'
    resource = 'update_product_category'

    @login_required
    def api_get(request):
        id2name = dict(mall_models.ProductCategory.objects.filter(owner=request.manager).values_list('id', 'name'))
        items = []
        for category_id,name in id2name.items():
            items.append({
                "id": category_id,
                "name": name
            })

        response = create_response(200)
        response.data = {
            'items': items,
        }

        return response.get_response()
    @login_required
    def api_post(request):
        product_id = request.POST.get('product_id')
        category_ids = request.POST.get('category_ids','')
        if category_ids:
            category_ids = map(lambda x:int(x), category_ids.split(','))
        else:
            category_ids = 0
        # category_ids = category_ids.split(',')
        update_product_categories(request, product_id, category_ids)

        response = create_response(200)
        return response.get_response()

class BatchUpdateProductCategory(resource.Resource):
    """
    商品列表：编辑商品分组
    """
    app = 'mall2'
    resource = 'batch_update_product_category'

    @login_required
    def api_post(request):
        product_ids = request.POST.get('product_ids')
        category_ids = request.POST.get('category_ids')
        product_ids = map(lambda x:int(x), product_ids.split(','))
        category_ids = map(lambda x:int(x), category_ids.split(','))

        for category_id in category_ids:
            tmp_product_ids = copy.copy(product_ids)
            category_product_ids = mall_models.CategoryHasProduct.objects.filter(category_id=category_id, category__owner=request.manager, 
                product_id__in=tmp_product_ids).values_list('product_id', flat=True)
            for product_id in category_product_ids:
                tmp_product_ids.remove(product_id)
            if tmp_product_ids:
                category_has_product_models = []
                for product_id in tmp_product_ids:
                    category_has_product_models.append(mall_models.CategoryHasProduct(
                        category_id=category_id,
                        product_id=product_id,
                        )
                    )
                mall_models.CategoryHasProduct.objects.bulk_create(category_has_product_models)
                mall_models.ProductCategory.objects.filter(id=category_id).update(product_count=F('product_count')+len(tmp_product_ids))
        response = create_response(200)
        return response.get_response()

def update_product_categories(request, product_id, category_ids):
    if category_ids:
    #删除勾去的
        category_has_products_by_product_id = mall_models.CategoryHasProduct.objects.filter(product_id=product_id, category__owner=request.manager)
        category_has_products = category_has_products_by_product_id.exclude(category_id__in=category_ids)
        decrease_category_ids = [category_has_product.category_id for category_has_product in category_has_products]
        mall_models.CategoryHasProduct.objects.filter(product_id=product_id, category_id__in=decrease_category_ids).delete()
        mall_models.ProductCategory.objects.filter(id__in=decrease_category_ids, owner=request.manager).update(product_count=F('product_count')-1)

        #去掉存在的分组id
        
        exist_category_ids = category_has_products_by_product_id.filter(category_id__in=category_ids).values_list('category_id', flat=True)
        for category_id in exist_category_ids:
            category_ids.remove(category_id)
        #创建CategoryHasProduct及商品分组数量+1
        category_has_product_models = []
        for category_id in category_ids:
            category_has_product_models.append(mall_models.CategoryHasProduct(
                category_id=category_id,
                product_id=product_id,
                )
            )
        mall_models.CategoryHasProduct.objects.bulk_create(category_has_product_models)
        mall_models.ProductCategory.objects.filter(id__in=category_ids).update(product_count=F('product_count')+1)
    else:
        decrease_category_ids = mall_models.CategoryHasProduct.objects.filter(product_id=product_id).values_list('category_id', flat=True)
        mall_models.CategoryHasProduct.objects.filter(product_id=product_id).delete()
        mall_models.ProductCategory.objects.filter(id__in=decrease_category_ids, owner=request.manager).update(product_count=F('product_count')-1)