# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import urllib
import urllib.request
import logging
from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import *
import re

_logger = logging.getLogger(__name__)

"""try:
    from SOAPpy import WSDL
except :
    _logger.warning("ERROR IMPORTING SOAPpy, if not installed, please install it:"
    " e.g.: apt-get install python-soappy")"""


class PartnerSmsSend(models.Model):
    _name = "partner.sms.send"
    _description = "Partner Sms Send"

    def _default_get_mobile(self):
        partner_pool = self.env['res.partner']
        active_ids = self._context.get('active_ids')
        res = {}
        i = 0
        for partner in partner_pool.browse(active_ids):
            i += 1
            res = partner.mobile
        if i > 1:
            raise Warning(_('You can only select one partner'))
        return res

    def _default_get_gateway(self):
        sms_obj = self.env['sms.smsclient']
        gateway_ids = sms_obj.search([])
        return gateway_ids and gateway_ids[0] or False

    @api.onchange('gateway')
    def onchange_gateway(self):
        """
            Update the following fields when the gateway is changed
        """
    mobile_to = fields.Char("To", size=256, default=_default_get_mobile, required=True, readonly=False)
    app_id = fields.Char('API ID', size=256, default=_default_get_gateway)
    user = fields.Char('Login', size=256)
    password = fields.Char('Password', size=256)
    text = fields.Text('SMS Message', required=True, default_focus="1")
    gateway = fields.Many2one('sms.smsclient', 'SMS Gateway', required=True, default=_default_get_gateway)
    coding = fields.Selection([
            ('0', 'FR'),
            ('8', 'AR')
        ], 'Language',default='0', required=True, help='The SMS coding: 0 for utf-8 or 8 for unicode')

    def sms_send(self):
        """
            send sms to smsclient
        """
        client_obj = self.env['sms.smsclient']
        for data in self:
            if not data.gateway:
                raise Warning(_('No Gateway Found'))
            else:
                client_obj._send_message(data)
        return {}


class SMSClient(models.Model):
    _name = 'sms.smsclient'
    _description = 'SMS Client'

    name = fields.Char('Gateway Name', size=256, required=True)
    url = fields.Char('Gateway URL', size=256, required=True, help='Base url for message')
    property_ids = fields.One2many('sms.smsclient.parms', 'gateway_id', 'Parameters')
    history_line = fields.One2many('sms.smsclient.history', 'gateway_id', 'History')
    method = fields.Selection([
            ('http', 'HTTP Method')
        ], 'API Method', default='http')
    state = fields.Selection([
            ('new', 'Not Verified'),
            ('waiting', 'Waiting for Verification'),
            ('confirm', 'Verified'),
        ], 'Gateway Status', default='new', readonly=True)
    users_id = fields.Many2many('res.users', string='Users Allowed')
    code = fields.Char('Verification Code', size=256)
    body = fields.Text('Message', help="The message text that will be send along with the email which is send through this server")
    coding = fields.Selection([
            ('0', 'FR'),
            ('8', 'AR')
        ],'Language', default='0', required=True , help='The SMS coding: 0 for utf-8 or 8 for unicode')
    char_limit = fields.Boolean('Character Limit', default=True)

    def _check_permissions(self,gateway_id):
        """
            Check permission
        """
        self._cr.execute('select * from res_users_sms_smsclient_rel where sms_smsclient_id=%s and res_users_id=%s' % (gateway_id, self.env.uid))
        data = self._cr.fetchall()
        if len(data) <= 0:
            return False
        return True

    def _prepare_smsclient_queue(self, data):
            """
                prepare sms client queue data
            """
            opid = {}
            if data.mobile_to[0]=='5':
                opid = 60501
            elif data.mobile_to[0]=='9':
                opid= 60502
            elif data.mobile_to[0]=='2':
                opid= 60503
        
            return {
                'MOBILE': data.mobile_to,
                'MESSAGE': data.text,
                'ENCODE': data.coding,
                'OPID': opid,
            }

    def _send_message(self, data):
        """
            check permission after send message
        """
        gateway = data.gateway
        data.mobile_to = re.sub(r"\D", "",data.mobile_to)[-8:]
        partner_id = self._context.get('active_ids')
        if gateway:
            if not self._context.get('default_intake_demo_data') and not self._check_permissions(gateway.id) and self.env.uid != SUPERUSER_ID:
                raise Warning(_('You have no permission to access %s ') % (gateway.name))
            url = gateway.url
            name = url
            if gateway.method == 'http':
                prms = {}
                for p in data.gateway.property_ids:
                    if p.type == 'serviceid':
                     prms[p.name] = p.value
                    elif p.type == 'prid':
                     prms[p.name] = p.value
                    elif p.type == 'sc':
                     prms[p.name] = p.value
                    elif p.type == 'user':
                     prms[p.name] = p.value
                    elif p.type == 'password':
                     prms[p.name] = p.value
                    elif p.type == 'sender':
                     prms[p.name] = p.value
                vals = self._prepare_smsclient_queue(data)
                fullparams = {**prms,**vals}
                params = urllib.parse.urlencode(fullparams)
                name = url + "?" + params
                vals['name']= name
                vals['gateway_id']= data.gateway.id
                vals['partner_id']= partner_id[0]
            queue_obj = self.env['sms.smsclient.queue']
            queue_obj.create(vals)
            """vals2 = self._prepare_smsclient_queue2(data)
            params2 = urllib.parse.urlencode(vals2)
            name2 = name + "&"+ params2
            urllib.request.urlopen(name2)"""

        return True

    @api.model
    def _check_queue(self):
        """
            check sms queue history
        """
        queue_obj = self.env['sms.smsclient.queue']
        history_obj = self.env['sms.smsclient.history']
        sids = queue_obj.search([('state', '!=', 'send'),('state', '!=', 'sending')], limit=30)
        for queue_id in sids:
            queue_id.write({'state': 'sending'})
        error_ids = []
        sent_ids = []
        for sms in sids:
            if sms.gateway_id.char_limit:
                if len(sms.MESSAGE) > 160:
                    error_ids.append(sms.id)
                    continue
            if sms.gateway_id.method == 'http':
                try:
                    urllib.request.urlopen(sms.name)

                except Exception as e:
                    raise UserError(_('Error %s') % (e,))
            ### New Send Process OVH Dedicated ###
            ## Parameter Fetch ##
            vals = { 'name': _('SMS Sent'), 'partner_id': sms.partner_id.id, 'gateway_id': sms.gateway_id.id, 'sms': sms.MESSAGE, 'to': sms.MOBILE}
            history_obj.create(vals)
            sent_ids.append(sms)
        for sent_id in sent_ids:
            sent_id.write({'state': 'send'})
        for error_id in queue_obj.browse(error_ids):
            error_id.write({'state': 'error', 'error': 'Size of SMS should not be more then 160 char'})
        return True


