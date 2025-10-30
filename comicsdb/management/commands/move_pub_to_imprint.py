from typing import TYPE_CHECKING

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

if TYPE_CHECKING:
    from django.db.models import QuerySet

from comicsdb.models import Attribution, Imprint, Publisher, Series


class Command(BaseCommand):
    help = "Moves publisher to imprint"

    def _delete_original(self, orig_pub: Publisher) -> None:
        """
        Deletes the original publisher.

        Args:
            orig_pub: The original Publisher object to be deleted.

        Returns:
            None
        """
        name = orig_pub.name
        num, _ = orig_pub.delete()
        if num > 0:
            self.stdout.write(self.style.SUCCESS(f"Deleted Publisher: '{name}'"))
        else:
            self.stdout.write(self.style.ERROR(f"Failed to Delete Publisher: '{name}'"))

    def _update_attribution(self, orig_pub: Publisher, imprint: Imprint) -> None:
        """
        Updates the attribution of the original publisher to the new imprint.

        Args:
            orig_pub: The original Publisher object whose attribution needs to be updated.
            imprint: The new Imprint object to which the attribution is updated.

        Returns:
            None
        """
        imprint_type = ContentType.objects.get_for_model(Imprint)
        orig_attributions: QuerySet[Attribution] = orig_pub.attribution.all()
        for attribution in orig_attributions:
            attribution.content_type = imprint_type
            attribution.object_id = imprint.pk

        res = Attribution.objects.bulk_update(orig_attributions, ["content_type", "object_id"])
        self.stdout.write(
            self.style.SUCCESS(f"Moved {res} attribution records from the publisher to imprint")
        )

    def _create_imprint(self, original: Publisher, parent: Publisher) -> Imprint:
        """
        Creates a new Imprint based on the information from the original Publisher.

        Args:
            original: The original Publisher object from which the Imprint is created.
            parent: The parent Publisher object for the new Imprint.

        Returns:
            The newly created Imprint object.
        """
        # TODO: Add image from original publisher
        imprint, create = Imprint.objects.get_or_create(
            name=original.name,
            slug=original.slug,
            desc=original.desc,
            cv_id=original.cv_id,
            publisher=parent,
            founded=original.founded,
        )
        if create:
            self.stdout.write(self.style.SUCCESS(f"Added Imprint: {imprint}"))
        else:
            self.stdout.write(self.style.WARNING(f"Retrieved Existing Imprint: {imprint}"))
        return imprint

    def _update_series(self, imprint: Imprint, series_qs) -> None:
        """
        Updates the series objects with the new imprint and publisher.

        Args:
            imprint: The new Imprint object to be assigned to the series.
            series_qs: QuerySet of series objects to be updated.

        Returns:
            None
        """
        for series in series_qs:
            series.imprint = imprint
            series.publisher = imprint.publisher
        changed = Series.objects.bulk_update(series_qs, ["imprint", "publisher"])
        self.stdout.write(self.style.SUCCESS(f"Updated {changed} series"))

    def add_arguments(self, parser):
        """
        Adds command line arguments for the move_pub_to_imprint management command.

        Args:
            parser: The parser object to which the arguments are added.

        Returns:
            None
        """
        parser.add_argument("--publisher", type=int, required=True)
        parser.add_argument("--parent", type=int, required=True)

    def handle(self, *args, **options):
        """
        Handles the process of moving a publisher to a new imprint by creating the imprint,
        updating series and attribution, and deleting the original publisher.

        Args:
            *args: Variable length argument list.
            **options: Keyword arguments.

        Returns:
            None
        """

        orig_pub = Publisher.objects.get(pk=options["publisher"])
        parent_pub = Publisher.objects.get(pk=options["parent"])

        new_imprint = self._create_imprint(orig_pub, parent_pub)
        series_qs = orig_pub.series.all()
        self._update_series(new_imprint, series_qs)
        self._update_attribution(orig_pub, new_imprint)
        # remove the original publisher
        self._delete_original(orig_pub)
