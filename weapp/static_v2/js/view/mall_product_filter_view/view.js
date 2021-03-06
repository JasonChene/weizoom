ensureNS('W.view.mall');
W.view.mall.ProductFilterView = Backbone.View.extend({
    getTemplate: function() {
        $('#mall-product-filter-view-tmpl-src').template('mall-product-filter-view-tmpl');
        return 'mall-product-filter-view-tmpl';
    },

    events: {
        'click .xa-search': 'onClickSearchButton',
        'click .xa-reset': 'onClickResetButton',
        'change #firstClassification': 'onChangeEvent'
    },

    initialize: function(options) {
        this.options = options || {};
        this.$el = $(options.el);
        this.filter_value = '';
        this.classifications='';
        this.bind('clickStatusBox', this.clickStatusBox);

    },

    render: function() {
        var webapp_type = this.$el.attr('data-webapp-type');
        W.resource.mall2.ProductClassification.get({
            scope: this,
            data: {'level': 1},
            success: function(data) {
                this.classifications = data.items;
                var a = data.items;

                var _this = this;
                low_stocks = this.options.low_stocks || -1;
                if(low_stocks < 0) {
                    low_stocks = '';
                }
                high_stocks = this.options.high_stocks || -1;
                if(high_stocks < 0) {
                    high_stocks = '';
                }
                mall_type = this.options.mall_type || 0;
                W.getApi().call({
                    method: 'get',
                    app: 'mall2',
                    resource: 'product_filter_param',
                    args:{},
                    success: function(data) {
                        var html = $.tmpl(this.getTemplate(), {
                            classifications: this.classifications,
                            categories: data.categories,
                            low_stocks: low_stocks,  //支持从首页店铺提醒“库存不足商品”过来的请求 duhao 20150925
                            high_stocks: high_stocks,  //支持从首页店铺提醒“库存不足商品”过来的请求 duhao 20150925
                            mall_type: mall_type, // 支持微众自营平台，按照供货商筛选
                            webapp_type: webapp_type
                        });
                        this.$el.append(html);
                        _this.addDatepicker();
                        //$('.xa-showFilterBox').append($('.xa-timelineControl'));
                    },
                    error: function(response) {
                        alert('加载失败！请刷新页面重试！');
                    },
                    scope: this
                });
            },
            error: function() {
                alert('加载失败！请刷新页面重试！');
            }
        });
        
    },

    onChangeEvent: function() {
        var $target = $(event.target);
        var father_id = $target.val();
        W.resource.mall2.ProductClassification.get({
            scope: this,
            data: {'level': 2, 'father_id': father_id},
            success: function(data) {
                console.log(data);
            var option = '<option value="-1">二级分类</option>';
            _.each(data.items,function(data,i){
                option+='<option value='+data.id+'>'+data.name+'</option>';
                });

                $('.xa-secondCategory').html(option);
            },
            error: function() {
                alert('加载失败！请刷新页面重试！');
            }
        })
    },

    clickStatusBox:function(value){
        this.onClickResetButton();
        $('#tabStatus').val(value);
        
        // 调用搜索事件
        this.onClickSearchButton();
    },
    // 点击‘最近7天’或‘最近30天’
    setDateText: function(event){
        var day = $(event.currentTarget).attr('data-day') -1 ;//parseInt(.toSting()) - 1;
        var today = new Date(); // 获取今天时间

        today.setTime(today.getTime()-day*24*3600*1000);
        var begin = $.datepicker.formatDate('yy-mm-dd', today);
        var end = $.datepicker.formatDate('yy-mm-dd', new Date());

        $('#start_date').val(begin);
        $('#end_date').val(end);
    },

    onClickSearchButton: function(){
        var data = this.getFilterData();
        xlog(data);
    },

    onClickResetButton: function(){
        xlog('reset');
        $('#name').val('');
        $('#bar_code').val('');
        $('#firstClassification').val('-1');
        $('#secondaryClassification').val('-1');
        $('#low_price').val('');
        $('#high_price').val('');
        $('#end_date').val('');
        $('#low_stocks').val('');
        $('#high_stocks').val('');
        $('#low_sales').val('');
        $('#high_sales').val('');
        $('#start_date').val('');
        $('#end_date').val('');
        $('#tabStatus').val('');
        $('#category').val('-1');
        $('#supplier').val('');
        $('#orderSupplierType').val('-1');
        $('#supplier_type').val('-1');
    },

    // 获取条件数据
    getFilterData: function(){
        var first_classification = $.trim(this.$('#firstClassification').val());
        if (!first_classification){
            first_classification = -1
        }

        var secondary_classification = $.trim(this.$('#secondaryClassification').val());
        if (!secondary_classification){
            secondary_classification = -1
        }
        var tabStatu = $('#tabStatus').val();
        //上架时间
        var startDate = $.trim(this.$('#start_date').val());
        var endDate = $.trim(this.$('#end_date').val());
        if (startDate.length === 0 && endDate.length > 0) {
            W.showHint('error', '请输入开始日期！');
            return false;
        }
        if (endDate.length === 0 && startDate.length > 0) {
            W.showHint('error', '请输入结束日期！');
            return false;
        }
        if (startDate > endDate) {
            W.showHint('error', '开始日期不能大于结束日期！');
            return false;
        }

        //价格
        var priceRex = /^\d*(\.\d{0,2})?$/;
        var lowPrice = $.trim(this.$('#low_price').val());
        var highPrice = $.trim(this.$('#high_price').val());
        if(!priceRex.test(lowPrice) || !priceRex.test(highPrice)){
            W.showHint('error', '请输入正确的价格');
            return false;
        }

        var webapp_type = this.$el.attr('data-webapp-type');
        //库存
        var stockRex = /^\d*$/;
        var lowStocks = $.trim(this.$('#low_stocks').val());
        var highStocks = $.trim(this.$('#high_stocks').val());
       //销量
        var salesRex = /^\d*$/;
        var lowSales = $.trim(this.$('#low_sales').val());
        var highSales = $.trim(this.$('#high_sales').val());
        if(!salesRex.test(lowSales) || !salesRex.test(highSales)){
            W.showHint('error', '请输入正确的销量, 仅数字');
            return false;
        }

        //分组
        var category = this.$('#category').val();

        //商品名
        var name = $.trim(this.$('#name').val());

        //商品编码
        var barCode = $.trim(this.$('#bar_code').val());
        //供货商类型
        var orderSupplierType = this.$('#orderSupplierType').val();

        var supplier_type = this.$('#supplier_type').val();
        if (webapp_type == 0) {
            if (lowPrice.length === 0 && highPrice.length > 0) {
                W.showHint('error', '请输入起始价格！');
                return false;
            }
            if (highPrice.length === 0 && lowPrice.length > 0) {
                W.showHint('error', '请输入最高价格！');
                return false;
            }
            if (parseFloat(highPrice) < parseFloat(lowPrice)) {
                W.showHint('error', '最高价格不能低于起始价格');
                return false;
            }
            if (lowStocks.length === 0 && highStocks.length > 0) {
                W.showHint('error', '请输入起始库存！');
                return false;
            }
            if (highStocks.length === 0 && lowStocks.length > 0) {
                W.showHint('error', '请输入最高库存！');
                return false;
            }
            if (parseFloat(highStocks) < parseFloat(lowStocks)) {
                W.showHint('error', '最高库存不能低于起始库存');
                return false;
            }
            if (lowSales.length === 0 && highSales.length > 0) {
                W.showHint('error', '请输入起始销量！');
                return false;
            }
            if (highSales.length === 0 && lowSales.length > 0) {
                W.showHint('error', '请输入最高销量！');
                return false;
            }
            if (parseFloat(highSales) < parseFloat(lowSales)) {
                W.showHint('error', '最高销量不能低于起始销量');
                return false;
            }
        }



        if(!stockRex.test(lowStocks) || (!stockRex.test(highStocks))){
            W.showHint('error', "请输入正确库存！ 仅数字")
            return false;
        }

        if (webapp_type == 0) {
            var data = {
                name: name,
                startDate: startDate,
                endDate: endDate,
                category: category,
                barCode: barCode,
                lowPrice: lowPrice,
                highPrice: highPrice,
                lowStocks: lowStocks,
                highStocks: highStocks,
                lowSales: lowSales,
                highSales: highSales,
                first_classification: first_classification,
                secondary_classification: secondary_classification,
                supplier_type:supplier_type
            }
        } else {
            var data = {
                name: name,
                category: category,
                lowPrice: lowPrice,
                highPrice: highPrice,
                lowStocks: lowStocks,
                highStocks: highStocks,
                lowSales: lowSales,
                highSales: highSales,
                first_classification: first_classification,
                secondary_classification: secondary_classification,
            }            
        }
        //微众系列 筛选‘供货商’
        if(this.$('#supplier').val()){
            var supplier = $.trim(this.$('#supplier').val());
            data['supplier'] = supplier;
        }
        // 筛选‘供货商类型’
        if (orderSupplierType && orderSupplierType != '-1'){
            data['orderSupplierType'] = orderSupplierType;
        }

        var urlEncode = function (param, key, encode) {  
            if(param==null) return '';  
            var paramStr = '';  
            var t = typeof (param);  
            if (t == 'string' || t == 'number' || t == 'boolean') {  
                paramStr += '&' + key + '=' + ((encode==null||encode) ? encodeURIComponent(param) : param);  
            } else {  
                for (var i in param) {  
                  var k = key == null ? i : key + (param instanceof Array ? '[' + i + ']' : '.' + i);  
                  paramStr += urlEncode(param[i], k, encode);  
                }  
            }  
            return paramStr;  
        };  

        this.filter_value = urlEncode(data);
        console.log('onClickSearchButton>>>>filter_value>>>',this.filter_value )
        if(tabStatu == 1){data['is_cps']=1};
        this.trigger('search', data);
    },

    // 组织筛选的查询参数格式
    getFilterValueByDict: function(args){
        if (args.length == 0) {
            return ""
        }else{
            args.push('"page":1')
            return '{'+ args.join(',') +'}';
        }
    },

    // 组织导出的查询参数格式
    getArgsExportValueByDict: function(args){
        if (args.length == 0) {
            return ""
        }else{
            for (var i = args.length - 1; i >= 0; i--) {
                args[i] = args[i].replace(/"/g, '').replace(':', '=')
            };
            return args.join('&');
        }
    },

    // 初始化日历控件
    addDatepicker: function() {
        var _this = this;
        $('input[data-ui-role="orderDatepicker"]').each(function() {
            var $datepicker = $(this);
            var format = $datepicker.attr('data-format');
            var min = $datepicker.attr('data-min');
            var max = $datepicker.attr('data-max');
            var $min_el = $($datepicker.attr('data-min-el'));
            var $max_el = $($datepicker.attr('data-max-el'));
            var options = {
                buttonText: '选择日期',
                currentText: '当前时间',
                numberOfMonths: 1,
                hourText: "小时",
                minuteText: "分钟",
                //dateFormat: format,
                dateFormat: 'yy-mm-dd',
                closeText: '确定',
                prevText: '&#x3c;上月',
                nextText: '下月&#x3e;',
                monthNames: ['一月','二月','三月','四月','五月','六月',
                    '七月','八月','九月','十月','十一月','十二月'],
                monthNamesShort: ['一','二','三','四','五','六',
                    '七','八','九','十','十一','十二'],
                dayNames: ['星期日','星期一','星期二','星期三','星期四','星期五','星期六'],
                dayNamesShort: ['周日','周一','周二','周三','周四','周五','周六'],
                dayNamesMin: ['日','一','二','三','四','五','六'],
                beforeShow: function(e) {
                    if(min === 'now') {
                        $(this).datepicker('option', 'minDate', new Date());
                    }else if(min){
                        $(this).datepicker('option', 'minDate', min);
                    }

                    if($min_el){
                        var startTime = $min_el.val();
                        if(startTime) {
                            $(this).datepicker('option', 'minDate', startTime);
                        }
                    }

                    if(max === 'now') {
                        $(this).datepicker('option', 'maxDate', new Date());
                    }else if(max){
                        $(this).datepicker('option', 'maxDate', max);
                    }

                    if($max_el){
                        var endTime = $max_el.val();
                        if(endTime) {
                            $(this).datepicker('option', 'maxDate', endTime);
                        }
                    }
                },
                onClose: function() {
                }
            };

            $datepicker.datetimepicker(options);
        });
    }
});
