# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json, copy
from datetime import datetime
from operator import attrgetter

from django.db.models import Q

from mall import models
from mall import signals as mall_signals
from account.models import UserProfile
from mall.promotion import models as promotion_model
from core import search_util
from utils import ding_util

DING_GROUP_ID = '80035247'

def process_custom_model(custom_model_str):
    """处理custommodels字符串

    Args:
        customModels(str): a str like 2:4_1:3

    Return:
        list: the list like [{
                                'property_id': 2,
                                'property_value_id': 4
                            },{
                                'property_id': 1,
                                'property_value_id': 4
                            }]
    """
    properties = []
    property_infos = custom_model_str.split('_')
    for property_info in property_infos:
        items = property_info.split(':')
        properties.append({
            'property_id': int(items[0]),
            'property_value_id': int(items[1])
        })
    return properties


def extract_product_model(request):
    is_use_custom_models = request.POST.get("is_use_custom_model", '') == u'true'

    use_custom_models = json.loads(request.POST.get('customModels', '[]'))
    if use_custom_models and is_use_custom_models:
        standard_model = {
            "price": 0.0,
            "weight": 0.0,
            "stock_type": models.PRODUCT_STOCK_TYPE_LIMIT,
            "stocks": 0,
            "user_code": '',
            "is_deleted": True
        }
        custom_models = use_custom_models
        for model in custom_models:
            model['properties'] = process_custom_model(model['name'])

    else:
        price = request.POST.get('price', '0.0').strip()
        weight = request.POST.get('weight', '0.0').strip()
        stock_type = int(request.POST.get(
            'stock_type',
            models.PRODUCT_STOCK_TYPE_UNLIMIT)
        )
        stocks = request.POST.get('stocks')
        if stocks and int(stocks) == -1:
            stocks = 0
        stocks = int(stocks) if stocks else 0
        user_code = request.POST.get('user_code', '').strip()
        standard_model = {
            "price": price,
            "weight": weight,
            "stock_type": stock_type,
            "stocks": stocks,
            "user_code": user_code,
        }
        custom_models = []
    return (standard_model, custom_models)

PRODUCT_FILTERS = {
    'product': [{
        'comparator': lambda product, filter_value: filter_value in product.name,
        'query_string_field': 'name'
    }, {
        'comparator': lambda product, filter_value: product.sales >= int(filter_value),
        'query_string_field': 'lowSales'
    }, {
        'comparator': lambda product, filter_value: product.sales <= int(filter_value),
        'query_string_field': 'highSales'
    }, {
        'comparator': lambda product, filter_value: (int(filter_value) == -1) or (int(filter_value) in [category['id'] for category in product.categories if category['is_selected']]),
        'query_string_field': 'category'
    }, {
        'comparator': lambda product, filter_value: filter_value == product.bar_code,
        'query_string_field': 'barCode'
    }, {
        'comparator': lambda product, filter_value: product.created_at >= datetime.strptime(filter_value, '%Y-%m-%d %H:%M'),
        'query_string_field': 'startDate'
    }, {
        'comparator': lambda product, filter_value: product.created_at <= datetime.strptime(filter_value, '%Y-%m-%d %H:%M'),
        'query_string_field': 'endDate'
    }],
    'models': [{
        'comparator': lambda model, filter_value: model['price'] >= float(filter_value),
        'query_string_field': 'lowPrice'
    }, {
        'comparator': lambda model, filter_value: model['price'] <= float(filter_value),
        'query_string_field': 'highPrice'
    }, {
        'comparator': lambda model, filter_value: model['stock_type'] == models.PRODUCT_STOCK_TYPE_UNLIMIT or model['stocks'] >= int(filter_value),
        'query_string_field': 'lowStocks'
    }, {
        'comparator': lambda model, filter_value: model['stock_type'] != models.PRODUCT_STOCK_TYPE_UNLIMIT and 0 <= model['stocks'] <= int(filter_value) or int(filter_value) < 0,
        'query_string_field': 'highStocks'
    }]
}


def filter_products(request, products):
    has_filter = search_util.init_filters(request, PRODUCT_FILTERS)
    if not has_filter:
        return products

    filtered_products = []
    products = search_util.filter_objects(products, PRODUCT_FILTERS['product'])
    if not products:
        return filtered_products

    for product in products:
        models = copy.copy(product.models)
        if None in models:
            models.remove(None)
        models = search_util.filter_objects(models, PRODUCT_FILTERS['models'])
        if models:
            filtered_products.append(product)
    return filtered_products


