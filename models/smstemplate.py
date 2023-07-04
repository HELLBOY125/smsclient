# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, api, _


class MailTemplate(models.Model):
    _inherit = "mail.template"

    sms_template = fields.Boolean('SMS Template')
    mobile_to = fields.Char('To (Mobile)', size=256)
    gateway_id = fields.Many2one('sms.smsclient', string='SMS Gateway')
