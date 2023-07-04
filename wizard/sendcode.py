# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import pooler

class SendCode(models.TransientModel):
    _name = 'sms.smsclient.code.send'
    _description = 'sms smsclient'

    def send_code(self, data):
        """
            send sms code
        """
        key = md5(time.strftime('%Y-%m-%d %H:%M:%S') + data['form']['smsto']).hexdigest()
        sms_pool = pooler.get_pool(self._cr.dbname).get('sms.smsclient')
        gate = sms_pool.browse(data['id'])
        msg = key[0:6]
        sms_pool._send_message(data['id'], data['form']['smsto'], msg)
        if not gate.state in('new', 'waiting'):
            raise UserError(_('Verification Failed. Please check the Server Configuration!'))

        pooler.get_pool(self._cr.dbname).get('sms.smsclient').write([data['id']], {'state': 'waiting', 'code': msg})
        return {}
