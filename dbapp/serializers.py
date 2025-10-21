from django.contrib.auth.models import Group
from rest_framework import serializers
from django.apps import apps

def get_serializer_for_model(model_class):
    class Meta:
        model = model_class
        fields = '__all__'

    serializer_name = f'{model_class.__name__}Serializer'
    return type(serializer_name, (serializers.ModelSerializer,), {'Meta': Meta})

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]

models = apps.get_app_config('dbapp').get_models()
SERIALIZERS = {model.__name__: get_serializer_for_model(model) for model in models}