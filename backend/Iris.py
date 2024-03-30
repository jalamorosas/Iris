from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import openai
import os

class WebAgent:
    def __init__(self):
        self.browser = webdriver.Chrome()  # Make sure you have ChromeDriver installed and in PATH
        self.browser.set_window_size(1280, 1080)
        self.client = openai.OpenAI(api_key= '') #os.environ["OPENAI_API_KEY"])  # Initialize the OpenAI client
        
    def go_to_page(self, url):
        self.browser.get(url if "://" in url else "http://" + url)

    def scroll(self, direction):
        if direction == "up":
            self.browser.execute_script("window.scrollBy(0, -window.innerHeight);")
        elif direction == "down":
            self.browser.execute_script("window.scrollBy(0, window.innerHeight);")

    def click(self, selector):
        js = """
        links = document.getElementsByTagName("a");
        for (var i = 0; i < links.length; i++) {
            links[i].removeAttribute("target");
        }
        """
        self.browser.execute_script(js)

        try:
            element = self.browser.find_element(By.XPATH, selector)
            print(element)
            if element:
                element.click()
            else:
                print(f"Element with selector '{selector}' not found on the web page.")
        except Exception as e:
            print(f"Error while clicking element: {str(e)}")
            return str(e)

    def type_input(self, selector, text):
        try:
            element = self.browser.find_element(By.XPATH, selector)
            if element:
                element.click()
                element.send_keys(text)
            else:
                print(f"Element with selector '{selector}' not found on the web page.")
        except Exception as e:
            print(f"Error while typing into element: {str(e)}")
            return str(e)

    def enter(self):
        actions = webdriver.ActionChains(self.browser)
        actions.send_keys(Keys.ENTER)
        actions.perform()

    def wait_for_element(self, selector, timeout=10):
        try:
            element = WebDriverWait(self.browser, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            return element
        except Exception as e:
            print(f"Error while waiting for element: {str(e)}")
            return str(e)


    def preprocess_html_for_llm(self, soup: BeautifulSoup) -> str:
        """Preprocess the HTML by extracting navigational and content elements."""
        navigational_elements = ["a", "button", "input"]
        content_elements = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "section", "article", "header", "footer", "main", "aside", "nav"]
        
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

    def determine_next_step(self, prompt, webpage_content, completed_tasks, error_message=None):
        print(f"Determining the next step for prompt: {prompt}")
        completed_tasks_str = ", ".join(completed_tasks)

        if error_message:
            prompt += f"\nError: {error_message}\n"

        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "user", "content": f"You are Iris, an AI assistant designed to help people with visual disabilities navigate the web. Your role is to determine the next action to be taken in the web browser to complete the user's request. You should always start out by navigating to a website url before trying to select elements\n\nAvailable tools:\n- go_to_page(url): Navigate to the specified URL.\n- scroll(direction): Scroll the webpage up or down.\n- click(xpath): Click on an element specified by the CSS selector.\n- type_input(xpath, text): Type the specified text into an input field specified by the xpath.\ntype_input_enter(xpath, text): Type the specified text into an input field specified by the xpath and press Enter. Useful for performing searches. When using this function ensure that the id refers to an <input></input> tag\n- enter(): Press the Enter key.\n- wait_for_element(xpath, timeout): Wait for an element specified by xpath to be present on the page, with an optional timeout.\n \nTask: {prompt}\n\nCompleted actions so far:\n{completed_tasks_str}\n\nCurrent webpage content:\n{webpage_content}\n Select elements from the webpage using their xpath \nBased on the current state of the web page and the overall task, determine the best next action to perform. If you believe the task is complete based on the current webpage content, respond with:\n<action>\nCOMPLETE\n</action>\n\nOtherwise, respond with the next action to take in the following format:\n<action>\nACTION_NAME\nPARAMETER_1\nPARAMETER_2\n...\n</action>\n\nReplace ACTION_NAME with the name of the action (e.g., click, type_input) and include any necessary parameters on separate lines below the action name. If the action doesn't require any parameters, only include the action name.\n\nOnly respond with a one action at a time. Use the actions that have already been completed to help determine the next one you should perform. select elements that can be acted upon using selenium to move around the web page. ignore search-icon-legacy. When the webpage content reflects the completion of the task, respond with 'COMPLETE'. if you are on google use //textarea[@name='q'] to search\n\n"}
            ]
        )

        response_text = response.choices[0].message.content.strip()
        print(f"Raw response text: {response_text}")
        response_xml = BeautifulSoup(response_text, "html.parser")

        action_elem = response_xml.find("action")
        if action_elem:
            action_text = action_elem.get_text(strip=True)
            if "COMPLETE" in action_text or "complete" in action_text:
                print("Task completed.")
                return "complete"
            else:
                print(f"Extracted action: {action_text}")
                return action_text
        else:
            print("No action found in the response")
            return None

    def process_action(self, action_text):
        if action_text:
            print(f"Processing action: {action_text}")
            action_parts = action_text.split("\n")
            action_name = action_parts[0]
            parameters = action_parts[1:]

            if action_name == "COMPLETE" or action_name == "complete":
                return "complete"
            elif action_name == "go_to_page":
                url = parameters[0]
                self.go_to_page(url)
                return f"go_to_page {url}"
            elif action_name == "scroll":
                direction = parameters[0]
                self.scroll(direction)
                return f"scroll {direction}"
            elif action_name == "click":
                selector = parameters[0]
                self.click(selector)
                return f"click {selector}"
            elif action_name == "type_input":
                selector = parameters[0]
                text = parameters[1]
                self.type_input(selector, text)
                return f"type_input {selector} {text}"
            elif action_name == "type_input_enter":
                selector = parameters[0]
                text = parameters[1]
                self.type_input(selector, text)
                self.enter()
                return f"type_input_enter {selector} {text}"
            elif action_name == "enter":
                self.enter()
                return "enter"
            elif action_name == "wait_for_element":
                selector = parameters[0]
                timeout = int(parameters[1]) if len(parameters) > 1 else 10
                self.wait_for_element(selector, timeout)
                return f"wait_for_element {selector} {timeout}"
            else:
                print(f"Unknown action: {action_name}")
                return f"unknown_action {action_name}"
        else:
            print("No action found in the response")
            return "no_action_found"
    
    def run_voice(self, voice_prompt):
          # Main loop to prompt for actions and execute generated Selenium code
        while True:
            # Prompt the user for an action
            prompt = voice_prompt
            
            if prompt.lower() == "quit":
                break
            
            try:
                completed_tasks = []
                
                # Get the current webpage content using BeautifulSoup
                webpage_content = BeautifulSoup(self.browser.page_source, "html.parser")
                webpage_content = self.preprocess_html_for_llm(webpage_content)
                print(f"Current webpage content: {webpage_content}")
                
                while True:
                    # Determine the next step based on the current webpage content, task, and completed tasks
                    next_step_xml = self.determine_next_step(prompt, webpage_content, completed_tasks)

                    if next_step_xml is None:
                        print("Unable to determine the next step. Exiting.")
                        break

                    # Process the action received from Claude
                    result = self.process_action(next_step_xml)

                    if isinstance(result, str) and result.startswith("Error"):
                        # If an error occurs during element interaction, retry the action
                        error_message = result
                        next_step_xml = self.determine_next_step(prompt, webpage_content, completed_tasks, error_message)
                        result = self.process_action(next_step_xml)

                    if result == "complete":
                        print("Task completed.")
                         # Generate a summary of the current webpage content
                        webpage_summary = self.summarize_webpage_content(webpage_content)
                        print(f"Webpage summary: {webpage_summary}")
                        return webpage_summary
                        

                    # Add the completed task to the list
                    completed_tasks.append(result)

                    # Update the webpage content after executing the step
                    webpage_content = BeautifulSoup(self.browser.page_source, "html.parser")
                    webpage_content = self.preprocess_html_for_llm(webpage_content)
                    print(f"Updated webpage content: {webpage_content}")

                    sleep(3)
                
                print("Action performed successfully.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # Quit the WebDriver
        self.browser.quit() 

    def run(self):
        # Main loop to prompt for actions and execute generated Selenium code
        while True:
            # Prompt the user for an action
            prompt = input("Enter an action to perform in the browser (or 'quit' to exit): ")
            
            if prompt.lower() == "quit":
                break
            
            try:
                completed_tasks = []
                
                # Get the current webpage content using BeautifulSoup
                webpage_content = BeautifulSoup(self.browser.page_source, "html.parser")
                webpage_content = self.preprocess_html_for_llm(webpage_content)
                print(f"Current webpage content: {webpage_content}")
                
                while True:
                    # Determine the next step based on the current webpage content, task, and completed tasks
                    next_step_xml = self.determine_next_step(prompt, webpage_content, completed_tasks)

                    if next_step_xml is None:
                        print("Unable to determine the next step. Exiting.")
                        break

                    # Process the action received from Claude
                    result = self.process_action(next_step_xml)

                    if isinstance(result, str) and result.startswith("Error"):
                        # If an error occurs during element interaction, retry the action
                        error_message = result
                        next_step_xml = self.determine_next_step(prompt, webpage_content, completed_tasks, error_message)
                        result = self.process_action(next_step_xml)

                    if result == "complete":
                        print("Task completed.")
                        break

                    # Add the completed task to the list
                    completed_tasks.append(result)

                    # Update the webpage content after executing the step
                    webpage_content = BeautifulSoup(self.browser.page_source, "html.parser")
                    webpage_content = self.preprocess_html_for_llm(webpage_content)
                    print(f"Updated webpage content: {webpage_content}")

                    sleep(3)
                
                print("Action performed successfully.")
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # Quit the WebDriver
        self.browser.quit()

if __name__ == "__main__":
    agent = WebAgent()
    agent.run()
    agent.close()