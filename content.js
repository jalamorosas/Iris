//import './styles.css'; // Import CSS file
const button = document.createElement("button");
button.id = "speechToTextButton";
button.textContent = "🎙️";
button.style.position = "fixed";
button.style.bottom = "20px";
button.style.right = "20px";
button.style.zIndex = "9999";
button.style.background = "#000";
button.style.color = "#fff";
button.style.border = "none";
button.style.borderRadius = "50%";
button.style.width = "50px";
button.style.height = "50px";
button.style.fontSize = "24px";
button.style.cursor = "pointer";
button.style.display = "none"; 
document.body.appendChild(button);

let isDragging = false;
let hasDragged = false;
let offsetX, offsetY;

// Function to handle mouse down event
function handleMouseDown(e) {
  // Calculate offset between mouse position and button position
  offsetX = e.clientX - button.offsetLeft;
  offsetY = e.clientY - button.offsetTop;
  // Set dragging state to true
  isDragging = true;
}

// Function to handle mouse move event
function handleMouseMove(e) {
  // If dragging, update button position based on mouse position
  if (isDragging) {
    button.style.left = (e.clientX - offsetX) + 'px';
    button.style.top = (e.clientY - offsetY) + 'px';
    hasDragged = true;

  }
}

// Function to handle mouse up event
function handleMouseUp(e) {
  // Reset dragging state to false
  isDragging = false;
}

// Function to handle button click event
function handleButtonClick(e) {
  // Perform different action when button is clicked
  // e.preventDefault();
  if (!hasDragged) {
    toggleRecognition();
  }
  hasDragged = false;

}

// Add event listeners for mouse events
button.addEventListener('mousedown', handleMouseDown);
button.addEventListener('mouseup', handleMouseUp);
document.addEventListener('mousemove', handleMouseMove);

// Add event listener for button click
button.addEventListener('click', handleButtonClick);

// Function to handle button click after dragging
// button.addEventListener("click", (e) => {
//     if (!isDragging) {
//         if (activeElement) activeElement.focus();
//         toggleRecognition();
//     }
// });

// Start or stop speech recognition
// button.addEventListener("mousedown", (event) => {
//     // Save the currently active element during the mousedown phase
//     activeElement = document.activeElement;
// });
// button.addEventListener("mouseup", (e) => {
//   if (!isDragging && !clickTimeout) {
//       if (activeElement) activeElement.focus();
//       toggleRecognition();
//   }
// });

function insertTextAtCursor(text) {
    const el = document.activeElement;
    const tagName = el.tagName.toLowerCase();

    if (tagName === "input" || tagName === "textarea") {
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const value = el.value;

        el.value = value.slice(0, start) + text + value.slice(end);
        el.selectionStart = el.selectionEnd = start + text.length;
    } else if (
        tagName === "div" &&
        el.getAttribute("contenteditable") === "true"
    ) {
        const selection = window.getSelection();
        const range = selection.getRangeAt(0);

        range.deleteContents();
        const textNode = document.createTextNode(text);
        range.insertNode(textNode);
        range.setStartAfter(textNode);
        range.setEndAfter(textNode);
        selection.removeAllRanges();
        selection.addRange(range);
    }
    // Make sure to trigger the website's own input listening events

    const inputEvent = new Event("input", { bubbles: true, cancelable: true });
    el.dispatchEvent(inputEvent);
    const changeEvent = new Event("change", {
        bubbles: true,
        cancelable: true,
    });
    el.dispatchEvent(changeEvent);
}

if (!window.recognition) {
    window.recognition = new webkitSpeechRecognition();
}
recognition.lang = "en-US";
// recognition.lang = "zh-CN";
recognition.interimResults = false;
recognition.maxAlternatives = 1;
recognition.continuous = true;

recognition.onresult = (event) => {
    console.log("End of recognition");

    const transcript = event.results[event.results.length - 1][0].transcript;
    console.log(transcript);
    // Check if the send keyword is included
    if (transcript.toLowerCase().includes("stop")) {
        toggleRecognition();
        const el = document.activeElement;
        const e = new KeyboardEvent("keydown", {
            keyCode: 13,
            bubbles: true,
            cancelable: true,
        });

        el.dispatchEvent(e);
        //toggleRecognition();

        return;
    }
    console.log(transcript)
    //var textToSpeak = prompt("wyoyoy");
    //chrome.runtime.sendMessage({ action: "speak", text: "ell" });
    //chrome.tts.speak("hello");
    insertTextAtCursor(transcript);
    sendSpeechToFlask(transcript);
};

recognition.onend = () => {
    console.log("Ended Rec");
    if (!recognition.manualStop) {
        setTimeout(() => {
            recognition.start();
            console.log("Ending recording");
        }, 100);
    }
};

chrome.runtime.onMessage.addListener((request) => {
    if (request.command === "toggleRecognition") {
        toggleRecognition();
    }
});

function startRotating() {
    button.style.animation = "rotate 2s linear infinite";
}

// Function to stop rotating animation
function stopRotating() {
    button.style.animation = "none";
}

function toggleRecognition() {
  console.log("toggle");
  if (!recognition.manualStop) {
      recognition.manualStop = true;
      recognition.stop();
      button.style.background = "#000";
      // Shrink the button
      button.style.width = "50px";
      button.style.height = "50px";
      stopRotating();
  } else {
      recognition.manualStop = false;
      recognition.start();
      button.style.background = "#f00";
      // Grow the button
      button.style.width = "60px";
      button.style.height = "60px";
      startRotating();
  }
}

function sendSpeechToFlask(text){
    fetch('http://127.0.0.1:5001/generate_text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    })
        .then(response => response.json())
        .then(data => {
            const utterance = new SpeechSynthesisUtterance(data['text']);
            speechSynthesis.speak(utterance);
            console.log('Response from Flask:', data);
        })
        .catch(error=> console.error('Error:', error));
}