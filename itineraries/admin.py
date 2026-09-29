from django.contrib import admin

from .models import Collaboration, DailyPlan, Itinerary

admin.site.register([Itinerary, Collaboration, DailyPlan])
