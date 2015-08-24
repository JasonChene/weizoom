# -*- coding: utf-8 -*-
from datetime import datetime
import os

import qrcode
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

from core import resource
from mall import export
from mall.models import *
from models import *
from modules.member import models as member_models
from core import paginator

from core.jsonresponse import create_response
from core import search_util
from mall.promotion.utils import coupon_id_maker


COUNT_PER_PAGE = 20
PROMOTION_TYPE_COUPON = 4
FIRST_NAV_NAME = export.MALL_PROMOTION_FIRST_NAV


class CouponRuleInfo(resource.Resource):
    app = "mall2"
    resource = "coupon_rule"

    @login_required
    def get(request):
        """
        单个优惠券规则页面
        """

        action = request.GET.get("action", None)
        promotion_id = request.GET.get("id",None)

        if action == "get":
            """
            查看优惠券信息
            """

            promotion = Promotion.objects.get(id=promotion_id)
            Promotion.fill_details(request.manager, [promotion], {
                'with_product': True,
                'with_concrete_promotion': True
            })

            coupon_rule = CouponRule.objects.get(id=promotion.detail_id)

            url = "http://"+request.META['HTTP_HOST']+"/termite/workbench/jqm/preview/?module=market_tool:coupon&model=coupon&action=get&workspace_id=market_tool:coupon&webapp_owner_id="+str(coupon_rule.owner_id)+"&project_id=0&rule_id="+str(coupon_rule.id)

            coupon_img_url = _create_coupon_qrcode(url, coupon_rule.id)

            coupon_rule.get_url = url
            coupon_rule.qrcode_url = coupon_img_url

            c = RequestContext(request, {
                'first_nav_name': FIRST_NAV_NAME,
                'second_navs': export.get_promotion_second_navs(request),
                'second_nav_name': export.MALL_PROMOTION_COUPON_NAV,
                'coupon_rule': coupon_rule,
            })
            return render_to_response('mall/editor/promotion/select_coupon_rule.html', c)


        elif promotion_id:
            promotion = Promotion.objects.get(id=promotion_id)
            Promotion.fill_details(request.manager, [promotion], {
                'with_product': True,
                'with_concrete_promotion': True
            })

            coupon_rule = CouponRule.objects.get(id=promotion.detail_id)

            c = RequestContext(request, {
                'first_nav_name': FIRST_NAV_NAME,
                'second_navs': export.get_promotion_second_navs(request),
                'second_nav_name': export.MALL_PROMOTION_COUPON_NAV,
                'coupon_rule': coupon_rule,
                'start_date': promotion.start_date.strftime("%Y-%m-%d %H:%M"),
                'end_date': promotion.end_date.strftime("%Y-%m-%d %H:%M"),
                'promotion': promotion
            })
            return render_to_response('mall/editor/promotion/create_coupon_rule.html', c)

        else:
            member_grades = member_models.MemberGrade.get_all_grades_list(request.user_profile.webapp_id)

            c = RequestContext(request, {
                'member_grades': member_grades,
                'first_nav_name': FIRST_NAV_NAME,
                'second_navs': export.get_promotion_second_navs(request),
                'second_nav_name': export.MALL_PROMOTION_COUPON_NAV,
            })
            return render_to_response('mall/editor/promotion/create_coupon_rule.html', c)


    @login_required
    def api_post(request):
        """
        创建，更新优惠券规则
        """
        rule_id = request.POST.get('rule_id', '-')
        if rule_id.isdigit():
            couponRole = CouponRule.objects.filter(id=rule_id)
            couponRole.update(
                name=request.POST.get('name', ''),
                remark=request.POST.get('remark', ''),
            )
            Promotion.objects.filter(detail_id=couponRole[0].id, type=PROMOTION_TYPE_COUPON).update(
                name=request.POST.get('name', ''),
            )
            return create_response(200).get_response()
        # 优惠券限制条件
        is_valid_restrictions = request.POST.get('is_valid_restrictions', '0')
        if is_valid_restrictions == '0':
            valid_restrictions = -1
        else:
            valid_restrictions = request.POST.get('valid_restrictions', '0')
        count = int(request.POST.get('count', '1'))
        limit_product = request.POST.get('limit_product', '0')
        limit_product_id = request.POST.get('product_ids', '-1')
        if limit_product == '1' and limit_product_id.isdigit():
            limit_product_id = int(limit_product_id)
        else:
            limit_product_id = 0

        start_date = request.POST.get('start_date', None)
        if not start_date:
            start_date = '2000-01-01 00:00'

        end_date = request.POST.get('end_date', None)
        if not end_date:
            end_date = '2000-01-01 00:00'

        couponRule = CouponRule.objects.create(
            owner=request.manager,
            name=request.POST.get('name', ''),
            money=request.POST.get('money', '0.0'),
            # valid_days = request.POST.get('valid_days', '0'),
            valid_restrictions=valid_restrictions,
            limit_counts=request.POST.get('limit_counts', '1'),
            count=count,
            remained_count=count,
            remark=request.POST.get('remark', ''),
            limit_product=limit_product == '1',
            limit_product_id=limit_product_id,
            start_date=start_date,
            end_date=end_date
        )

        promotion = Promotion.objects.create(
            owner=request.manager,
            name=request.POST.get('name', ''),
            type=PROMOTION_TYPE_COUPON,
            member_grade_id=request.POST.get('member_grade', 0),
            start_date=start_date,
            end_date=end_date,
            detail_id=couponRule.id,
            status=PROMOTION_STATUS_NOT_START
        )

        if limit_product == '1':
            product_ids = request.POST.get('product_ids', '-1').split(',')
            for product_id in product_ids:
                ProductHasPromotion.objects.create(
                    product_id=product_id,
                    promotion=promotion
                )
        now = datetime.today()
        start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
        if start_date <= now:
            promotion.status = PROMOTION_STATUS_STARTED
            promotion.save()
        _create_coupons(couponRule, count, promotion)
        return create_response(200).get_response()


