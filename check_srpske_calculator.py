from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


URL = "https://www.postesrpske.com/calc/kalkulator.html"
OUTPUT_FILE = "results.txt"

TRAFFIC_VALUE = "M"
SERVICE_VALUE = "DR"
WEIGHT = "10"

DESTINATION_SELECTOR = "#zemlja"
WEIGHT_SELECTOR = "#tezina"
CALCULATE_SELECTOR = "#dopisnicaU"

MODAL_SELECTOR = ".msgBox:visible"
MODAL_CONTENT_SELECTOR = ".msgBoxContent"
MODAL_CLOSE_SELECTOR = ".msgBoxButtons input.msgButton"

AVAILABLE_MARKER = "Price Stationery (postcard)"


def close_result_modal(page):
    """
    Close the calculator result modal and wait for its overlay to disappear.
    """

    modal = page.locator(MODAL_SELECTOR)

    if modal.count() == 0:
        return

    if not modal.first.is_visible():
        return

    close_button = modal.first.locator(MODAL_CLOSE_SELECTOR)

    if close_button.count() > 0 and close_button.first.is_visible():
        close_button.first.click(timeout=5000)

        try:
            page.locator(".msgBoxBackGround:visible").wait_for(
                state="hidden",
                timeout=5000
            )
        except PlaywrightTimeoutError:
            page.wait_for_timeout(300)

    else:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)


def calculate_destination(page, destination_name):
    """
    Select a destination, enter weight 10g, calculate, read the result,
    classify the destination, and close the result modal.
    """

    print(f"Checking: {destination_name}")

    destination = page.locator(DESTINATION_SELECTOR)

    # Select destination.
    destination.select_option(label=destination_name)

    # The weight field is created dynamically after selecting a destination.
    page.locator(WEIGHT_SELECTOR).wait_for(
        state="visible",
        timeout=10000
    )

    # Enter 10 grams.
    weight = page.locator(WEIGHT_SELECTOR)
    weight.fill(WEIGHT)

    # Make sure a previous result modal is not still open.
    visible_modal = page.locator(MODAL_SELECTOR)

    if visible_modal.count() > 0 and visible_modal.first.is_visible():
        close_result_modal(page)

    # Click Calculate.
    page.locator(CALCULATE_SELECTOR).click(timeout=10000)

    # Wait for the result modal.
    modal = page.locator(MODAL_SELECTOR)

    try:
        modal.wait_for(
            state="visible",
            timeout=10000
        )
    except PlaywrightTimeoutError:
        print("  ERROR: Calculation result modal did not appear.")
        return "error"

    # Read the calculation result specifically from the modal.
    content = modal.first.locator(MODAL_CONTENT_SELECTOR)

    if content.count() > 0:
        result_text = content.first.inner_text()
    else:
        result_text = modal.first.inner_text()

    print("  Result:")
    print("  " + result_text.replace("\n", "\n  "))

    # Check whether the postcard price exists.
    if AVAILABLE_MARKER.lower() in result_text.lower():
        status = "available"
        print("  AVAILABLE")
    else:
        status = "suspended"
        print("  SUSPENDED")

    # Close the result modal before continuing.
    close_result_modal(page)

    return status


def main():
    print("=" * 70)
    print("Pošte Srpske calculator checker")
    print("=" * 70)

    available = []
    suspended = []
    errors = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1000
            }
        )

        # Prevent long waits if the website genuinely has a problem.
        page.set_default_timeout(10000)

        print("Opening calculator...")

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(2000)

        print("Selecting International traffic...")

        page.locator("#vrsta_usl").select_option(
            TRAFFIC_VALUE
        )

        page.wait_for_timeout(1000)

        print("Selecting Stationery (Postcard)...")

        page.locator("#uslugaM").select_option(
            SERVICE_VALUE
        )

        page.wait_for_timeout(1000)

        # Get all destinations from the dropdown.
        destination_select = page.locator(
            DESTINATION_SELECTOR
        )

        options = destination_select.locator("option")

        destinations = []

        for i in range(options.count()):
            option = options.nth(i)

            value = option.get_attribute("value")
            label = option.inner_text().strip()

            # Ignore the empty placeholder option.
            if value and label:
                destinations.append(
                    {
                        "value": value,
                        "label": label
                    }
                )

        total_destinations = len(destinations)

        print(
            f"Found {total_destinations} destinations."
        )
        print()

        # -----------------------------------------------------------
        # Check every destination.
        # -----------------------------------------------------------

        for index, destination in enumerate(
            destinations,
            start=1
        ):
            destination_name = destination["label"]

            print(
                f"[{index}/{total_destinations}] "
                f"{destination_name}"
            )

            try:
                status = calculate_destination(
                    page,
                    destination_name
                )

                if status == "available":
                    available.append(destination_name)

                elif status == "suspended":
                    suspended.append(destination_name)

                else:
                    errors.append(destination_name)

            except Exception as exc:
                print(
                    f"  ERROR while checking "
                    f"{destination_name}: {exc}"
                )

                errors.append(destination_name)

                # Attempt to recover if the calculator left a modal open.
                try:
                    close_result_modal(page)
                except Exception:
                    pass

            print()

        browser.close()

    # ---------------------------------------------------------------
    # Calculate totals.
    # ---------------------------------------------------------------

    total_available = len(available)
    total_suspended = len(suspended)
    total_errors = len(errors)

    # ---------------------------------------------------------------
    # Write results.txt
    #
    # No timestamp is included.
    # ---------------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as output:

        output.write(
            f"TOTAL ALL DESTINATIONS: {total_destinations}\n"
        )

        output.write(
            f"TOTAL AVAILABLE DESTINATIONS: {total_available}\n"
        )

        output.write(
            f"TOTAL SUSPENDED DESTINATIONS: {total_suspended}\n"
        )

        output.write("\n")

        output.write("ALL DESTINATIONS\n")
        output.write("================\n")

        for destination in destinations:
            output.write(
                destination["label"] + "\n"
            )

        output.write("\n")

        output.write("AVAILABLE DESTINATIONS\n")
        output.write("======================\n")

        for destination_name in available:
            output.write(
                destination_name + "\n"
            )

        output.write("\n")

        output.write("SUSPENDED DESTINATIONS\n")
        output.write("======================\n")

        for destination_name in suspended:
            output.write(
                destination_name + "\n"
            )

        # Technical errors are kept separate so they aren't incorrectly
        # classified as suspended.
        if errors:
            output.write("\n")

            output.write("TECHNICAL ERRORS\n")
            output.write("================\n")

            for destination_name in errors:
                output.write(
                    destination_name + "\n"
                )

    # ---------------------------------------------------------------
    # Final console summary.
    # ---------------------------------------------------------------

    print("=" * 70)
    print("CHECK COMPLETE")
    print("=" * 70)

    print(
        f"Total destinations: {total_destinations}"
    )

    print(
        f"Available: {total_available}"
    )

    print(
        f"Suspended: {total_suspended}"
    )

    print(
        f"Technical errors: {total_errors}"
    )

    print(
        f"Results written to: {OUTPUT_FILE}"
    )

    print("=" * 70)

    if errors:
        print()
        print("Destinations with technical errors:")

        for destination_name in errors:
            print(
                f"  - {destination_name}"
            )


if __name__ == "__main__":
    main()
