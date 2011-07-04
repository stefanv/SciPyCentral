from collections import defaultdict

from django.http import HttpResponse
from django.utils import simplejson
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.conf import settings
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist

# Imports from other SciPy Central apps
from scipy_central.pages.views import page_404_error
from scipy_central.submission.models import Revision, Submission
from scipy_central.utils import paginated_queryset

import models
import forms
import re
import random
import logging

logger = logging.getLogger('scipycentral')
logger.debug('Initializing person::views.py')

from django.contrib.auth import views as auth_views

def user_logged_in(sender, signal, request, user, **kwargs):
    """
    Work done when the user signs in.
    """
    logger.debug('User logged in: %s' % user.username)

@login_required
def profile_page_edit(request, slug):
    """
    User wants to edit his/her profile page.
    """
    # First verify that request.user is the same as slug
    return HttpResponse('Still to do.')


def profile_page(request, slug):
    """
    Shows the user's profile.
    """
    if slug is None:
        the_user = request.user
    else:
        try:
            the_user = models.User.objects.get(profile__slug=slug)
        except ObjectDoesNotExist:
            return page_404_error(request)

    # Don't show the profile for inactive (unvalidated) users
    if not(the_user.is_active):
        return page_404_error(request)


    # Items created by this user
    all_revs = Revision.objects.filter(created_by=the_user)
    all_subs = set()
    for rev in all_revs:
        all_subs.add(rev.entry)


    if the_user == request.user:
        no_entries = 'You have not submitted any entries to SciPy Central.'
    else:
        no_entries = 'This user has not submitted any entries to SciPy Central.'

    return render_to_response('person/profile.html', {},
                context_instance=RequestContext(request,
                            {'theuser': the_user,
                             'entries':paginated_queryset(request, all_subs),
                             'no_entries_message': no_entries, }))


def create_new_account_internal(email):
    """
    Creates a *temporary* new user account so submissions can be made via
    email address. User's submission will be deleted if their account is not
    activated.

    We assume the ``email`` has already been validated as an email address.
    """
    # First check if that email address have been used; return ``False``
    previous = models.User.objects.filter(email=email)
    if len(previous) > 0:
        return previous[0]

    new_user = models.User.objects.create(username=email,
                                                 email=email)
    temp_password = ''.join([random.choice('abcdefghjkmnpqrstuvwxyz2345689')\
                             for i in range(50)])
    new_user.set_password(temp_password)
    new_user.save()
    return new_user


def create_new_account(sender, signal, request=None, user=None, **kwargs):
    """
    Complete creating the new user account: i.e. a new ``User`` object.
    """
    if 'instance' in kwargs and kwargs.get('created', False):
        new_user = kwargs.get('instance', user)

        # Create a UserProfile object in the DB
        new_user_profile = models.UserProfile.objects.create(user=new_user)
        new_user_profile.save()

def account_activation(sender, signal, request, user, **kwargs):
    """ User's account has been successfully activated.

    Make all their previous submissions visible.
    """
    user_profile = models.UserProfile.objects.get(user=user)
    user_profile.is_validated = True
    user_profile.save()

    user_submissions = Submission.objects.filter(created_by = user)
    for sub in user_submissions:
        sub.is_displayed = True
        sub.save()



    # TODO(KGD): activate any previous submissions by this user
