from io import StringIO

from django.core.management import call_command


def test_delete_desc_clears_solicitation_flag(solicited_issue):
    call_command(
        "old_anthologies",
        "--series",
        str(solicited_issue.series.id),
        "--delete-desc",
        stdout=StringIO(),
    )

    solicited_issue.refresh_from_db()
    assert solicited_issue.desc == ""
    assert solicited_issue.desc_is_solicitation is False
