#!/usr/bin/env python3

"""
Pošte Srpske calculator destination availability checker.

Website:
    https://www.postesrpske.com/calc/kalkulator.html

Process:

1. Open the English calculator.
2. Select "International traffic" for Type of service.
3. Select "Stationery (Postcard)" for Service.
4. Read ALL destinations from the Destination information dropdown.
5. For every destination:
       - select the destination
       - enter weight 10
       - click Calculate
       - check whether "Price Stationery (postcard)" appears
6. Write one output file:
       results.txt

Availability rule:

    "Price Stationery (postcard)" found
        = AVAILABLE

    "Price Stationery (postcard)" not found
        = SUSPENDED

The output file intentionally contains no timestamp so that
changedetection.io only detects actual changes.
"""

from pathlib import Path
import sys
import time

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ================================================================
# SETTINGS
# ================================================================

URL = "https://www.postesrpske.com/calc/kalkulator.html"

OUTPUT_FILE = Path("results.txt")

TYPE_OF_SERVICE = "International traffic"

SERVICE = "Stationery (Postcard)"

WEIGHT = "10"

PRICE_TEXT = "Price Stationery (postcard)"

TIMEOUT_MS = 30000

CALCULATION_WAIT_MS = 2000


# ================================================================
# TEXT HELPERS
# ================================================================

def clean_text(value):
    """Normalize whitespace."""

    if value is None:
        return ""

    return " ".join(value.split()).strip()


# ================================================================
# DEBUGGING
# ================================================================

def print_dropdown_information(page):
    """
    Print every SELECT and its options to the GitHub Actions log.
    """

    print()
    print("=" * 70)
    print("CURRENT DROPDOWNS")
    print("=" * 70)

    selects = page.locator("select")

    print(
        f"Number of SELECT elements: {selects.count()}"
    )

    for index in range(selects.count()):

        select = selects.nth(index)

        print()
        print(
            f"SELECT #{index}"
        )

        print(
            f"  id: {select.get_attribute('id')}"
        )

        print(
            f"  name: {select.get_attribute('name')}"
        )

        options = select.locator("option")

        print(
            f"  options: {options.count()}"
        )

        for option_index in range(
            options.count()
        ):

            option = options.nth(
                option_index
            )

            text = clean_text(
                option.inner_text()
            )

            value = option.get_attribute(
                "value"
            )

            print(
                f"    {option_index}: "
                f"text={text!r}, "
                f"value={value!r}"
            )

    print()
    print("=" * 70)
    print()


# ================================================================
# FIND SELECT
# ================================================================

def find_select_containing_option(
    page,
    option_text,
):
    """
    Find a SELECT containing an option whose visible text matches
    option_text.
    """

    wanted = clean_text(
        option_text
    ).casefold()

    selects = page.locator("select")

    for select_index in range(
        selects.count()
    ):

        select = selects.nth(
            select_index
        )

        options = select.locator(
            "option"
        )

        for option_index in range(
            options.count()
        ):

            option = options.nth(
                option_index
            )

            text = clean_text(
                option.inner_text()
            )

            if text.casefold() == wanted:
                return select

    return None


def select_option_by_visible_text(
    select,
    wanted_text,
):
    """
    Select an option using its visible text.
    """

    wanted = clean_text(
        wanted_text
    ).casefold()

    options = select.locator(
        "option"
    )

    for option_index in range(
        options.count()
    ):

        option = options.nth(
            option_index
        )

        text = clean_text(
            option.inner_text()
        )

        if text.casefold() == wanted:

            value = option.get_attribute(
                "value"
            )

            if value is not None:

                select.select_option(
                    value=value
                )

            else:

                select.select_option(
                    label=text
                )

            return

    raise RuntimeError(
        f'Could not find option "{wanted_text}".'
    )


# ================================================================
# WAIT FOR CALCULATOR
# ================================================================

def wait_for_dynamic_dropdowns(page):
    """
    Wait until the Service option appears.

    IMPORTANT:
    Playwright Python requires the JavaScript function argument
    to be supplied using arg=.
    """

    page.wait_for_timeout(
        1000
    )

    try:

        page.wait_for_function(
            """
            expected => {
                const selects =
                    Array.from(
                        document.querySelectorAll("select")
                    );

                return selects.some(select =>
                    Array.from(
                        select.options
                    ).some(option =>
                        option.textContent
                            .trim()
                            .toLowerCase() ===
                        expected
                            .toLowerCase()
                    )
                );
            }
            """,
            arg=SERVICE,
            timeout=TIMEOUT_MS,
        )

    except PlaywrightTimeoutError:

        print_dropdown_information(
            page
        )

        raise RuntimeError(
            'The "Stationery (Postcard)" option '
            "did not appear."
        )

    page.wait_for_timeout(
        1000
    )


