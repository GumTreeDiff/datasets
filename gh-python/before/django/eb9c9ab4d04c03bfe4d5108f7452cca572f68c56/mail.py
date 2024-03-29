"""
Use this for e-mailing
"""

from django.conf.settings import DEFAULT_FROM_EMAIL, EMAIL_HOST
from email.MIMEText import MIMEText
import smtplib

def send_mail(subject, message, from_email, recipient_list, fail_silently=False):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.
    """
    return send_mass_mail([[subject, message, from_email, recipient_list]], fail_silently)

def send_mass_mail(datatuple, fail_silently=False):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    """
    try:
        server = smtplib.SMTP(EMAIL_HOST)
    except:
        if fail_silently:
            return
        raise
    num_sent = 0
    for subject, message, from_email, recipient_list in datatuple:
        if not recipient_list:
            continue
        from_email = from_email or DEFAULT_FROM_EMAIL
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(recipient_list)
        server.sendmail(from_email, recipient_list, msg.as_string())
        num_sent += 1
    server.quit()
    return num_sent

def mail_admins(subject, message, fail_silently=False):
    "Sends a message to the admins, as defined by the ADMINS constant in settings.py."
    from django.conf.settings import ADMINS, SERVER_EMAIL
    send_mail('[CMS] ' + subject, message, SERVER_EMAIL, [a[1] for a in ADMINS], fail_silently)

def mail_managers(subject, message, fail_silently=False):
    "Sends a message to the managers, as defined by the MANAGERS constant in settings.py"
    from django.conf.settings import MANAGERS, SERVER_EMAIL
    send_mail('[CMS] ' + subject, message, SERVER_EMAIL, [a[1] for a in MANAGERS], fail_silently)
