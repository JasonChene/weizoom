/**
 * @class W.component.appkit.ExSignDescription
 *
 */
ensureNS('W.component.appkit');
W.component.appkit.ExSignDescription = W.component.Component.extend({
	type: 'appkit.exsigndescription',
	selectable: 'yes',
	propertyViewTitle: '签到页面',

    dynamicComponentTypes: [{
        type: 'appkit.exsignitem',
        model: 2
    }],

	properties: [
		{
		group: '占空位',
		groupClass: '',
		fields: [{
		}]},{
		group: '活动名称',
		groupClass: 'xui-propertyView-app-SignNameGroup',
		fields: [{
			name: 'title',
			type: 'text',
			displayName: '活动名称',
			isUserProperty: true,
			maxLength: 10,
			validate: 'data-validate="require-notempty::活动不能为空,,require-word"',
			validateIgnoreDefaultValue: true,
			default: ''
		},{
			name: 'description',
			type: 'rich_text',
			displayName: '签到说明',
			maxLength: 200,
			isUserProperty: true,
			default: ''
		}]},{
		group:'分享设置',
		groupClass:'xui-propertyView-app-ShareGroup',
		groupHelp:{
			className:'xui-propertyView-app-ShareGroup-helper',
			id:'propertyView-app-ShareGroup-helper',
			tip:{
				text:'此分享图片和描述用户分享到朋友圈、微信群、微信好友'
			}
		},

		fields:[{
			name: 'image',
			type: 'image_dialog_select',
			displayName: '分享图片',
			isUserProperty: true,
			isShowCloseButton: false,
			triggerButton: {nodata:'选择图片', hasdata:'修改'},
			selectedButton: '选择图片',
			dialog: 'W.dialog.termite.SelectImagesDialog',
			dialogParameter: '{"multiSelection": false}',
			help: '注:不上传则使用默认图片,建议尺寸90*90，仅支持jpg/png',
			default: "/termite_static/img/component/sign/default_gift.png"
		},{
			name: 'share_description',
			type: 'textarea',
			displayName: '分享描述',
			maxLength: 200,
			isUserProperty: true,
			default: '签到赚积分啦！'
		}]},{
		//group:"自动回复",
		//groupClass:'xui-propertyView-app-ReplyGroup',
		//fields:[{
		//	name: 'reply_keyword',
		//	type: 'badge',
		//	displayName: '关键字',
		//	isUserProperty: true,
		//	plugin: 'apps_prize_keywordpane',
		//	uirole: 'apps-prize-keyword-pane',
		//	'btnName': '+ 添加',
		//	default: {}
        //
		//},{
		//	name: 'reply_content',
		//	type: 'textarea',
		//	displayName: '回复内容',
		//	maxLength: 200,
		//	isUserProperty: true,
		//	placeholder: '建议填写店铺近期活动通知，签到奖励等内容……',
		//	default: '建议填写店铺近期活动通知，签到奖励等内容……'
		//}]},{
			group:"签到设置",
			groupClass:"xui-propertyView-app-SignSettingGroupName",
			groupHelp:{
				className:'xui-propertyView-app-SignSettingGroupName-helper',
				id:'propertyView-app-SignSettingGroupName-helper',
				link:{
					className:'xui-outerFunctionTrigger xa-outerFunctionTrigger',
					id:'outerFunctionTrigger',
					text:'奖励说明',
					handler: 'W.component.appkit.ExSignDescription.handleHelp'
				}
			},
			fields:[{
				name:'SignSettingGroupName',
				isUserProperty: true,
				type:'title'
			}]
		},{
		group:"",
		groupClass:'xui-propertyView-app-SignSettingGroup xa-dayly-setting',
		fields:[{
			name:'daily_group',
			displayName:'每日签到',
			type:'title_with_annotation',
			isUserProperty:true

		},{
			name: 'daily_points',
			type: 'text_with_annotation_v2',
			displayName: '送积分',
			isUserProperty: true,
			maxLength: 5,
			size: '70px',
			annotation: '积分',
			//validate: 'data-validate="require-notempty::选项不能为空,,require-nonnegative::只能填入数字"',
			//validateIgnoreDefaultValue: true,
			default: '0'
		},{
			name: 'daily_prizes',
			type: 'prize_selector_v5',
			displayName: '送优惠券',
			isUserProperty: true,
			help:"仅能选择限领为“不限”的优惠券",
			default: []
		}]},{
		group:"",
		groupClass:"xui-propertyView-app-SignDynamicGroup",
		fields:[{
			name: 'items',//动态组件,那个加好
			displayName: '',
			type: 'dynamic-generated-control',
			isShowCloseButton: true,
			minItemLength: 0,
			maxItemLength: 10,
			isUserProperty: true,
			default: []
			}]
	}],
	propertyChangeHandlers: {
		description: function($node, model, value, $propertyViewNode) {
			if(value !== '') {
				$node.find('.wui-description').html(value).show();
			}else{
				$node.find('.wui-description').hide();
			}
		},
		image: function($node, model, value, $propertyViewNode) {
			var image = {url:''};
			var data = {type:null};
			if (value !== '') {
				data = $.parseJSON(value);
				image = data.images[0];
			}
			model.set({
				image: image.url
			}, {silent: true});

			if (data.type === 'newImage') {
				W.resource.termite2.Image.put({
					data: image,
					success: function(data) {
					},
					error: function(resp) {
					}
				});
			}

			if (value) {
				//更新propertyView中的图片
				$propertyViewNode.find('.propertyGroup_property_dialogSelectField .xa-dynamicComponentControlImgBox').removeClass('xui-hide').find('img').attr('src',image.url);
				$propertyViewNode.find('.propertyGroup_property_dialogSelectField .propertyGroup_property_input').find('.xui-i-triggerButton').text('修改');
			}
		},
		items: function($node, model, value) {
			this.refresh($node, {resize:true, refreshPropertyView:true});
			parent.W.Broadcaster.trigger('exsign:change:items', model.get("daily_prizes").length);
		},
		daily_points:function($node, model, value, $propertyViewNode){
			if(value === ''){
				model.set('daily_points', 0);
				$propertyViewNode.find('.xa-dayly-setting').find('input[data-field="daily_points"]').val('0');
			}
			if(value !== '' && value !== 0){
				$node.find('.daily_points').show().find('.wui-points-count').html(value);
				$node.find('.wui-ExSignRules .wui-rules-daily-point').html('获得'+value+'积分').show();
			}else{
				$node.find('.daily_points').hide();
				$node.find('.wui-ExSignRules .wui-rules-daily-point').hide();
			}
		},
		daily_prizes:function($node, model, value){
			if(value.length>0){
				$node.find('.daily_prizes').show();
				var html_str = "和<b class='wui-coupon-count'>"+value.length+"张</b>优惠券";
				$node.find('.daily_prizes').html(html_str);
				var coupon_str = '';
				for (var i in value){
					coupon_str += '<div>获得'+value[i].name+'</div>';
				}
				$node.find('.wui-ExSignRules .wui-rules-daily-prizes').html(coupon_str).show();
			}else{
				$node.find('.daily_prizes').hide();
			}
		},
		share_description: function($node, model, value){
			model.set({share_description:value.replace(/\n/g,'')},{silent: true});
		}
	},
		initialize: function(obj) {
			this.super('initialize', obj);

		}
	});