class CouponRuleList(resource.Resource):
    app = "mall2"
    resource = "coupon_rule_list"

    @login_required
    def get(request):
        """
        优惠券规则列表页面
        """
        c = RequestContext(request, {
            'first_nav_name': FIRST_NAV_NAME,
            'second_navs': export.get_promotion_second_navs(request),
            'second_nav_name': export.MALL_PROMOTION_COUPON_NAV,
        })
        return render_to_response('mall/editor/promotion/coupon_rules.html', c)

    # @login_required
    # def api_get(request):
    #     """
    #     优惠券规则列表
    #     """
    #     name = request.GET.get('name', '')
    #     bar_code = request.GET.get('barCode', '')
    #     promotion_status = int(request.GET.get('promotionStatus', -1))
    #     start_date = request.GET.get('startDate', '')
    #     end_date = request.GET.get('endDate', '')
    #     type_str = request.GET.get('type', 'all')
    #     coupon_id = request.GET.get('couponId', '')
    #     promotion_type = PROMOTIONSTR2TYPE[type_str]

    #     is_fetch_all_promotions = (not name) and (not bar_code) and (not start_date) and (not end_date) and (
    #         not coupon_id) and (promotion_status == -1) and (promotion_type == 'all')
    #     if is_fetch_all_promotions:
    #         # 获取promotion列表
    #         if promotion_type == PROMOTION_TYPE_ALL:
    #             # 全部类型不查询优惠券数据
    #             promotions = [promotion for promotion in list(Promotion.objects.filter(owner=request.manager)) if
    #                           promotion.status != PROMOTION_STATUS_DELETED and promotion.type != PROMOTION_TYPE_COUPON]
    #         else:
    #             promotions = [promotion for promotion in
    #                           list(Promotion.objects.filter(owner=request.manager, type=promotion_type)) if
    #                           promotion.status != PROMOTION_STATUS_DELETED]
    #         promotions.sort(lambda x, y: cmp(y.id, x.id))

    #         # 进行分页
    #         count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
    #         cur_page = int(request.GET.get('page', '1'))
    #         pageinfo, promotions = paginator.paginate(promotions, cur_page, count_per_page,
    #                                                   query_string=request.META['QUERY_STRING'])
    #         # id2promotion = dict([(promotion.id, promotion) for promotion in promotions])
    #         Promotion.fill_details(request.manager, promotions, {
    #             'with_product': True,
    #             'with_concrete_promotion': True
    #         })
    #     else:
    #         # 获得promotion集合并过滤
    #         if promotion_type == PROMOTION_TYPE_ALL:
    #             # 全部类型不查询优惠券数据
    #             promotions = [promotion for promotion in
    #                           list(Promotion.objects.filter(owner=request.manager).order_by('-id')) if
    #                           promotion.status != PROMOTION_STATUS_DELETED and promotion.type != PROMOTION_TYPE_COUPON]
    #         else:
    #             promotions = [promotion for promotion in
    #                           list(Promotion.objects.filter(owner=request.manager, type=promotion_type).order_by('-id'))
    #                           if promotion.status != PROMOTION_STATUS_DELETED]
    #         # if promotion_type != PROMOTION_TYPE_COUPON:
    #         promotions = _filter_promotions(request, promotions)

    #         #
    #         if coupon_id:
    #             coupon_rule_id2promotion = dict([(promotion.detail_id, promotion) for promotion in promotions])
    #             coupon = Coupon.objects.filter(coupon_id=coupon_id)
    #             if coupon.count() > 0:
    #                 promotions = [coupon_rule_id2promotion[coupon[0].coupon_rule_id]]
    #             else:
    #                 promotions = []

    #         # 进行分页
    #         count_per_page = int(request.GET.get('count_per_page', COUNT_PER_PAGE))
    #         cur_page = int(request.GET.get('page', '1'))
    #         pageinfo, promotions = paginator.paginate(promotions, cur_page, count_per_page,
    #                                                   query_string=request.META['QUERY_STRING'])
    #         Promotion.fill_details(request.manager, promotions, {
    #             'with_product': True,
    #             'with_concrete_promotion': True
    #         })

    #     # 获取返回数据
    #     promotions.sort(lambda x, y: cmp(y.id, x.id))
    #     items = []
    #     for promotion in promotions:
    #         if promotion.detail.has_key('money'):
    #             promotion.detail['money'] = str(promotion.detail['money'])
    #         data = {
    #             "id": promotion.id,
    #             "status": promotion.status_name,
    #             "name": promotion.name,
    #             "promotionTitle": promotion.promotion_title,
    #             "type": PROMOTION2TYPE[promotion.type],
    #             "start_date": promotion.start_date.strftime("%Y-%m-%d %H:%M"),
    #             "end_date": promotion.end_date.strftime("%Y-%m-%d %H:%M"),
    #             "created_at": promotion.created_at.strftime("%Y-%m-%d"),
    #             "detail": promotion.detail,
    #             "products": []
    #         }
    #         if hasattr(promotion, 'products'):
    #             for product in promotion.products:
    #                 data["products"].append({
    #                     'id': product.id,
    #                     'name': product.name,
    #                     'thumbnails_url': product.thumbnails_url,
    #                     'display_price': product.display_price,
    #                     'display_price_range': product.display_price_range,
    #                     'bar_code': product.bar_code,
    #                     'stocks': product.stocks,
    #                     'sales': product.sales,
    #                     'is_use_custom_model': product.is_use_custom_model,
    #                     'models': product.models[1:],
    #                     'standard_model': product.standard_model,
    #                     'current_used_model': product.current_used_model,
    #                     'created_at': datetime.strftime(product.created_at, '%Y-%m-%d %H:%M'),
    #                     "detail_link": '/mall2/product/?id=%d&source=onshelf' % product.id
    #                 })

    #             if len(data['products']) == 1:
    #                 data['product'] = data['products'][0]
    #             else:
    #                 data['product'] = []
    #         items.append(data)

    #     data = {
    #         "items": items,
    #         'pageinfo': paginator.to_dict(pageinfo),
    #         'sortAttr': 'id',
    #         'data': {}
    #     }
    #     response = create_response(200)
    #     response.data = data
    #     return response.get_response()


