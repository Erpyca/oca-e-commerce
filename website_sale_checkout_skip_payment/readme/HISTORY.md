## 18.0.1.2.0

- The confirmation email is now built after the order is confirmed, so it says the order was confirmed and its PDF is titled as an order, not as a quotation.
- Confirmation and email are all or nothing: if either fails, the order stays as it was and no email is sent. When Odoo rejects the confirmation with a reason, the customer sees it; any other failure shows the generic error and is logged.
- Opening the confirmation URL without tapping "Confirm" no longer confirms a pending order: the customer is taken to the payment page. An already confirmed order still shows the confirmation page.

## 18.0.1.1.2

- Order confirmation is now idempotent: repeated taps or page reloads on the confirm button no longer fail or re-confirm an already confirmed order.
- Concurrent confirmation requests for the same order are serialized: no error is raised and no duplicate confirmation email is sent.
- The confirm button is disabled and shows a spinner after the first tap.
- A cancelled order can no longer be confirmed; the customer is told why.
- If the cart no longer matches the order being confirmed, the customer is redirected to the checkout.
