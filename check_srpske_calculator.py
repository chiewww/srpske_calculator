#!/usr/bin/env python3

"""
Pošte Srpske calculator destination availability checker.

Website:
    https://www.postesrpske.com/calc/kalkulator.html

The script:

1. Opens the English calculator.
2. Selects "International traffic" for Type of service.
3. Selects "Stationery (Postcard)" for Service.
4. Reads ALL destinations from the Destination information dropdown.
5. For every destination:
       - selects the destination
       - enters weight 10
       - clicks Calculate
       - checks whether "Price Stationery (postcard)" appears
6. Writes the results to:
       results.txt

IMPORTANT:
    results.txt intentionally does NOT contain a timestamp.
    This prevents changedetection.io from detecting a change every
    time the script runs when the actual results have not changed.

Requirements:
    Python 3.9+
    Playwright

Install:
    pip install -r requirements.txt

Run:
    python check_srpske_calculator.py
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

CALCULATION_WAIT_MS = 1500


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def clean_text(value):
    """Normalize whitespace in text."""
    if value is None:
        return ""

    return " ".join(value.split()).strip()


def get_select_options(page):
    """
    Return information about every SELECT element on the page.
    """

    return page.locator("select").evaluate_all(
        """
        selects => selects.map((select, index) => ({
            index: index,
            id: select.id || "",
            name: select.name || "",
            ariaLabel: select.getAttribute("aria-label") || "",
            options: Array.from(select.options).map(option => ({
                text: option.textContent.trim(),
                value: option.value
            }))
        }))
        """
    )


def print_dropdown_information(page):
    """
    Print all dropdowns to the GitHub Actions log.

    This is useful for troubleshooting if the website changes.
    """

    print()
    print("=" * 70)
    print("CURRENT DROPDOWNS")
    print("=" * 70)

    dropdowns = get_select_options(page)

    for dropdown in dropdowns:
        print()
        print(
            f"SELECT #{dropdown['index']} "
            f"id={dropdown['id']!r} "
            f"name={dropdown['name']!r}"
        )

        for option in dropdown["options"]:
            print(f"    {option['text']!r}")

    print("=" * 70)
    print()


def find_select_containing_option(page, option_text):
    """
    Find a SELECT containing an option with the specified visible text.
    """

    selects = page.locator("select")

    wanted = clean_text(option_text).casefold()

    for index in range(selects.count()):

        select = selects.nth(index)

        options = select.locator("option")

        for option_index in range(options.count()):

            text = clean_text(
                options.nth(option_index).inner_text()
            )

            if text.casefold() == wanted:
                return select

    return None


def select_option_by_visible_text(page, select, wanted_text):
    """
    Select an option using its visible text.
    """

    wanted = clean_text(wanted_text).casefold()

    options = select.locator("option")

    for index in range(options.count()):

        option = options.nth(index)

        text = clean_text(option.inner_text())

        if text.casefold() == wanted:

            value = option.get_attribute("value")

            if value is not None:
                select.select_option(value=value)
            else:
                select.select_option(label=text)

            return

    raise RuntimeError(
        f'Could not find option "{wanted_text}" '
        "in the selected dropdown."
    )


def wait_for_dynamic_dropdowns(page):
    """
    Wait for the calculator JavaScript to populate the Service
    and Destination dropdowns.
    """

    page.wait_for_timeout(1000)

    try:

        page.wait_for_function(
            """
            expected => {
                const selects =
                    Array.from(document.querySelectorAll("select"));

                return selects.some(select =>
                    Array.from(select.options).some(option =>
                        option.textContent.trim().toLowerCase() ===
                        expected.toLowerCase()
                    )
                );
            }
            """,
            SERVICE,
            timeout=TIMEOUT_MS,
        )

    except PlaywrightTimeoutError:

        raise RuntimeError(
            'The "Stationery (Postcard)" option did not appear. '
            "The website may have changed."
        )

    page.wait_for_timeout(1000)


def get_destination_select(page):
    """
    Find the Destination information dropdown.

    The script first looks for a dropdown containing recognizable
    country names.

    If that does not work, it falls back to the dropdown containing
    the largest number of options.
    """

    selects = page.locator("select")

    candidates = []

    for index in range(selects.count()):

        select = selects.nth(index)

        options = select.locator("option")

        option_texts = []

        for option_index in range(options.count()):

            text = clean_text(
                options.nth(option_index).inner_text()
            )

            if text:
                option_texts.append(text)

        if len(option_texts) < 2:
            continue

        candidates.append(
            (
                select,
                option_texts,
            )
        )

    # Recognizable country names.
    destination_keywords = [
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

        joined = " ".join(options).casefold()

        matches = sum(
            1
            for keyword in destination_keywords
            if keyword.casefold() in joined
        )

        if matches >= 2:
            return select

    # Fallback: use the dropdown with the most options.
    if candidates:

        candidates.sort(
            key=lambda item: len(item[1]),
            reverse=True,
        )

        return candidates[0][0]

    raise RuntimeError(
        "Could not find the Destination information dropdown."
    )


def get_all_destinations(destination_select):
    """
    Extract every destination from the dropdown.

    Placeholder entries such as "Select" are excluded.
    """

    destinations = []

    options = destination_select.locator("option")

    for index in range(options.count()):

        option = options.nth(index)

        text = clean_text(
            option.inner_text()
        )

        if not text:
            continue

        value = option.get_attribute("value")

        lower = text.casefold()

        # Ignore common placeholder options.
        if lower in {
            "select",
            "[select]",
            "select destination",
            "destination",
            "choose",
            "please select",
        }:
            continue

        # Ignore empty-value placeholders.
        if value is not None and not value.strip():
            continue

        destinations.append(
            {
                "text": text,
                "value": value,
            }
        )

    # Remove duplicates while preserving website order.
    unique = []

    seen = set()

    for destination in destinations:

        key = destination["text"].casefold()

        if key not in seen:

            seen.add(key)

            unique.append(destination)

    return unique


def find_weight_input(page):
    """
    Find the Weight input field.
    """

    # ------------------------------------------------------------
    # Try labels.
    # ------------------------------------------------------------

    labels = page.locator("label")

    for index in range(labels.count()):

        label = labels.nth(index)

        text = clean_text(
            label.inner_text()
        ).casefold()

        if "weight" in text:

            label_for = label.get_attribute("for")

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

    # ------------------------------------------------------------
    # Try input attributes.
    # ------------------------------------------------------------

    inputs = page.locator("input")

    for index in range(inputs.count()):

        input_element = inputs.nth(index)

        identifier = " ".join(
            [
                input_element.get_attribute("id") or "",
                input_element.get_attribute("name") or "",
                input_element.get_attribute("placeholder") or "",
                input_element.get_attribute("aria-label") or "",
            ]
        ).casefold()

        if "weight" in identifier:
            return input_element

    # ------------------------------------------------------------
    # Fallback to visible number/text input.
    # ------------------------------------------------------------

    for index in range(inputs.count()):

        input_element = inputs.nth(index)

        if not input_element.is_visible():
            continue

        input_type = (
            input_element.get_attribute("type")
            or "text"
        ).casefold()

        if input_type in {
            "number",
            "text",
        }:
            return input_element

    raise RuntimeError(
        "Could not find the Weight input."
    )


def find_calculate_button(page):
    """
    Find the Calculate button.
    """

    buttons = page.locator(
        "button, input[type='button'], input[type='submit']"
    )

    for index in range(buttons.count()):

        button = buttons.nth(index)

        if not button.is_visible():
            continue

        tag_name = button.evaluate(
            "(el) => el.tagName.toLowerCase()"
        )

        if tag_name == "button":

            text = clean_text(
                button.inner_text()
            )

        else:

            text = clean_text(
                button.get_attribute("value")
                or ""
            )

        if text.casefold() == "calculate":
            return button

    raise RuntimeError(
        'Could not find the "Calculate" button.'
    )


def page_contains_price(page):
    """
    Check whether the calculator result contains:

        Price Stationery (postcard)

    Returns True if found.
    Returns False otherwise.
    """

    body_text = clean_text(
        page.locator("body").inner_text()
    ).casefold()

    wanted = clean_text(
        PRICE_TEXT
    ).casefold()

    return wanted in body_text


# ================================================================
# CHECK ONE DESTINATION
# ================================================================

def check_destination(
    page,
    destination_select,
    destination,
    weight_input,
    calculate_button,
):
    """
    Test one destination.

    Returns:
        True  = available
        False = suspended
    """

    destination_text = destination["text"]

    print(
        f"Checking destination: {destination_text}"
    )

    # ------------------------------------------------------------
    # Select destination.
    # ------------------------------------------------------------

    if destination["value"] is not None:

        try:

            destination_select.select_option(
                value=destination["value"]
            )

        except Exception:

            select_option_by_visible_text(
                page,
                destination_select,
                destination_text,
            )

    else:

        select_option_by_visible_text(
            page,
            destination_select,
            destination_text,
        )

    # ------------------------------------------------------------
    # Enter weight 10.
    # ------------------------------------------------------------

    weight_input.fill("")

    weight_input.fill(
        WEIGHT
    )

    # ------------------------------------------------------------
    # Click Calculate.
    # ------------------------------------------------------------

    calculate_button.click()

    # Allow the calculator to update the result.
    page.wait_for_timeout(
        CALCULATION_WAIT_MS
    )

    # ------------------------------------------------------------
    # Check result.
    # ------------------------------------------------------------

    available = page_contains_price(
        page
    )

    if available:

        print(
            f"  RESULT: AVAILABLE"
        )

    else:

        print(
            f"  RESULT: SUSPENDED"
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
    Write exactly one output file.

    No timestamp is included so changedetection.io only detects
    actual changes in the destination lists.
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
    # 1. ALL DESTINATIONS
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
        f"Total destinations: {len(all_destinations)}"
    )

    lines.append("")

    # ============================================================
    # 2. AVAILABLE DESTINATIONS
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
        f"Total available: {len(available_destinations)}"
    )

    lines.append("")

    # ============================================================
    # 3. SUSPENDED DESTINATIONS
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
        f"Total suspended: {len(suspended_destinations)}"
    )

    lines.append("")

    # ============================================================
    # CHECK RULE
    # ============================================================

    lines.append(
        "CHECK RULE"
    )

    lines.append(
        "-" * 70
    )

    lines.append(
        'Available = calculator returned "Price Stationery (postcard)"'
    )

    lines.append(
        'Suspended = calculator did not return "Price Stationery (postcard)"'
    )

    lines.append("")

    # Write the complete file.
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
    # Start Playwright
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
            # STEP 1: Open website
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
            # STEP 2: International traffic
            # ====================================================

            print(
                'STEP 2: Selecting "International traffic"...'
            )

            type_select = find_select_containing_option(
                page,
                TYPE_OF_SERVICE,
            )

            if type_select is None:

                print_dropdown_information(
                    page
                )

                raise RuntimeError(
                    'Could not find "International traffic" '
                    "in any dropdown."
                )

            select_option_by_visible_text(
                page,
                type_select,
                TYPE_OF_SERVICE,
            )

            page.wait_for_timeout(
                1000
            )

            # ====================================================
            # STEP 3: Stationery (Postcard)
            # ====================================================

            print(
                'STEP 3: Selecting "Stationery (Postcard)"...'
            )

            service_select = find_select_containing_option(
                page,
                SERVICE,
            )

            if service_select is None:

                print_dropdown_information(
                    page
                )

                raise RuntimeError(
                    'Could not find "Stationery (Postcard)" '
                    "in any dropdown."
                )

            select_option_by_visible_text(
                page,
                service_select,
                SERVICE,
            )

            # ====================================================
            # Wait for Destination information
            # ====================================================

            print(
                "Waiting for destination list..."
            )

            wait_for_dynamic_dropdowns(
                page
            )

            # ====================================================
            # STEP 4: Get ALL destinations
            # ====================================================

            print(
                'STEP 4: Reading "Destination information"...'
            )

            destination_select = get_destination_select(
                page
            )

            destinations = get_all_destinations(
                destination_select
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
            # Find Weight field
            # ====================================================

            print(
                "Finding Weight input..."
            )

            weight_input = find_weight_input(
                page
            )

            # ====================================================
            # Find Calculate button
            # ====================================================

            print(
                'Finding "Calculate" button...'
            )

            calculate_button = find_calculate_button(
                page
            )

            # ====================================================
            # STEP 5: Check every destination
            # ====================================================

            print()

            print(
                "STEP 5: Checking every destination..."
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

                    available = check_destination(
                        page,
                        destination_select,
                        destination,
                        weight_input,
                        calculate_button,
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
                        "  Classified as SUSPENDED."
                    )

                    suspended_destinations.append(
                        destination["text"]
                    )

                # Small delay between destinations.
                time.sleep(0.5)

            # ====================================================
            # STEP 6: Write results.txt
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
            # Final summary
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
                f"Output file: "
                f"{OUTPUT_FILE.resolve()}"
            )

            print()

        finally:

            browser.close()


# ================================================================
# PROGRAM ENTRY POINT
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
