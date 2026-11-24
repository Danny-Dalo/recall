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
    chatMessages.replaceChildren()

    if (!Array.isArray(messages) || messages.length === 0) {
        const emptyMessage = document.createElement('p')
        emptyMessage.className = 'm-auto max-w-xs text-center text-sm leading-6 text-[#78867d]'
        emptyMessage.textContent = 'No messages found in this chat.'
        chatMessages.append(emptyMessage)
        return
    }

    const fragment = document.createDocumentFragment()
    let currentDate = null

    messages.forEach(message => {
        const chatProfile = document.querySelector('#chat-profile')
        chatProfile.textContent = message.sender

        if (message.date && message.date !== currentDate) {
            currentDate = message.date
            const dateDivider = document.createElement('div')
            dateDivider.className = 'sticky top-0 z-10 self-center rounded-full bg-white/90 px-3 py-1 text-[11px] font-medium text-[#68766e] shadow-sm'
            dateDivider.textContent = message.date
            fragment.append(dateDivider)
        }

        const isOwnMessage = message.sender === 'You'
        const messageRow = document.createElement('div')
        messageRow.className = `flex w-full ${isOwnMessage ? 'justify-end' : 'justify-start'}`

        const bubble = document.createElement('article')
        bubble.className = `max-w-[88%] rounded-2xl px-3.5 py-2 shadow-sm sm:max-w-[75%] ${isOwnMessage ? 'rounded-br-md bg-[#d9fdd3]' : 'rounded-bl-md bg-white'}`

        if (!isOwnMessage && message.sender) {
            const sender = document.createElement('p')
            sender.className = 'mb-1 text-xs font-semibold text-[#16856b]'
            sender.textContent = message.sender
            bubble.append(sender)
        }

        const messageText = document.createElement('p')
        messageText.className = 'whitespace-pre-wrap break-words text-sm leading-5 text-[#26332b]'
        messageText.textContent = message.message ?? ''

        const messageTime = document.createElement('p')
        messageTime.className = 'mt-1 text-right text-[10px] text-[#718078]'
        messageTime.textContent = message.time ? message.time.replace(/:\d{2}(?=\s)/, '') : ''

        bubble.append(messageText, messageTime)
        messageRow.append(bubble)
        fragment.append(messageRow)
    })

    chatMessages.append(fragment)
    chatMessages.scrollTop = chatMessages.scrollHeight
}






// Add loading/success/error states
// add logging and exception handling in fastapi
