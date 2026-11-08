from django.contrib import admin

from .models import Chat, LanguageModel, Message


@admin.register(LanguageModel)
class LanguageModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'repo_id', 'parameters')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('title', 'soul', 'model_name', 'updated_at')
    list_filter = ('soul', 'model_name')
    inlines = [MessageInline]
