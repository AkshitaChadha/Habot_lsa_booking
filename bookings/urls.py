from django.urls import path
from .views import BookingCreateView, LSASearchView, PaymentWebhookView
from .debug_views import n_plus_one_test

urlpatterns=[
  path(
    "bookings/",
    BookingCreateView.as_view(),
    name="booking-create",
  ),
  
  path("lsas/search/",
      LSASearchView.as_view(),
      name="lsa-search",
  ),
  path(
    "debug/n-plus-one/",
    n_plus_one_test,
    name="n-plus-one-test",
  ),
  path(
    "payments/webhook/",
    PaymentWebhookView.as_view(),
    name="payment-webhook",
  ),
]