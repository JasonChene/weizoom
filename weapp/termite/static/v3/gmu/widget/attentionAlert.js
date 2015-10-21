/*
Copyright (c) 2011-2012 Weizoom Inc
*/

/**
 * weizoom.AttentionAlert widget
 */
 (function($, undefined) {
	// component definition
	gmu.define('AttentionAlert', {
        setting: {
            isShowButton: function(_this) {
                return _this.$el.data('is-show-button') ? true : false;
            },
            isShowCover: function(_this) {
                return _this.$el.data('is-show-cover') ? true : false;
            },
            getUrl: function(_this) {
                var url = _this.$el.data('url');
                url = url.replace(/(^\s*)|(\s*$)/g,'');
                return url;
            },
            getDataId: function(_this) {
                var id = _this.$el.data('id');
                return id;
            }
        },
		_create : function() {
			// this.$el = this.element;
            this.url = this.setting.getUrl(this);
            if(this.setting.isShowButton(this)) {
                this.render();
            }
            this.$el.data('view', this);
        },
        
        render: function() {
            var url = this.url;
            var height;
            if(this.url && !this.$el.data('varnish')) {
                if (this.setting.getDataId(this) == '124') {
                    this.$button = $('<a href="'+url+'">点击此处关注未来广场官方微信哦<i class="xui-icon xui-icon-rightarrow"></i></a>');
                } else {
                    this.$button = $('<a href="'+url+'">关注我们可查看账户积分、红包、优惠券等！<i class="xui-icon xui-icon-rightarrow"></i></a>');
                }
                this.$el.html(this.$button);
                if($('.xa-page')){
                    $('.xa-page').css('padding-top','40px');
                }
                //编辑订单页的布局因为配合iscroll滚动所以使用了绝对定位脱离了page，因而单独处理
                if($('xa-editOrderPage')){
                    $('#wrapper').css('top','40px');
                }
                height = this.setting.isShowCover(this) ? '100%' : '40px';
            }else {
                height = this.setting.isShowCover(this) ? '100%' : '0px';
            }
            this.$el.css('height', height);
        },

		_bind : function() {
		},
		
		_unbind : function() {
		},
		
		destroy : function() {
			// Unbind any events that were bound at _create
			this._unbind();

			this.options = null;
		}
	});

	// taking into account of the component when creating the window
	// or at the create event
	$(function() {
    	$('[data-ui-role="attentionAlert"]').each(function() {
    		$(this).attentionAlert();
    	});

	})
})(Zepto);