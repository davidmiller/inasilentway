"""
inasilentway forms
"""
from django import forms


class ScrobbleForm(forms.Form):
    date      = forms.CharField(label='Date', max_length=100)
    time      = forms.CharField(label='Time', max_length=100)
    record_id = forms.IntegerField()
    tracks    = forms.CharField(label='Tracks', max_length=100)
