from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URL = "https://www.postesrpske.com/calc/kalkulator.html"

OUTPUT_FILE = "results.txt"
WEIGHT = "10"

SERVICE_VALUE = "DR"
TRAFFIC_VALUE = "M"

DESTINATION_SELECTOR = "#zemlja"
WEIGHT_SELECTOR = "#tezina"
CALCULATE_SELECTOR = "#dopisnicaU"

AVAILABLE_MARKER = "Price Stationery (postcard)"


def get_destinations(page):
    destination_select = page.locator(DESTINATION_SELECTOR)

    count = destination_select.locator("option").count()

    destinations = []

    for i in range(count):
        option = destination_select.locator("option").nth(i)

        text = option.inner_text().strip()
        value = option.get_attribute("value")

        # Ignore the empty/default option.
        if text and value:
            destinations.append((text, value))

    return destinations


def calculate_destination(page, destination_name, destination_value):
    print(f"Checking: {destination_name}")

    # Select destination.
    page.locator(DESTINATION_SELECTOR).select_option(destination_value)

    # The weight field is created dynamically after destination selection.
    try:
        page.locator(WEIGHT_SELECTOR).wait_for(
            state="visible",
            timeout=10000
        )
    except PlaywrightTimeoutError:
        print(f"  ERROR: Weight field did not appear for {destination_name}")
        return False

    # Enter 10 grams.
    weight = page.locator(WEIGHT_SELECTOR)

    weight.fill(WEIGHT)

    # Click Calculate.
    calculate_button = page.locator(CALCULATE_SELECTOR)

    try:
        calculate_button.wait_for(
            state="visible",
            timeout=10000
        )
    except PlaywrightTimeoutError:
        print(f"  ERROR: Calculate button did not appear for {destination_name}")
        return False

    calculate_button.click()

    # Give the calculator JavaScript time to update the result.
    page.wait_for_timeout(500)

    # Look for the exact availability marker anywhere in the visible page.
    body_text = page.locator("body").inner_text()

    if AVAILABLE_MARKER.lower() in body_text.lower():
        print("  AVAILABLE")
        return True

    print("  SUSPENDED")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={
                "width": 1400,
                "height": 1000
            }
        )

        print("=" * 70)
        print("Pošte Srpske calculator checker")
        print("=" * 70)

        print("\nOpening calculator...")
        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        page.wait_for_timeout(2000)

        # ------------------------------------------------------------
        # Select International traffic.
        # ------------------------------------------------------------
        print("Selecting International traffic...")

        page.locator("#vrsta_usl").select_option(TRAFFIC_VALUE)

        page.wait_for_timeout(1000)

        # ------------------------------------------------------------
        # Select Stationery (Postcard).
        # ------------------------------------------------------------
        print("Selecting Stationery (Postcard)...")

        page.locator("#uslugaM").select_option(SERVICE_VALUE)

        page.wait_for_timeout(1000)

        # ------------------------------------------------------------
        # Get all destinations.
        # ------------------------------------------------------------
        destinations = get_destinations(page)

        print(f"\nFound {len(destinations)} destinations.")

        if not destinations:
            raise RuntimeError("No destinations were found.")

        # ------------------------------------------------------------
        # Check every destination.
        # ------------------------------------------------------------
        available = []
        suspended = []

        for index, (destination_name, destination_value) in enumerate(
            destinations,
            start=1
        ):
            print(
                f"\n[{index}/{len(destinations)}] "
                f"{destination_name}"
            )

            try:
                is_available = calculate_destination(
                    page,
                    destination_name,
                    destination_value
                )

                if is_available:
                    available.append(destination_name)
                else:
                    suspended.append(destination_name)

            except Exception as e:
                print(
                    f"  ERROR while checking {destination_name}: {e}"
                )

                # If something unexpected happens, classify it as
                # suspended rather than silently omitting the country.
                suspended.append(destination_name)

        # ------------------------------------------------------------
        # Write results.txt.
        #
        # No timestamp is included because changedetection.io
        # should detect only actual calculator-result changes.
        # ------------------------------------------------------------
        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8",
            newline="\n"
        ) as f:

            f.write("ALL DESTINATIONS\n")
            f.write("================\n")

            for destination in destinations:
                f.write(f"{destination[0]}\n")

            f.write("\n")

            f.write("AVAILABLE DESTINATIONS\n")
            f.write("======================\n")

            for destination in available:
                f.write(f"{destination}\n")

            f.write("\n")

            f.write("SUSPENDED DESTINATIONS\n")
            f.write("======================\n")

            for destination in suspended:
                f.write(f"{destination}\n")

        # ------------------------------------------------------------
        # Summary.
        # ------------------------------------------------------------
        print("\n" + "=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)

        print(f"Total destinations:     {len(destinations)}")
        print(f"Available destinations: {len(available)}")
        print(f"Suspended destinations: {len(suspended)}")
        print(f"Results written to:     {OUTPUT_FILE}")

        browser.close()


if __name__ == "__main__":
    main()
