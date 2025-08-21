const removedFiles = new Set();

function previewImage(inputId, previewVideoId, previewImageId, durationId) {
    console.log(`previewImage called with inputId: ${inputId}, videoId: ${previewVideoId}, imageId: ${previewImageId}, durationId: ${durationId}`);
    const fileInput = document.getElementById(inputId);
    const previewVideo = document.getElementById(previewVideoId);
    const previewImage = document.getElementById(previewImageId);
    const durationField = document.getElementById(durationId);

    if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        const fileType = file.type;
        console.log('Selected file:', file);
        console.log('File type:', fileType);

        if (fileType.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function (e) {
                console.log('Image preview URL:', e.target.result);
                previewVideo.style.display = 'none'; // Hide video preview
                previewImage.style.display = 'block'; // Show image preview
                previewImage.src = e.target.result; // Set image src
                if (durationField) {
                    durationField.value = 0; // Reset duration for images
                }
            };
            reader.readAsDataURL(file);
        } else if (fileType.startsWith('video/')) {
            const url = URL.createObjectURL(file);
            console.log('Video preview URL:', url);
            previewImage.style.display = 'none'; // Hide image preview
            previewVideo.style.display = 'block'; // Show video preview
            previewVideo.src = url; // Set video src
            previewVideo.style.width = '100%'; // Set video width
            previewVideo.style.height = 'auto'; // Maintain aspect ratio

            // Get the video duration after metadata is loaded
            previewVideo.onloadedmetadata = function () {
                console.log('Video duration:', previewVideo.duration);
                if (durationField) {
                    durationField.value = Math.round(previewVideo.duration); // Set duration in seconds
                }
            };
        } else {
            console.error('Unsupported file type:', fileType);
            previewImage.style.display = 'none';
            previewVideo.style.display = 'none';
            if (durationField) {
                durationField.value = 0;
            }
        }
    } else {
        console.error('No file selected or fileInput is null');
    }
}

function removeFile(textId) {
    const index = textId.match(/\d+/)[0]; 
    const previewVideoId = `file${index}Preview`;
    const previewImageId = `file${index}ImagePreview`;
    const fileInputId = `file${index}Input`;
    const durationFieldId = `duration${index}`;

    const previewVideo = document.getElementById(previewVideoId);
    const previewImage = document.getElementById(previewImageId);
    const fileInput = document.getElementById(fileInputId);
    const durationField = document.getElementById(durationFieldId);

    if (previewVideo) {
        previewVideo.style.display = 'none';
        previewVideo.src = '';
    }

    if (previewImage) {
        previewImage.style.display = 'none';
        previewImage.src = '';
    }

    if (fileInput) {
        fileInput.value = '';
    }

    if (durationField) {
        durationField.value = 0;
    }

    // Add to the set of removed files for tracking
    removedFiles.add(index);
    
    // Mark the file as removed for the save function
    fileInput.setAttribute('data-removed', 'true');
}

document.getElementById('saqlashBtn').addEventListener('click', function() {
    saveAllData();
});

async function saveAllData() {
    const formData = new FormData();
    
    const reklamaData = {
        id: 1, // Ensure this ID is dynamic if handling multiple records
        duration1: document.getElementById('duration1').value,
        duration2: document.getElementById('duration2').value,
        duration3: document.getElementById('duration3').value,
        duration4: document.getElementById('duration4').value,
        duration5: document.getElementById('duration5').value,
        date_start1: document.getElementById('date_start1').value,
        date_start2: document.getElementById('date_start2').value,
        date_start3: document.getElementById('date_start3').value,
        date_start4: document.getElementById('date_start4').value,
        date_start5: document.getElementById('date_start5').value,
        date_end1: document.getElementById('date_end1').value,
        date_end2: document.getElementById('date_end2').value,
        date_end3: document.getElementById('date_end3').value,
        date_end4: document.getElementById('date_end4').value,
        date_end5: document.getElementById('date_end5').value,
        check1: document.getElementById('check1').checked,
        check2: document.getElementById('check2').checked,
        check3: document.getElementById('check3').checked,
        check4: document.getElementById('check4').checked,
        check5: document.getElementById('check5').checked,
        rek: document.getElementById('reklamalarHolati').checked,
        reko: document.getElementById('reklamaniOtkazib').checked
    };

    // Add removed files information to reklamaData object
    for (let i = 1; i <= 5; i++) {
        const fileInput = document.getElementById(`file${i}Input`);
        if (fileInput.getAttribute('data-removed') === 'true' || removedFiles.has(i.toString())) {
            // Add explicit deletion flag for backend to process
            reklamaData[`delete_file${i}`] = true;
        }
    }

    formData.append('reklamaData', JSON.stringify(reklamaData));

    const videoFileInputs = ['file1Input', 'file2Input', 'file3Input', 'file4Input', 'file5Input'];

    for (const [index, inputId] of videoFileInputs.entries()) {
        const inputElement = document.getElementById(inputId);
        const fileNum = index + 1;

        if (inputElement.getAttribute('data-removed') === 'true' || removedFiles.has(fileNum.toString())) {
            // Explicitly mark this file for deletion in the formData
            formData.append(`file${fileNum}Path`, 'DELETE_FILE');
            continue;
        }

        if (inputElement.files.length > 0) {
            const file = inputElement.files[0];
            try {
                const uploadResponse = await uploadFile(file, `file${fileNum}ad`);
                if (uploadResponse.success) {
                    // Append the file path received from the upload
                    formData.append(`file${fileNum}Path`, uploadResponse.filePath);
                } else {
                    console.error(`Failed to upload file: ${file.name}`);
                    alert(`Failed to upload file: ${file.name}`);
                    return; // Stop execution if an upload fails
                }
            } catch (error) {
                console.error(`Error uploading file ${file.name}:`, error);
                alert(`Error uploading file ${file.name}.`);
                return; // Stop execution if an upload fails
            }
        } else {
            // If no file is selected and it's not marked for deletion, 
            // pass an empty string (keep existing file)
            formData.append(`file${fileNum}Path`, '');
        }
    }

    const apiUrl = '/api/reklama_data';

    fetch(apiUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'Accept': 'application/json',
        },
        mode: 'cors'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('header-content').style.display = 'none';
            document.getElementById('container').style.display = 'none';
            document.getElementById('successMessage').style.display = 'flex';
            removedFiles.clear();

            setTimeout(function() {
                window.location.href = '/admin_panel_main';
            }, 1500);
        } else {
            alert('Failed to save data: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while saving data.');
    });
}

