// Initialize socket connection
let socket;

// DOM Elements
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const gestureStatus = document.getElementById('gesture-status');
const gestureList = document.getElementById('gesture-list');
const recordButton = document.querySelector('.record-gesture');
const startTrainingButton = document.querySelector('.start-training');
const flipButton = document.querySelector('.flip-btn');
const gestureAction = document.querySelector('.gesture-action');
const actionInput = document.querySelector('.action-input');
const gestureName = document.querySelector('.gesture-name');
const trainingModal = document.getElementById('training-modal');
const progressBar = document.querySelector('.progress-bar');
const progressText = document.querySelector('.progress-text');

// Global variables
let isRecording = false;
let isCameraActive = false;
let isTrainingMode = false;
let cameraStream = null;
let trainingData = [];
let frameCount = 0;

// Initialize Three.js background
function initBackground() {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    const container = document.querySelector('.background-3d');
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // Create particles
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 5000;
    const posArray = new Float32Array(particlesCount * 3);

    for(let i = 0; i < particlesCount * 3; i++) {
        posArray[i] = (Math.random() - 0.5) * 5;
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.005,
        color: 0x00f3ff
    });

    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);

    camera.position.z = 2;

    function animate() {
        requestAnimationFrame(animate);
        particlesMesh.rotation.y += 0.001;
        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// Initialize socket connection with debugging
function initializeSocket() {
    console.log('Initializing WebSocket connection...');
    socket = io();
    
    socket.on('connect', () => {
        console.log('WebSocket Connected - Socket ID:', socket.id);
        gestureStatus.textContent = 'Connected to server';
    });

    socket.on('video_frame', (data) => {
        if (!isTrainingMode) {
            // Live prediction mode
            console.log(`Frame received. Gesture: ${data.gesture_data.gesture}`);
            
            // Update video frame
            const img = new Image();
            img.onerror = (error) => {
                console.error('Error loading frame:', error);
            };
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };
            img.src = `data:image/jpeg;base64,${data.frame}`;

            // Update gesture information
            if (data.gesture_data.gesture !== 'none') {
                const message = `${data.gesture_data.gesture} (${(data.gesture_data.confidence * 100).toFixed(1)}%)`;
                gestureStatus.textContent = message;
                gestureStatus.style.color = '#00f3ff';
            }
        }
    });

    socket.on('training_progress', (data) => {
        if (isTrainingMode) {
            // Update training progress
            const progress = (data.frames_collected / data.total_frames) * 100;
            progressBar.style.width = `${progress}%`;
            progressText.textContent = `${Math.round(progress)}%`;
            
            if (data.frames_collected >= data.total_frames) {
                finishTraining();
            }
        }
    });

    socket.on('training_complete', (data) => {
        console.log('Training completed:', data);
        addGestureToList(data.gesture_name, data.action);
        finishTraining();
    });

    socket.on('disconnect', () => {
        console.error('WebSocket Disconnected');
        gestureStatus.textContent = 'Disconnected from server';
        gestureStatus.style.color = '#ff0000';
    });

    socket.on('error', (error) => {
        console.error('WebSocket Error:', error);
        gestureStatus.textContent = 'Connection error';
        gestureStatus.style.color = '#ff0000';
    });
}

// Camera controls with improved error handling
async function startCamera() {
    try {
        console.log('Starting camera...');
        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            }
        };

        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('Camera stream obtained:', cameraStream.getVideoTracks()[0].getSettings());
        
        video.srcObject = cameraStream;
        video.onloadedmetadata = () => {
            console.log('Video metadata loaded:', {
                width: video.videoWidth,
                height: video.videoHeight
            });
        };
        
        await video.play();
        console.log('Video playback started');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        isCameraActive = true;
        if (!isTrainingMode) {
            console.log('Starting live prediction mode');
            socket.emit('start_stream');
            gestureStatus.textContent = 'Camera active - Starting gesture recognition';
        } else {
            console.log('Starting training mode');
            socket.emit('start_training', {
                gesture_name: gestureName.value,
                action: actionInput.value
            });
            showTrainingModal();
        }
        
        recordButton.innerHTML = '<span class="button-text">Stop Camera</span><span class="button-icon">⏹</span>';
    } catch (error) {
        console.error('Camera Error:', error);
        gestureStatus.textContent = `Camera error: ${error.message}`;
        gestureStatus.style.color = '#ff0000';
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        if (!isTrainingMode) {
            console.log('Stopping live prediction');
            socket.emit('stop_stream');
        } else {
            console.log('Stopping training');
            socket.emit('stop_training');
            hideTrainingModal();
        }
        isCameraActive = false;
        gestureStatus.textContent = 'Camera stopped';
        recordButton.innerHTML = '<span class="button-text">Start Camera</span><span class="button-icon">🎥</span>';
    }
}

function showTrainingModal() {
    trainingModal.style.display = 'flex';
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
}

function hideTrainingModal() {
    trainingModal.style.display = 'none';
    isTrainingMode = false;
}

function finishTraining() {
    hideTrainingModal();
    stopCamera();
    gestureName.value = '';
    actionInput.value = '';
}

function addGestureToList(name, action) {
    const gestureItem = document.createElement('div');
    gestureItem.className = 'gesture-item';
    gestureItem.innerHTML = `
        <div class="gesture-info">
            <strong>${name}</strong>
            <span>${action}</span>
        </div>
        <button class="cyber-button delete-gesture" data-gesture="${name}">
            <span class="button-icon">🗑️</span>
        </button>
    `;
    gestureList.appendChild(gestureItem);
}

// Event listeners
recordButton.addEventListener('click', () => {
    if (!isCameraActive) {
        startCamera();
    } else {
        stopCamera();
    }
});

startTrainingButton.addEventListener('click', () => {
    if (!gestureName.value || !actionInput.value) {
        alert('Please enter both gesture name and action');
        return;
    }
    isTrainingMode = true;
    startCamera();
});

flipButton.addEventListener('click', async () => {
    if (cameraStream) {
        const currentFacingMode = cameraStream.getVideoTracks()[0].getSettings().facingMode;
        const newFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
        
        stopCamera();
        
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: newFacingMode
                }
            });
            video.srcObject = cameraStream;
            await video.play();
            if (!isTrainingMode) {
                socket.emit('start_stream');
            } else {
                socket.emit('start_training', {
                    gesture_name: gestureName.value,
                    action: actionInput.value
                });
            }
        } catch (error) {
            console.error('Camera Flip Error:', error);
            gestureStatus.textContent = `Camera flip error: ${error.message}`;
            gestureStatus.style.color = '#ff0000';
        }
    }
});

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing application...');
    initializeSocket();
    initBackground();
    gestureStatus.textContent = 'Ready to start';
}); 