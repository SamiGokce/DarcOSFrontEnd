from django.contrib import admin

from .models import Persona


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('name', 'epithet', 'updated_at')
    search_fields = ('name', 'epithet', 'personality')
