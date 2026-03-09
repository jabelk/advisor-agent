"""Unit tests for sfdc_tasks.py (019-sfdc-sandbox)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest

from finance_agent.sandbox.models import ADVISOR_AGENT_TAG
from finance_agent.sandbox.sfdc_tasks import (
    resolve_contact,
    create_task,
    list_tasks,
    complete_task,
    get_task_summary,
    log_activity,
    get_outreach_queue,
    create_outreach_tasks,
)


@pytest.fixture
def sf():
    """Create a mock Salesforce client."""
    mock = MagicMock()
    mock.sf_instance = "test.salesforce.com"
    mock.query.return_value = {"records": []}
    mock.Task.create.return_value = {"id": "00Txx000001AAAA"}
    return mock


# ---------------------------------------------------------------------------
# resolve_contact
# ---------------------------------------------------------------------------


class TestResolveContact:
    def test_single_match(self, sf):
        sf.query.return_value = {
            "records": [
                {"Id": "003xx000001AAAA", "FirstName": "Jordan", "LastName": "McElroy"},
            ],
        }

        result = resolve_contact(sf, "Jordan")

        assert len(result) == 1
        assert result[0]["id"] == "003xx000001AAAA"
        assert result[0]["name"] == "Jordan McElroy"

    def test_multiple_matches(self, sf):
        sf.query.return_value = {
            "records": [
                {"Id": "003xx000001AAAA", "FirstName": "Jane", "LastName": "Smith"},
                {"Id": "003xx000001BBBB", "FirstName": "John", "LastName": "Smith"},
            ],
        }

        result = resolve_contact(sf, "Smith")

        assert len(result) == 2
        assert result[0]["name"] == "Jane Smith"
        assert result[1]["name"] == "John Smith"

    def test_no_matches(self, sf):
        sf.query.return_value = {"records": []}

        result = resolve_contact(sf, "Nonexistent")

        assert result == []

    def test_soql_escaping(self, sf):
        """Single quotes in name should be escaped in the SOQL query."""
        sf.query.return_value = {"records": []}

        resolve_contact(sf, "O'Brien")

        soql = sf.query.call_args[0][0]
        assert "O\\'Brien" in soql
        assert "O'Brien" not in soql

    def test_missing_first_name(self, sf):
        """Contact with no FirstName should still produce a clean name."""
        sf.query.return_value = {
            "records": [
                {"Id": "003xx000001CCCC", "FirstName": None, "LastName": "Solo"},
            ],
        }

        result = resolve_contact(sf, "Solo")

        assert result[0]["name"] == "Solo"


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


class TestCreateTask:
    def test_default_due_date(self, sf):
        """When due_date is None, defaults to today + 7 days."""
        result = create_task(sf, "003xx000001AAAA", "Follow up with client")

        expected_due = (date.today() + timedelta(days=7)).isoformat()
        assert result["due_date"] == expected_due
        assert result["status"] == "Not Started"
        assert result["priority"] == "Normal"
        assert result["task_id"] == "00Txx000001AAAA"
        assert result["subject"] == "Follow up with client"
        assert result["client_id"] == "003xx000001AAAA"

        # Verify the data sent to Salesforce
        task_data = sf.Task.create.call_args[0][0]
        assert task_data["ActivityDate"] == expected_due
        assert task_data["WhoId"] == "003xx000001AAAA"
        assert task_data["Status"] == "Not Started"

    def test_explicit_due_date_and_priority(self, sf):
        """Explicit due_date and priority are passed through."""
        result = create_task(
            sf,
            "003xx000001BBBB",
            "Quarterly review",
            due_date="2026-04-15",
            priority="High",
        )

        assert result["due_date"] == "2026-04-15"
        assert result["priority"] == "High"

        task_data = sf.Task.create.call_args[0][0]
        assert task_data["ActivityDate"] == "2026-04-15"
        assert task_data["Priority"] == "High"

    def test_advisor_agent_tag_in_description(self, sf):
        """Task description should contain the [advisor-agent] tag."""
        create_task(sf, "003xx000001AAAA", "Test task")

        task_data = sf.Task.create.call_args[0][0]
        assert ADVISOR_AGENT_TAG in task_data["Description"]

    def test_returns_task_id_from_salesforce(self, sf):
        """Task ID comes from the Salesforce create response."""
        sf.Task.create.return_value = {"id": "00Txx000001ZZZZ"}

        result = create_task(sf, "003xx000001AAAA", "Test")

        assert result["task_id"] == "00Txx000001ZZZZ"


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    def test_returns_tasks_with_all_fields(self, sf):
        """Verify all expected fields are present in returned task dicts."""
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"

        # First query: tasks
        # Second query: contact name lookup
        sf.query.side_effect = [
            {
                "records": [
                    {
                        "Id": "00Txx000001AAAA",
                        "Subject": "Call client",
                        "WhoId": "003xx000001AAAA",
                        "ActivityDate": yesterday,
                        "Priority": "High",
                        "Status": "Not Started",
                        "Description": tag,
                    },
                    {
                        "Id": "00Txx000001BBBB",
                        "Subject": "Send email",
                        "WhoId": "003xx000001BBBB",
                        "ActivityDate": today,
                        "Priority": "Normal",
                        "Status": "In Progress",
                        "Description": tag,
                    },
                ],
            },
            {
                "records": [
                    {"Id": "003xx000001AAAA", "FirstName": "Jane", "LastName": "Doe"},
                    {"Id": "003xx000001BBBB", "FirstName": "John", "LastName": "Smith"},
                ],
            },
        ]

        result = list_tasks(sf)

        assert len(result) == 2
        assert result[0]["task_id"] == "00Txx000001AAAA"
        assert result[0]["subject"] == "Call client"
        assert result[0]["client_name"] == "Jane Doe"
        assert result[0]["client_id"] == "003xx000001AAAA"
        assert result[0]["due_date"] == yesterday
        assert result[0]["priority"] == "High"
        assert result[0]["status"] == "Not Started"
        assert result[0]["overdue"] is True  # yesterday is overdue

        assert result[1]["overdue"] is False  # today is not overdue

    def test_filters_by_client_name(self, sf):
        """When client_name is provided, resolves to IDs and filters."""
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"
        # First call: resolve_contact query
        # Second call: task list query
        # Third call: contact name bulk lookup
        sf.query.side_effect = [
            {
                "records": [
                    {"Id": "003xx000001AAAA", "FirstName": "Jane", "LastName": "Doe"},
                ],
            },
            {
                "records": [
                    {
                        "Id": "00Txx000001AAAA",
                        "Subject": "Follow up",
                        "WhoId": "003xx000001AAAA",
                        "ActivityDate": date.today().isoformat(),
                        "Priority": "Normal",
                        "Status": "Not Started",
                        "Description": tag,
                    },
                ],
            },
            {
                "records": [
                    {"Id": "003xx000001AAAA", "FirstName": "Jane", "LastName": "Doe"},
                ],
            },
        ]

        result = list_tasks(sf, client_name="Doe")

        assert len(result) == 1
        assert result[0]["client_name"] == "Jane Doe"

        # Verify the task query contains WhoId IN clause
        task_soql = sf.query.call_args_list[1][0][0]
        assert "WhoId IN" in task_soql
        assert "003xx000001AAAA" in task_soql

    def test_client_name_not_found_returns_empty(self, sf):
        """If client_name resolves to no contacts, return empty list."""
        sf.query.return_value = {"records": []}

        result = list_tasks(sf, client_name="Nobody")

        assert result == []

    def test_overdue_only_filter(self, sf):
        """overdue_only adds ActivityDate < today condition."""
        sf.query.side_effect = [
            {"records": []},
        ]

        list_tasks(sf, overdue_only=True)

        soql = sf.query.call_args[0][0]
        assert f"ActivityDate < {date.today().isoformat()}" in soql

    def test_empty_results(self, sf):
        sf.query.return_value = {"records": []}

        result = list_tasks(sf)

        assert result == []

    def test_overdue_flag_set_correctly(self, sf):
        """Tasks with due_date before today are marked overdue=True."""
        past_date = (date.today() - timedelta(days=3)).isoformat()
        future_date = (date.today() + timedelta(days=3)).isoformat()
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"

        sf.query.side_effect = [
            {
                "records": [
                    {
                        "Id": "00T1",
                        "Subject": "Past task",
                        "WhoId": "003A",
                        "ActivityDate": past_date,
                        "Priority": "Normal",
                        "Status": "Not Started",
                        "Description": tag,
                    },
                    {
                        "Id": "00T2",
                        "Subject": "Future task",
                        "WhoId": "003B",
                        "ActivityDate": future_date,
                        "Priority": "Normal",
                        "Status": "Not Started",
                        "Description": tag,
                    },
                ],
            },
            {
                "records": [
                    {"Id": "003A", "FirstName": "A", "LastName": "Client"},
                    {"Id": "003B", "FirstName": "B", "LastName": "Client"},
                ],
            },
        ]

        result = list_tasks(sf)

        assert result[0]["overdue"] is True
        assert result[1]["overdue"] is False


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------


class TestCompleteTask:
    def test_single_match_completed(self, sf):
        """Single open match is completed and details returned."""
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"
        sf.query.side_effect = [
            {"records": []},  # completed check
            {
                "records": [
                    {
                        "Id": "00Txx000001AAAA",
                        "Subject": "Call client",
                        "WhoId": "003xx000001AAAA",
                        "ActivityDate": "2026-03-15",
                        "Priority": "Normal",
                        "Description": tag,
                    },
                ],
            },  # open check
            {
                "records": [
                    {"Id": "003xx000001AAAA", "FirstName": "Jane", "LastName": "Doe"},
                ],
            },  # _resolve_contact_name
        ]

        result = complete_task(sf, "Call")

        assert result["status"] == "completed"
        assert result["task_id"] == "00Txx000001AAAA"
        assert result["subject"] == "Call client"
        assert result["client_name"] == "Jane Doe"
        assert result["due_date"] == "2026-03-15"
        assert result["completed_date"] == date.today().isoformat()

        # Verify task was updated to Completed
        sf.Task.update.assert_called_once_with(
            "00Txx000001AAAA", {"Status": "Completed"}
        )

    def test_multiple_matches_ambiguous(self, sf):
        """Multiple open matches return 'ambiguous' with match list."""
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"
        sf.query.side_effect = [
            {"records": []},  # completed check
            {
                "records": [
                    {
                        "Id": "00T1",
                        "Subject": "Call Jane",
                        "WhoId": "003A",
                        "ActivityDate": "2026-03-10",
                        "Priority": "Normal",
                        "Description": tag,
                    },
                    {
                        "Id": "00T2",
                        "Subject": "Call John",
                        "WhoId": "003B",
                        "ActivityDate": "2026-03-12",
                        "Priority": "High",
                        "Description": tag,
                    },
                ],
            },  # open check
            # _resolve_contact_name calls for each match
            {"records": [{"Id": "003A", "FirstName": "Jane", "LastName": "Doe"}]},
            {"records": [{"Id": "003B", "FirstName": "John", "LastName": "Smith"}]},
        ]

        result = complete_task(sf, "Call")

        assert result["status"] == "ambiguous"
        assert len(result["matches"]) == 2
        assert result["matches"][0]["task_id"] == "00T1"
        assert result["matches"][0]["subject"] == "Call Jane"
        assert result["matches"][1]["task_id"] == "00T2"

        # Should NOT update any task
        sf.Task.update.assert_not_called()

    def test_no_matches_not_found(self, sf):
        """No matches at all returns 'not_found'."""
        sf.query.side_effect = [
            {"records": []},  # completed check
            {"records": []},  # open check
        ]

        result = complete_task(sf, "Nonexistent")

        assert result["status"] == "not_found"
        sf.Task.update.assert_not_called()

    def test_already_completed(self, sf):
        """Match only in completed tasks returns 'already_completed'."""
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"
        sf.query.side_effect = [
            {
                "records": [
                    {
                        "Id": "00Txx000001DONE",
                        "Subject": "Old task",
                        "WhoId": "003xx000001AAAA",
                        "Status": "Completed",
                        "Description": tag,
                    },
                ],
            },  # completed check
            {"records": []},  # open check — empty
        ]

        result = complete_task(sf, "Old task")

        assert result["status"] == "already_completed"
        assert result["task_id"] == "00Txx000001DONE"
        assert result["subject"] == "Old task"
        sf.Task.update.assert_not_called()


# ---------------------------------------------------------------------------
# get_task_summary
# ---------------------------------------------------------------------------


class TestGetTaskSummary:
    def test_counts_categories(self, sf):
        """Verify counts for overdue, due_today, due_this_week, total_open."""
        today = date.today()
        yesterday = (today - timedelta(days=1)).isoformat()
        today_str = today.isoformat()
        tomorrow = (today + timedelta(days=1)).isoformat()
        far_future = (today + timedelta(days=30)).isoformat()
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"

        sf.query.return_value = {
            "records": [
                {"Id": "00T1", "ActivityDate": yesterday, "Description": tag},      # overdue
                {"Id": "00T2", "ActivityDate": today_str, "Description": tag},       # due_today + due_this_week
                {"Id": "00T3", "ActivityDate": tomorrow, "Description": tag},        # due_this_week (if within week)
                {"Id": "00T4", "ActivityDate": far_future, "Description": tag},      # none of the special counts
                {"Id": "00T5", "ActivityDate": None, "Description": tag},            # no date — counted in total only
            ],
        }

        result = get_task_summary(sf)

        assert result["total_open"] == 5
        assert result["overdue"] == 1
        assert result["due_today"] == 1
        # due_this_week includes today and possibly tomorrow depending on day of week
        assert result["due_this_week"] >= 1

    def test_empty_tasks(self, sf):
        sf.query.return_value = {"records": []}

        result = get_task_summary(sf)

        assert result["total_open"] == 0
        assert result["overdue"] == 0
        assert result["due_today"] == 0
        assert result["due_this_week"] == 0

    def test_all_overdue(self, sf):
        """All tasks with dates in the past are overdue."""
        past1 = (date.today() - timedelta(days=5)).isoformat()
        past2 = (date.today() - timedelta(days=10)).isoformat()
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"

        sf.query.return_value = {
            "records": [
                {"Id": "00T1", "ActivityDate": past1, "Description": tag},
                {"Id": "00T2", "ActivityDate": past2, "Description": tag},
            ],
        }

        result = get_task_summary(sf)

        assert result["total_open"] == 2
        assert result["overdue"] == 2
        assert result["due_today"] == 0

    def test_due_today_also_counted_in_due_this_week(self, sf):
        """A task due today should be counted in both due_today and due_this_week."""
        today_str = date.today().isoformat()
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"

        sf.query.return_value = {
            "records": [
                {"Id": "00T1", "ActivityDate": today_str, "Description": tag},
            ],
        }

        result = get_task_summary(sf)

        assert result["due_today"] == 1
        assert result["due_this_week"] == 1


# ---------------------------------------------------------------------------
# log_activity
# ---------------------------------------------------------------------------


class TestLogActivity:
    def test_call_type_maps_to_call_subtype(self, sf):
        result = log_activity(sf, "003A", "Called about portfolio", "call")

        task_data = sf.Task.create.call_args[0][0]
        assert task_data["TaskSubtype"] == "Call"
        assert task_data["Status"] == "Completed"
        assert result["activity_type"] == "call"
        assert result["status"] == "Completed"

    def test_email_type_maps_to_email_subtype(self, sf):
        log_activity(sf, "003A", "Sent quarterly report", "email")

        task_data = sf.Task.create.call_args[0][0]
        assert task_data["TaskSubtype"] == "Email"

    def test_meeting_type_no_subtype(self, sf):
        log_activity(sf, "003A", "Annual review meeting", "meeting")

        task_data = sf.Task.create.call_args[0][0]
        assert "TaskSubtype" not in task_data

    def test_other_type_no_subtype(self, sf):
        log_activity(sf, "003A", "Mailed document", "other")

        task_data = sf.Task.create.call_args[0][0]
        assert "TaskSubtype" not in task_data

    def test_future_date_raises_value_error(self, sf):
        future = (date.today() + timedelta(days=1)).isoformat()

        with pytest.raises(ValueError, match="future"):
            log_activity(sf, "003A", "Test", "call", activity_date=future)

        sf.Task.create.assert_not_called()

    def test_default_date_is_today(self, sf):
        result = log_activity(sf, "003A", "Quick call", "call")

        assert result["activity_date"] == date.today().isoformat()
        task_data = sf.Task.create.call_args[0][0]
        assert task_data["ActivityDate"] == date.today().isoformat()

    def test_explicit_past_date(self, sf):
        past = (date.today() - timedelta(days=5)).isoformat()

        result = log_activity(sf, "003A", "Old call", "call", activity_date=past)

        assert result["activity_date"] == past

    def test_advisor_agent_tag_in_description(self, sf):
        log_activity(sf, "003A", "Test", "call")

        task_data = sf.Task.create.call_args[0][0]
        assert ADVISOR_AGENT_TAG in task_data["Description"]

    def test_invalid_activity_type_raises_value_error(self, sf):
        with pytest.raises(ValueError, match="Invalid activity type"):
            log_activity(sf, "003A", "Test", "fax")

        sf.Task.create.assert_not_called()

    def test_returns_expected_fields(self, sf):
        sf.Task.create.return_value = {"id": "00Txx999"}

        result = log_activity(sf, "003A", "Check-in call", "call")

        assert result["task_id"] == "00Txx999"
        assert result["subject"] == "Check-in call"
        assert result["client_id"] == "003A"
        assert result["activity_type"] == "call"
        assert result["status"] == "Completed"


# ---------------------------------------------------------------------------
# get_outreach_queue
# ---------------------------------------------------------------------------


class TestGetOutreachQueue:
    def test_filters_by_days_since_contact(self, sf):
        """Contacts contacted within the threshold are excluded."""
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        old_date = (date.today() - timedelta(days=60)).isoformat()

        sf.query.return_value = {
            "records": [
                {
                    "Id": "003A",
                    "FirstName": "Recent",
                    "LastName": "Client",
                    "Account_Value__c": 500000,
                    "Tasks": {"records": [{"ActivityDate": recent_date}]},
                },
                {
                    "Id": "003B",
                    "FirstName": "Old",
                    "LastName": "Client",
                    "Account_Value__c": 300000,
                    "Tasks": {"records": [{"ActivityDate": old_date}]},
                },
            ],
        }

        result = get_outreach_queue(sf, days=30)

        # Only the contact not contacted in 30+ days should appear
        assert len(result) == 1
        assert result[0]["name"] == "Old Client"
        assert result[0]["days_since_contact"] == 60

    def test_filters_by_min_value(self, sf):
        """min_value appears in the SOQL WHERE clause."""
        sf.query.return_value = {"records": []}

        get_outreach_queue(sf, days=30, min_value=100000)

        soql = sf.query.call_args[0][0]
        assert "Account_Value__c >= 100000" in soql

    def test_days_zero_returns_all(self, sf):
        """days=0 should include all contacts regardless of last contact."""
        recent_date = (date.today() - timedelta(days=1)).isoformat()

        sf.query.return_value = {
            "records": [
                {
                    "Id": "003A",
                    "FirstName": "A",
                    "LastName": "Client",
                    "Account_Value__c": 200000,
                    "Tasks": {"records": [{"ActivityDate": recent_date}]},
                },
            ],
        }

        result = get_outreach_queue(sf, days=0)

        assert len(result) == 1
        assert result[0]["days_since_contact"] == 1

    def test_sorts_by_account_value_desc(self, sf):
        """SOQL should ORDER BY Account_Value__c DESC."""
        sf.query.return_value = {"records": []}

        get_outreach_queue(sf, days=30)

        soql = sf.query.call_args[0][0]
        assert "ORDER BY Account_Value__c DESC" in soql

    def test_contacts_with_no_activity(self, sf):
        """Contacts with no tasks get days_since_contact=9999."""
        sf.query.return_value = {
            "records": [
                {
                    "Id": "003A",
                    "FirstName": "Never",
                    "LastName": "Contacted",
                    "Account_Value__c": 100000,
                    "Tasks": None,
                },
            ],
        }

        result = get_outreach_queue(sf, days=30)

        assert len(result) == 1
        assert result[0]["days_since_contact"] == 9999
        assert result[0]["last_activity_date"] == ""

    def test_contacts_with_empty_tasks_records(self, sf):
        """Tasks subquery returns but with empty records list."""
        sf.query.return_value = {
            "records": [
                {
                    "Id": "003A",
                    "FirstName": "Empty",
                    "LastName": "Tasks",
                    "Account_Value__c": 50000,
                    "Tasks": {"records": []},
                },
            ],
        }

        result = get_outreach_queue(sf, days=0)

        assert len(result) == 1
        assert result[0]["days_since_contact"] == 9999


# ---------------------------------------------------------------------------
# create_outreach_tasks
# ---------------------------------------------------------------------------


class TestCreateOutreachTasks:
    def test_creates_tasks_for_contacts_without_open_tasks(self, sf):
        """Contacts with no existing open [advisor-agent] task get new tasks."""
        sf.query.return_value = {"records": []}  # no existing tasks

        contacts = [
            {
                "client_id": "003A",
                "name": "Jane Doe",
                "account_value": 500000,
                "last_activity_date": "",
                "days_since_contact": 60,
            },
            {
                "client_id": "003B",
                "name": "John Smith",
                "account_value": 300000,
                "last_activity_date": "",
                "days_since_contact": 45,
            },
        ]

        result = create_outreach_tasks(sf, contacts, days=30)

        assert result["tasks_created"] == 2
        assert result["tasks_skipped"] == 0
        assert result["skipped_reasons"] == []

        # Verify Task.create was called twice (once per contact via create_task)
        assert sf.Task.create.call_count == 2

    def test_skips_contacts_with_existing_open_tasks(self, sf):
        """Contacts with existing open [advisor-agent] tasks are skipped."""
        tag = f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI"
        # First contact: has existing task
        # Second contact: no existing task
        sf.query.side_effect = [
            {
                "records": [
                    {"Id": "00Txx000001EXIST", "Subject": "Existing follow-up", "Description": tag},
                ],
            },
            {"records": []},
        ]

        contacts = [
            {
                "client_id": "003A",
                "name": "Jane Doe",
                "account_value": 500000,
                "last_activity_date": "",
                "days_since_contact": 60,
            },
            {
                "client_id": "003B",
                "name": "John Smith",
                "account_value": 300000,
                "last_activity_date": "",
                "days_since_contact": 45,
            },
        ]

        result = create_outreach_tasks(sf, contacts, days=30)

        assert result["tasks_created"] == 1
        assert result["tasks_skipped"] == 1
        assert len(result["skipped_reasons"]) == 1
        assert result["skipped_reasons"][0]["name"] == "Jane Doe"
        assert "Existing follow-up" in result["skipped_reasons"][0]["reason"]

    def test_empty_contacts_list(self, sf):
        """Empty contacts list returns zero counts."""
        result = create_outreach_tasks(sf, [], days=30)

        assert result["tasks_created"] == 0
        assert result["tasks_skipped"] == 0
        assert result["skipped_reasons"] == []
        sf.Task.create.assert_not_called()

    def test_task_subject_contains_days_since(self, sf):
        """Created tasks should mention the actual days since contact."""
        sf.query.return_value = {"records": []}

        contacts = [
            {
                "client_id": "003A",
                "name": "Jane Doe",
                "account_value": 500000,
                "last_activity_date": "",
                "days_since_contact": 90,
            },
        ]

        create_outreach_tasks(sf, contacts, days=30)

        task_data = sf.Task.create.call_args[0][0]
        assert "90 days" in task_data["Subject"]

    def test_task_due_date_is_today(self, sf):
        """Outreach tasks are due today."""
        sf.query.return_value = {"records": []}

        contacts = [
            {
                "client_id": "003A",
                "name": "Jane Doe",
                "account_value": 500000,
                "last_activity_date": "",
                "days_since_contact": 60,
            },
        ]

        create_outreach_tasks(sf, contacts, days=30)

        task_data = sf.Task.create.call_args[0][0]
        assert task_data["ActivityDate"] == date.today().isoformat()
