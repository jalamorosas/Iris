from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import anthropic

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")

# Initialize the Chrome WebDriver
driver = webdriver.Chrome(options=chrome_options)

# Initialize the Anthropic client
client = anthropic.Anthropic(api_key="")


# Helper functions

def remove_non_navigational_elements(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove HTML elements that are not typically used for navigation."""
    non_navigational_elements = set(
        [
            "img",
            "iframe",
            "embed",
            "object",
            "video",
            "audio",
            "canvas",
            "figure",
            "picture",
            "source",
            "track",
            "map",
            "area",
            "table",
            "form",
            "input",
            "textarea",
            "select",
            "option",
            "label",
            "fieldset",
            "legend",
            "datalist",
            "output",
            "meter",
            "progress",
            "details",
            "summary",
            "dialog",
            "script"
            "style"
        ]
    )

    for element in non_navigational_elements:
        for tag in soup.find_all(element):
            tag.decompose()

    return soup

def remove_empty_elements(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove empty elements without any content."""
    empty_elements = soup.find_all(lambda tag: not tag.contents and not tag.text.strip())
    for element in empty_elements:
        element.decompose()

    return soup

def simplify_attributes(soup: BeautifulSoup) -> BeautifulSoup:
    """Simplify attributes by removing unnecessary ones."""
    unnecessary_attributes = set(["alt", "title", "tabindex", "role", "target", "rel"])

    for tag in soup.find_all(True):
        for attr in unnecessary_attributes:
            if attr in tag.attrs:
                del tag[attr]

    return soup

def preprocess_html_for_llm(soup: BeautifulSoup) -> str:
    """Preprocess the HTML by removing unnecessary elements and attributes."""
    soup = remove_non_navigational_elements(soup)
    soup = remove_empty_elements(soup)
    soup = simplify_attributes(soup)
    return soup.prettify()

def get_steps(prompt):
    print(f"Getting steps for prompt: {prompt}")
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"Put the steps you write for this task in between <steps></steps> tags. Break down the following task into individual steps: {prompt}. Provide the steps in a numbered list format.  "}
        ]
    )
    if message.content and isinstance(message.content, list):
        steps_text = message.content[0].text.strip()
        print(f"Raw steps text: {steps_text}")
        steps_xml = BeautifulSoup(steps_text, "html.parser")
        steps = steps_xml.find("steps").get_text(strip=True).split("\n")
        print(f"Extracted steps: {steps}")
        return steps
    else:
        print("No steps found in the response")
        return []

def determine_next_step(prompt, webpage_content, completed_tasks):
    print(f"Determining the next step for prompt: {prompt}")
    completed_tasks_str = ", ".join(completed_tasks)
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"Based on the current state of the web page and the overall task, determine the best next step to perform. Only respond with a single step to complete. Based on what is in the current webpage content if you believe the task is complete, respond with <complete>Task completed</complete>. Otherwise, put the next step in between <step></step> tags. Task: {prompt}. Current webpage content: {webpage_content}. Completed tasks: {completed_tasks_str}. Do not repeat any of the completed tasks. Stop when the task appears to be completed."}
        ]
    )
    if message.content and isinstance(message.content, list):
        response_text = message.content[0].text.strip()
        print(f"Raw response text: {response_text}")
        response_xml = BeautifulSoup(response_text, "html.parser")
        
        if response_xml.find("complete"):
            print("Task completed.")
            return "complete"
        else:
            step = response_xml.find("step").get_text(strip=True)
            print(f"Extracted step: {step}")
            return step
    else:
        print("No step or completion status found in the response")
        return None

def get_selenium_code(prompt, webpage_content, error_message=None):
    print(f"Getting Selenium code for step: {prompt}")
    
    if error_message:
        messages = [
            {"role": "user", "content": f"The previous Selenium code encountered an error: {error_message}. Please fix the code to resolve the error. Please wrap the selenium code you write based on the prompt in <code></code> tags. Generate Selenium code to perform the following step: {prompt}. Use the provided webpage content to select elements: {webpage_content}. Provide only the raw Selenium code without any additional text, explanations, or formatting. The code should be ready to execute without any modifications. If the step involves navigating to a URL, make sure to include the complete URL with the appropriate protocol prefix (e.g., 'https://')."}
        ]
    else:
        messages = [
            {"role": "user", "content": f"Please wrap the selenium code you write based on the prompt in <code></code> tags. Generate Selenium code to perform the following step: {prompt}. Use the provided webpage content to select elements: {webpage_content}. Provide only the raw Selenium code without any additional text, explanations, or formatting. The code should be ready to execute without any modifications. If the step involves navigating to a URL, make sure to include the complete URL with the appropriate protocol prefix (e.g., 'https://')."}
        ]
    
    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=messages
    )
    
    if message.content and isinstance(message.content, list):
        code_text = message.content[0].text.strip()
        print(f"Raw code text: {code_text}")
        code_xml = BeautifulSoup(code_text, "html.parser")
        code = code_xml.find("code").get_text(strip=True)
        print(f"Extracted code: {code}")
        return code
    else:
        print("No code found in the response")
        return ""

# Main loop to prompt for actions and execute generated Selenium code
while True:
    # Prompt the user for an action
    prompt = input("Enter an action to perform in the browser (or 'quit' to exit): ")
    
    if prompt.lower() == "quit":
        break
    
    try:
        completed_tasks = []
        
        # Get the current webpage content using BeautifulSoup
        webpage_content = BeautifulSoup(driver.page_source, "html.parser")
        webpage_content = preprocess_html_for_llm(webpage_content)
        print(f"Current webpage content: {webpage_content}")
        
        while True:
            # Determine the next step based on the current webpage content, task, and completed tasks
            next_step = determine_next_step(prompt, webpage_content, completed_tasks)
            
            if next_step == "complete":
                print("Task completed.")
                break
            elif next_step is None:
                print("Unable to determine the next step. Exiting.")
                break
            
            print(f"Next step: {next_step}")
            
            error_message = None
            while True:
                # Get the Selenium code for the next step
                selenium_code = get_selenium_code(next_step, webpage_content, error_message)
                print(f"Generated Selenium code: {selenium_code}")
                
                try:
                    # Execute the generated Selenium code
                    exec(selenium_code, {'driver': driver, 'By': By, 'WebDriverWait': WebDriverWait, 'EC': EC})
                    completed_tasks.append(next_step)  # Add the completed task to the list
                    break  # If no error occurs, break the loop and move to the next step
                except Exception as e:
                    error_message = str(e)
                    print(f"Error: {error_message}")
                    # If an error occurs, prompt the AI to fix the code and retry
            
            # Update the webpage content after executing the step
            webpage_content = BeautifulSoup(driver.page_source, "html.parser")
            webpage_content = preprocess_html_for_llm(webpage_content)
            print(f"Updated webpage content: {webpage_content}")
        
        print("Action performed successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")

# Quit the WebDriver
driver.quit()