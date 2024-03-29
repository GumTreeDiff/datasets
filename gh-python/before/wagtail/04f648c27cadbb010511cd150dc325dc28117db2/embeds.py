from datetime import datetime
from django.conf import settings
from embedly import Embedly
from .models import Embed


def get_embed(url, max_width=None):
    # Check database
    try:
        return Embed.objects.get(url=url, max_width=max_width)
    except Embed.DoesNotExist:
        pass

    # Call embedly API
    client = Embedly(key=settings.EMBEDLY_KEY)
    if max_width is not None:
        oembed = client.oembed(url, maxwidth=max_width, better=False)
    else:
        oembed = client.oembed(url, better=False)

    # Check for error
    if oembed.error:
        return None

    # Save result to database
    row, created = Embed.objects.get_or_create(url=url, max_width=max_width,
                defaults={'type': oembed.type, 'title': oembed.title, 'thumbnail_url': oembed.thumbnail_url, 'width': oembed.width, 'height': oembed.height})

    if oembed.type == 'photo':
        html = '<img src="%s" />' % (oembed.url, )
    else:
        html = oembed.html

    if html:
        row.html = html
        row.last_updated = datetime.now()
        row.save()

    # Return new embed
    return row