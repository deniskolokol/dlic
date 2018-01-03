from django.core.management.base import BaseCommand
from web.ws_server import run


class Command(BaseCommand):
    help = "Starts a Web Sockets server"

    def handle(self, *args, **options):
        run()
