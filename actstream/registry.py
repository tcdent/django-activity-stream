from inspect import isclass

import django
from django.db.models import get_model
from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.utils.six import string_types


from actstream.compat import generic


def setup_generic_relations(model_class):
    """
    Set up GenericRelations for actionable models.
    """
    Action = get_model('actstream', 'Action')
    related_attr_name = 'related_name'
    related_attr_value = 'actions_with_%s' % label(model_class)
    if django.VERSION >= (1, 7):
        related_attr_name = 'related_query_name'
    relations = {}
    for field in ('actor', 'target', 'action_object'):
        attr = '%s_actions' % field
        attr_value = '%s_as_%s' % (related_attr_value, field)
        kwargs = {
            'content_type_field': '%s_content_type' % field,
            'object_id_field': '%s_object_id' % field,
            related_attr_name: attr_value
        }
        rel = generic.GenericRelation('actstream.Action', **kwargs
                        ).contribute_to_class(model_class, attr)
        relations[field] = rel
        setattr(Action, attr_value, None)
    return relations


def label(model_class):
    if hasattr(model_class._meta, 'model_name'):
        model_name = model_class._meta.model_name
    else:
        model_name = model_class._meta.module_name
    return '%s_%s' % (model_class._meta.app_label, model_name)


def validate(model_class, exception_class=ImproperlyConfigured):
    if isinstance(model_class, string_types):
        model_class = get_model(*model_class.split('.'))
    if not isinstance(model_class, ModelBase):
        raise exception_class(
            'Object %r is not a Model class.' % model_class)
    if model_class._meta.abstract:
        raise exception_class(
            'The model %s is abstract, so it cannot be registered with '
            'actstream.' % model_class.__name__)
    if not model_class._meta.installed:
        raise exception_class(
            'The model %s is not installed, please put %s in your '
            'INSTALLED_APPS setting.' % (model_class.__name__,
                                         model_class._meta.app_label))
    return model_class


class ActionableModelRegistry(dict):

    def register(self, *model_classes_or_labels):
        for class_or_label in model_classes_or_labels:
            model_class = validate(class_or_label)
            if not model_class in self:
                self[model_class] = setup_generic_relations(model_class)

    def unregister(self, *model_classes_or_labels):
        for class_or_label in model_classes_or_labels:
            model_class = validate(class_or_label)
            if model_class in self:
                del self[model_class]

    def check(self, model_class_or_object):
        if not isclass(model_class_or_object):
            model_class_or_object = model_class_or_object.__class__
        model_class = validate(model_class_or_object, RuntimeError)
        if not model_class in self:
            raise ImproperlyConfigured(
                'The model %s is not registered. Please use actstream.registry '
                'to register it.' % model_class.__name__)

registry = ActionableModelRegistry()
register = registry.register
unregister = registry.unregister
check = registry.check
