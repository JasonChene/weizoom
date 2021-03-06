# -*- coding: utf-8 -*-
from datetime import datetime
import urllib2
import urllib
import json

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.template import Context, RequestContext
from django.shortcuts import render_to_response
from django.db.models import Q, F

from apps.request_util import get_consume_coupon
from modules.member import util as member_util
from modules.member.models import Member
from mall.promotion.models import CouponRule, Coupon, RedEnvelopeRule, RedEnvelopeToOrder, GetRedEnvelopeRecord, RedEnvelopeParticipences
from mall.models import Order
from market_tools.tools.coupon.util import consume_coupon
from modules.member.models import Member
from weixin.user.util import get_component_info_from
from weixin.user import module_api

def get_share_red_envelope(request):
    """
    领取分享红包
    """
    red_envelope_rule_id = request.GET.get('red_envelope_rule_id', 0)
    order_id = request.GET.get('order_id', 0) # 下单领取会带有order_id
    user_id = request.GET.get('webapp_owner_id', 0)
    is_share = request.GET.get('is_share', 0)
    material_id = 0 #除下单领取记录rule_id作为material_id
    # 订单
    # if order_id:
    #     order = Order.objects.get(id=order_id)

    #会员
    member_id = -1
    if request.member:
        member_id = request.member.id

    member = Member.objects.filter(id=member_id)

    #分享链接的会员id
    cookie_fmt = request.COOKIES.get('fmt', None)
    followed_member_id = 0
    if cookie_fmt and cookie_fmt != 'None':
        followed_member_id = Member.objects.get(token=cookie_fmt).id
        is_share = False

    auth_appid = module_api.get_mp_info(user_id)
    qcode_img_url = ''
    shop_name = ''
    if auth_appid:
        qcode_img_url = auth_appid.qrcode_url if auth_appid.qrcode_url else ''
        shop_name = auth_appid.nick_name if auth_appid.nick_name else ''

    try:
        red_envelope_rule = RedEnvelopeRule.objects.get(id=red_envelope_rule_id,is_delete=False)
    except:
        c = RequestContext(request, {
            'is_deleted_data': True
        })
        return render_to_response('shareRedEnvelope/webapp/share_red_envelope.html', c)
    coupon_rule_id = red_envelope_rule.coupon_rule_id
    coupon_rule = CouponRule.objects.get(id=coupon_rule_id)

    member_coupon_record_count = 0
    if order_id:
        relation = RedEnvelopeToOrder.objects.filter(order_id=order_id, red_envelope_rule_id=red_envelope_rule_id)
    else:
        material_id = red_envelope_rule_id #除下单领取记录rule_id作为material_id
        if followed_member_id == member_id or not followed_member_id:
            relation = RedEnvelopeToOrder.objects.filter(red_envelope_rule_id=red_envelope_rule_id, member_id=member_id)
        else:
            member_get_red_envelope_records = GetRedEnvelopeRecord.objects.filter(member_id=followed_member_id, red_envelope_rule_id=red_envelope_rule_id)
            if member_get_red_envelope_records.count() > 0:
                relation = RedEnvelopeToOrder.objects.filter(id=member_get_red_envelope_records[0].red_envelope_relation_id)
            else:
                relation = RedEnvelopeToOrder.objects.filter(red_envelope_rule_id=red_envelope_rule_id, member_id=followed_member_id)
        member_coupon_record_count = GetRedEnvelopeRecord.objects.filter(member_id=member_id, red_envelope_rule_id=red_envelope_rule_id).count()

    return_data = {
        'red_envelope_rule': red_envelope_rule,
        'shop_name': shop_name,
        'page_title': "优惠大放送",
        'share_page_title': "优惠大放送",
        'share_page_desc': red_envelope_rule.share_title,
        'share_img_url': red_envelope_rule.share_pic,
        'share_to_timeline_use_desc': True,  #分享到朋友圈的时候信息变成分享给朋友的描述
        'is_share': is_share
    }

    if member:
        member = member[0]
        if relation.count() > 0 or member_coupon_record_count > 0:
            #分享获取红包
            if member_coupon_record_count:
                records = GetRedEnvelopeRecord.objects.filter(member_id=member_id, red_envelope_rule_id=red_envelope_rule_id)
                p = RedEnvelopeParticipences.objects.get(coupon_id=records[0].coupon_id) #获取领取关系的记录
                relation = RedEnvelopeToOrder.objects.filter(id=p.red_envelope_relation_id)
                friends = GetRedEnvelopeRecord.objects.filter(red_envelope_relation_id=records[0].red_envelope_relation_id).order_by("-id")[:4]
            else:
                records = GetRedEnvelopeRecord.objects.filter(member_id=member_id, red_envelope_rule_id=red_envelope_rule_id)
                friends = GetRedEnvelopeRecord.objects.filter(red_envelope_relation_id=relation[0].id).order_by("-id")[:4]

            for friend in friends:
                friend.member_name = friend.member.username
                friend.member_header_img = friend.member.user_icon

            member_red_envelope_relation = RedEnvelopeToOrder.objects.filter(member_id=member_id, red_envelope_rule_id=red_envelope_rule_id)

            red_envelope_relation_ids = [record.red_envelope_relation_id for record in records]

            if (records.count() > 0
                and ((relation[0].id in red_envelope_relation_ids)
                or records.count() > member_red_envelope_relation.count()) or member_coupon_record_count):
                #会员已经领了
                return_data['has_red_envelope'] = True
                return_data['coupon_rule'] = coupon_rule
                return_data['member'] = member if member.is_subscribed else ""
                return_data['qcode_img_url'] = qcode_img_url
                return_data['friends'] = friends
            else:
                if (red_envelope_rule.status and (red_envelope_rule.end_time > datetime.now() or red_envelope_rule.limit_time)):
                    # coupon, msg = consume_coupon(request.webapp_owner_id, coupon_rule_id, member_id)
                    coupon, msg, _ = get_consume_coupon(request.webapp_owner_id,'red_envelope',str(red_envelope_rule.id), coupon_rule_id, member_id)
                    if coupon:
                        this_received_count = RedEnvelopeParticipences.objects.filter(owner_id=request.webapp_owner_id,
                                        red_envelope_rule_id=red_envelope_rule_id,
                                        red_envelope_relation_id=relation[0].id,
                                        member_id=member.id).count()
                        if this_received_count > 0:
                            pass
                        else:
                            GetRedEnvelopeRecord.objects.create(
                                        owner_id=request.webapp_owner_id,
                                        coupon_id=coupon.id,
                                        red_envelope_rule_id=red_envelope_rule_id,
                                        red_envelope_relation_id=relation[0].id,
                                        member=member,
                                )
                            if followed_member_id:
                                RedEnvelopeParticipences.objects.create(
                                            owner_id=request.webapp_owner_id,
                                            coupon_id=coupon.id,
                                            red_envelope_rule_id=red_envelope_rule_id,
                                            red_envelope_relation_id=relation[0].id,
                                            member_id=member.id,
                                            is_new= False if member.is_subscribed else True,
                                            introduced_by=followed_member_id
                                )
                                RedEnvelopeParticipences.objects.filter(
                                            owner_id=request.webapp_owner_id,
                                            red_envelope_rule_id=red_envelope_rule_id,
                                            red_envelope_relation_id=relation[0].id,
                                            member_id=followed_member_id
                                ).update(introduce_received_number = F('introduce_received_number') + 1)
                            if member.is_subscribed:
                                return_data['has_red_envelope'] = False
                                return_data['coupon_rule'] = coupon_rule
                                return_data['member'] = member
                                return_data['friends'] = friends
                            else:
                                return_data['has_red_envelope'] = False
                                return_data['coupon_rule'] = coupon_rule
                                return_data['qcode_img_url'] = qcode_img_url
                                return_data['friends'] = friends

        else:
            #用户订单获取
            # if not order.webapp_user_id == member_id:
            #     return HttpResponseRedirect("/workbench/jqm/preview/?module=mall&model=products&action=list&workspace_id=mall&project_id=0&webapp_owner_id=%s" % user_id)
            member.member_name = member.username_for_html
            if (red_envelope_rule.status and (red_envelope_rule.end_time > datetime.now() or red_envelope_rule.limit_time)):
                # coupon, msg = consume_coupon(request.webapp_owner_id, coupon_rule_id, member_id)
                coupon, msg, _ = get_consume_coupon(request.webapp_owner_id,'red_envelope',str(red_envelope_rule.id), coupon_rule_id, member_id)
                if coupon:
                    this_received_count = RedEnvelopeToOrder.objects.filter(owner_id=request.webapp_owner_id,
                                                                                order_id=order_id,
                                                                                material_id=material_id,
                                                                                member_id=member.id,
                                                                                red_envelope_rule_id=red_envelope_rule_id).count()
                    if this_received_count > 0:
                        pass
                    else:
                        relation = RedEnvelopeToOrder.objects.create(
                                    owner_id=request.webapp_owner_id,
                                    member_id=member_id,
                                    order_id=order_id,
                                    material_id=material_id,
                                    red_envelope_rule_id=red_envelope_rule_id,
                                    count = 1
                            )
                        GetRedEnvelopeRecord.objects.create(
                                    owner_id=request.webapp_owner_id,
                                    coupon_id=coupon.id,
                                    red_envelope_rule_id=red_envelope_rule_id,
                                    red_envelope_relation_id=relation.id,
                                    member_id=member.id
                            )

                        RedEnvelopeParticipences.objects.create(
                                    owner_id=request.webapp_owner_id,
                                    coupon_id=coupon.id,
                                    red_envelope_rule_id=red_envelope_rule_id,
                                    red_envelope_relation_id=relation.id,
                                    member_id=member.id,
                                    is_new= False if member.is_subscribed else True
                        )

                        return_data['has_red_envelope'] = False
                        return_data['coupon_rule'] = coupon_rule
                        return_data['member'] = member if member.is_subscribed else ""
                        return_data['qcode_img_url'] = qcode_img_url
    else:
        return_data['coupon_rule'] = coupon_rule
        return_data['hide_non_member_cover'] = True,
        return_data['qcode_img_url'] = qcode_img_url
    request.META['should_remove_shared_url_session'] = True
    c = RequestContext(request, return_data)
    return render_to_response('shareRedEnvelope/webapp/share_red_envelope.html', c)