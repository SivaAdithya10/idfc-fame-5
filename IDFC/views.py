from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
import os
import markdown

def index(request):
    return render(request, 'index.html')

# def transactions_view(request):
#     return HttpResponse("This is the transactions page.")

# def instructions_view(request):
#     return render(request, 'index.html')