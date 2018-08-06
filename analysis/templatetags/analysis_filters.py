from functools import reduce

from django import template
register = template.Library()


@register.filter
def is_system_threshold_reached(system, user):
    user_related_objects = user.user_profile.related_objects.all().values_list("object_id", flat=True)

    symptoms = []

    for symptom in system.symptoms.all():
        related_object = symptom.related_objects.filter(
            object_id__in=user_related_objects
        ).first()
        if related_object:
            symptoms.append(
                related_object.parent
            )

    user_symptoms = list(user.user_profile.symptoms.exclude(
        pk__in=[symptom.pk for symptom in symptoms]
    ).all())

    user_symptoms += symptoms
    system_symptoms = system.systemsymptoms_set.filter(symptom__in=user_symptoms)

    total_weight = reduce(lambda t, o: t + o.weight, system_symptoms, 0)

    if total_weight >= system.threshold:
        return True
    return False


@register.simple_tag
def progress_status(page):
    return (100 * page.number) // page.paginator.num_pages


@register.simple_tag(takes_context=True)
def extra_get_params(context):
    if context.request.GET.get('show_user_systems') == 'on':
        return '&show_user_systems=on'
    return ''

