from selenium import webdriver

chrome_options = webdriver.ChromeOptions()
chrome_options.add_extension('/path/to/your/extension.crx')

driver = webdriver.Chrome(options=chrome_options)
driver.get('https://example.com')

# Sending message to extension and receiving response
response = driver.execute_script('''
    // Sending message to extension
    chrome.runtime.sendMessage({ action: "getDOM" }, function(response) {
        console.log(response.dom);
        // You can send the response back to Python or process it here
    });
''')

print(response)

driver.quit()
