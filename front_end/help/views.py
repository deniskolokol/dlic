# Create your views here.
from os import path
import markdown
from django.shortcuts import render
from django.http import HttpResponseNotFound
from django.contrib.auth.decorators import login_required


@login_required
def help_view(request, md):
    pwd = path.join(path.dirname(path.abspath(__file__)),
                    'templates/help', md + '.md')
    try:
        with open(pwd, 'r') as f:
            markdown_content = markdown.markdown(f.read())
    except (OSError, IOError):
        return HttpResponseNotFound('Not found!')
    return render(request, 'help/index.html',
                  {'view': 'help', 'markdown_content': markdown_content})