# ================================================================
# DESTINATION DROPDOWN
# ================================================================

def get_destination_select(page):
    """
    Find the Destination information dropdown.

    We identify it by looking for a SELECT with multiple country
    options.
    """

    selects = page.locator(
        "select"
    )

    candidates = []

    for select_index in range(
        selects.count()
    ):

        select = selects.nth(
            select_index
        )

        options = select.locator(
            "option"
        )

        option_texts = []

        for option_index in range(
            options.count()
        ):

            text = clean_text(
                options.nth(
                    option_index
                ).inner_text()
            )

            if text:
                option_texts.append(
                    text
                )

        if len(option_texts) >= 2:

            candidates.append(
                (
                    select,
                    option_texts,
                )
            )

    # Look for recognizable country names.
    country_keywords = [
        "Albania",
        "Austria",
        "Belgium",
        "Bosnia",
        "Bulgaria",
        "Croatia",
        "France",
        "Germany",
        "Greece",
        "Italy",
        "Montenegro",
        "Serbia",
        "Slovenia",
        "Switzerland",
        "United",
        "USA",
    ]

    for select, options in candidates:

        combined = " ".join(
            options
        ).casefold()

        matches = 0

        for keyword in country_keywords:

            if keyword.casefold() in combined:
                matches += 1

        if matches >= 2:
            return select

    # Fallback: dropdown with most options.
    if candidates:

        candidates.sort(
            key=lambda item: len(
                item[1]
            ),
            reverse=True,
        )

        return candidates[0][0]

    print_dropdown_information(
        page
    )

    raise RuntimeError(
        "Could not find Destination information dropdown."
    )


def get_all_destinations(
    destination_select,
):
    """
    Return every destination from the dropdown.

    Placeholder options are ignored.
    """

    destinations = []

    options = destination_select.locator(
        "option"
    )

    placeholders = {
        "select",
        "[select]",
        "select destination",
        "destination",
        "choose",
        "please select",
    }

    for option_index in range(
        options.count()
    ):

        option = options.nth(
            option_index
        )

        text = clean_text(
            option.inner_text()
        )

        if not text:
            continue

        value = option.get_attribute(
            "value"
        )

        if text.casefold() in placeholders:
            continue

        if value is not None and not value.strip():
            continue

        destinations.append(
            {
                "text": text,
                "value": value,
            }
        )

    # Remove duplicates while preserving order.
    unique = []

    seen = set()

    for destination in destinations:

        key = destination[
            "text"
        ].casefold()

        if key not in seen:

            seen.add(key)

            unique.append(
                destination
            )

    return unique


# ================================================================
# WEIGHT
# ================================================================

def find_weight_input(page):
    """
    Find the Weight input field.
    """

    # First try labels.
    labels = page.locator(
        "label"
    )

    for label_index in range(
        labels.count()
    ):

        label = labels.nth(
            label_index
        )

        label_text = clean_text(
            label.inner_text()
        ).casefold()

        if "weight" not in label_text:
            continue

        label_for = label.get_attribute(
            "for"
        )

        if label_for:

            candidate = page.locator(
                f"#{label_for}"
            )

            if candidate.count() > 0:
                return candidate

        candidate = label.locator(
            "xpath=following::input[1]"
        )

        if candidate.count() > 0:
            return candidate.first

    # Then inspect input attributes.
    inputs = page.locator(
        "input"
    )

    for input_index in range(
        inputs.count()
    ):

        input_element = inputs.nth(
            input_index
        )

        identifier = " ".join(
            [
                input_element.get_attribute(
                    "id"
                ) or "",
                input_element.get_attribute(
                    "name"
                ) or "",
                input_element.get_attribute(
                    "placeholder"
                ) or "",
                input_element.get_attribute(
                    "aria-label"
                ) or "",
            ]
        ).casefold()

        if "weight" in identifier:
            return input_element

    # Final fallback.
    for input_index in range(
        inputs.count()
    ):

        input_element = inputs.nth(
            input_index
        )

        if not input_element.is_visible():
            continue

        input_type = (
            input_element.get_attribute(
                "type"
            )
            or "text"
        ).casefold()

        if input_type in {
            "number",
            "text",
        }:

            return input_element

    raise RuntimeError(
        "Could not find Weight input."
    )


# ================================================================
# CALCULATE BUTTON
# ================================================================

