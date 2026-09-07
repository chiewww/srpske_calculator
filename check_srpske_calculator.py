#!/usr/bin/env python3

"""
Pošte Srpske calculator destination availability checker.

Website:
    https://www.postesrpske.com/calc/kalkulator.html

What this script does:

1. Opens the English Pošte Srpske calculator.
2. Selects "International traffic" for Type of service.
3. Selects "Stationery (Postcard)" for Service.
4. Reads ALL destinations from the "Destination information" dropdown.
5. For every destination:
       - selects the destination
       - enters weight 10
       - clicks Calculate
       - checks whether "Price Stationery (postcard)" appears
6. Writes one text file containing:
       - ALL DESTINATIONS
       - AVAILABLE DESTINATIONS
       - SUSPENDED DESTINATIONS

Requirements:
    Python 3.9+
    Playwright

Install Playwright:
    pip install playwright

Install Chromium:
    playwright install chromium

Run:
    python check_srpske_calculator.py

The output file is:
    results.txt
"""

from pathlib import Path
from datetime import datetime
import sys
import time

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


URL = "https://www.postesrpske.com/calc/kalkulator.html"

OUTPUT_FILE = Path("results.txt")

TYPE_OF_SERVICE = "International traffic"
SERVICE = "Stationery (Postcard)"
WEIGHT = "10"

PRICE_TEXT = "Price Stationery (postcard)"

# How long Playwright waits for normal operations.
TIMEOUT_MS = 30000

# How long to wait after clicking Calculate before checking the result.
CALCULATION_WAIT_MS = 1500


def clean_text(value):
    """Normalize whitespace in a string."""
    if value is None:
        return ""

    return " ".join(value.split()).strip()


def get_select_options(page):
    """
    Return information about all SELECT elements currently on the page.

    This is mainly useful because the website dynamically creates/populates
    its dropdowns. It lets us identify the correct dropdowns without
    depending entirely on fragile element IDs.
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
    Print the current SELECT elements.

    This is useful if the website changes its HTML and the script needs
    adjustment later.
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
    Find the SELECT element containing an option with the requested text.

    Matching is case-insensitive and ignores surrounding whitespace.
    """

    selects = page.locator("select")

    count = selects.count()

    wanted = clean_text(option_text).casefold()

    for index in range(count):
        select = selects.nth(index)

        options = select.locator("option")

        option_count = options.count()

        for option_index in range(option_count):
            text = clean_text(
                options.nth(option_index).inner_text()
            )

            if text.casefold() == wanted:
                return select

    return None


def find_select_by_label_text(page, label_text):
    """
    Try to find a SELECT associated with a visible label.

    This is a secondary method. The primary method used by this script is
    finding the SELECT that actually contains the requested option.
    """

    wanted = clean_text(label_text).casefold()

    labels = page.locator("label")

    for index in range(labels.count()):
        label = labels.nth(index)

        text = clean_text(label.inner_text())

        if wanted in text.casefold():
            label_for = label.get_attribute("for")

            if label_for:
                candidate = page.locator(f"#{label_for}")

                if candidate.count() > 0:
                    return candidate

            candidate = label.locator("xpath=following::select[1]")

            if candidate.count() > 0:
                return candidate.first

    return None


