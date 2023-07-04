# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PartSms(models.TransientModel):
    _name = 'part.sms'
    _description = 'Part SMS'

    def _default_get_gateway(self):
        sms_obj = self.env['sms.smsclient']
        gateway_ids = sms_obj.search([], limit=1)
        return gateway_ids and gateway_ids[0] or False

    @api.onchange('gateway')
    def onchange_gateway_mass(self):
        """
            Update the following fields when the gateway is changed
        """
        if self.gateway:
            self.validity = self.gateway.validity
            self.classes = self.gateway.classes
            self.deferred = self.gateway.deferred
            self.priority = self.gateway.priority
            self.coding = self.gateway.coding
            self.tag = self.gateway.tag
            self.nostop = self.gateway.nostop

    def _merge_message(self, message, object, partner):
        def merge(match):
            exp = str(match.group()[2:-2]).strip()
            result = eval(exp, {'object': object, 'partner': partner})
            if result in (None, False):
                return str("--------")
            return str(result)
        com = re.compile('(\[\[.+?\]\])')
        msg = com.sub(merge, message)
        return msg

    def sms_mass_send(self):
        """
            send sms
        """
        datas = {}
        gateway_id = self[0].gateway.id
        client_obj = self.env['sms.smsclient']
        partner_obj = self.env['res.partner']
        active_ids = self._context.get('active_ids')
        for data in self:
            if not data.gateway:
                raise UserError(_('No Gateway Found'))
            else:
                name_list = []
                for partner in partner_obj.browse(active_ids):
                    if not partner.mobile:
                        name_list.append(partner.name)
                if name_list:
                    name = ''
                    name = ', '.join(name for name in name_list)
                    raise UserError(_(' Before sending message please enter mobile no of %s .') % (name))
                for partner in partner_obj.browse(active_ids):
                    data.mobile_to = partner.mobile
                    client_obj._send_message(data)
        return True

    gateway = fields.Many2one('sms.smsclient', 'SMS Gateway', default=_default_get_gateway, required=True)
    text = fields.Text('Text', required=True)
    validity = fields.Integer('Validity', help='The maximum time -in minute(s)- before the message is dropped')
    classes = fields.Selection([
            ('0', 'Flash'),
            ('1', 'Phone display'),
            ('2', 'SIM'),
            ('3', 'Toolkit'),
        ], 'Class', help='The sms class: flash(0),phone display(1),SIM(2),toolkit(3)')
    deferred = fields.Integer('Deferred', help='The time -in minute(s)- to wait before sending the message')
    priority = fields.Selection([
            ('0', '0'),
            ('1', '1'),
            ('2', '2'),
            ('3', '3')
        ], 'Priority', help='The priority of the message')
    coding = fields.Selection([
            ('0', 'utf-8'),
            ('8', 'Unicode')
        ], 'Coding', help='The sms coding: 0 for utf-8 or 8 for unicode')
    tag = fields.Char('Tag', size=256, help='An optional tag')
    nostop = fields.Boolean('NoStop', help='Do not display STOP clause in the message, this requires that this is not an advertising message')
