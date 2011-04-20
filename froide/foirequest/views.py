import json
import logging

from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _
from django.http import (HttpResponseRedirect, HttpResponse,
        HttpResponseForbidden, HttpResponseBadRequest)
from django.conf import settings
from django.contrib import messages

from foirequest.forms import RequestForm
from account.forms import NewUserForm
from account.models import AccountManager
from publicbody.forms import PublicBodyForm
from publicbody.models import PublicBody
from foirequest.models import FoiRequest
from foirequest.tasks import process_mail
from foirequest.forms import SendMessageForm, get_status_form_class
from froide.helper.utils import get_next


def index(request):
    public_bodies = PublicBody.objects.get_for_homepage()
    foi_requests = FoiRequest.objects.get_for_homepage()
    return render(request, 'index.html', 
            {'public_bodies': public_bodies,
            'foi_requests': foi_requests
        })

def show(request, slug, template_name="foirequest/show.html"):
    obj = get_object_or_404(FoiRequest, slug=slug)
    if not obj.is_visible(request.user):
        return HttpResponseForbidden()
    return render(request, template_name, {"object": obj})

def success(request):
    return render(request, 'index.html')

def make_request(request, public_body=None):
    public_body_form = None
    if public_body is not None:
        public_body = get_object_or_404(PublicBody,
                slug=public_body)
    else:
        public_body_form = PublicBodyForm()
    rq_form = RequestForm()
    topic = request.GET.get("topic", "")
    user_form = None
    if not request.user.is_authenticated():
        user_form = NewUserForm()
    return render(request, 'foirequest/request.html', 
            {"public_body": public_body,
            "public_body_form": public_body_form,
            "request_form": rq_form,
            "user_form": user_form,
            "topic": topic})

@require_POST
def submit_request(request, public_body=None):
    error = False
    if public_body is not None:
        public_body = get_object_or_404(PublicBody,
                slug=public_body)

    context = {"public_body": public_body}
    request_form = RequestForm(request.POST)
    context['request_form'] = request_form
    context['public_body_form'] = PublicBodyForm()
    if public_body is None and \
                request.POST.get('public_body') == "new":
            pb_form = PublicBodyForm(request.POST)
            context["public_body_form"] = pb_form
            if pb_form.is_valid():
                data = pb_form.cleaned_data
                data['confirmed'] = False
                public_body = PublicBody(**data)
            else:
                error = True
    if not request_form.is_valid():
        error = True
    context['user_form'] = None
    user = None
    if not request.user.is_authenticated():
        user_form = NewUserForm(request.POST)
        context['user_form'] = user_form
        if not user_form.is_valid():
            error = True
    else:
        user = request.user

    if not error:
        password = None
        if user is None:
            user, password = AccountManager.create_user(**user_form.cleaned_data)
        if public_body is not None and public_body.pk is None:
            public_body._created_by = user
            public_body.save()

        try:
            foilaw = request_form.foi_law_object
        except AttributeError:
            foilaw = None
        
        foi_request = FoiRequest.from_request_form(user, public_body,
                foilaw, **request_form.cleaned_data)
        if user.is_active:
            messages.add_message(request, messages.INFO, 
                    _('Your request has been sent.'))
        else:
            AccountManager(user).send_confirmation_mail(request_id=foi_request.pk,
                    password=password)
            messages.add_message(request, messages.INFO,
                    _('Please check your inbox for mail from us to confirm your mail address.'))
        return HttpResponseRedirect(foi_request.get_absolute_url())
    messages.add_message(request, messages.ERROR,
        _('There were errors in your form submission. Please review and submit again.'))
    return render(request, 'foirequest/request.html', context, status=400)

@require_POST
def message(request):
    authorization = None
    if 'Authorization' in request.META:
        authorization = request.META['Authorization']
    elif 'HTTP_AUTHORIZATION' in request.META:
        authorization =  request.META['HTTP_AUTHORIZATION']
    if authorization != settings.REMAIL_ENGINE_API_KEY:
        return HttpResponse('', status=403)

    try:
        email_dict = json.loads(request.raw_post_data)
    except ValueError:
        logging.error("Invalid JSON data", request.raw_post_data)
        return HttpResponse('', status=400)
    try:
        email_string = email_dict['email']['raw']
    except KeyError:
        logging.error("Invalid Mail Dict", email_dict)
        return HttpResponse('', status=400)
    process_mail.delay(email_string)
    return HttpResponse('')

@require_POST
def set_public_body(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return HttpResponseForbidden()
    try:
        public_body_pk = int(request.POST.get('public_body', None))
    except ValueError:
        return HttpResponseBadRequest()
    try:
        public_body = PublicBody.objects.get(pk=public_body_pk)
    except PublicBody.DoesNotExist:
        return HttpResponseBadRequest()
    if foirequest.status != "publicbody_needed":
        return HttpResponseBadRequest()
    # FIXME: make foilaw dynamic
    foilaw = public_body.default_law
    foirequest.set_public_body(public_body, foilaw)
    return HttpResponseRedirect(foirequest.get_absolute_url())

@require_POST
def set_status(request, slug):
    foirequest = get_object_or_404(FoiRequest, slug=slug)
    if not request.user.is_authenticated() or request.user != foirequest.user:
        return HttpResponseForbidden()
    form = get_status_form_class(foirequest)(request.POST)
    if form.is_valid():
        foirequest.set_status(form.cleaned_data)
        messages.add_message(request, messages.SUCCESS,
                _('Status of request has been updated.'))
    else:
        messages.add_message(request, messages.ERROR,
        _('Invalid value for form submission!'))
    return HttpResponseRedirect(foirequest.get_absolute_url())


@require_POST
def sent_message(request):
    form = SendMessageForm(request.POST)
    if form.is_valid():
        foimessage = form.foimessage_object
        if foimessage.sender_user != request.user:
            return HttpResponseForbidden()
        messages.add_message(request, messages.SUCCESS,
                _('Your Message has been sent.'))
        foimessage.send()
        return HttpResponseRedirect(get_next(request))
    else:
        return HttpResponseBadRequest()
