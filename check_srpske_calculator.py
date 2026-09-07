#!/usr/bin/env python3

"""
Pošte Srpske calculator destination availability checker.

Website:
    https://www.postesrpske.com/calc/kalkulator.html

Procedure:

1. Open the English calculator.
2. Select "International traffic".
3. Select "Stationery (Postcard)".
4. Read ALL destinations from the Destination information dropdown.
5. For every destination:
       - select destination
       - enter weight 10
       - click Calculate
       - check for "Price Stationery (postcard)"
6. Write results.txt.

Availability rule:

    "Price Stationery (postcard)" found
        = AVAILABLE

    Otherwise
        = SUSPENDED

No timestamp is written to results.txt.
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

    return " ".join(str(value).split()).strip()


# ================================================================
# DEBUG: PRINT ALL FORM CONTROLS
# ================================================================

def print_form_controls(page):
    """
    Print every visible form control and useful attributes.

    This is deliberately verbose because the calculator uses
    dynamically generated controls and the exact Weight element
    is not exposed clearly by the normal HTML text representation.
    """

    print()
    print("=" * 80)
    print("FORM CONTROL INVENTORY")
    print("=" * 80)

    # ------------------------------------------------------------
    # SELECTS
    # ------------------------------------------------------------

    selects = page.locator("select")

    print()
    print(f"SELECT elements: {selects.count()}")

    for index in range(selects.count()):

        element = selects.nth(index)

        print()
        print(f"SELECT #{index}")
        print(
            f"  id={element.get_attribute('id')!r}"
        )
        print(
            f"  name={element.get_attribute('name')!r}"
        )
        print(
            f"  class={element.get_attribute('class')!r}"
        )
        print(
            f"  visible={element.is_visible()}"
        )

        options = element.locator("option")

        print(
            f"  option_count={options.count()}"
        )

        for option_index in range(
            min(options.count(), 15)
        ):

            option = options.nth(
                option_index
            )

            print(
                f"    option {option_index}: "
                f"text={clean_text(option.inner_text())!r}, "
                f"value={option.get_attribute('value')!r}"
            )

        if options.count() > 15:
            print(
                f"    ... {options.count() - 15} more options"
            )

    # ------------------------------------------------------------
    # INPUTS
    # ------------------------------------------------------------

    inputs = page.locator("input")

    print()
    print(f"INPUT elements: {inputs.count()}")

    for index in range(inputs.count()):

        element = inputs.nth(index)

        print()
        print(f"INPUT #{index}")

        attributes = [
            "type",
            "id",
            "name",
            "class",
            "value",
            "placeholder",
            "aria-label",
            "title",
            "min",
            "max",
            "step",
        ]

        for attribute in attributes:

            value = element.get_attribute(
                attribute
            )

            if value is not None:

                print(
                    f"  {attribute}={value!r}"
                )

        print(
            f"  visible={element.is_visible()}"
        )

    # ------------------------------------------------------------
    # TEXTAREAS
    # ------------------------------------------------------------

    textareas = page.locator("textarea")

    print()
    print(
        f"TEXTAREA elements: {textareas.count()}"
    )

    for index in range(
        textareas.count()
    ):

        element = textareas.nth(index)

        print()
        print(
            f"TEXTAREA #{index}"
        )

        print(
            f"  id={element.get_attribute('id')!r}"
        )

        print(
            f"  name={element.get_attribute('name')!r}"
        )

        print(
            f"  placeholder={element.get_attribute('placeholder')!r}"
        )

        print(
            f"  class={element.get_attribute('class')!r}"
        )

        print(
            f"  visible={element.is_visible()}"
        )

    # ------------------------------------------------------------
    # CONTENTEDITABLE
    # ------------------------------------------------------------

    content_editable = page.locator(
        "[contenteditable='true']"
    )

    print()
    print(
        "CONTENTEDITABLE elements: "
        f"{content_editable.count()}"
    )

    for index in range(
        content_editable.count()
    ):

        element = content_editable.nth(index)

        print()
        print(
            f"CONTENTEDITABLE #{index}"
        )

        print(
            f"  tag={element.evaluate('(e) => e.tagName')}"
        )

        print(
            f"  id={element.get_attribute('id')!r}"
        )

        print(
            f"  name={element.get_attribute('name')!r}"
        )

        print(
            f"  class={element.get_attribute('class')!r}"
        )

        print(
            f"  aria-label={element.get_attribute('aria-label')!r}"
        )

        print(
            f"  visible={element.is_visible()}"
        )

    # ------------------------------------------------------------
    # BUTTONS
    # ------------------------------------------------------------

    buttons = page.locator(
        "button, input[type='button'], "
        "input[type='submit'], [role='button']"
    )

    print()
    print(
        f"BUTTON elements: {buttons.count()}"
    )

    for index in range(
        buttons.count()
    ):

        element = buttons.nth(index)

        if not element.is_visible():
            continue

        try:

            text = clean_text(
                element.inner_text()
            )

        except Exception:

            text = ""

        value = element.get_attribute(
            "value"
        )

        print()
        print(
            f"BUTTON #{index}"
        )

        print(
            f"  tag={element.evaluate('(e) => e.tagName')}"
        )

        print(
            f"  text={text!r}"
        )

        print(
            f"  value={value!r}"
        )

        print(
            f"  id={element.get_attribute('id')!r}"
        )

        print(
            f"  name={element.get_attribute('name')!r}"
        )

        print(
            f"  class={element.get_attribute('class')!r}"
        )

    print()
    print("=" * 80)
    print()


# ================================================================
# DEBUG: PRINT LABELS AND NEARBY TEXT
# ================================================================

def print_weight_related_elements(page):
    """
    Print elements containing the word Weight or similar wording.
    """

    print()
    print("=" * 80)
    print("WEIGHT-RELATED ELEMENTS")
    print("=" * 80)

    # Search visible text nodes/elements containing Weight.
    locator = page.locator(
        "text=/weight/i"
    )

    print(
        f"Elements containing 'weight': "
        f"{locator.count()}"
    )

    for index in range(
        min(locator.count(), 30)
    ):

        element = locator.nth(index)

        try:
            text = clean_text(
                element.inner_text()
            )
        except Exception:
            text = ""

        try:
            tag = element.evaluate(
                "(e) => e.tagName"
            )
        except Exception:
            tag = "?"

        print()
        print(
            f"#{index}: tag={tag}, text={text!r}"
        )

        for attribute in [
            "id",
            "name",
            "class",
            "for",
            "type",
            "placeholder",
            "aria-label",
        ]:

            value = element.get_attribute(
                attribute
            )

            if value is not None:
                print(
                    f"  {attribute}={value!r}"
                )

    print()
    print("=" * 80)
    print()


# ================================================================
# FIND SELECT
# ================================================================

def find_select_containing_option(
    page,
    option_text,
):
    """
    Find a SELECT containing an exact visible option.
    """

    wanted = clean_text(
        option_text
    ).casefold()

    selects = page.locator(
        "select"
    )

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
    Select an option by visible text.
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
# WAIT FOR DYNAMIC CONTENT
# ================================================================

def wait_for_dynamic_dropdowns(page):
    """
    Wait for the Service option to become available.
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

        print_form_controls(
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
    Find the destination SELECT.

    The calculator currently exposes a large destination list.
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

    if candidates:

        candidates.sort(
            key=lambda item: len(
                item[1]
            ),
            reverse=True,
        )

        return candidates[0][0]

    print_form_controls(
        page
    )

    raise RuntimeError(
        "Could not find Destination information dropdown."
    )


def get_all_destinations(
    destination_select,
):
    """
    Return all actual destination options.
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
# FIND WEIGHT CONTROL
# ================================================================

def find_weight_control(page):
    """
    Find the calculator's Weight control.

    This is deliberately much more flexible than simply looking
    for an <input> whose id/name contains "weight".

    The control may be:

        - input
        - select
        - textarea
        - contenteditable element

    We first inspect labels and nearby DOM elements, then inspect
    attributes, then fall back to visible numeric/text controls.
    """

    # ------------------------------------------------------------
    # 1. Look for an explicit label.
    # ------------------------------------------------------------

    labels = page.locator(
        "label"
    )

    for label_index in range(
        labels.count()
    ):

        label = labels.nth(
            label_index
        )

        if not label.is_visible():
            continue

        label_text = clean_text(
            label.inner_text()
        ).casefold()

        if "weight" not in label_text:
            continue

        print(
            f"Found Weight label: {label_text!r}"
        )

        label_for = label.get_attribute(
            "for"
        )

        if label_for:

            candidate = page.locator(
                f"#{label_for}"
            )

            if candidate.count() > 0:

                print(
                    "Weight control found through label 'for'."
                )

                return candidate.first

        # Try controls inside the label.
        candidate = label.locator(
            "input, select, textarea, "
            "[contenteditable='true']"
        )

        if candidate.count() > 0:

            print(
                "Weight control found inside label."
            )

            return candidate.first

        # Try the next few controls in DOM order.
        candidate = label.locator(
            "xpath=following::input[1]"
        )

        if candidate.count() > 0:

            try:

                if candidate.first.is_visible():

                    print(
                        "Weight control found after label."
                    )

                    return candidate.first

            except Exception:
                pass

    # ------------------------------------------------------------
    # 2. Look for attributes containing "weight".
    # ------------------------------------------------------------

    all_controls = page.locator(
        "input, select, textarea, "
        "[contenteditable='true']"
    )

    for index in range(
        all_controls.count()
    ):

        control = all_controls.nth(
            index
        )

        if not control.is_visible():
            continue

        searchable = " ".join(
            [
                control.get_attribute(
                    "id"
                ) or "",
                control.get_attribute(
                    "name"
                ) or "",
                control.get_attribute(
                    "class"
                ) or "",
                control.get_attribute(
                    "placeholder"
                ) or "",
                control.get_attribute(
                    "aria-label"
                ) or "",
                control.get_attribute(
                    "title"
                ) or "",
            ]
        ).casefold()

        if "weight" in searchable:

            print(
                "Weight control found through attributes."
            )

            return control

    # ------------------------------------------------------------
    # 3. Look for nearby text in parent/container.
    # ------------------------------------------------------------

    for index in range(
        all_controls.count()
    ):

        control = all_controls.nth(
            index
        )

        if not control.is_visible():
            continue

        try:

            context = control.evaluate(
                """
                element => {
                    let node = element;

                    for (let i = 0; i < 4 && node; i++) {
                        const text =
                            (node.innerText || "")
                            .replace(/\\s+/g, " ")
                            .trim();

                        if (text.length > 0) {
                            return text;
                        }

                        node = node.parentElement;
                    }

                    return "";
                }
                """
            )

        except Exception:

            context = ""

        context = clean_text(
            context
        ).casefold()

        if "weight" in context:

            print(
                "Weight control found from surrounding container."
            )

            return control

    # ------------------------------------------------------------
    # 4. Look for numeric inputs.
    # ------------------------------------------------------------

    for index in range(
        all_controls.count()
    ):

        control = all_controls.nth(
            index
        )

        if not control.is_visible():
            continue

        tag = control.evaluate(
            "(e) => e.tagName.toLowerCase()"
        )

        if tag != "input":
            continue

        input_type = (
            control.get_attribute(
                "type"
            )
            or "text"
        ).casefold()

        if input_type == "number":

            print(
                "Weight control found as visible numeric input."
            )

            return control

    # ------------------------------------------------------------
    # 5. Look for a visible text input.
    #
    # We deliberately only use this as a last resort.
    # ------------------------------------------------------------

    visible_text_inputs = []

    for index in range(
        all_controls.count()
    ):

        control = all_controls.nth(
            index
        )

        if not control.is_visible():
            continue

        tag = control.evaluate(
            "(e) => e.tagName.toLowerCase()"
        )

        if tag != "input":
            continue

        input_type = (
            control.get_attribute(
                "type"
            )
            or "text"
        ).casefold()

        if input_type in {
            "text",
            "number",
            "tel",
        }:

            visible_text_inputs.append(
                control
            )

    if len(visible_text_inputs) == 1:

        print(
            "Only one visible text/numeric input exists; "
            "using it as Weight."
        )

        return visible_text_inputs[0]

    # ------------------------------------------------------------
    # Nothing found.
    # Print diagnostics before failing.
    # ------------------------------------------------------------

    print_weight_related_elements(
        page
    )

    print_form_controls(
        page
    )

    raise RuntimeError(
        "Could not find Weight control."
    )


# ================================================================
# ENTER WEIGHT
# ================================================================

def enter_weight(
    weight_control,
    value,
):
    """
    Put the requested weight into the detected control.
    """

    tag = weight_control.evaluate(
        "(e) => e.tagName.toLowerCase()"
    )

    print(
        f"Weight control type: {tag}"
    )

    if tag == "select":

        # If weight is a dropdown, try exact 10 first.
        options = weight_control.locator(
            "option"
        )

        for index in range(
            options.count()
        ):

            option = options.nth(index)

            text = clean_text(
                option.inner_text()
            )

            option_value = (
                option.get_attribute(
                    "value"
                )
            )

            if (
                text == value
                or option_value == value
            ):

                if option_value is not None:

                    weight_control.select_option(
                        value=option_value
                    )

                else:

                    weight_control.select_option(
                        label=text
                    )

                return

        raise RuntimeError(
            f'Weight dropdown does not contain "{value}".'
        )

    # ------------------------------------------------------------
    # Input / textarea / contenteditable.
    # ------------------------------------------------------------

    if tag in {
        "input",
        "textarea",
    }:

        weight_control.fill(
            value
        )

        return

    if weight_control.get_attribute(
        "contenteditable"
    ) == "true":

        weight_control.fill(
            value
        )

        return

    raise RuntimeError(
        f"Unsupported Weight control: {tag}"
    )


# ================================================================
# CALCULATE BUTTON
# ================================================================

def find_calculate_button(page):
    """
    Find the Calculate control.
    """

    buttons = page.locator(
        "button, "
        "input[type='button'], "
        "input[type='submit'], "
        "[role='button']"
    )

    for button_index in range(
        buttons.count()
    ):

        button = buttons.nth(
            button_index
        )

        if not button.is_visible():
            continue

        try:

            text = clean_text(
                button.inner_text()
            )

        except Exception:

            text = ""

        value = clean_text(
            button.get_attribute(
                "value"
            )
            or ""
        )

        aria = clean_text(
            button.get_attribute(
                "aria-label"
            )
            or ""
        )

        combined = " ".join(
            [
                text,
                value,
                aria,
            ]
        ).casefold()

        if "calculate" in combined:

            print(
                f'Calculate button found: '
                f'text={text!r}, '
                f'value={value!r}, '
                f'aria-label={aria!r}'
            )

            return button

    raise RuntimeError(
        'Could not find "Calculate" button.'
    )


# ================================================================
# PRICE CHECK
# ================================================================

def page_contains_price(page):
    """
    Check whether the expected price text exists.
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
    weight_control,
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
    # Destination
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
    # Weight
    # ------------------------------------------------------------

    enter_weight(
        weight_control,
        WEIGHT,
    )

    # ------------------------------------------------------------
    # Calculate
    # ------------------------------------------------------------

    calculate_button.click()

    page.wait_for_timeout(
        CALCULATION_WAIT_MS
    )

    # ------------------------------------------------------------
    # Result
    # ------------------------------------------------------------

    available = page_contains_price(
        page
    )

    if available:

        print(
            "  -> AVAILABLE"
        )

    else:

        print(
            "  -> SUSPENDED"
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
    Write results.txt without a timestamp.
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

    # ------------------------------------------------------------
    # ALL
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # AVAILABLE
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # SUSPENDED
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # RULE
    # ------------------------------------------------------------

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

    print("=" * 80)
    print(
        "POŠTE SRPSKE CALCULATOR CHECK"
    )
    print("=" * 80)

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

                print_form_controls(
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

                print_form_controls(
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
            # WAIT
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

                print_form_controls(
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
            # FIND WEIGHT
            # ====================================================

            print(
                "Finding Weight control..."
            )

            weight_control = (
                find_weight_control(
                    page
                )
            )

            print(
                "Weight control located successfully."
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
                            weight_control,
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
            print("=" * 80)
            print(
                "FINISHED"
            )
            print("=" * 80)
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
        print("=" * 80)
        print(
            "ERROR"
        )
        print("=" * 80)
        print()

        print(
            str(error)
        )

        print()

        sys.exit(1)
