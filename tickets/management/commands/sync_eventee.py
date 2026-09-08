from django.core.management.base import BaseCommand, CommandError

from tickets.models import Event
from tickets.services.eventee_service import EventeeService


class Command(BaseCommand):
    help = "Sync all tickets of an event to Eventee, or show a reconcile report."

    def add_arguments(self, parser):
        parser.add_argument("event_id", type=int)
        parser.add_argument("--reconcile", action="store_true",
                            help="Show reconcile report only (read-only).")

    def handle(self, *args, **options):
        try:
            event = Event.objects.get(pk=options["event_id"])
        except Event.DoesNotExist:
            raise CommandError(f"Event {options['event_id']} not found")

        svc = EventeeService(event=event)
        if options["reconcile"]:
            result = svc.reconcile(event)
            if not result["ok"]:
                raise CommandError(f"Reconcile failed: {result.get('detail')}")
            self.stdout.write(
                f"only_in_eventee={len(result['only_in_eventee'])} "
                f"missing_in_eventee={len(result['missing_in_eventee'])} "
                f"cancelled_present={len(result['cancelled_present'])}"
            )
            return

        result = svc.sync_event(event)
        self.stdout.write(
            f"total={result['total']} done={result['done']} failed={result['failed']}"
        )
