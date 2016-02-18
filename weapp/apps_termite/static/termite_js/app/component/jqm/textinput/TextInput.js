/**
 * @class W.component.jqm.TextInput
 * 
 */
W.component.jqm.TextInput = W.component.Component.extend({
	type: 'jqm.textinput',
	propertyViewTitle: 'Text Input',

	properties: [
        {
            group: 'Model属性',
            fields: [{
                name: 'title',
                type: 'text',
                displayName: 'Title',
                default: 'Title'
            }, {
                name: 'is_mini',
                type: 'boolean',
                displayName: 'Mini? ',
                default: 'no'
            }, {
                name: 'placeholder',
                type: 'text',
                displayName: 'PlaceHolder',
                default: ''
            }, {
                name: 'initial_text',
                type: 'text',
                displayName: 'Initial Text',
                default: ''
            }, {
                name: 'type',
                type: 'select',
                displayName: 'Input type',
                source: W.data.TextInputType,
                default: 'text'
            }]
        }
    ],

    propertyChangeHandlers: {
        title: function($node, model, value) {
            $node.find('label').text(value);

            W.Broadcaster.trigger('component:resize', this);
        },

        is_mini: function($node, model, value) {
            if (value === 'yes') {
                $node.find('input').eq(0).addClass('ui-mini');
            } else {
                $node.find('input').eq(0).removeClass('ui-mini');
            }

            W.Broadcaster.trigger('component:resize', this);
        },

        placeholder: function($node, model, value) {
            $node.find('input').attr('placeholder', value);
        }
    },

    initialize: function(obj) {
    	this.super('initialize', obj);
    }
}, {
    indicator: {
        name: 'Text Input',
        imgClass: 'componentList_component_text_input'
    }
});