# PROMOTION_FILTERS = {
#     'promotion': [{
#                       'comparator': lambda promotion, filter_value: (filter_value == 'all') or (
#                           PROMOTION2TYPE[promotion.type]['name'] == filter_value),
#                       'query_string_field': 'promotionType'
#                   }, {
#                       'comparator': lambda promotion, filter_value: (int(filter_value) == -1) or (
#                           int(filter_value) == promotion.status),
#                       'query_string_field': 'promotionStatus'
#                   }, {
#                       'comparator': lambda promotion, filter_value: filter_value <= promotion.start_date.strftime(
#                           "%Y-%m-%d %H:%M"),
#                       'query_string_field': 'startDate'
#                   }, {
#                       'comparator': lambda promotion, filter_value: filter_value >= promotion.end_date.strftime(
#                           "%Y-%m-%d %H:%M"),
#                       'query_string_field': 'endDate'
#                   }
#     ],
#     'coupon': [{
#                    'comparator': lambda promotion, filter_value: filter_value in promotion.name,
#                    'query_string_field': 'name'
#                }, {
#                    'comparator': lambda promotion, filter_value: filter_value in promotion.name,
#                    'query_string_field': 'coupon_type'
#                }, {
#                    'comparator': lambda promotion, filter_value: filter_value <= promotion.start_date.strftime(
#                        "%Y-%m-%d %H:%M"),
#                    'query_string_field': 'startDate'
#                }, {
#                    'comparator': lambda promotion, filter_value: filter_value >= promotion.end_date.strftime(
#                        "%Y-%m-%d %H:%M"),
#                    'query_string_field': 'endDate'
#                }
#     ],
#     'product': [{
#                     'comparator': lambda product, filter_value: filter_value in product.name,
#                     'query_string_field': 'name'
#                 }, {
#                     'comparator': lambda product, filter_value: filter_value == product.bar_code,
#                     'query_string_field': 'barCode',
#                 }
#     ],
# }


