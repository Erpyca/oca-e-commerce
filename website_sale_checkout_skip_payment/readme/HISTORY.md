## 19.0.1.1.0

- Order confirmation is now idempotent: repeated taps or page reloads on the confirm button no longer fail or re-confirm an already confirmed order.
- Concurrent confirmation requests for the same order are serialized: no error is raised and no duplicate confirmation email is sent.
- The confirm button is disabled and shows a spinner after the first tap.
- A cancelled order can no longer be confirmed; the customer is told why.
- If the cart no longer matches the order being confirmed, the customer is redirected to the checkout.
- Opening the confirmation URL without tapping the confirm button no longer confirms a pending order: the customer is taken to the payment page.
- The confirmation and its email are done as a single unit: if Odoo refuses the confirmation or anything fails, the order is left untouched, no email is sent and the customer sees the module error page (with Odoo's reason when there is one).
