const BASE_URL = "http://127.0.0.1:8000"

const eventStatus = document.querySelector("#status")
eventStatus.classList.add("hidden")

async function uploadFile(event) {
        event.preventDefault()
    try {
        eventStatus.classList.remove("hidden")
        eventStatus.textContent = "Uploading please wait..."

        const formData = new FormData()
        const fileInput = document.querySelector('#file-input')

        if(!fileInput.files.length){
            eventStatus.textContent = 'Please select a file to upload'
            console.log("No File uploaded")

            return
        }

        formData.append("file", fileInput.files[0])     //file matches FastAPI parameter name

        const response = await fetch(`${BASE_URL}/upload`, {
            method : "POST",
            body : formData
        })
        
        const data = await response.json()
        if(!response.ok){
            throw new Error(data.detail || `HTTP Error ${response.status}`);
        }

        // Upload success
        eventStatus.textContent = "Upload Successful"
        setTimeout(() => {
            eventStatus.textContent = ''
            eventStatus.classList.add("hidden")
            }, 6000);

        console.log(data)
        loadMessages(data)
        return data
    } catch (error) {
        eventStatus.textContent = `Error: ${error.message}`
        throw error
    }
}


const uploadForm = document.querySelector('#upload-form')
uploadForm.addEventListener('submit', uploadFile)



const chatMessages = document.querySelector('#chat-messages')
async function loadMessages(messages) {
    messages.forEach(message => {
        const messageDiv = document.createElement('div')
        const messageText = document.createElement('span')
        const messageTime = document.createElement('sub')
        const messageSender = document.createElement('sup')



        messageText.textContent = message.message
        messageTime.textContent = message.time.replace(/:\d{2}(?=\s)/, "");
        messageSender.textContent = message.sender
        

        messageDiv.append(messageTime, messageText, messageSender)

        

        chatMessages.append(messageDiv)
    });
}






// Add loading/success/error states
// add logging and exception handling in fastapi