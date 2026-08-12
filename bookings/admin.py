from django.contrib import admin

# Register your models here.
from .models import Parent, Skill, LSAProfile, Booking, Payment

admin.site.register(Parent)
admin.site.register(Skill)
admin.site.register(LSAProfile)
admin.site.register(Booking)
admin.site.register(Payment)