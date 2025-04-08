/**
 * Photo Booth Application
 * 
 * This script handles the photo booth functionality including:
 * - Camera access and photo capture
 * - Countdown timer
 * - Photo strip creation and template application
 * - Download functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const video = document.getElementById('camera');
    const captureBtn = document.getElementById('take-photo');
    const resetBtn = document.getElementById('reset-photos');
    const countdown = document.getElementById('countdown');
    const photoThumbnails = document.getElementById('photo-thumbnails');
    const templateSelect = document.getElementById('template-style');
    const frameSelect = document.getElementById('frame-select');
    const photoStrip = document.getElementById('photo-strip');
    const downloadBtn = document.getElementById('download-strip');
    const printBtn = document.getElementById('print-strip');
    const createStripBtn = document.getElementById('create-strip');
    const startCameraBtn = document.getElementById('start-camera');
    const cameraStatus = document.getElementById('camera-status');
    
    // Print modal elements
    const printModal = new bootstrap.Modal(document.getElementById('printModal'));
    const confirmPrintBtn = document.getElementById('confirm-print');
    const printerSelect = document.getElementById('printer-select');
    
    // Variables
    let stream = null;
    let capturedPhotos = [];
    let requiredPhotos = 3; // Default to 3 photos
    let currentPhoto = 0;
    let countdownTime = 3; // Default countdown time

    // Set required photos based on select
    const numPhotosSelect = document.getElementById('num-photos');
    if (numPhotosSelect) {
        requiredPhotos = parseInt(numPhotosSelect.value);
        numPhotosSelect.addEventListener('change', function() {
            requiredPhotos = parseInt(this.value);
            resetPhotos();
        });
    }

    // Set countdown time based on select
    const countdownTimeSelect = document.getElementById('countdown-time');
    if (countdownTimeSelect) {
        countdownTime = parseInt(countdownTimeSelect.value);
        countdownTimeSelect.addEventListener('change', function() {
            countdownTime = parseInt(this.value);
        });
    }

    // Initialize empty photo thumbnails
    function initializeThumbnails() {
        photoThumbnails.innerHTML = '';
        for (let i = 0; i < requiredPhotos; i++) {
            const thumbContainer = document.createElement('div');
            thumbContainer.classList.add('thumbnail-placeholder', 'me-2', 'mb-2');
            
            const emptyThumb = document.createElement('div');
            emptyThumb.classList.add('empty-thumbnail');
            emptyThumb.textContent = (i + 1).toString();
            
            thumbContainer.appendChild(emptyThumb);
            photoThumbnails.appendChild(thumbContainer);
        }
    }
    
    /**
     * Initialize the camera stream
     */
    async function initCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                }, 
                audio: false
            });
            
            video.srcObject = stream;
            captureBtn.disabled = false;
            cameraStatus.textContent = 'Active';
            cameraStatus.classList.remove('bg-secondary');
            cameraStatus.classList.add('bg-success');
            startCameraBtn.textContent = 'Stop Camera';
        } catch (err) {
            console.error('Error accessing camera:', err);
            cameraStatus.textContent = 'Error';
            cameraStatus.classList.remove('bg-secondary');
            cameraStatus.classList.add('bg-danger');
            alert('Unable to access the camera. Please ensure you have a camera connected and have granted permission to use it.');
        }
    }
    
    /**
     * Stop the camera stream
     */
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            video.srcObject = null;
            captureBtn.disabled = true;
            cameraStatus.textContent = 'Off';
            cameraStatus.classList.remove('bg-success', 'bg-danger');
            cameraStatus.classList.add('bg-secondary');
            startCameraBtn.textContent = 'Start Camera';
        }
    }
    
    /**
     * Start the countdown for photo capture
     */
    function startCountdown() {
        let secondsLeft = countdownTime;
        
        countdown.textContent = secondsLeft;
        countdown.style.display = 'block';
        
        const countdownInterval = setInterval(() => {
            secondsLeft--;
            
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval);
                countdown.style.display = 'none';
                capturePhoto();
            } else {
                countdown.textContent = secondsLeft;
            }
        }, 1000);
    }
    
    /**
     * Capture a photo from the camera stream
     */
    function capturePhoto() {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const photoData = canvas.toDataURL('image/jpeg');
        capturedPhotos.push(photoData);
        addPhotoThumbnail(photoData);
        
        currentPhoto++;
        
        if (currentPhoto < requiredPhotos) {
            // Wait 1 second before starting the next countdown
            setTimeout(() => {
                startCountdown();
            }, 1000);
        } else {
            // All photos captured
            resetBtn.disabled = false;
            captureBtn.disabled = true;
            createStripBtn.disabled = false;
        }
    }
    
    /**
     * Add a captured photo to the thumbnails
     * @param {string} photoData - Base64 encoded photo data
     */
    function addPhotoThumbnail(photoData) {
        const thumbnailContainer = photoThumbnails.children[currentPhoto];
        if (thumbnailContainer) {
            thumbnailContainer.innerHTML = '';
            
            const img = document.createElement('img');
            img.src = photoData;
            img.classList.add('img-thumbnail', 'thumbnail-image');
            
            thumbnailContainer.appendChild(img);
        }
    }
    
    /**
     * Reset all captured photos
     */
    function resetPhotos() {
        capturedPhotos = [];
        currentPhoto = 0;
        
        // Reset thumbnails
        initializeThumbnails();
        
        // Hide photo strip
        photoStrip.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-images fa-4x mb-3"></i><h5>Photos will appear here after capturing</h5></div>';
        
        // Reset buttons
        resetBtn.disabled = true;
        captureBtn.disabled = !stream;
        createStripBtn.disabled = true;
        downloadBtn.disabled = true;
        printBtn.disabled = true;
    }
    
    /**
     * Create a photo strip with the captured photos
     */
    async function createPhotoStrip() {
        try {
            const templateStyle = templateSelect.value;
            const frameId = frameSelect.value;
            
            // Display loading state
            photoStrip.innerHTML = '<div class="text-center py-5"><div class="spinner-border" role="status"></div><p class="mt-2">Creating photo strip...</p></div>';
            
            // Create data for server request
            const data = {
                photos: capturedPhotos,
                templateStyle: templateStyle,
                frameId: frameId ? parseInt(frameId) : null
            };
            
            // Send to server for processing
            const response = await fetch('/process_photo_strip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }
            
            // Create a div to display the photo strip
            photoStrip.innerHTML = '';
            const img = document.createElement('img');
            img.src = 'data:image/jpeg;base64,' + result.photo_strip;
            img.classList.add('img-fluid', 'photo-strip-img');
            photoStrip.appendChild(img);
            
            // Store the photo strip data for download
            photoStrip.dataset.photoStripData = result.photo_strip;
            
            // Enable download and print buttons
            downloadBtn.disabled = false;
            printBtn.disabled = false;
            
        } catch (err) {
            console.error('Error creating photo strip:', err);
            photoStrip.innerHTML = '<div class="alert alert-danger">Error creating photo strip: ' + err.message + '</div>';
        }
    }
    
    /**
     * Download the created photo strip
     */
    async function downloadPhotoStrip() {
        try {
            const photoStripData = photoStrip.dataset.photoStripData;
            
            if (!photoStripData) {
                throw new Error('No photo strip to download');
            }
            
            // Create download link
            const link = document.createElement('a');
            link.download = 'photobooth_strip.jpg';
            link.href = 'data:image/jpeg;base64,' + photoStripData;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (err) {
            console.error('Error downloading photo strip:', err);
            alert('Error downloading photo strip: ' + err.message);
        }
    }
    
    /**
     * Print the photo strip
     */
    async function printPhotoStrip() {
        try {
            const printerName = printerSelect.value;
            const photoStripData = photoStrip.dataset.photoStripData;
            
            if (!photoStripData) {
                throw new Error('No photo strip to print');
            }
            
            // Close the modal
            printModal.hide();
            
            // Display loading message
            const loadingToast = document.createElement('div');
            loadingToast.className = 'toast align-items-center text-white bg-info border-0 position-fixed bottom-0 end-0 m-3';
            loadingToast.setAttribute('role', 'alert');
            loadingToast.setAttribute('aria-live', 'assertive');
            loadingToast.setAttribute('aria-atomic', 'true');
            loadingToast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-spinner fa-spin me-2"></i> Memproses dan mengirim ke printer...
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            document.body.appendChild(loadingToast);
            const toast = new bootstrap.Toast(loadingToast);
            toast.show();
            
            // Send print job to server
            const response = await fetch('/print_photo_strip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    photoStrip: photoStripData,
                    printerName: printerName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Error creating printable PDF');
            }
            
            const result = await response.json();
            
            // Remove loading toast
            toast.hide();
            setTimeout(() => {
                document.body.removeChild(loadingToast);
            }, 500);
            
            // Show a success toast
            const successToast = document.createElement('div');
            successToast.className = 'toast align-items-center text-white bg-success border-0 position-fixed bottom-0 end-0 m-3';
            successToast.setAttribute('role', 'alert');
            successToast.setAttribute('aria-live', 'assertive');
            successToast.setAttribute('aria-atomic', 'true');
            successToast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-check-circle me-2"></i> Foto telah dikirim ke printer dengan kualitas tinggi!
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            document.body.appendChild(successToast);
            const successToastObj = new bootstrap.Toast(successToast);
            successToastObj.show();
            
            // Setup cleanup
            setTimeout(() => {
                successToastObj.hide();
                setTimeout(() => {
                    document.body.removeChild(successToast);
                }, 500);
            }, 5000);
            
        } catch (err) {
            console.error('Error printing photo strip:', err);
            alert('Error mencetakkan foto: ' + err.message);
        }
    }
    
    // Initialize the thumbnails on page load
    initializeThumbnails();
    
    // Event Listeners
    startCameraBtn.addEventListener('click', function() {
        if (stream) {
            stopCamera();
        } else {
            initCamera();
        }
    });
    
    captureBtn.addEventListener('click', function() {
        startCountdown();
        captureBtn.disabled = true;
    });
    
    resetBtn.addEventListener('click', resetPhotos);
    
    createStripBtn.addEventListener('click', createPhotoStrip);
    
    downloadBtn.addEventListener('click', downloadPhotoStrip);
    
    printBtn.addEventListener('click', function() {
        // Show print modal
        printModal.show();
    });
    
    confirmPrintBtn.addEventListener('click', printPhotoStrip);
    
    // Clean up when the page is unloaded
    window.addEventListener('beforeunload', stopCamera);
});
