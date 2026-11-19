# Copyright 2017 Sergio Teruel <sergio.teruel@tecnativa.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tools import SQL

from odoo.addons.website_sale.controllers.main import WebsiteSale

from ..models.sale_order import CONFIRM_CONTEXT_KEY, ConfirmationMailError

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
        """When we skip the payment, submitting the confirm form confirms the order
        and sends the confirmation mail. Any other visit just shows the payment page
        of a pending order or the confirmation of a confirmed one."""
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
            return self._render_skip_payment_error()
        if order.state == "cancel":
            return self._render_skip_payment_error(
                request.env._(
                    "Order %s is cancelled and cannot be confirmed. "
                    "Go back to the shop to create a new order.",
                    order.name,
                )
            )
        if order.state in ("draft", "sent"):
            # Wait for a concurrent confirmation of the same order to finish. If it
            # committed after the state above was read, the lock raises a
            # serialization failure and Odoo retries this request with the new state.
            # A confirmed or cancelled order is not locked: it does not change here.
            request.env.cr.execute(
                SQL(
                    "SELECT 1 FROM sale_order WHERE id = %s FOR NO KEY UPDATE",
                    order.id,
                ),
                log_exceptions=False,  # the waiting retries are expected, not errors
            )
            # Only the submit of the confirm form confirms: opening the URL (typed,
            # autocompleted or prefetched) leads to the payment page instead.
            if request.httprequest.method != "POST":
                return request.redirect("/shop/payment")
            error_page = self._skip_payment_confirm_order(order)
            if error_page:
                return error_page
        # An already confirmed order (repeated tap, reload, back button) only shows
        # the confirmation page again.
        request.website.sale_reset()
        values = self._prepare_shop_payment_confirmation_values(order)
        return request.render("website_sale.confirmation", values)

    def _skip_payment_confirm_order(self, order):
        """Confirm the order and send its confirmation mail as a single unit.

        Whatever fails inside leaves the order untouched.

        :return: the error page if the order could not be confirmed, else None
        """
        try:
            with request.env.cr.savepoint() as savepoint:
                order.with_context(
                    send_email=True,
                    mark_so_as_sent=True,
                    **{CONFIRM_CONTEXT_KEY: True},
                ).action_confirm()
                # The confirmation can end without error and without confirming
                # (e.g.: sale_financial_risk exceeded)
                if order.state != "sale":
                    savepoint.close(rollback=True)
                    _logger.error("Order id %s was not confirmed", order.id)
                    return self._render_skip_payment_error()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # Let Odoo retry the request instead of swallowing the error
            raise
        except ConfirmationMailError:
            # Not a refusal with a reason for the buyer: only the log has the detail
            _logger.exception("Confirmation mail failed for order id %s", order.id)
            return self._render_skip_payment_error()
        except UserError as exc:
            # Odoo refuses the confirmation with a reason for the buyer
            return self._render_skip_payment_error(
                request.env._(
                    "Could not confirm order %(name)s: %(reason)s",
                    name=order.name,
                    reason=str(exc),
                )
            )
        except Exception:
            _logger.exception("Confirmation failed for order id %s", order.id)
            return self._render_skip_payment_error()
        return None

    def _render_skip_payment_error(self, reason=None):
        return request.render(
            "website_sale_checkout_skip_payment.confirmation_order_error",
            {"reason": reason},
        )