def sorted_products(manager_id, product_categories, reverse):
    """根据display_index对在售商品进行排序

    Args:
      products(list): 根据CategoryHasProduct，添加过display的product列表
    """
    #获取与category关联的product集合
    category_ids = (category.id for category in product_categories)
    relations = models.CategoryHasProduct.objects.filter(
        category_id__in=category_ids).select_related('product')
    categoryId2relations = dict()
    for relation in relations:
        categoryId2relations.setdefault(relation.category_id, []).append(relation)
    productIds = set([x.product_id for x in relations])
    products = models.Product.objects.filter(id__in=productIds, is_deleted=False).exclude(
        shelve_type=models.PRODUCT_SHELVE_TYPE_RECYCLED)
    # 微众商城代码
    #duhao 20151120
    #微众商城的商品-分组管理 页面  商品的状态应该是商品在微众商城里的状态，而不是在商户里的状态
    # if manager_id == 216:
    #     _products = []
    #     for product in products:
    #         if product.owner_id == 216 or (product.weshop_sync > 0 and product.shelve_type == models.PRODUCT_SHELVE_TYPE_ON):
    #             if product.owner_id != 216:
    #                 product.shelve_type = product.weshop_status
    #             _products.append(product)
    #     products = _products

    models.Product.fill_display_price(products)
    models.Product.fill_sales_detail(manager_id, products, productIds)
    id2product = dict([(product.id, product) for product in products])

    for c in product_categories:
        products = []
        for i in categoryId2relations.get(c.id, []):
            if id2product.has_key(i.product_id):
                product = copy.copy(id2product[i.product_id])
                product.display_index = i.display_index
                product.join_category_time = i.created_at
                products.append(product)

        products_is_0 = filter(lambda p: p.display_index == 0 or p.shelve_type != models.PRODUCT_SHELVE_TYPE_ON, products)
        products_not_0 = filter(lambda p: p.display_index != 0, products)
        products_is_0 = sorted(products_is_0, key=attrgetter('shelve_type', 'join_category_time', 'id'), reverse=True)
        products_not_0 = sorted(products_not_0, key=attrgetter('display_index'))
        products = products_not_0 + products_is_0

        # products = sorted(products, key=attrgetter('join_category_time', 'id'), reverse=True)
        # products = sorted(products, key=attrgetter('shelve_type', 'display_index'))
        # products = sorted(products, key=attrgetter('shelve_type'), reverse=reverse)


        c.products = products
    return product_categories

MALL_PRODUCT_DELETED = -1
MALL_PRODUCT_OFF_SHELVE = 0
MALL_PRODUCT_HAS_MORE_MODEL = 1

DELETED_WEIZOOM_PRODUCT_REASON = {
    MALL_PRODUCT_DELETED: u'供货商商品删除',
    MALL_PRODUCT_OFF_SHELVE: u'供货商商品下架',
    MALL_PRODUCT_HAS_MORE_MODEL: u'供货商修改商品为多规格'
}

def delete_weizoom_mall_sync_product(request, product, reason):
    try:
        relations = models.WeizoomHasMallProductRelation.objects.filter(Q(mall_product_id=product.id)|Q(weizoom_product_id=product.id))
        weizoom_product_ids = [relation.weizoom_product_id for relation in relations]
        models.Product.objects.filter(id__in=weizoom_product_ids).update(is_deleted=True)
        relations.update(is_deleted=True)
        mall_signals.products_not_online.send(
                sender=models.Product,
                product_ids=weizoom_product_ids,
                request=request
            )
        
        text = u'商品删除提示：\n'
        text += u'账号：%s\n' % request.user.username
        text += u'商品名称：%s\n' % product.name
        text += u'删除原因：%s\n' % DELETED_WEIZOOM_PRODUCT_REASON[reason]
        text += u'请及时处理！'
        ding_util.send_to_ding(text, DING_GROUP_ID)
    except:
       pass

