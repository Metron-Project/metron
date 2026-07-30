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
DEFAULT_EXTREME_DAY_THRESHOLD = 100
DEFAULT_COOLDOWN_DAYS = 7
DEFAULT_ENFORCE_AFTER = 2


class Command(BaseCommand):
    help = (
        "Find accounts whose API client keeps getting rate-limited without backing off, "
        "and (with --send) email them. Without --send, only reports candidates. With "
        "--enforce, an account that's already had --enforce-after prior notices gets its "
        "API tokens revoked (or, if it has none, the account disabled) instead of another "
        "plain warning - add --send to actually do it, or leave it off to preview."
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
            help=(
                "Flag accounts with at least this many days whose throttled count "
                "reaches --single-day-threshold"
            ),
        )
        parser.add_argument(
            "--single-day-threshold",
            type=int,
            default=DEFAULT_SINGLE_DAY_THRESHOLD,
            help="A day only counts toward --min-days if its throttled count is at least this",
        )
        parser.add_argument(
            "--extreme-day-threshold",
            type=int,
            default=DEFAULT_EXTREME_DAY_THRESHOLD,
            help="Flag an account outright if any single day's throttled count reaches this",
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
        parser.add_argument(
            "--enforce",
            action="store_true",
            help=(
                "Escalate instead of warning again once an account already has "
                "--enforce-after prior notices. Combine with --send to actually revoke "
                "tokens/disable the account; without --send, only previews the action."
            ),
        )
        parser.add_argument(
            "--enforce-after",
            type=int,
            default=DEFAULT_ENFORCE_AFTER,
            help=(
                "Number of prior notices an account must already have before --enforce "
                "escalates its next one (default 2, so the 3rd notice escalates)"
            ),
        )

    def handle(self, *args, **options) -> None:
        send = options["send"]
        enforce = options["enforce"]
        cooldown_cutoff = timezone.now() - timedelta(days=options["cooldown_days"])

        offenders = find_repeat_offenders(
            lookback_days=options["lookback_days"],
            min_days=options["min_days"],
            single_day_threshold=options["single_day_threshold"],
            extreme_day_threshold=options["extreme_day_threshold"],
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

            prior_notices = ThrottleNotice.objects.filter(user=user).count()
            will_enforce = enforce and prior_notices >= options["enforce_after"]
            candidates.append((user, offender, will_enforce))

        self._print_summary(candidates, send)

        if candidates:
            send_pushover(self._pushover_message(candidates, send))

        if send:
            for user, offender, will_enforce in candidates:
                if will_enforce:
                    self._enforce_and_notify(user, offender)
                else:
                    self._notify(user, offender)

    def _print_summary(self, candidates, send: bool) -> None:
        if not candidates:
            self.stdout.write("No candidates found.")
            return

        for user, offender, will_enforce in candidates:
            if will_enforce:
                action = self._predict_enforcement_action(user)
                verb = f"Enforcing ({action})" if send else f"Would enforce ({action})"
            else:
                verb = "Emailing" if send else "Would email"
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
    def _predict_enforcement_action(user: CustomUser) -> str:
        return "revoke tokens" if user.auth_token_set.exists() else "disable account"

    @staticmethod
    def _pushover_message(candidates, send: bool) -> str:
        verb = "Emailed" if send else "Found"
        names = ", ".join(user.username for user, _, _ in candidates)
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

    @staticmethod
    def _enforce_and_notify(user: CustomUser, offender) -> None:
        # Revoke tokens if the account has any - that alone stops a token-based
        # client. Only disable the account outright once there's nothing left to
        # revoke, since disabling also blocks Basic/Session auth for this user.
        if user.auth_token_set.exists():
            user.auth_token_set.all().delete()
            account_disabled = False
        else:
            user.is_active = False
            user.save(update_fields=["is_active"])
            account_disabled = True

        context = {"user": user, "account_disabled": account_disabled}
        html_message = render_to_string("api/throttle_enforcement_email.html", context)
        text_message = render_to_string("api/throttle_enforcement_email.txt", context)
        email = EmailMultiAlternatives(
            subject="Your Metron API access has been restricted",
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
