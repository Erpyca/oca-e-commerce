# Copyright 2017 Sergio Teruel <sergio.teruel@tecnativa.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, http
from odoo.http import request
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tools import SQL

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class CheckoutSkipPaymentWebsite(WebsiteSale):
    def _get_shop_payment_values(self, order, **kwargs):
        values = super()._get_shop_payment_values(order, **kwargs)
        partner = values.get("partner")
        if partner.skip_website_checkout_payment:
            values["hide_payment_button"] = True
        return values

    @http.route()
    def shop_payment_confirmation(self, **post):
        """When we skip the payment, we'll just confirm the order and send the proper
        confirmation message"""
        order_id = request.session.get("sale_last_order_id")
        if not request.website.checkout_skip_payment or not order_id:
            return super().shop_payment_confirmation(**post)
        # The payment page the buyer is looking at belongs to another order than the
        # one pinned in the session (e.g. the buyer confirmed order A and then reached
        # the payment page of a new cart B without going through the checkout). The
        # checkout pins the cart as the order to confirm and leads the buyer to its
        # payment page, where "Confirm" is tapped again. The posted id is only
        # compared, never browsed nor confirmed.
        # It is absent on a reload or back button, which just show the confirmation.
        posted_order_id = post.get("order_id")
        if posted_order_id and posted_order_id != str(order_id):
            return request.redirect("/shop/checkout?try_skip_step=true")
        # The portal user cannot read nor confirm the order: the id comes from the
        # server-side session, not from the request.
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if not order:
            # The order was deleted meanwhile
            return request.render(
                "website_sale_checkout_skip_payment.confirmation_order_error"
            )
        # Wait for a concurrent confirmation of the same order to finish. The state
        # is read afterwards: if the other request committed meanwhile, the lock
        # raises a serialization failure and Odoo retries this one with the new state.
        request.env.cr.execute(
            SQL("SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE", order.id),
            log_exceptions=False,  # the waiting retries are expected, not errors
        )
        if order.state in ("draft", "sent"):
            try:
                order.with_context(mark_so_as_sent=True)._send_order_confirmation_mail()
            except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                # Let Odoo retry the request instead of swallowing the error
                raise
            except Exception:
                _logger.exception(
                    "Confirmation mail failed for order id %s", order.id
                )
                return request.render(
                    "website_sale_checkout_skip_payment.confirmation_order_error"
                )
            # This could not finish (e.g.: sale_financial_risk exceeded)
            order.action_confirm()
        elif order.state != "sale":
            return request.render(
                "website_sale_checkout_skip_payment.confirmation_order_error",
                {
                    "reason": _(
                        "Order %s is cancelled and cannot be confirmed. "
                        "Go back to the shop to create a new order.",
                        order.name,
                    )
                },
            )
        # An already confirmed order (repeated tap, reload, back button) only shows
        # the confirmation page again.
        request.website.sale_reset()
        values = self._prepare_shop_payment_confirmation_values(order)
        return request.render("website_sale.confirmation", values)