def update_weizoom_mall_sync_product_status(request, product, update_data):
    try:
        models.WeizoomHasMallProductRelation.objects.filter(mall_product_id=product.id, is_deleted=False).update(is_updated=True)

        text = u'商品更新提示：\n'
        text += u'账号：%s\n' % request.user.username
        text += u'商品名称：%s\n' % product.name
        text += u'更新内容：%s\n' % u'，'.join(update_data)
        text += u'请及时处理！'
        ding_util.send_to_ding(text, DING_GROUP_ID)
    except:
        pass

def get_sync_product_store_name(product_ids):
    # try:
    relations = models.WeizoomHasMallProductRelation.objects.filter(weizoom_product_id__in=product_ids, is_deleted=False)
    product_id2mall_id = {}
    product_id2sync_time = {}
    for relation in relations:
        product_id2mall_id[relation.weizoom_product_id] = relation.mall_id
        product_id2sync_time[relation.weizoom_product_id] = relation.sync_time.strftime('%Y-%m-%d %H:%M')
    mall_ids = product_id2mall_id.values()
    mall_id2store_name = dict([(profile.user_id, profile.store_name) for profile in UserProfile.objects.filter(user_id__in=mall_ids)])
    product_id2store_name = {}
    for product_id in product_id2mall_id.keys():
        product_id2store_name[product_id] = mall_id2store_name[product_id2mall_id[product_id]]
    return product_id2store_name, product_id2sync_time

def weizoom_filter_products(request, products):
    """
    weizoom自营平台筛选商品
    """
    store_name = request.GET.get('supplier', '')
    start_date = request.GET.get('startDate', '')
    end_date = request.GET.get('endDate', '')

    from_supplier_product_ids = []
    from_store_product_ids = []
    if not store_name and not start_date and not end_date:
        return filter_products(request, products)

    # 同步商品
    from weixin.user.module_api import get_all_active_mp_user_ids
    all_user_ids = get_all_active_mp_user_ids()
    all_mall_userprofiles = UserProfile.objects.filter(user_id__in=all_user_ids, webapp_type=0)
    if store_name:
        owner_ids = [profile.user_id for profile in all_mall_userprofiles.filter(store_name__contains=store_name)]
        # 手动添加供货商
        supplier_ids = [supplier.id for supplier in models.Supplier.objects.filter(
                                        owner=request.manager,
                                        name__contains=store_name,
                                        is_delete=False
                                    )]
        from_supplier_product_ids = [product.id for product in models.Product.objects.filter(
                                        owner=request.manager,
                                        supplier__in=supplier_ids,
                                        is_deleted=False
                                    )]
    else:
        owner_ids = [profile.user_id for profile in all_mall_userprofiles.all()]

    if start_date and end_date:
        params = dict(
                owner=request.manager,
                mall_id__in=owner_ids,
                is_deleted=False,
                delete_time__gte=start_date,
                delete_time__lte=end_date
            )
    else:
        params = dict(
                owner=request.manager,
                mall_id__in=owner_ids,
                is_deleted=False,
            )

    from_store_product_ids = [relation.weizoom_product_id for relation in models.WeizoomHasMallProductRelation.objects.filter(**params)]
    filter_product_ids = from_store_product_ids + from_supplier_product_ids

    filtered_products = filter_products(request, products)
    new_filtered_products = []
    for product in filtered_products:
        if product.id in filter_product_ids:
            new_filtered_products.append(product)
    return new_filtered_products

#
# def update_one_product(request):
#     try:
#         name = request.POST.get('name')
#         product = models.Product.objects.get(name=name)
#     except models.Product.DoesNotExist:
#         print("Product with id does not exist")


# def validate_product_necessary_arguments(request):
#     """验证商品必要的参数是否已提供

#     Return:

#     """
#     try:
#         # 商品名称验证
#         name_pattern = r'\A\w{1,20}\Z'  # 1 到 20 个字符
#         name = request.POST['name']
#         result = re.match(name_pattern, name, re.UNICODE)
#         name = True if result else False

#         # 商品图片验证
#         swipe_images = json.loads(request.POST['swipe_images'])
#         swipe_images = True if swipe_images else False

#         # 无规格商品必要参数验证
#         if not request.POST.get('is_use_custom_model'):
#             price = request.POST['price']
#             weight = request.POST['weight']
#         # 有规格商品必要参数验证
#         else:
#             is_custom_model_validation = True
#             custom_model = json.loads(request.POST['customModels'])
#             for i in customModels:
#                 price = i['price']
#                 weight = i['weight']
#     except KeyError:
#         return False