def find_calculate_button(page):
    """
    Find the Calculate button.
    """

    buttons = page.locator(
        "button, input[type='button'], "
        "input[type='submit']"
    )

    for button_index in range(
        buttons.count()
    ):

        button = buttons.nth(
            button_index
        )

        if not button.is_visible():
            continue

        tag_name = button.evaluate(
            "(element) => "
            "element.tagName.toLowerCase()"
        )

        if tag_name == "button":

            text = clean_text(
                button.inner_text()
            )

        else:

            text = clean_text(
                button.get_attribute(
                    "value"
                )
                or ""
            )

        if text.casefold() == "calculate":

            return button

    raise RuntimeError(
        'Could not find "Calculate" button.'
    )


# ================================================================
# PRICE CHECK
# ================================================================

def page_contains_price(page):
    """
    Determine whether the expected postcard price text is present.
    """

    body_text = clean_text(
        page.locator(
            "body"
        ).inner_text()
    ).casefold()

    expected = clean_text(
        PRICE_TEXT
    ).casefold()

    return expected in body_text


# ================================================================
# CHECK DESTINATION
# ================================================================

def check_destination(
    page,
    destination_select,
    destination,
    weight_input,
    calculate_button,
):
    """
    Check one destination.

    True  = AVAILABLE
    False = SUSPENDED
    """

    name = destination[
        "text"
    ]

    print(
        f"Checking: {name}"
    )

    # ------------------------------------------------------------
    # Select destination.
    # ------------------------------------------------------------

    value = destination[
        "value"
    ]

    if value is not None:

        try:

            destination_select.select_option(
                value=value
            )

        except Exception:

            select_option_by_visible_text(
                destination_select,
                name,
            )

    else:

        select_option_by_visible_text(
            destination_select,
            name,
        )

    # ------------------------------------------------------------
    # Enter weight 10.
    # ------------------------------------------------------------

    weight_input.fill(
        WEIGHT
    )

    # ------------------------------------------------------------
    # Click Calculate.
    # ------------------------------------------------------------

    calculate_button.click()

    # Give JavaScript time to update.
    page.wait_for_timeout(
        CALCULATION_WAIT_MS
    )

    # ------------------------------------------------------------
    # Check for expected price text.
    # ------------------------------------------------------------

    available = page_contains_price(
        page
    )

    if available:

        print(
            f"  -> AVAILABLE"
        )

    else:

        print(
            f"  -> SUSPENDED"
        )

    return available


# ================================================================
# WRITE RESULTS
# ================================================================

