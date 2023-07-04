# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

import pooler
from odoo import fields, models, api, _

form = '''<?xml version="1.0"?>
<form string="Verify Code">
    <field name="code" colspan="4"/>
</form>'''

fields = {
    'code': {'string': 'Verification Code', 'required': True, 'size': 255,
             'type': 'char', 'help': 'Enter the verification code that you get in your verification sms'}
}


class VerifyCode(models.TransientModel):
    _name = 'sms.smsclient.code.verify'
    _description = 'verify code'

    def checkcode(self, data):
        """
            verify code
        """
        gate = pooler.get_pool(self._cr.dbname).get('sms.smsclient').browse(data['id'])
        if gate.state == 'confirm':
            raise Warning(_('Error'), _('Gateway already verified!'))

        if gate.code == data['form']['code']:
            pooler.get_pool(self._cr.dbname).get('sms.smsclient').write([data['id']], {'state': 'confirm'})
        else:
            raise Warning(_('Verification failed. Invalid Verification Code!'))
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': form, 'fields': fields, 'state': [('end', 'Cancel'), ('check', 'Verify Code')]}
        },
        'check': {
            'actions': [checkcode],
            'result': {'type': 'state', 'state': 'end'}
        }
    }
