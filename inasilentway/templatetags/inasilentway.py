"""
Templatetags for inasilentway
"""
from urllib.parse import urlencode
from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def this_url_replace(context, **kwargs):
    """
    Return the current path, replacing any GET
    params passed in with KWARGS
    """
    query = context['request'].GET.dict()
    query.update(kwargs)
    return '{}?{}'.format(
        context['view'].request.META['PATH_INFO'],
        urlencode(query)
    )


@register.inclusion_tag('partials/bar_chart.html')
def bar_chart(data_fn):
    return {'data': data_fn}
