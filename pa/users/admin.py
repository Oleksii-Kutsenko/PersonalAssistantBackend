from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


class UserAdmin(BaseUserAdmin):
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {
            'fields': ('first_name', 'last_name',)
        }),
    )


admin.site.register(User, UserAdmin)
