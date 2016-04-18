/**
 * @class W.component.appkit.ShvoteDescription
 *
 */
ensureNS('W.component.appkit');
W.component.appkit.ShvoteDescription = W.component.Component.extend({
	type: 'appkit.shvotedescription',
	selectable: 'yes',
	propertyViewTitle: '投票',

	properties: [{
		group: '文本调研项',
		groupClass: 'xui-propertyView-app-TextSurvey',
		fields: [{
			name: 'title',
			type: 'text',
			displayName: '标题',
			isUserProperty: true,
			maxLength: 35,
			validate: 'data-validate="require-notempty::页面标题不能为空,,require-word"',
			validateIgnoreDefaultValue: true,
			default: '',
			placeholder: '活动标题'
		},{
			name: 'rule',
			type: 'textarea',
			displayName: '投票规则',
			maxLength: 50,
			isUserProperty: true,
			validate: 'data-validate="require-notempty::投票规则不能为空,,require-word"',
			placeholder: '每组每人每天可被投票1次(最多可输入50字)',
			default: ""
		},{
			name: 'votecount_per_one',
			type: 'text',
			displayName: '每天投票数',
			isUserProperty: true,
			maxLength: 35,
			validate: 'data-validate="require-notempty::请输入正整数,,require-positive-int"',
			validateIgnoreDefaultValue: true,
			default: '',
			placeholder: '每个选手只能投一票'
		},{
			name: 'groups',
			type: 'badge',
			displayName: '选手分组',
			plugin: 'apps_badge_tools',
			uirole: 'apps-badge-tools-pane',
			btnName: '+添加',
			maxcount: 5,
			maxlen: 5,
			isUserProperty: true,
			default: []
		},{
			name: 'description',
			type: 'rich_text',
			displayName: '活动介绍',
			isUserProperty: true,
			default: ''
		}, {
			name: 'start_time',
			type: 'hidden',
			displayName: '开始时间',
			isUserProperty: false,
			default: ''
		}, {
			name: 'end_time',
			type: 'hidden',
			displayName: '结束时间',
			isUserProperty: false,
			default: ''
		}, {
			name: 'valid_time',
			type: 'date_range_selector',
			displayName: '有效时间',
			isUserProperty: true,
			validate: 'data-validate="require-notempty::有效时间不能为空"',
			validateIgnoreDefaultValue: true,
			format: 'yy.mm.dd',
			default: ''
		}, {
			name: 'material_image',
			type: 'image_dialog_select_v2',
			displayName: '活动图片',
			isUserProperty: true,
			isShowCloseButton: true,
			triggerButton: {nodata:'选择图片', hasdata:'修改'},
			selectedButton: '选择图片',
			dialog: 'W.dialog.termite.SelectImagesDialog',
			dialogParameter: '{"multiSelection": false}',
			help: '提示:图片格式jpg/png, 图片宽度640px, 高度自定义, 请上传风格与背景配色协调的图片',
			validate: 'data-validate="require-notempty::请添加一张图片"',
			default: ""
		}]
	}],

	propertyChangeHandlers: {
		title: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		name: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		rule: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		description: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		start_time: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		end_time: function($node, model, value, $propertyViewNode) {
			this.refresh($node, {resize:true});
		},
		material_image: function($node, model, value, $propertyViewNode){
			var image = {url:''};
            var data = {type:null};
            if (value !== '') {
                data = $.parseJSON(value);
                image = data.images[0];
            }
            model.set({
                material_image: image.url
            }, {silent: true});

            if (data.type === 'newImage') {
                W.resource.termite2.Image.put({
                    data: image,
                    success: function(data) {
                    },
                    error: function(resp) {
                    }
                })
            }
            this.refresh($node, {refreshPropertyView: true});
		}
	},

	initialize: function(obj) {
		this.super('initialize', obj);
	}
});
