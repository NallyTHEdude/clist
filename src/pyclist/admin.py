from django import forms
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import connection, models, transaction
from django.db.models.fields.related import RelatedField
from django.shortcuts import redirect
from django_json_widget.widgets import JSONEditorWidget
from guardian.admin import GuardedModelAdmin

from pyclist.models import BaseModel


class CachingPaginator(Paginator):
    '''
    A custom paginator that helps to cut down on the number of
    SELECT COUNT(*) form table_name queries. These are really slow, therefore
    once we execute the query, we will cache the result which means the page
    numbers are not going to be very accurate but we don't care
    '''

    def _get_count(self):
        """
        Returns the total number of objects, across all pages.
        """
        if getattr(self, '_count', None) is None:
            try:
                key = "adm:{0}:count".format(hash(self.object_list.query.__str__()))
                self._count = cache.get(key, -1)
                if self._count == -1:
                    with transaction.atomic(), connection.cursor() as cursor:
                        if not self.object_list.query.where:
                            # This query that avoids a count(*) alltogether is
                            # stolen from https://djangosnippets.org/snippets/2593/
                            cursor.execute(
                                "SELECT reltuples FROM pg_class WHERE relname = %s",
                                [self.object_list.query.model._meta.db_table]
                            )
                            self._count = int(cursor.fetchone()[0])
                        else:
                            try:
                                cursor.execute('SET LOCAL statement_timeout TO 2000;')
                                self._count = self.object_list.count()
                            except Exception:
                                return 0
                    cache.set(key, self._count, 3600)
            except Exception:
                self._count = len(self.object_list)
        return self._count
    count = property(_get_count)


def admin_register(*args, **kwargs):
    def _model_admin_wrapper(admin_class):
        admin_class = admin.register(*args, **kwargs)(admin_class)

        model = next(iter(args))
        if any(issubclass(b, BaseModel) for b in model.__bases__):
            autocomplete_fields = getattr(admin_class, 'autocomplete_fields', None)
            if autocomplete_fields is not None:
                autocomplete_fields = list(autocomplete_fields)
                for field in model._meta.get_fields():
                    if field.name in autocomplete_fields:
                        continue
                    if not isinstance(field, RelatedField):
                        continue
                    if isinstance(field, GenericRelation):
                        continue
                    if field.related_model is ContentType:
                        continue
                    autocomplete_fields.append(field.name)
                setattr(admin_class, 'autocomplete_fields', autocomplete_fields)

        return admin_class
    return _model_admin_wrapper


class CustomJSONEditorWidget(JSONEditorWidget):

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value in {'{}', '[]', '', 'null'}:
            context['widget']['height'] = '100px'
        return context


class BaseModelAdmin(GuardedModelAdmin):
    readonly_fields = ['created', 'modified']
    save_as = True
    paginator = CachingPaginator

    formfield_overrides = {
        models.JSONField: {'widget': CustomJSONEditorWidget(mode='code', height='300px')},
    }

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if isinstance(db_field, models.fields.CharField) and db_field.name in getattr(self, 'textarea_fields', []):
            formfield.widget = forms.Textarea(attrs=formfield.widget.attrs)
        elif isinstance(db_field, models.fields.TextField) and db_field.name in getattr(self, 'one_line_fields', []):
            formfield.widget = forms.TextInput()
        return formfield

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term and getattr(self, 'search_entirely', False):
            search_fields = getattr(self, 'search_fields', [])
            condition = models.Q()
            for field in search_fields:
                condition |= models.Q(**{f'{field}__contains': search_term})
            queryset = queryset.filter(condition)
        return queryset, use_distinct

    def changelist_view(self, request, *args, **kwargs):
        if sort_by := request.GET.get('sort_by'):
            params = request.GET.copy()
            params.pop('sort_by')
            display_fields = list(self.get_list_display(request))
            field = sort_by.lstrip('-')
            if field in display_fields:
                index = display_fields.index(field) + 1
                if sort_by.startswith('-'):
                    index = -index
                params['o'] = str(index)
                request.GET = params
                return redirect(f'{request.path}?{params.urlencode()}')
        return super().changelist_view(request, *args, **kwargs)

    class Meta:
        abstract = True


@admin_register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_type', 'codename']
    search_fields = ['name', 'codename']
