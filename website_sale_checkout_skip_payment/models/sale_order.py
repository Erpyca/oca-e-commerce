# Copyright 2026 Erpyca
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models
from odoo.exceptions import UserError

CONFIRM_CONTEXT_KEY = "website_sale_checkout_skip_payment_confirm"


class ConfirmationMailError(UserError):
    """The confirmation mail could not be built or sent.

    Unlike the other UserError raised while confirming, it is not a refusal to
    confirm the order with a reason for the buyer.
    """


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _send_order_confirmation_mail(self):
        if not self.env.context.get(CONFIRM_CONTEXT_KEY):
            return super()._send_order_confirmation_mail()
        try:
            return super()._send_order_confirmation_mail()
        except UserError as exc:
            raise ConfirmationMailError(str(exc)) from exc
