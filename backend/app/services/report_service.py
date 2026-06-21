import re
from pathlib import Path
from xml.etree import ElementTree


def parse_junit_xml(xml_path: str) -> dict:
    tree = ElementTree.parse(xml_path)
    root = tree.getroot()

    testsuite = root if root.tag == "testsuite" else root.find("testsuite")
    if testsuite is None:
        testsuite_elements = root.findall("testsuite")
        if not testsuite_elements:
            return {"tests": 0, "passed": 0, "errors": 0, "failures": 0, "skipped": 0, "time": "0", "details": []}
        return _parse_suites(testsuite_elements)

    return _parse_single_suite(testsuite)


def _parse_suites(suites) -> dict:
    all_details = []
    total = {"tests": 0, "passed": 0, "errors": 0, "failures": 0, "skipped": 0, "time": 0.0}

    for suite in suites:
        suite_data = _parse_single_suite(suite)
        total["tests"] += suite_data["tests"]
        total["passed"] += suite_data["passed"]
        total["errors"] += suite_data["errors"]
        total["failures"] += suite_data["failures"]
        total["skipped"] += suite_data["skipped"]
        total["time"] += float(suite_data.get("time", 0))
        all_details.extend(suite_data["details"])

    total["time"] = f"{total['time']:.3f}"
    total["details"] = all_details
    return total


def _parse_single_suite(testsuite) -> dict:
    errors = int(testsuite.get("errors", 0))
    failures = int(testsuite.get("failures", 0))
    skipped = int(testsuite.get("skipped", 0))
    tests = int(testsuite.get("tests", 0))
    run_time = testsuite.get("time", "0")
    passed = tests - errors - failures - skipped

    details = []
    for testcase in testsuite.findall("testcase"):
        class_name = testcase.get("classname", "")
        name = testcase.get("name", "")
        case_time = testcase.get("time", "0")

        failure_el = testcase.find("failure")
        error_el = testcase.find("error")
        skipped_el = testcase.find("skipped")

        system_out_el = testcase.find("system-out")
        system_err_el = testcase.find("system-err")

        system_out = system_out_el.text or "" if system_out_el is not None else ""
        system_err = system_err_el.text or "" if system_err_el is not None else ""

        if failure_el is not None:
            result = "failed"
            failure_out = failure_el.text or ""
            error_out = ""
            skipped_message = ""
        elif error_el is not None:
            result = "error"
            failure_out = ""
            error_out = error_el.text or ""
            skipped_message = ""
        elif skipped_el is not None:
            result = "skipped"
            failure_out = ""
            error_out = ""
            skipped_message = skipped_el.get("message", "")
        else:
            result = "passed"
            failure_out = ""
            error_out = ""
            skipped_message = ""

        details.append({
            "class_name": class_name,
            "name": name,
            "run_time": case_time,
            "result": result,
            "system_out": system_out,
            "system_err": system_err,
            "failure_out": failure_out,
            "error_out": error_out,
            "skipped_message": skipped_message,
        })

    return {
        "tests": tests,
        "passed": passed,
        "errors": errors,
        "failures": failures,
        "skipped": skipped,
        "time": run_time,
        "details": details,
    }
