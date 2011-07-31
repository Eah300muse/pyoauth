#!/usr/bin/env python
# -*- coding: utf-8 -*-
# OpenID Mixin (Google OAuth+OpenID Hybrid style)
#
# Copyright (C) 2009 Facebook.
# Copyright (C) 2011 Yesudeep Mangalapilly <yesudeep@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from urllib import urlencode
from mom.functional import select_dict, map_dict
from pyoauth._compat import urljoin
from pyoauth.url import url_add_query
from pyoauth.http import RequestAdapter, CONTENT_TYPE_FORM_URLENCODED


class OpenIdMixin(object):
    """
    Abstract implementation of OpenID and Attribute Exchange.
    Useful for Hybrid OAuth+OpenID auth.

    See GoogleMixin for example implementation. Use it with an
    HttpAdapterMixin class.

    http://code.google.com/apis/accounts/docs/OpenID.html
    """

    # Implement this in subclasses.
    _OPENID_ENDPOINT = None

    ATTRIB_EMAIL = "http://axschema.org/contact/email"
    ATTRIB_COUNTRY = "http://axschema.org/contact/country/home"
    ATTRIB_LANGUAGE = "http://axschema.org/pref/language"
    ATTRIB_USERNAME = "http://axschema.org/namePerson/friendly"
    ATTRIB_FIRST_NAME = "http://axschema.org/namePerson/first"
    ATTRIB_FULL_NAME = "http://axschema.org/namePerson"
    ATTRIB_LAST_NAME = "http://axschema.org/namePerson/last"
    SPEC_IDENTIFIER_SELECT= "http://specs.openid.net/auth/2.0/identifier_select"
    SPEC_OPENID_NS = "http://specs.openid.net/auth/2.0"
    SPEC_OAUTH_NS = "http://specs.openid.net/extensions/oauth/1.0"
    SPEC_AX_NS = "http://openid.net/srv/ax/1.0"

    def authenticate_redirect(self, callback_uri=None, ax_attrs=None):
        """
        Redirects to the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI.

        We request the given attributes for the authenticated user by default
        (name, email, language, and username). If you don't need all those
        attributes for your app, you can request fewer with the ax_attrs keyword
        argument.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :returns:
            None
        """
        ax_attrs = ax_attrs or ("name", "email",
                                "language", "username", "country")
        callback_uri = callback_uri or self.adapter_request_path
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        self.adapter_redirect(url_add_query(self._OPENID_ENDPOINT, args))

    def get_authenticated_user(self, callback):
        """
        Fetches the authenticated user data upon redirect.

        This method should be called by the handler that handles the callback
        URL to which the service redirects when the authenticate_redirect()
        or authorize_redirect() methods are called.

        :param callback:
            A function that is called after the authentication attempt. It is
            called passing a dictionary with the requested user attributes or
            None if the authentication failed.
        """
        request_arguments = self.adapter_request_params
        http = self.adapter_http_client

        # Verify the OpenID response via direct request to the OP
        args = map_dict(lambda k, v: (k, v[-1]), request_arguments)
        args["openid.mode"] = u"check_authentication"
        url = self._OPENID_ENDPOINT

        response = http.fetch(RequestAdapter(
            "POST", url, urlencode(args), {
                "content-type": CONTENT_TYPE_FORM_URLENCODED,
            }
        ))
        self._on_authentication_verified(callback, response)

    def _openid_args(self, callback_uri, ax_attrs=None, oauth_scope=None):
        """
        Builds and returns the OpenID arguments used in the authentication
        request.

        :param callback_uri:
            The URL to redirect to after authentication.
        :param ax_attrs:
            List of Attribute Exchange attributes to be fetched.
        :param oauth_scope:
            OAuth scope.
        :returns:
            A dictionary of arguments for the authentication URL.
        """
        ax_attrs = ax_attrs or ()
        url = urljoin(self.adapter_request_full_url, callback_uri)
        request_host = self.adapter_request_host
        request_protocol = self.adapter_request_scheme

        args = {
            "openid.ns": self.SPEC_OPENID_NS,
            "openid.claimed_id": self.SPEC_IDENTIFIER_SELECT,
            "openid.identity": self.SPEC_IDENTIFIER_SELECT,
            "openid.return_to": url,
            "openid.realm": request_protocol + "://" + request_host + "/",
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update({
                "openid.ns.ax": self.SPEC_AX_NS,
                "openid.ax.mode": "fetch_request",
            })
            ax_attrs = set(ax_attrs)
            required = []
            if "name" in ax_attrs:
                ax_attrs -= set(["name", "firstname", "fullname", "lastname"])
                required += ["firstname", "fullname", "lastname"]
                args.update({
                    "openid.ax.type.firstname": self.ATTRIB_FIRST_NAME,
                    "openid.ax.type.fullname": self.ATTRIB_FULL_NAME,
                    "openid.ax.type.lastname": self.ATTRIB_LAST_NAME,
                    })
            known_attrs = {
                "email": self.ATTRIB_EMAIL,
                "country": self.ATTRIB_COUNTRY,
                "language": self.ATTRIB_LANGUAGE,
                "username": self.ATTRIB_USERNAME,
                }
            for name in ax_attrs:
                args["openid.ax.type." + name] = known_attrs[name]
                required.append(name)
            args["openid.ax.required"] = ",".join(required)
        if oauth_scope:
            args.update({
                "openid.ns.oauth": self.SPEC_OAUTH_NS,
                "openid.oauth.consumer": request_host.split(":")[0],
                "openid.oauth.scope": oauth_scope,
                })
        return args


    def _on_authentication_verified(self, callback, response):
        """
        Called after the authentication attempt. It calls the callback function
        set when the authentication process started, passing a dictionary of
        user data if the authentication was successful or None if it failed.

        :param callback:
            A function that is called after the authentication attempt
        """
        if not response:
            logging.warning("Missing OpenID response.")
            callback(None)
            return
        elif response.error or "is_value:true" not in response.body:
            logging.warning("Invalid OpenID response (%s): %r",
                            str(response.status) + response.reason,
                            response.body)
            callback(None)
            return

        request_arguments = self.adapter_request_params
        claimed_id = self.adapter_request_get("openid.claimed_id", "")

        # Make sure we got back at least an email from Attribute Exchange.
        ax_ns = None
        for name, values in request_arguments.items():
            if name.startswith("openid.ns.") and values[-1] == SPEC_AX_NS:
                ax_ns = name[10:]
                break

        ax_args = self._get_ax_args(request_arguments, ax_ns)
        def get_ax_arg(uri, ax_args=ax_args, ax_ns=ax_ns):
            ax_name = self._get_ax_name(ax_args, uri, ax_ns)
            return self.adapter_request_get(ax_name, u"")

        email = get_ax_arg(self.ATTRIB_EMAIL)
        country = get_ax_arg(self.ATTRIB_COUNTRY)
        name = get_ax_arg(self.ATTRIB_FULL_NAME)
        first_name = get_ax_arg(self.ATTRIB_FIRST_NAME)
        last_name = get_ax_arg(self.ATTRIB_LAST_NAME)
        username = get_ax_arg(self.ATTRIB_USERNAME)
        locale = get_ax_arg(self.ATTRIB_LANGUAGE).lower()

        user = dict()
        name_parts = []
        if first_name:
            user["first_name"] = first_name
            name_parts.append(first_name)
        if last_name:
            user["last_name"] = last_name
            name_parts.append(last_name)
        if name:
            user["name"] = name
        elif name_parts:
            user["name"] = u" ".join(name_parts)
        elif email:
            user["name"] = email.split("@")[0]
        if email: user["email"] = email
        if locale: user["locale"] = locale
        if username: user["username"] = username
        if country: user["country"] = country

        # Get the claimed ID. Not in facebook code. Borrowed from Tipfy.
        user["claimed_id"] = claimed_id

        callback(user)

    @classmethod
    def _get_ax_args(cls, request_arguments, ax_ns):
        if not ax_ns:
            return {}
        prefix = "openid." + ax_ns + ".type."
        return select_dict(lambda k, v: k.startswith(prefix), request_arguments)

    @classmethod
    def _get_ax_name(cls, ax_args, uri, ax_ns):
        """
        Returns an Attribute Exchange value from the request.

        :param ax_args:
            Attribute Exchange-specific request arguments.
        :param uri:
            Attribute Exchange URI.
        :param ax_ns:
            Attribute Exchange namespace.
        :returns:
            The Attribute Exchange value, if found in the request.
        """
        if not ax_ns:
            return ""
        ax_name = ""
        prefix = "openid." + ax_ns + ".type."
        for name, values in ax_args.items():
            if values[-1] == uri:
                part = name[len(prefix):]
                ax_name = "openid." + ax_ns + ".value." + part
                break
        return ax_name
