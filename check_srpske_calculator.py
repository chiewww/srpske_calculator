#!/usr/bin/env python3

"""
Diagnostic version of the Pošte Srpske calculator checker.

This version intentionally stops after identifying the calculator
controls. It is designed to determine exactly how the calculator
represents the Weight field after:

    Type of service = International traffic
    Service = Stationery (Postcard)

Known from previous run:

    select #0 = vrsta_usl
    select #1 = uslugaM
    select #2 = zemlja

There are currently no visible input elements.

The diagnostic output therefore inspects:

    - the calculator form
    - visible elements
    - links
    - labels
    - tables
    - divs/spans
    - elements containing numbers
    - elements containing weight-related text
    - relevant HTML surrounding the calculator
"""


from pathlib import Path
import sys

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ================================================================
# SETTINGS
# ================================================================

URL = "https://www.postesrpske.com/calc/kalkulator.html"

TYPE_OF_SERVICE = "International traffic"

SERVICE = "Stationery (Postcard)"

TIMEOUT_MS = 30000


# ================================================================
# HELPERS
# ================================================================

def clean_text(value):
    """Normalize whitespace."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    ).strip()


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
    Select an option by its visible text.
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
# WAIT FOR SERVICE
# ================================================================

def wait_for_service(page):
    """
    Wait until Stationery (Postcard) exists.
    """

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

        raise RuntimeError(
            'The "Stationery (Postcard)" option '
            "did not appear."
        )


# ================================================================
# PRINT SELECTS
# ================================================================

def print_selects(page):

    print()
    print("=" * 80)
    print("SELECT ELEMENTS")
    print("=" * 80)

    selects = page.locator(
        "select"
    )

    print(
        f"Number of SELECT elements: "
        f"{selects.count()}"
    )

    for index in range(
        selects.count()
    ):

        select = selects.nth(
            index
        )

        print()
        print(
            f"SELECT #{index}"
        )

        for attribute in [
            "id",
            "name",
            "class",
            "style",
        ]:

            value = select.get_attribute(
                attribute
            )

            if value is not None:

                print(
                    f"  {attribute}={value!r}"
                )

        print(
            f"  visible={select.is_visible()}"
        )

        options = select.locator(
            "option"
        )

        print(
            f"  option_count={options.count()}"
        )

        for option_index in range(
            min(options.count(), 20)
        ):

            option = options.nth(
                option_index
            )

            print(
                f"    {option_index}: "
                f"text={clean_text(option.inner_text())!r}, "
                f"value={option.get_attribute('value')!r}"
            )

        if options.count() > 20:

            print(
                f"    ... "
                f"{options.count() - 20} more options"
            )


# ================================================================
# PRINT VISIBLE ELEMENTS
# ================================================================

def print_visible_elements(page):

    print()
    print("=" * 80)
    print("VISIBLE ELEMENTS")
    print("=" * 80)

    elements = page.locator(
        "body *"
    )

    count = elements.count()

    print(
        f"Total DOM elements: {count}"
    )

    printed = 0

    for index in range(count):

        element = elements.nth(
            index
        )

        try:

            if not element.is_visible():
                continue

        except Exception:

            continue

        try:

            tag = element.evaluate(
                "(e) => e.tagName.toLowerCase()"
            )

        except Exception:

            continue

        # Skip huge containers.
        if tag in {
            "html",
            "body",
            "script",
            "style",
            "option",
        }:

            continue

        try:

            text = clean_text(
                element.inner_text()
            )

        except Exception:

            text = ""

        # Only print elements with useful text
        # or interactive attributes.
        interesting = bool(
            text
        )

        for attribute in [
            "id",
            "name",
            "class",
            "href",
            "onclick",
            "for",
            "role",
            "type",
            "value",
        ]:

            if element.get_attribute(
                attribute
            ):

                interesting = True

        if not interesting:
            continue

        print()
        print(
            f"[{printed}] "
            f"<{tag}>"
        )

        print(
            f"  text={text[:300]!r}"
        )

        for attribute in [
            "id",
            "name",
            "class",
            "href",
            "onclick",
            "for",
            "role",
            "type",
            "value",
            "style",
        ]:

            value = element.get_attribute(
                attribute
            )

            if value is not None:

                print(
                    f"  {attribute}={value!r}"
                )

        printed += 1

        if printed >= 200:

            print()
            print(
                "... output limited to first "
                "200 visible elements ..."
            )

            break


# ================================================================
# PRINT LINKS
# ================================================================

def print_links(page):

    print()
    print("=" * 80)
    print("LINKS")
    print("=" * 80)

    links = page.locator(
        "a"
    )

    print(
        f"Number of links: {links.count()}"
    )

    for index in range(
        links.count()
    ):

        link = links.nth(
            index
        )

        try:

            visible = link.is_visible()

        except Exception:

            visible = False

        text = clean_text(
            link.inner_text()
        )

        href = link.get_attribute(
            "href"
        )

        onclick = link.get_attribute(
            "onclick"
        )

        if (
            visible
            or text
            or onclick
        ):

            print()
            print(
                f"LINK #{index}"
            )

            print(
                f"  visible={visible}"
            )

            print(
                f"  text={text!r}"
            )

            print(
                f"  href={href!r}"
            )

            print(
                f"  onclick={onclick!r}"
            )


# ================================================================
# PRINT LABELS
# ================================================================

def print_labels(page):

    print()
    print("=" * 80)
    print("LABELS")
    print("=" * 80)

    labels = page.locator(
        "label"
    )

    print(
        f"Number of labels: {labels.count()}"
    )

    for index in range(
        labels.count()
    ):

        label = labels.nth(
            index
        )

        print()
        print(
            f"LABEL #{index}"
        )

        print(
            f"  text={clean_text(label.inner_text())!r}"
        )

        for attribute in [
            "for",
            "id",
            "class",
        ]:

            value = label.get_attribute(
                attribute
            )

            if value is not None:

                print(
                    f"  {attribute}={value!r}"
                )


# ================================================================
# PRINT TABLES
# ================================================================

def print_tables(page):

    print()
    print("=" * 80)
    print("TABLES")
    print("=" * 80)

    tables = page.locator(
        "table"
    )

    print(
        f"Number of tables: {tables.count()}"
    )

    for index in range(
        tables.count()
    ):

        table = tables.nth(
            index
        )

        print()
        print(
            f"TABLE #{index}"
        )

        print(
            f"  visible={table.is_visible()}"
        )

        text = clean_text(
            table.inner_text()
        )

        print(
            f"  text={text[:3000]!r}"
        )

        print(
            f"  id={table.get_attribute('id')!r}"
        )

        print(
            f"  class={table.get_attribute('class')!r}"
        )


# ================================================================
# SEARCH FOR WEIGHT TEXT
# ================================================================

def print_weight_search(page):

    print()
    print("=" * 80)
    print("WEIGHT SEARCH")
    print("=" * 80)

    # Search the complete page text.
    body_text = clean_text(
        page.locator(
            "body"
        ).inner_text()
    )

    print(
        "Complete visible page text:"
    )

    print(
        body_text[:10000]
    )

    print()

    for keyword in [
        "weight",
        "mass",
        "gram",
        "grams",
        "g",
        "težina",
        "grama",
    ]:

        print(
            f"Searching for {keyword!r}: "
            f"{keyword.casefold() in body_text.casefold()}"
        )


# ================================================================
# PRINT CALCULATOR CONTAINER HTML
# ================================================================

def print_calculator_html(page):

    print()
    print("=" * 80)
    print("CALCULATOR HTML")
    print("=" * 80)

    # Try common calculator containers.
    selectors = [
        "form",
        "#calculator",
        "#kalkulator",
        ".calculator",
        "#content",
        "#main",
    ]

    printed = False

    for selector in selectors:

        locator = page.locator(
            selector
        )

        if locator.count() == 0:
            continue

        for index in range(
            min(locator.count(), 3)
        ):

            element = locator.nth(
                index
            )

            try:

                html = element.evaluate(
                    "(e) => e.outerHTML"
                )

            except Exception:

                continue

            print()
            print(
                f"SELECTOR: {selector} "
                f"#{index}"
            )

            print(
                html[:30000]
            )

            printed = True

    if not printed:

        print(
            "No common calculator container "
            "was found."
        )


# ================================================================
# PRINT ALL ELEMENTS WITH DATA ATTRIBUTES
# ================================================================

def print_data_attributes(page):

    print()
    print("=" * 80)
    print("DATA ATTRIBUTES")
    print("=" * 80)

    elements = page.locator(
        "[data-*]"
    )

    # CSS does not support [data-*] as a wildcard
    # in all engines, so use JavaScript instead.

    data = page.evaluate(
        """
        () => {
            const result = [];

            document
                .querySelectorAll("*")
                .forEach(element => {

                    const attributes = {};

                    for (const attr of element.attributes) {

                        if (attr.name.startsWith("data-")) {

                            attributes[attr.name] =
                                attr.value;
                        }
                    }

                    if (
                        Object.keys(attributes).length > 0
                    ) {

                        result.push({
                            tag: element.tagName,
                            id: element.id || "",
                            className:
                                element.className || "",
                            text:
                                (element.innerText || "")
                                    .replace(/\\s+/g, " ")
                                    .trim()
                                    .slice(0, 300),
                            attributes
                        });
                    }
                });

            return result;
        }
        """
    )

    print(
        f"Elements with data-* attributes: "
        f"{len(data)}"
    )

    for item in data:

        print()
        print(
            f"tag={item['tag']}"
        )

        print(
            f"id={item['id']!r}"
        )

        print(
            f"class={item['className']!r}"
        )

        print(
            f"text={item['text']!r}"
        )

        print(
            f"attributes={item['attributes']!r}"
        )


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 80)
    print(
        "POŠTE SRPSKE CALCULATOR DIAGNOSTIC"
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

    print()

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 1200,
            }
        )

        page.set_default_timeout(
            TIMEOUT_MS
        )

        try:

            # ----------------------------------------------------
            # STEP 1
            # ----------------------------------------------------

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

            # ----------------------------------------------------
            # STEP 2
            # ----------------------------------------------------

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

            # ----------------------------------------------------
            # STEP 3
            # ----------------------------------------------------

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

                raise RuntimeError(
                    'Could not find "Stationery (Postcard)".'
                )

            select_option_by_visible_text(
                service_select,
                SERVICE,
            )

            # ----------------------------------------------------
            # WAIT
            # ----------------------------------------------------

            print(
                "Waiting for calculator controls..."
            )

            wait_for_service(
                page
            )

            page.wait_for_timeout(
                2000
            )

            # ----------------------------------------------------
            # DIAGNOSTICS
            # ----------------------------------------------------

            print_selects(
                page
            )

            print_labels(
                page
            )

            print_links(
                page
            )

            print_tables(
                page
            )

            print_weight_search(
                page
            )

            print_visible_elements(
                page
            )

            print_data_attributes(
                page
            )

            print_calculator_html(
                page
            )

            # ----------------------------------------------------
            # FINISHED
            # ----------------------------------------------------

            print()
            print("=" * 80)
            print(
                "DIAGNOSTIC FINISHED"
            )
            print("=" * 80)
            print()

            print(
                "No results.txt was created."
            )

            print(
                "The output above shows the actual "
                "calculator structure after selecting "
                "Stationery (Postcard)."
            )

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
