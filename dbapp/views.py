from rest_framework import viewsets, status
from rest_framework.response import Response
from django.apps import apps
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType

from .serializers import SERIALIZERS, GroupSerializer

class BaseViewSet(viewsets.ModelViewSet):
    def check_auth(self):
        if not self.request.user.is_authenticated:
            return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return None

    def log_action(self, instance, action_flag, changed_fields=None):
        user = self.request.user
        if not user.is_authenticated:
            return

        if action_flag == ADDITION:
            change_message = "Добавлено."
        elif action_flag == DELETION:
            change_message = "Удалено."
        elif action_flag == CHANGE:
            if not changed_fields:
                change_message = 'Ни одно поле не изменено.'
            else:
                if len(changed_fields) == 1:
                    change_message = f'Изменено {changed_fields[0]}.'
                elif len(changed_fields) == 2:
                    change_message = f'Изменено {changed_fields[0]} и {changed_fields[1]}.'
                else:
                    change_message = f'Изменено {", ".join(changed_fields[:-1])} и {changed_fields[-1]}.'
        else:
            change_message = '[]'

        LogEntry.objects.log_action(
            user_id=user.pk,  # type: ignore
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=instance.pk,
            object_repr=str(instance),
            action_flag=action_flag,
            change_message=change_message
        )

    def create(self, request, *args, **kwargs):
        print("INCOMING DATA:", request.data) 
        auth_resp = self.check_auth()
        if auth_resp:
            return auth_resp
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        self.perform_create(serializer)

        self.log_action(serializer.instance, ADDITION)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        auth_resp = self.check_auth()
        if auth_resp:
            return auth_resp

        instance = self.get_object()
        old_data = {f.name: getattr(instance, f.name) for f in instance._meta.fields}

        response = super().update(request, *args, **kwargs)
        if response.status_code in (200, 204):
            new_instance = self.get_object()
            changed_fields = []
            for f in instance._meta.fields:
                old_val = old_data[f.name]
                new_val = getattr(new_instance, f.name)
                if old_val != new_val:
                    changed_fields.append(str(f.verbose_name))
            self.log_action(new_instance, CHANGE, changed_fields)
        return response

    def destroy(self, request, *args, **kwargs):
        auth_resp = self.check_auth()
        if auth_resp:
            return auth_resp

        instance = self.get_object()
        response = super().destroy(request, *args, **kwargs)
        if response.status_code in (200, 204):
            self.log_action(instance, DELETION)
        return response

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

def create_viewset_for_model(model_class):
    serializer_class = SERIALIZERS[model_class.__name__]
    return type(
        f'{model_class.__name__}ViewSet',
        (BaseViewSet,),
        {
            'queryset': model_class.objects.all(),
            'serializer_class': serializer_class
        }
    )

models = apps.get_app_config('dbapp').get_models()
VIEWSETS = {model.__name__: create_viewset_for_model(model) for model in models}
