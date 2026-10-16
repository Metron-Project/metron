from io import StringIO

from django.core.management import call_command


def test_delete_desc_clears_solicitation_flag(basic_issue):
    basic_issue.desc = "Solicitation text"
    basic_issue.desc_is_solicitation = True
    basic_issue.save()

    call_command(
        "old_anthologies",
        "--series",
        str(basic_issue.series.id),
        "--delete-desc",
        stdout=StringIO(),
    )

    basic_issue.refresh_from_db()
    assert basic_issue.desc == ""
    assert basic_issue.desc_is_solicitation is False
