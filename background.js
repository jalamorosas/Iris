async function toggleSpeechToText() {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    chrome.tabs.sendMessage(activeTab.id, { command: "toggleRecognition" });
    chrome.scripting.executeScript({
      target: { tabId: activeTab.id },
      function: function() {        
        const button = document.getElementById("speechToTextButton");
        if (button) {
          button.style.display = "block";
        }
      }
    });
  }
  
  chrome.action.onClicked.addListener(() => {
    toggleSpeechToText();
  });
 
  chrome.commands.onCommand.addListener((command) => {
    const utterance = new SpeechSynthesisUtterance(' yo yo yo');
     speechSynthesis.speak(utterance);
    if (command === "toggle_speech_to_text") {
      toggleSpeechToText();
    }
  });