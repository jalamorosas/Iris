from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import anthropic
import os
import time

class WebAgent:
    def __init__(self):
        self.browser = sync_playwright().start().chromium.launch(headless=False)
        self.page = self.browser.new_page()
        self.page.set_viewport_size({"width": 1280, "height": 1080})
        self.client = anthropic.Anthropic(api_key="YOUR_API_KEY")

    def go_to_page(self, url):
        self.page.goto(url=url if "://" in url else "http://" + url)

    def scroll(self, direction):
        if direction == "up":
            self.page.evaluate('window.scrollBy(0, -window.innerHeight)')
        elif direction == "down":
            self.page.evaluate('window.scrollBy(0, window.innerHeight)')
    
    def click(self, selector):
        js = """
        links = document.getElementsByTagName("a");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("target");
        }
        """
        self.page.evaluate(js)
        
        element = self.page.query_selector(selector)
        if element:
            x = element.get("center_x")
            y = element.get("center_y")
            self.page.mouse.click(x, y)
        else:
            print(f"Element with selector '{selector}' not found on the web page.")
        
    def type_input(self, selector, text):
        element = self.page.query_selector(selector)
        if element:
            element.click()
            element.type(text)
        else:
            print(f"Element with selector '{selector}' not found on the web page.")
    
    def enter(self):
        self.page.keyboard.press("Enter")

    def preprocess_html_for_llm(self, soup: BeautifulSoup) -> str:
        """Preprocess the HTML by extracting navigational and content elements."""
        navigational_elements = ["a", "button", "input"]
        content_elements = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div", "section", "article", "header", "footer", "main", "aside", "nav"]
        
        # Find all navigational and content elements
        elements = soup.find_all(navigational_elements + content_elements)
        
        # Create a new soup object to store the simplified HTML
        simplified_soup = BeautifulSoup("", "html.parser")
        
        # Extract relevant attributes
        for element in elements:
            if element.name in navigational_elements:
                if element.name == "input" and element.get("type") not in ["submit", "button"]:
                    continue
                
                simplified_element = simplified_soup.new_tag(element.name)
                
                if "id" in element.attrs:
                    simplified_element["id"] = element["id"]
                if "class" in element.attrs:
                    simplified_element["class"] = element["class"]
                
                if element.name == "a" and element.get("href"):
                    simplified_element["href"] = element["href"]
                elif element.name == "input":
                    simplified_element["type"] = element.get("type", "submit")
                    simplified_element["value"] = element.get("value", "")
                
                simplified_element.string = element.get_text(strip=True)
                simplified_soup.append(simplified_element)
            
            elif element.name in content_elements:
                simplified_element = simplified_soup.new_tag(element.name)
                
                if "id" in element.attrs:
                    simplified_element["id"] = element["id"]
                if "class" in element.attrs:
                    simplified_element["class"] = element["class"]
                
                simplified_element.string = element.get_text(strip=True)
                simplified_soup.append(simplified_element)
        
        return simplified_soup.prettify()

    def determine_next_step(self, prompt, webpage_content, completed_tasks):
        completed_tasks_str = ", ".join(completed_tasks)
        prompt_text = f"""
                You are an agent controlling a browser. You are given:

                (1) an objective that you are trying to achieve
                (2) the URL of your current web page
                (3) a simplified text description of what's visible in the browser window (more on that below)

            You can issue these commands:
                SCROLL UP - scroll up one page
                SCROLL DOWN - scroll down one page
                CLICK selector - click on a given element using CSS selector
                TYPE selector "TEXT" - type the specified text into the input with CSS selector
                TYPESUBMIT selector "TEXT" - same as TYPE above, except then it presses ENTER to submit the form

            Example:

            html looks like this:
            <input class="gNO89b" type="submit" value="Google Search">
            </input>
            If you're on this page and you want to google search for "cats", you might issue the command:
            TYPESUBMIT gNO89b "cats"
            Based on your given objective, issue whatever command you believe will get you closest to achieving your goal.
            You always start on Google; you should submit a search query to Google that will take you to the best page for
            achieving your objective. And then interact with that page to achieve your objective.

            Don't try to interact with elements that you can't see.
            Based on the current state of the web page and the overall task, determine the best next step to perform. Choose from the following actions: SCROLL UP, SCROLL DOWN, CLICK selector, TYPE selector 'TEXT', TYPESUBMIT selector 'TEXT', or COMPLETE if the task is finished. Only respond with a single action. Task: {prompt}. Current webpage content: {webpage_content}. Completed tasks: {completed_tasks_str}. Do not repeat any of the completed tasks. Stop when the task appears to be completed.
            """
        print(f"Determining the next step for prompt: {prompt}")
        
        message = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt_text}",
                }
            ],
        )
        if message.content and isinstance(message.content, list):
            response_text = message.content[0].text.strip()
            print(f"Raw response text: {response_text}")
            if response_text.lower() == "complete":
                print("Task completed.")
                return "complete"
            else:
                return response_text
        else:
            print("No action or completion status found in the response")
            return None

    def process_command(self, command):
        try:
            if command.startswith("SCROLL UP"):
                print("Executing command: SCROLL UP")
                self.scroll("up")
            elif command.startswith("SCROLL DOWN"):
                print("Executing command: SCROLL DOWN")
                self.scroll("down")
            elif command.startswith("CLICK"):
                _, selector = command.split(" ", 1)
                print(f"Executing command: CLICK {selector}")
                self.click(selector)
            elif command.startswith("TYPE") or command.startswith("TYPESUBMIT"):
                _, selector, text = command.split(" ", 2)
                text = text.strip('"')
                if command.startswith("TYPESUBMIT"):
                    print(f"Executing command: TYPESUBMIT {selector} with text: {text}")
                    self.type_input(selector, text)
                    self.enter()
                else:
                    print(f"Executing command: TYPE {selector} with text: {text}")
                    self.type_input(selector, text)
            else:
                print(f"Invalid command: {command}. Skipping.")
        except Exception as e:
            print(f"Error executing command: {command}")
            print(f"Error details: {str(e)}")
            raise e
        
        time.sleep(2)

    def run(self):
        while True:
            prompt = input("Enter an action to perform in the browser (or 'quit' to exit): ")

            if prompt.lower() == "quit":
                break

            try:
                completed_tasks = []

                # Get the current webpage content using BeautifulSoup
                webpage_content = BeautifulSoup(self.page.content(), "html.parser")
                webpage_content = self.preprocess_html_for_llm(webpage_content)
                print(f"Current webpage content: {webpage_content}")

                while True:
                    # Determine the next step based on the current webpage content, task, and completed tasks
                    next_step = self.determine_next_step(prompt, webpage_content, completed_tasks)

                    if next_step == "complete":
                        print("Task completed.")
                        break
                    elif next_step is None:
                        print("Unable to determine the next step. Exiting.")
                        break

                    print(f"Playwright code: {next_step}")

                    # Get the Playwright code for the next step
                    self.process_command(next_step)

                    # Update the webpage content after executing the step
                    webpage_content = BeautifulSoup(self.page.content(), "html.parser")
                    webpage_content = self.preprocess_html_for_llm(webpage_content)
                    print(f"Updated webpage content: {webpage_content}")

                print("Action performed successfully.")
            except Exception as e:
                print(f"Error: {str(e)}")

    def close(self):
        self.browser.close()
        self.playwright.stop()

if __name__ == "__main__":
    agent = WebAgent()
    agent.go_to_page("https://www.google.com")
    agent.run()
    agent.close()