def write_results(
    all_destinations,
    available_destinations,
    suspended_destinations,
):
    """
    Write the single results.txt file.

    No timestamp is written.
    """

    lines = []

    lines.append(
        "POŠTE SRPSKE - STATIONERY (POSTCARD) DESTINATION CHECK"
    )

    lines.append(
        "=" * 70
    )

    lines.append("")

    lines.append(
        "Website: https://www.postesrpske.com/calc/kalkulator.html"
    )

    lines.append(
        "Type of service: International traffic"
    )

    lines.append(
        "Service: Stationery (Postcard)"
    )

    lines.append(
        "Weight: 10"
    )

    lines.append("")

    # ============================================================
    # ALL DESTINATIONS
    # ============================================================

    lines.append(
        "1) ALL DESTINATIONS"
    )

    lines.append(
        "-" * 70
    )

    for index, destination in enumerate(
        all_destinations,
        start=1,
    ):

        lines.append(
            f"{index}. {destination}"
        )

    lines.append("")

    lines.append(
        f"Total destinations: "
        f"{len(all_destinations)}"
    )

    lines.append("")

    # ============================================================
    # AVAILABLE
    # ============================================================

    lines.append(
        "2) AVAILABLE DESTINATIONS"
    )

    lines.append(
        "-" * 70
    )

    for index, destination in enumerate(
        available_destinations,
        start=1,
    ):

        lines.append(
            f"{index}. {destination}"
        )

    lines.append("")

    lines.append(
        f"Total available: "
        f"{len(available_destinations)}"
    )

    lines.append("")

    # ============================================================
    # SUSPENDED
    # ============================================================

    lines.append(
        "3) SUSPENDED DESTINATIONS"
    )

    lines.append(
        "-" * 70
    )

    for index, destination in enumerate(
        suspended_destinations,
        start=1,
    ):

        lines.append(
            f"{index}. {destination}"
        )

    lines.append("")

    lines.append(
        f"Total suspended: "
        f"{len(suspended_destinations)}"
    )

    lines.append("")

    # ============================================================
    # RULE
    # ============================================================

    lines.append(
        "CHECK RULE"
    )

    lines.append(
        "-" * 70
    )

    lines.append(
        'Available = "Price Stationery (postcard)" '
        "was returned."
    )

    lines.append(
        'Suspended = "Price Stationery (postcard)" '
        "was not returned."
    )

    lines.append("")

    OUTPUT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 70)
    print(
        "POŠTE SRPSKE CALCULATOR CHECK"
    )
    print("=" * 70)

    print()

    print(
        f"URL: {URL}"
    )

    print(
        f"Type of service: {TYPE_OF_SERVICE}"
    )

    print(
        f"Service: {SERVICE}"
    )

    print(
        f"Weight: {WEIGHT}"
    )

    print()

    all_destinations = []

    available_destinations = []

    suspended_destinations = []

    # ============================================================
    # START PLAYWRIGHT
    # ============================================================

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 1000,
            }
        )

        page.set_default_timeout(
            TIMEOUT_MS
        )

        try:

            # ====================================================
            # STEP 1
            # ====================================================

            print(
                "STEP 1: Opening calculator..."
            )

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_MS,
            )

            page.wait_for_timeout(
                1500
            )

            # ====================================================
            # STEP 2
            # ====================================================

            print(
                'STEP 2: Selecting "International traffic"...'
            )

            type_select = (
                find_select_containing_option(
                    page,
                    TYPE_OF_SERVICE,
                )
            )

            if type_select is None:

                print_dropdown_information(
                    page
                )

                raise RuntimeError(
                    'Could not find "International traffic".'
                )

            select_option_by_visible_text(
                type_select,
                TYPE_OF_SERVICE,
            )

            page.wait_for_timeout(
                1000
            )

            # ====================================================
            # STEP 3
            # ====================================================

            print(
                'STEP 3: Selecting "Stationery (Postcard)"...'
            )

            service_select = (
                find_select_containing_option(
                    page,
                    SERVICE,
                )
            )

            if service_select is None:

                print_dropdown_information(
                    page
                )

                raise RuntimeError(
                    'Could not find "Stationery (Postcard)".'
                )

            select_option_by_visible_text(
                service_select,
                SERVICE,
            )

            # ====================================================
            # WAIT FOR DESTINATION LIST
            # ====================================================

            print(
                "Waiting for destination list..."
            )

            wait_for_dynamic_dropdowns(
                page
            )

            # ====================================================
            # STEP 4
            # ====================================================

            print(
                'STEP 4: Reading "Destination information"...'
            )

            destination_select = (
                get_destination_select(
                    page
                )
            )

            destinations = (
                get_all_destinations(
                    destination_select
                )
            )

            if not destinations:

                print_dropdown_information(
                    page
                )

                raise RuntimeError(
                    "No destinations were found."
                )

            all_destinations = [
                destination["text"]
                for destination in destinations
            ]

            print()

            print(
                f"Found {len(destinations)} destinations."
            )

            print()

            # ====================================================
            # WEIGHT
            # ====================================================

            print(
                "Finding Weight input..."
            )

            weight_input = (
                find_weight_input(
                    page
                )
            )

            # ====================================================
            # CALCULATE
            # ====================================================

            print(
                'Finding "Calculate" button...'
            )

            calculate_button = (
                find_calculate_button(
                    page
                )
            )

            # ====================================================
            # STEP 5
            # ====================================================

            print()

            print(
                "STEP 5: Checking destinations..."
            )

            print()

            for number, destination in enumerate(
                destinations,
                start=1,
            ):

                print(
                    f"[{number}/{len(destinations)}]"
                )

                try:

                    available = (
                        check_destination(
                            page,
                            destination_select,
                            destination,
                            weight_input,
                            calculate_button,
                        )
                    )

                    if available:

                        available_destinations.append(
                            destination["text"]
                        )

                    else:

                        suspended_destinations.append(
                            destination["text"]
                        )

                except Exception as error:

                    print(
                        f"  ERROR: {error}"
                    )

                    print(
                        "  -> SUSPENDED"
                    )

                    suspended_destinations.append(
                        destination["text"]
                    )

                # Small pause between requests.
                time.sleep(
                    0.5
                )

            # ====================================================
            # STEP 6
            # ====================================================

            print()

            print(
                "STEP 6: Writing results.txt..."
            )

            write_results(
                all_destinations,
                available_destinations,
                suspended_destinations,
            )

            # ====================================================
            # SUMMARY
            # ====================================================

            print()

            print("=" * 70)

            print(
                "FINISHED"
            )

            print("=" * 70)

            print()

            print(
                f"Total destinations: "
                f"{len(all_destinations)}"
            )

            print(
                f"Available: "
                f"{len(available_destinations)}"
            )

            print(
                f"Suspended: "
                f"{len(suspended_destinations)}"
            )

            print()

            print(
                f"Output: "
                f"{OUTPUT_FILE.resolve()}"
            )

            print()

        finally:

            browser.close()


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Stopped by user."
        )

        sys.exit(130)

    except Exception as error:

        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()

        print(
            str(error)
        )

        print()

        sys.exit(1)