def select_option_by_visible_text(page, select, wanted_text):
    """
    Select an option by its visible text.

    Uses Playwright's label matching first, then manually searches the
    options in case the website has unusual option formatting.
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
        f'Could not find option "{wanted_text}" in the selected dropdown.'
    )


def wait_for_dynamic_dropdowns(page):
    """
    Wait until the calculator has populated its dropdowns.

    The page initially loads with only the Type of service dropdown populated.
    Selecting the service causes the other controls to become populated.
    """

    # Give the calculator JavaScript a chance to initialize.
    page.wait_for_timeout(1000)

    # Wait until the requested service exists.
    try:
        page.wait_for_function(
            """
            expected => {
                const selects = Array.from(document.querySelectorAll("select"));

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

    # After selecting Service, the Destination dropdown should populate.
    page.wait_for_timeout(1000)


def get_destination_select(page):
    """
    Locate the Destination information SELECT.

    We identify it by looking for a SELECT with multiple meaningful
    destination options. This avoids depending on a specific HTML id.
    """

    selects = page.locator("select")

    candidates = []

    for index in range(selects.count()):
        select = selects.nth(index)

        option_texts = []

        options = select.locator("option")

        for option_index in range(options.count()):
            text = clean_text(options.nth(option_index).inner_text())

            if text:
                option_texts.append(text)

        if len(option_texts) < 2:
            continue

        candidates.append((select, option_texts))

    # Prefer a dropdown containing recognizable destination names.
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

    # If the website's country names are different from the examples above,
    # use the SELECT with the largest number of options.
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
    Extract every non-empty destination option from the destination
    dropdown.

    The first placeholder such as "Select" is excluded.
    """

    destinations = []

    options = destination_select.locator("option")

    for index in range(options.count()):
        option = options.nth(index)

        text = clean_text(option.inner_text())

        if not text:
            continue

        value = option.get_attribute("value")

        # Skip common placeholder options.
        lower = text.casefold()

        if lower in {
            "select",
            "[select]",
            "select destination",
            "destination",
            "choose",
            "please select",
        }:
            continue

        # Also skip options with empty values that are clearly placeholders.
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
    Find the weight input.

    We first look for an input associated with a label containing
    "Weight". If that fails, we inspect numeric/text inputs.
    """

    # Try labels first.
    labels = page.locator("label")

    for index in range(labels.count()):
        label = labels.nth(index)

        text = clean_text(label.inner_text()).casefold()

        if "weight" in text:
            label_for = label.get_attribute("for")

            if label_for:
                candidate = page.locator(f"#{label_for}")

                if candidate.count() > 0:
                    return candidate

            candidate = label.locator("xpath=following::input[1]")

            if candidate.count() > 0:
                return candidate.first

    # Try inputs whose name/id/placeholder mentions weight.
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

    # Last fallback: first visible numeric/text input.
    for index in range(inputs.count()):
        input_element = inputs.nth(index)

        if not input_element.is_visible():
            continue

        input_type = (
            input_element.get_attribute("type") or "text"
        ).casefold()

        if input_type in {"number", "text"}:
            return input_element

    raise RuntimeError("Could not find the Weight input.")


def find_calculate_button(page):
    """
    Find the Calculate button using its visible text.
    """

    buttons = page.locator(
        "button, input[type='button'], input[type='submit']"
    )

    for index in range(buttons.count()):
        button = buttons.nth(index)

        if not button.is_visible():
            continue

        text = clean_text(
            button.inner_text()
            if button.evaluate(
                "(el) => el.tagName.toLowerCase() === 'button'"
            )
            else (
                button.get_attribute("value") or ""
            )
        )

        if text.casefold() == "calculate":
            return button

    raise RuntimeError(
        'Could not find the "Calculate" button.'
    )


def page_contains_price(page):
    """
    Check whether the calculation result contains exactly the expected
    postcard price heading/text.

    The check is case-insensitive and whitespace-normalized.
    """

    body_text = clean_text(
        page.locator("body").inner_text()
    ).casefold()

    wanted = clean_text(PRICE_TEXT).casefold()

    return wanted in body_text


def clear_previous_result(page):
    """
    Clear/refresh the calculator result if possible.

    We do not reload the entire page because that would require selecting
    International traffic and Stationery (Postcard) again for every
    destination.

    Instead, we simply allow the calculator to overwrite its previous
    result when Calculate is pressed.
    """

    page.wait_for_timeout(300)


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

    print(f"Checking: {destination_text}")

    # Select destination.
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

    # Enter weight 10.
    weight_input.fill("")
    weight_input.fill(WEIGHT)

    clear_previous_result(page)

    # Click Calculate.
    calculate_button.click()

    # Give the calculator time to update the result.
    page.wait_for_timeout(CALCULATION_WAIT_MS)

    # Check result.
    available = page_contains_price(page)

    if available:
        print(f"  -> AVAILABLE")
    else:
        print(f"  -> SUSPENDED")

    return available


def write_results(
    all_destinations,
    available_destinations,
    suspended_destinations,
):
    """
    Create the single requested output text file.
    """

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = []

    lines.append(
        "POŠTE SRPSKE - STATIONERY (POSTCARD) DESTINATION CHECK"
    )
    lines.append("=" * 70)
    lines.append("")
    lines.append(
        f"Website: {URL}"
    )
    lines.append(
        f"Type of service: {TYPE_OF_SERVICE}"
    )
    lines.append(
        f"Service: {SERVICE}"
    )
    lines.append(
        f"Weight: {WEIGHT}"
    )
    lines.append(
        f"Checked: {timestamp}"
    )
    lines.append("")

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

    lines.append(
        "CHECK RULE"
    )
    lines.append(
        "-" * 70
    )
    lines.append(
        f'Available = calculator returned "{PRICE_TEXT}"'
    )
    lines.append(
        f'Suspended = calculator did NOT return "{PRICE_TEXT}"'
    )
    lines.append("")

    OUTPUT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():
    print("=" * 70)
    print("POŠTE SRPSKE CALCULATOR CHECK")
    print("=" * 70)
    print()
    print(f"URL: {URL}")
    print(f"Service: {SERVICE}")
    print(f"Weight: {WEIGHT}")
    print()

    all_destinations = []
    available_destinations = []
    suspended_destinations = []

    with sync_playwright() as playwright:

        # Chromium is used rather than WebKit/Firefox because it is
        # generally the most compatible with websites designed for Chrome.
        browser = playwright.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 1000,
            }
        )

        page.set_default_timeout(TIMEOUT_MS)

        try:
            print("Opening calculator...")
            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=TIMEOUT_MS,
            )

            # Wait for calculator JavaScript.
            page.wait_for_timeout(1500)

            # ---------------------------------------------------------
            # STEP 1:
            # Select "International traffic"
            # ---------------------------------------------------------

            print(
                'Selecting "International traffic"...'
            )

            type_select = find_select_containing_option(
                page,
                TYPE_OF_SERVICE,
            )

            if type_select is None:
                print_dropdown_information(page)

                raise RuntimeError(
                    f'Could not find "{TYPE_OF_SERVICE}" '
                    "in any dropdown."
                )

            select_option_by_visible_text(
                page,
                type_select,
                TYPE_OF_SERVICE,
            )

            page.wait_for_timeout(1000)

            # ---------------------------------------------------------
            # STEP 2:
            # Select "Stationery (Postcard)"
            # ---------------------------------------------------------

            print(
                'Selecting "Stationery (Postcard)"...'
            )

            service_select = find_select_containing_option(
                page,
                SERVICE,
            )

            if service_select is None:
                print_dropdown_information(page)

                raise RuntimeError(
                    f'Could not find "{SERVICE}" '
                    "in any dropdown."
                )

            select_option_by_visible_text(
                page,
                service_select,
                SERVICE,
            )

            # Allow destination information to populate.
            wait_for_dynamic_dropdowns(page)

            # ---------------------------------------------------------
            # STEP 3:
            # Find Destination information dropdown
            # ---------------------------------------------------------

            print(
                'Finding "Destination information" dropdown...'
            )

            destination_select = get_destination_select(
                page
            )

            # ---------------------------------------------------------
            # STEP 4:
            # Read ALL destinations
            # ---------------------------------------------------------

            destinations = get_all_destinations(
                destination_select
            )

            if not destinations:
                print_dropdown_information(page)

                raise RuntimeError(
                    "The Destination information dropdown "
                    "contained no destinations."
                )

            print()
            print(
                f"Found {len(destinations)} destinations."
            )
            print()

            all_destinations = [
                destination["text"]
                for destination in destinations
            ]

            # ---------------------------------------------------------
            # Find Weight input
            # ---------------------------------------------------------

            weight_input = find_weight_input(page)

            # ---------------------------------------------------------
            # Find Calculate button
            # ---------------------------------------------------------

            calculate_button = find_calculate_button(
                page
            )

            # ---------------------------------------------------------
            # STEP 5:
            # Test every destination
            # ---------------------------------------------------------

            for number, destination in enumerate(
                destinations,
                start=1,
            ):

                print(
                    f"[{number}/{len(destinations)}] "
                    f"{destination['text']}"
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

                    # If an individual destination causes an error,
                    # classify it as suspended rather than stopping the
                    # entire run.
                    #
                    # This means one bad destination will not prevent
                    # the remaining destinations from being checked.
                    print(
                        f"  -> ERROR: {error}"
                    )
                    print(
                        "  -> Classified as SUSPENDED"
                    )

                    suspended_destinations.append(
                        destination["text"]
                    )

                # Small delay so the website is not hammered with
                # immediate requests.
                time.sleep(0.5)

            # ---------------------------------------------------------
            # STEP 6:
            # Write ONE output text file
            # ---------------------------------------------------------

            write_results(
                all_destinations,
                available_destinations,
                suspended_destinations,
            )

            print()
            print("=" * 70)
            print("FINISHED")
            print("=" * 70)
            print()
            print(
                f"All destinations: "
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
                f"Output file: {OUTPUT_FILE.resolve()}"
            )
            print()

        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print()
        print("Stopped by user.")
        sys.exit(130)

    except Exception as error:
        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print()
        print(str(error))
        print()
        sys.exit(1)