async function uploadFile(file, filename) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', filename);
    
    console.log("Uploading file:", file, "with filename:", filename);
    console.log("File size:", Math.round(file.size / 1024 / 1024 * 100) / 100, "MB");

    const uploadApiUrl = '/api/upload';
    
    // Add retry logic
    let retries = 3;
    while (retries > 0) {
        try {
            const response = await fetch(uploadApiUrl, {
                method: 'POST',
                body: formData,
                // Add timeout to prevent hanging requests
                timeout: 60000 // 60 seconds
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            retries--;
            console.error(`Error uploading file (retries left: ${retries}):`, error);
            if (retries <= 0) {
                return { success: false, error: error.message };
            }
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}

window.onload = async function() {
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

    try {
        const adsApiUrl = '/api/reklama_data';
        const response = await fetch(adsApiUrl);

        if (!response.ok) {
            throw new Error('Failed to fetch ads data');
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Unknown error occurred');
        }

        const reklamaData = data.reklamaData;

        if (reklamaData.length > 0) {
            // Assuming we are dealing with a single reklama entry (id=1)
            const reklama = reklamaData.find(r => r.id === 1) || reklamaData[0];

            // Iterate through file1Preview to file5Preview
            for (let i = 1; i <= 5; i++) {
                const filePath = reklama[`file${i}Preview`];
                const previewVideo = document.getElementById(`file${i}Preview`);
                const previewImage = document.getElementById(`file${i}ImagePreview`);

                if (filePath) {
                    const fileExtension = filePath.split('.').pop().toLowerCase();

                    if (['mp4', 'webm', 'ogg', 'mov'].includes(fileExtension)) {
                        previewVideo.src = filePath;
                        previewVideo.style.display = 'block';
                        previewImage.style.display = 'none';
                    } else if (['png', 'jpg', 'jpeg', 'gif'].includes(fileExtension)) {
                        previewImage.src = filePath;
                        previewImage.style.display = 'block';
                        previewVideo.style.display = 'none';
                    } else {
                        console.error(`Unsupported file type: ${fileExtension}`);
                        previewVideo.style.display = 'none';
                        previewImage.style.display = 'none';
                    }
                } else {
                    previewVideo.style.display = 'none';
                    previewImage.style.display = 'none';
                }
            }

            // Populate form fields with reklama data
            document.getElementById('duration1').value = reklama.duration1 || 0;
            document.getElementById('duration2').value = reklama.duration2 || 0;
            document.getElementById('duration3').value = reklama.duration3 || 0;
            document.getElementById('duration4').value = reklama.duration4 || 0;
            document.getElementById('duration5').value = reklama.duration5 || 0;

            document.getElementById('date_start1').value = reklama.date_start1 || '';
            document.getElementById('date_start2').value = reklama.date_start2 || '';
            document.getElementById('date_start3').value = reklama.date_start3 || '';
            document.getElementById('date_start4').value = reklama.date_start4 || '';
            document.getElementById('date_start5').value = reklama.date_start5 || '';

            document.getElementById('date_end1').value = reklama.date_end1 || '';
            document.getElementById('date_end2').value = reklama.date_end2 || '';
            document.getElementById('date_end3').value = reklama.date_end3 || '';
            document.getElementById('date_end4').value = reklama.date_end4 || '';
            document.getElementById('date_end5').value = reklama.date_end5 || '';

            document.getElementById('check1').checked = reklama.check1 || false;
            document.getElementById('check2').checked = reklama.check2 || false;
            document.getElementById('check3').checked = reklama.check3 || false;
            document.getElementById('check4').checked = reklama.check4 || false;
            document.getElementById('check5').checked = reklama.check5 || false;

            document.getElementById('reklamalarHolati').checked = reklama.rek || false;
            document.getElementById('reklamaniOtkazib').checked = reklama.reko || false;
        } else {
            console.warn('No reklama data found.');
        }
    } catch (error) {
        console.error('Error fetching ads:', error);
        alert('Failed to load advertisements. Please try again later.');
    }
};