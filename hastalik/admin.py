from django.contrib import admin
from .models import Village, Profile, Field, Report, Message, Alert
from django.contrib import admin
from .models import Village


admin.site.register(Profile)
admin.site.register(Field)
admin.site.register(Report)
admin.site.register(Message)
admin.site.register(Alert)

@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ("name", "latitude", "longitude")
    search_fields = ("name",)