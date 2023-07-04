from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sms_count = fields.Integer(string="SMS History", compute='_compute_sms_count')

    def _compute_sms_count(self):
        SmsHistory = self.env['sms.smsclient.history']
        for partner in self:
            partner.sms_count = SmsHistory.search_count([('partner_ids', 'child_of', partner.id)])