# def _filter_promotions(request, promotions):
#     has_filter = search_util.init_filters(request, PROMOTION_FILTERS)
#     if not has_filter:
#         # 没有filter，直接返回
#         return promotions

#     filtered_promotions = []
#     if request.GET.get('type', 'all') == 'coupon':
#         promotions = search_util.filter_objects(promotions, PROMOTION_FILTERS['coupon'])
#         coupon_type = request.GET.get('couponPromotionType', None)
#         if coupon_type != '-1':
#             coupon_type = coupon_type == '2'
#             Promotion.fill_details(request.manager, promotions, {
#                 'with_concrete_promotion': True
#             })
#             promotions = [promotion for promotion in promotions if promotion.detail['limit_product'] == coupon_type]
#         return promotions
#         # 过滤promotion集合
#     promotions = search_util.filter_objects(promotions, PROMOTION_FILTERS['promotion'])
#     Promotion.fill_details(request.manager, promotions, {
#         'with_product': True
#     })

#     if not promotions:
#         return filtered_promotions

#     for promotion in promotions:
#         products = search_util.filter_objects(promotion.products, PROMOTION_FILTERS['product'])
#         if not products:
#             # product filter没有通过，跳过该promotion
#             print 'end in product filter'
#             continue
#         else:
#             print 'pass product filter'
#             filtered_promotions.append(promotion)

#             # filtered_products = []
#             # for product in products:
#             # models = search_util.filter_objects(product.models, PROMOTION_FILTERS['model'])
#             #             if models:
#             #                 print 'pass model filter'
#             #                 filtered_products.append(product)
#             #             else:
#             #                 print 'end in model filter'
#             #
#             #         if filtered_products:
#             #             #promotion有通过了product filter和model filter的商品，将promotion放入结果
#             #             filtered_promotions.append(promotion)
#             #         else:
#             #             pass
#     return filtered_promotions


def _create_coupons(couponRule, count, promotion=None):
    """
    创建未使用的优惠券
    """
    i = 0
    if not promotion:
        promotion = Promotion.objects.filter(type=PROMOTION_TYPE_COUPON, detail_id=couponRule.id)[0]

    a = couponRule.owner.id
    b = couponRule.id

    # 创建未使用的优惠券
    current_coupon_ids = [coupon.coupon_id for coupon in Coupon.objects.all()]
    new_coupons = []
    while i < count:
        # 生成优惠券ID
        coupon_id = coupon_id_maker(a, b)
        while coupon_id in current_coupon_ids:
            coupon_id = coupon_id_maker(a, b)
        current_coupon_ids.append(coupon_id)
        new_coupons.append(Coupon(
                owner=couponRule.owner,
                coupon_id=coupon_id,
                provided_time=promotion.start_date,
                start_time=promotion.start_date,
                expired_time=promotion.end_date,
                money=couponRule.money,
                coupon_rule_id=couponRule.id,
                is_manual_generated=False,
                status=COUPON_STATUS_UNGOT
        ))
        i += 1
    Coupon.objects.bulk_create(new_coupons)

def _create_coupon_qrcode(coupon_url, coupon_id):
    """
    创建优惠券二维码
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(coupon_url)
    img = qr.make_image()

    file_name = '%d.png' % coupon_id
    dir_path = os.path.join(settings.UPLOAD_DIR, '../coupon_qrcode')
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    file_path = os.path.join(dir_path, file_name)
    img.save(file_path)

    return '/static/coupon_qrcode/%s' % file_name