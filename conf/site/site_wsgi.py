import os, logging
from django.core.wsgi import get_wsgi_application

logger= logging.getLogger("engine")

# Override the DJANGO SETTINGS MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.site.site_settings")

application = get_wsgi_application()

# Initialize recurring tasks.
try:
    import uwsgidecorators
    from django.core.management import call_command

    @uwsgidecorators.timer(30)
    def send_queued_mail(num):
        """Send queued mail every 30 seconds"""
        pass

    @uwsgidecorators.timer(3600)
    def savedata(num):
        """Save the data every hour"""
        pass

except ImportError:
    logger.error("uwsgidecorators not found, timers are disabled!")
