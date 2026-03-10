from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Service, Log, Notification


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'nombre_utilisateurs', 'created_at']
    search_fields = ['nom', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def nombre_utilisateurs(self, obj):
        return obj.utilisateurs.count()
    nombre_utilisateurs.short_description = 'Nb utilisateurs'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'service', 'is_active', 'date_joined']
    list_filter = ['role', 'service', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'service'),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'service'),
        }),
    )


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action']
    list_filter = ['timestamp']
    search_fields = ['user__username', 'action']
    readonly_fields = ['timestamp']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'type', 'titre', 'lue', 'created_at']
    list_filter = ['type', 'lue', 'created_at']
    search_fields = ['utilisateur__username', 'titre', 'message']
    readonly_fields = ['created_at', 'lue_at']
    ordering = ['-created_at']
