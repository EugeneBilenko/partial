from django import template

from analysis.models import Symptom
from genome.models import UserProfileSymptoms, UserProfileCondition, Condition

register = template.Library()


@register.assignment_tag()
def exclude_similar_symptom(item, query_set_symptoms):
    """
    Removes similar related objects from symptoms list
    :param item: RelatesObject
    :param query_set_symptoms: QuerySet
    :return: bool
    """
    symptoms_lower = [symptom.lower() for symptom in query_set_symptoms.values_list('name', flat=True)]
    related_lower = item.object.name.lower()
    return related_lower not in symptoms_lower


@register.simple_tag
def progress_status(page):
    """
    Calc progress on the personalized health report page
    :param page: PageObject
    :return: int
    """
    return (100 * page.number) // page.paginator.num_pages


@register.simple_tag
def get_severity(obj, user):
    """
    Get severity of selected symptom
    :param obj: Symptom or Condition object
    :param user: User object
    :return: integer
    """
    if isinstance(obj, Symptom):
        symptom = UserProfileSymptoms.objects.filter(userprofile=user.user_profile, symptom=obj).first()
        if symptom:
            return symptom.severity
    elif isinstance(obj, Condition):
        condition = UserProfileCondition.objects.filter(userprofile=user.user_profile, condition=obj).first()
        if condition:
            return condition.severity
    return 0
