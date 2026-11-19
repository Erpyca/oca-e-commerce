## 18.0.1.1.2

- Order confirmation is now idempotent: repeated taps or page reloads on the confirm button no longer fail or re-confirm an already confirmed order.
- Concurrent confirmation requests for the same order are serialized: no error is raised and no duplicate confirmation email is sent.
- The confirm button is disabled and shows a spinner after the first tap.
- A cancelled order can no longer be confirmed; the customer is told why.
- If the cart no longer matches the order being confirmed, the customer is redirected to the checkout.
