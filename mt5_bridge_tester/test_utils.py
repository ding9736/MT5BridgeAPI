# test_utils.py

import pandas as pd


def record_result(
    suite_name: str,
    case_name: str,
    response: dict,
    success_condition: bool = None,
    detail_on_pass: str = "",
    detail_on_fail: str = "",
):
    """
    A helper function to uniformly generate and record test results.

    :param suite_name: The name of the test suite.
    :param case_name: The name of the test case.
    :param response: The raw response dictionary from the APIClient.
    :param success_condition: Optional, a boolean value to override the default success check (response.get("status") == "success").
    :param detail_on_pass: Optional, custom detail to display on success.
    :param detail_on_fail: Optional, custom detail to display on failure.
    :return: A test result dictionary in a standard format.
    """
    if success_condition is None:
        is_success = response.get("status") == "success"
    else:
        is_success = success_condition

    status = "PASS" if is_success else "FAIL"

    if is_success:
        detail = (
            detail_on_pass
            if detail_on_pass
            else f"Success: {response.get('data', 'OK')}"
        )
    else:
        detail = (
            detail_on_fail
            if detail_on_fail
            else f"Failure: {response.get('message', 'No message')}"
        )

    return {
        "Suite": suite_name,
        "Case": case_name,
        "Status": status,
        "End-to-End Duration (ms)": response.get("end_to_end_duration_ms", "N/A"),
        "Details": detail,
    }


def record_df_result(
    suite_name: str,
    case_name: str,
    df: pd.DataFrame,
    duration_ms: str,
    success_condition: bool,
    detail_on_pass: str,
    detail_on_fail: str,
):
    """A helper function specifically for recording test results of functions that return a DataFrame."""
    status = "PASS" if success_condition else "FAIL"
    detail = detail_on_pass if success_condition else detail_on_fail

    return {
        "Suite": suite_name,
        "Case": case_name,
        "Status": status,
        "End-to-End Duration (ms)": duration_ms,
        "Details": detail,
    }
