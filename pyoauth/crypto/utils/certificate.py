#!/usr/bin/env python
# -*- coding: utf-8 -*-


import base64
import textwrap


CERT_PEM_HEADER = '-----BEGIN CERTIFICATE-----'
CERT_PEM_FOOTER = '-----END CERTIFICATE-----'

PRIVATE_KEY_PEM_HEADER = '-----BEGIN PRIVATE KEY-----'
PRIVATE_KEY_PEM_FOOTER = '-----END PRIVATE KEY-----'

PUBLIC_KEY_PEM_HEADER = '-----BEGIN PUBLIC KEY-----'
PUBLIC_KEY_PEM_FOOTER = '-----END PUBLIC KEY-----'


def pem_to_der(pem_cert_string, pem_header, pem_footer):
    """
    Extracts the DER as a byte sequence out of an ASCII PEM formatted
    certificate or key.

    Taken from the Python SSL module.

    :param pem_cert_string:
        The PEM certificate or key string.
    :param pem_header:
        The PEM header to find.
    :param pem_footer:
        The PEM footer to find.
    """
    if not pem_cert_string.startswith(pem_header):
        raise ValueError("Invalid PEM encoding; must start with %s"
                         % pem_header)
    if not pem_cert_string.strip().endswith(pem_footer):
        raise ValueError("Invalid PEM encoding; must end with %s"
                         % pem_footer)
    d = pem_cert_string.strip()[len(pem_header):-len(pem_footer)]
    return base64.decodestring(d)


def der_to_pem(der_cert_bytes, pem_header, pem_footer):
    """
    Takes a certificate in binary DER format and returns the
    PEM version of it as a string.

    Taken from the Python SSL module.

    :param der_cert_bytes:
        A byte string of the DER.
    :param pem_header:
        The PEM header to use.
    :param pem_footer:
        The PEM footer to use.
    """
    if hasattr(base64, 'standard_b64encode'):
        # preferred because older API gets line-length wrong
        f = base64.standard_b64encode(der_cert_bytes)
        return (pem_header + '\n' +
                textwrap.fill(f, 64) + '\n' +
                pem_footer + '\n')
    else:
        return (pem_header + '\n' +
                base64.encodestring(der_cert_bytes) +
                pem_footer + '\n')