class SMSQueue(models.Model):
    _name = 'sms.smsclient.queue'
    _description = 'SMS Queue'

    def _default_partner_mobile(self):
        if self.partner_id:
            return self.partner_id.mobile
        return False    

    def _default_get_gateway(self):
        sms_obj = self.env['sms.smsclient']
        gateway_ids = sms_obj.search([])
        return gateway_ids and gateway_ids[0] or False

    name = fields.Text('SMS Request', size=256, required=True, readonly=True, states={'draft': [('readonly', False)]})
    MESSAGE = fields.Text('SMS Text', size=256, required=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one('res.partner', 'Partner', required=True, readonly=True, states={'draft': [('readonly', False)]})
    MOBILE = fields.Char('Mobile No', default=_default_partner_mobile, size=256, required=True, readonly=True, states={'draft': [('readonly', False)]})
    gateway_id = fields.Many2one('sms.smsclient', 'SMS Gateway', default=_default_get_gateway, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Queued'),
        ('sending', 'Waiting'),
        ('send', 'Sent'),
        ('error', 'Error'),
    ], 'Message Status', default='draft', readonly=True)
    error = fields.Text('Last Error', size=256, readonly=True, states={'draft': [('readonly', False)]})
    date_create = fields.Datetime('Date', default=lambda self: fields.Datetime.now(), readonly=True)
    ENCODE = fields.Selection([
            ('0', 'utf-8'),
            ('8', 'Unicode')
        ], 'Language',default='0' , required=True, help='The sms coding: 0 for utf-8 or 8 for unicode')
    OPID =  fields.Char('Operator ID', size=10)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.MOBILE = self.partner_id.mobile
        else:
            self.MOBILE = False


class Properties(models.Model):
    _name = 'sms.smsclient.parms'
    _description = 'SMS Client Properties'

    name = fields.Char('Property name', size=256, help='Name of the property whom appear on the URL')
    value = fields.Char('Property value', size=256, help='Value associate on the property for the URL')
    gateway_id = fields.Many2one('sms.smsclient', 'SMS Gateway')
    type = fields.Selection([
            ('serviceid','Service ID'),
            ('prid','Partner ID'),
            ('sc','Short Code'),
            ('user', 'Login'),
            ('password', 'Password'),
            ('sender', 'Sender Name')
        ], 'API Method', help='If parameter concern a value to substitute, indicate it')


class HistoryLine(models.Model):
    _name = 'sms.smsclient.history'
    _description = 'SMS Client History'

    name = fields.Char('Description', size=160, required=True, readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_create = fields.Datetime('Date', default=lambda self: fields.Datetime.now(), readonly=True)
    user_id = fields.Many2one('res.users', 'Username', default=lambda self: self.env.user, readonly=True)
    gateway_id = fields.Many2one('sms.smsclient', 'SMS Gateway', ondelete='cascade', required=True, readonly=True)
    to = fields.Char('Mobile No', size=15, readonly=True)
    sms = fields.Text('SMS', size=160, readonly=True)

    @api.model
    def create(self, vals):
        res = super(HistoryLine, self).create(vals)
        self._cr.commit()
        return res
