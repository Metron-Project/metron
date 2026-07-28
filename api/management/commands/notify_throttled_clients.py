from datetime import timedelta

from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from api.client_health import find_repeat_offenders
from api.models import ThrottleNotice
from users.models import CustomUser
from users.utils import send_pushover

DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_MIN_DAYS = 3
DEFAULT_SINGLE_DAY_THRESHOLD = 50
DEFAULT_COOLDOWN_DAYS = 7


class Command(BaseCommand):
    help = (
        "Find accounts whose API client keeps getting rate-limited without backing off, "
        "and (with --send) email them. Without --send, only reports candidates."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--lookback-days",
            type=int,
            default=DEFAULT_LOOKBACK_DAYS,
            help="How many trailing UTC days of throttle counters to consider",
        )
        parser.add_argument(
            "--min-days",
            type=int,
            default=DEFAULT_MIN_DAYS,
            help="Flag accounts throttled on at least this many distinct days",
        )
        parser.add_argument(
            "--single-day-threshold",
            type=int,
            default=DEFAULT_SINGLE_DAY_THRESHOLD,
            help="Flag accounts with any single day's throttled count at or above this",
        )
        parser.add_argument(
            "--cooldown-days",
            type=int,
            default=DEFAULT_COOLDOWN_DAYS,
            help="Don't re-notify an account already notified within this many days",
        )
        parser.add_argument(
            "--send",
            action="store_true",
            help="Actually send emails and record ThrottleNotice rows (default: report only)",
        )

    def handle(self, *args, **options) -> None:
        send = options["send"]
        cooldown_cutoff = timezone.now() - timedelta(days=options["cooldown_days"])

        offenders = find_repeat_offenders(
            lookback_days=options["lookback_days"],
            min_days=options["min_days"],
            single_day_threshold=options["single_day_threshold"],
        )

        candidates = []
        for offender in offenders:
            user = (
                CustomUser.objects.filter(
                    username=offender.username, is_active=True, email_confirmed=True
                )
                .exclude(email="")
                .first()
            )
            if user is None:
                continue
            if ThrottleNotice.objects.filter(user=user, sent_at__gte=cooldown_cutoff).exists():
                continue
            candidates.append((user, offender))

        self._print_summary(candidates, send)

        if candidates:
            send_pushover(self._pushover_message(candidates, send))

        if send:
            for user, offender in candidates:
                self._notify(user, offender)

    def _print_summary(self, candidates, send: bool) -> None:
        if not candidates:
            self.stdout.write("No candidates found.")
            return

        verb = "Emailing" if send else "Would email"
        for user, offender in candidates:
            self.stdout.write(
                f"{verb} {user.username} <{user.email}>: throttled on "
                f"{offender.days_throttled} day(s), {offender.total_count} total, "
                f"worst day {offender.worst_day_count}"
            )
        if not send:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(candidates)} candidate(s) found. Re-run with --send to email them."
                )
            )

    @staticmethod
    def _pushover_message(candidates, send: bool) -> str:
        verb = "Emailed" if send else "Found"
        names = ", ".join(user.username for user, _ in candidates)
        return f"{verb} {len(candidates)} throttled API client(s) on Metron: {names}"

    @staticmethod
    def _notify(user: CustomUser, offender) -> None:
        context = {"user": user}
        html_message = render_to_string("api/throttle_notice_email.html", context)
        text_message = render_to_string("api/throttle_notice_email.txt", context)
        email = EmailMultiAlternatives(
            subject="Your Metron API client is being rate-limited",
            body=text_message,
            to=[user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

        ThrottleNotice.objects.create(
            user=user,
            days_throttled=offender.days_throttled,
            total_count=offender.total_count,
            worst_day_count=offender.worst_day_count,
        )
