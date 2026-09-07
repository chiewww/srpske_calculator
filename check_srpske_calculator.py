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

    if not modal.is_visible():
        return

    close_button = modal.locator(MODAL_CLOSE_SELECTOR)

    if close_button.count() > 0 and close_button.first.is_visible():
        close_button.first.click(timeout=5000)

        try:
            page.locator(".msgBoxBackGround:visible").wait_for(
                state="hidden",
                timeout=5000
            )
        except PlaywrightTimeoutError:
            # If the site's JavaScript removes the modal slightly differently,
            # give it a short additional moment.
            page.wait_for_timeout(300)

    else:
        # Fallback: press Escape if the close image cannot be clicked.
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)


def calculate_destination(page, destination_name):
    """
    Select a destination, enter weight 10g, calculate, read the modal,
    classify the destination, and close the modal.
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

    # Make sure the result modal from a previous calculation is gone.
    visible_modal = page.locator(MODAL_SELECTOR)

    if visible_modal.count() > 0 and visible_modal.first.is_visible():
        close_result_modal(page)

    # Click Calculate.
    page.locator(CALCULATE_SELECTOR).click(timeout=10000)

    # Wait for the result modal to appear.
    modal = page.locator(MODAL_SELECTOR)

    try:
        modal.wait_for(
            state="visible",
            timeout=10000
        )
    except PlaywrightTimeoutError:
        print("  ERROR: Calculation result modal did not appear.")
        return "error"

    # Read the result specifically from the modal.
    content = modal.locator(MODAL_CONTENT_SELECTOR)

    if content.count() > 0:
        result_text = content.inner_text()
    else:
        result_text = modal.inner_text()

    print("  Result:")
    print("  " + result_text.replace("\n", "\n  "))

    # Determine availability from the actual calculation result.
    if AVAILABLE_MARKER.lower() in result_text.lower():
        status = "available"
        print("  AVAILABLE")
    else:
        status = "suspended"
        print("  SUSPENDED")

    # IMPORTANT:
    # Close the result modal before moving to the next destination.
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

        # Shorter default timeout so a genuine problem doesn't stall
        # the entire GitHub Actions run for many minutes.
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

        # Get all destination names from the dropdown.
        destination_select = page.locator(DESTINATION_SELECTOR)

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

        print(f"Found {len(destinations)} destinations.")
        print()

        for index, destination in enumerate(destinations, start=1):
            destination_name = destination["label"]

            print(
                f"[{index}/{len(destinations)}] "
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

                # Try to recover from any modal/overlay that may have
                # been left behind by the calculator.
                try:
                    close_result_modal(page)
                except Exception:
                    pass

            print()

        browser.close()

    # ---------------------------------------------------------------
    # Write results.txt
    #
    # No timestamp is included because changedetection.io should only
    # detect actual changes to the calculator results.
    # ---------------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as output:

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
            output.write(destination_name + "\n")

        output.write("\n")

        output.write("SUSPENDED DESTINATIONS\n")
        output.write("======================\n")

        for destination_name in suspended:
            output.write(destination_name + "\n")

    print("=" * 70)
    print("CHECK COMPLETE")
    print("=" * 70)
    print(f"Total destinations: {len(destinations)}")
    print(f"Available: {len(available)}")
    print(f"Suspended: {len(suspended)}")
    print(f"Technical errors: {len(errors)}")
    print(f"Results written to: {OUTPUT_FILE}")
    print("=" * 70)

    if errors:
        print()
        print("Destinations with technical errors:")
        for destination_name in errors:
            print(f"  - {destination_name}")


if __name__ == "__main__":
    main()
