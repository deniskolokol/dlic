from django.contrib import admin
from payments.models import Gift


class GiftAdmin(admin.ModelAdmin):
    model = Gift
    list_display = ['user', 'minutes', 'description', 'created_at']
    date_hierarchy = 'created_at'
    actions = None

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super(GiftAdmin, self).has_change_permission(request,
                                                                obj=obj)
        return False


admin.site.register(Gift, GiftAdmin)
