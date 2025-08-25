document.getElementById('saveButton').addEventListener('click', function() {
    const formData = new FormData();
    const file1Input = document.getElementById('file1Input');
    const file2Input = document.getElementById('file2Input');
    const termsUpload = document.getElementById('terms-upload');

    const settingsData = {
        id: 1, // Assuming a single settings entry
        switch1: document.getElementById('1').checked,
        switch2: document.getElementById('2').checked,
        switch3: document.getElementById('3').checked,
        switch4: document.getElementById('4').checked,
        switch5: document.getElementById('5').checked,
        switch6: document.getElementById('6').checked,
        freeTime: document.getElementById('freeTime').value,
        freeTimeRepeat: document.getElementById('freeTimeRepeat').value,
        docx: document.getElementById('MAXFIYLIK').value,
        phone: document.getElementById('supportPhone').value,
        text1: document.getElementById('entryTitle').value,
        text2: document.getElementById('connectButtonText').value
    };

    formData.append('settingsData', JSON.stringify(settingsData));

    // Append files if they are selected
    if (file1Input.files[0]) {
        formData.append('file1', file1Input.files[0]);
    }

    if (file2Input.files[0]) {
        formData.append('file2', file2Input.files[0]);
    }

    fetch('/api/settings_data', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const notif = document.getElementById('notifSuccess');
            notif.textContent = "Sozlamalar muvaffaqiyatli saqlandi!";
            notif.classList.remove('hidden');
            notif.classList.add('flex');
            setTimeout(() => {
                notif.classList.add('hidden');
                notif.classList.remove('flex');
            }, 2000);
        } else {
            alert('Failed to save settings: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while saving settings.');
    });
});

window.onload = function() {
    const loggedInUser = localStorage.getItem('loggedInUser');
    const expirationTime = localStorage.getItem('loginExpiration');

    if (loggedInUser && expirationTime) {
        const currentTime = new Date().getTime();

        if (currentTime > expirationTime) {
            localStorage.removeItem('loggedInUser');
            localStorage.removeItem('loginExpiration');
            alert("Your session has expired. Please log in again.");
            window.location.href = '/admin_panel_login';
        }
    } else {
        window.location.href = '/admin_panel_login';
    }

    fetch('/api/settings_data', {
        method: 'GET',
        headers: {
            'Accept': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.settingsData) {
            console.log('Settings data loaded successfully:', data.settingsData);
            const setting = data.settingsData;

            // Set switches
            for (let i = 1; i <= 6; i++) {
                const switchElement = document.getElementById(String(i));
                if (switchElement !== null && setting[`switch${i}`] !== undefined) {
                    switchElement.checked = setting[`switch${i}`];
                }
            }

            // Set text inputs
            const freeTimeElement = document.getElementById('freeTime');
            if (freeTimeElement) freeTimeElement.value = setting.freeTime || '';

            const freeTimeRepeatElement = document.getElementById('freeTimeRepeat');
            if (freeTimeRepeatElement) freeTimeRepeatElement.value = setting.freeTimeRepeat || '';

            const supportPhoneElement = document.getElementById('supportPhone');
            if (supportPhoneElement) supportPhoneElement.value = setting.phone || '';

            const maxfiylikElement = document.getElementById('MAXFIYLIK');
            if (maxfiylikElement) maxfiylikElement.value = setting.docx || '';

            const entryTitleElement = document.getElementById('entryTitle');
            if (entryTitleElement) entryTitleElement.value = setting.text1 || '';

            const connectButtonTextElement = document.getElementById('connectButtonText');
            if (connectButtonTextElement) connectButtonTextElement.value = setting.text2 || '';

            // Set file previews
            if (setting.file1Preview) {
                const file1Preview = document.getElementById('file1Preview');
                file1Preview.src = setting.file1Preview; // Assign the URL to the `src` attribute
                file1Preview.style.display = 'block';
                document.getElementById('logo-text').textContent = setting.file1Preview.split('/').pop();
            }

            if (setting.file2Preview) {
                const file2Preview = document.getElementById('file2Preview');
                file2Preview.src = setting.file2Preview;
                file2Preview.style.display = 'block';
                document.getElementById('banner-text').textContent = setting.file2Preview.split('/').pop();
            }

            // Additional handling for DOCX preview if needed
        } else {
            console.warn('No settings data found.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
};

function previewFile(inputId, textId) {
    const fileInput = document.getElementById(inputId);
    const textElement = document.getElementById(textId);

    if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        textElement.textContent = file.name;

        if (inputId !== 'terms-upload') { // Only preview images
            const filePreviewId = inputId.replace('Input', 'Preview');
            const filePreview = document.getElementById(filePreviewId);

            const reader = new FileReader();
            reader.onload = function (e) {
                filePreview.src = e.target.result;
                filePreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }
}

function removeFile(previewId) {
    const filePreview = document.getElementById(previewId);
    let fileInputId = '';
    let textId = '';

    if (previewId === 'termsPreview') {
        fileInputId = 'terms-upload';
        textId = 'terms-text';
    } else {
        fileInputId = previewId.replace('Preview', 'Input');
        textId = previewId.replace('Preview', '-text');
    }

    const fileInput = document.getElementById(fileInputId);
    const textElement = document.getElementById(textId);

    if (filePreview) {
        filePreview.src = '';
        filePreview.style.display = 'none';
    }

    if (fileInput) {
        fileInput.value = '';
    }

    if (textElement) {
        textElement.textContent = previewId.includes('terms') ? 'FAYL 1.DOCX' : 'FAYL 1.JPG';
    }
}
