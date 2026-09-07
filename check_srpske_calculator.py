from playwright.sync_api import sync_playwright
import time

URL = "https://www.postesrpske.com/calc/kalkulator.html"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        print("=" * 80)
        print("OPENING CALCULATOR")
        print("=" * 80)

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # ------------------------------------------------------------
        # Select International traffic
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("SELECTING INTERNATIONAL TRAFFIC")
        print("=" * 80)

        page.locator("#vrsta_usl").select_option("M")
        page.wait_for_timeout(1500)

        print("Selected International traffic")

        # ------------------------------------------------------------
        # Select Stationery (Postcard)
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("SELECTING STATIONERY (POSTCARD)")
        print("=" * 80)

        page.locator("#uslugaM").select_option("DR")
        page.wait_for_timeout(1500)

        print("Selected Stationery (Postcard)")

        # ------------------------------------------------------------
        # Destination inventory
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("DESTINATION INVENTORY")
        print("=" * 80)

        destination_select = page.locator("#zemlja")

        count = destination_select.locator("option").count()
        print(f"Total option elements: {count}")

        destinations = []

        for i in range(count):
            option = destination_select.locator("option").nth(i)

            text = option.inner_text().strip()
            value = option.get_attribute("value")

            if text and value:
                destinations.append((text, value))

        print(f"Destinations found: {len(destinations)}")

        if not destinations:
            print("ERROR: No destinations found.")
            browser.close()
            return

        print("\nFirst 10 destinations:")

        for i, (text, value) in enumerate(destinations[:10]):
            print(f"  {i}: text={text!r}, value={value!r}")

        # ------------------------------------------------------------
        # Select FIRST destination
        # ------------------------------------------------------------
        first_name, first_value = destinations[0]

        print("\n" + "=" * 80)
        print("SELECTING FIRST DESTINATION")
        print("=" * 80)

        print(f"Destination text: {first_name}")
        print(f"Destination value: {first_value}")

        destination_select.select_option(first_value)

        # Give JavaScript plenty of time to react.
        page.wait_for_timeout(3000)

        print("Destination selected.")

        # ------------------------------------------------------------
        # Inspect page after destination selection
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("PAGE AFTER DESTINATION SELECTION")
        print("=" * 80)

        print("\nVisible page text:")
        print("-" * 80)
        print(page.locator("body").inner_text())
        print("-" * 80)

        # ------------------------------------------------------------
        # Inspect inputs
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("INPUT ELEMENTS AFTER DESTINATION SELECTION")
        print("=" * 80)

        inputs = page.locator("input")
        input_count = inputs.count()

        print(f"Input count: {input_count}")

        for i in range(input_count):
            el = inputs.nth(i)

            try:
                print(f"\nINPUT #{i}")
                print(f"  type={el.get_attribute('type')!r}")
                print(f"  id={el.get_attribute('id')!r}")
                print(f"  name={el.get_attribute('name')!r}")
                print(f"  class={el.get_attribute('class')!r}")
                print(f"  value={el.input_value()!r}")
                print(f"  placeholder={el.get_attribute('placeholder')!r}")
                print(f"  visible={el.is_visible()}")
            except Exception as e:
                print(f"  ERROR inspecting input: {e}")

        # ------------------------------------------------------------
        # Inspect selects
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("SELECT ELEMENTS AFTER DESTINATION SELECTION")
        print("=" * 80)

        selects = page.locator("select")
        select_count = selects.count()

        print(f"Select count: {select_count}")

        for i in range(select_count):
            el = selects.nth(i)

            try:
                print(f"\nSELECT #{i}")
                print(f"  id={el.get_attribute('id')!r}")
                print(f"  name={el.get_attribute('name')!r}")
                print(f"  visible={el.is_visible()}")
                print(f"  selected={el.input_value()!r}")
            except Exception as e:
                print(f"  ERROR inspecting select: {e}")

        # ------------------------------------------------------------
        # Search for weight-related elements AFTER destination selection
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("WEIGHT-RELATED ELEMENTS AFTER DESTINATION SELECTION")
        print("=" * 80)

        all_elements = page.locator("*")
        element_count = all_elements.count()

        found_weight = 0

        for i in range(element_count):
            el = all_elements.nth(i)

            try:
                text = el.inner_text(timeout=100).strip()
            except Exception:
                text = ""

            attrs = []

            for attr in ["id", "name", "class", "type", "placeholder", "value"]:
                try:
                    value = el.get_attribute(attr)
                except Exception:
                    value = None

                if value:
                    attrs.append(f"{attr}={value!r}")

            combined = (text + " " + " ".join(attrs)).lower()

            if any(word in combined for word in [
                "weight",
                "mass",
                "gram",
                "grams",
                "težina",
                "grama",
                "gramaža"
            ]):
                if el.is_visible():
                    found_weight += 1

                    print(f"\nELEMENT #{i}: <{el.evaluate('(e) => e.tagName').lower()}>")
                    print(f"  text={text[:500]!r}")
                    print(f"  {' '.join(attrs)}")

        print(f"\nVisible weight-related elements found: {found_weight}")

        # ------------------------------------------------------------
        # Inspect buttons and clickable elements
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("BUTTON / CLICKABLE ELEMENTS")
        print("=" * 80)

        buttons = page.locator("button, input[type='button'], input[type='submit'], a")
        button_count = buttons.count()

        print(f"Potential clickable elements: {button_count}")

        for i in range(button_count):
            el = buttons.nth(i)

            try:
                if not el.is_visible():
                    continue

                tag = el.evaluate("(e) => e.tagName")
                text = el.inner_text(timeout=100).strip()

                print(f"\nCLICKABLE #{i}")
                print(f"  tag={tag!r}")
                print(f"  text={text!r}")
                print(f"  id={el.get_attribute('id')!r}")
                print(f"  name={el.get_attribute('name')!r}")
                print(f"  type={el.get_attribute('type')!r}")
                print(f"  value={el.get_attribute('value')!r}")
                print(f"  class={el.get_attribute('class')!r}")

            except Exception as e:
                print(f"  ERROR: {e}")

        # ------------------------------------------------------------
        # Save HTML for inspection in GitHub Actions
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("SAVING HTML")
        print("=" * 80)

        html = page.content()

        with open("calculator_after_destination.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("Saved calculator_after_destination.html")

        # ------------------------------------------------------------
        # Take screenshot
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("TAKING SCREENSHOT")
        print("=" * 80)

        page.screenshot(
            path="calculator_after_destination.png",
            full_page=True
        )

        print("Saved calculator_after_destination.png")

        # ------------------------------------------------------------
        # Do NOT create results.txt yet.
        # This is still a diagnostic run.
        # ------------------------------------------------------------
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)

        browser.close()


if __name__ == "__main__":
    main()
