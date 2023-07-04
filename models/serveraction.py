# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _


class ActionsServer(models.Model):
    """
    Possibility to specify the SMS Gateway when configure this server action
    """
    _inherit = 'ir.actions.server'

    def _get_states(self):
        res = super(ActionsServer, self)._get_states()
        res.insert(0, ('sms', 'SMS'))
        return res

    mobile = fields.Char('Mobile No', size=512, help="Provides fields that be used to fetch the mobile number, e.g. you select the invoice, then `object.invoice_address_id.mobile` is the field which gives the correct mobile number")
    sms_template_id = fields.Many2one('mail.template', 'SMS Template', help='Select the SMS Template configuration to use with this action')
    sms = fields.Char('SMS', size=520, translate=True)
    sms_server = fields.Many2one('sms.smsclient', 'SMS Server', help='Select the SMS Gateway configuration to use with this action')
